# Money Master — Stage 3 Design: Spouse Character Model

**Status:** DESIGN ONLY. No code/DB/UI/AI/negotiation change; nothing committed. Builds on the approved economic archetypes, the Stage-2 festival formula (`Ask = round500(base_k × HHI × Posture × importance × CharAdj)`, base_k 0.62 / importance 1.08 / `CharAdj` placeholder = 1.0), and the existing deterministic negotiation engine (`negotiation_service.evaluate`, floor = `ask × negotiation_min_ratio(archetype, satisfaction)`).

**Two design commitments up front (both are the point of this stage):**
1. **Frugality is NOT a character trait.** It is already the *economic archetype* (`expense_mod` → `Posture`). Adding a "frugality" trait would duplicate exactly what the brief forbids. The character layer models only what economics does *not*: social/family/relational/flexibility dimensions.
2. **The character can drive the INITIAL BUDGET today with zero engine change** (via the `CharAdj` seam in the future `festival_service`). Making the character drive the **negotiation floor and arguments** requires a *small, backward-compatible* extension to `evaluate()` — designed here, **not** done now, and phased so nothing forces a `negotiation_service` rewrite.

---

## 1. Character Model

```
Economic Archetype (Saver/Earner/Investor/Anchor)   ← income, expense_mod, assets  (existing, unchanged)
        +
Character Traits (5)                                ← social/relational disposition (NEW layer)
        +
[Family Background]                                 ← folded into traits for v1 (§4)
        +
Live Economic Context (cash/EF/debt/goals)          ← the real books (existing game state)
        +
Event Context (festival importance, month)          ← Stage-2 constant
        ↓  deterministic
Spouse Behaviour (initial budget · floor · flexibility · which arguments land · voice)
```

The character sits **above** the economic archetype and is **independent** of it: an Earner can be status-driven *or* prudent-hearted; a Saver can be traditional *or* modern. That independence is what lets "two people in the same economic bracket behave oppositely."

## 2. Core Traits (evaluated and pruned to 5)

The brief offered six candidates. My evaluation:

| Candidate | Keep? | Why |
|---|---|---|
| frugality / spending orientation | **DROP** | Already the economic archetype (`expense_mod`/`Posture`). Duplicates economics. |
| financial prudence | **KEEP → PRU** | Distinct from spend-level: how much she weights the household's *future/safety* → governs which financial arguments land. |
| social-status sensitivity | **KEEP → STA** | Reputation/appearance → raises budget & floor; countered by "no one will judge" framing. |
| family-tradition orientation | **KEEP → FAM** | Ritual/family duty → raises budget & floor; countered by "family will understand / reallocate to a family need." Kept *separate* from STA because it routes to a **different winning argument**. |
| flexibility / compromise | **KEEP → FLX** | How far she moves → counteroffer distance + accept threshold. |
| emotional importance of event | **FOLD** | Overlaps STA/FAM/REL; folded to avoid a near-duplicate lever. |
| (added) relational sensitivity | **KEEP → REL** *(optional)* | Response to tone/warmth/fairness. Keep if you want respect/tone to matter; droppable to reach 4 traits. |

**Final five traits (0–100, authored in the five bands from Stage 1B-style scaling: VL 10 / L 30 / M 50 / H 70 / VH 90):**

| Trait | Code | Effect on **festival expectation** | Effect on **negotiation flexibility** | Effect on **conversation style** |
|---|---|---|---|---|
| **Financial Prudence** | PRU | slightly ↓ ask | ↑ willingness to accept a *well-argued* cut | cites future/safety; persuaded by real numbers |
| **Status Sensitivity** | STA | ↑ ask, ↑ floor | ↓ (defends visible spend) | appearance/what-people-think; yields only to "tasteful, not showy" |
| **Family & Tradition Weight** | FAM | ↑ ask, ↑ floor | ↓ on ritual grounds | duty/family; yields to "honour it simply / redirect to a family need" |
| **Flexibility** | FLX | — | ↑↑ counteroffer travel; ↓ accept threshold | collaborative, "let's find a number" |
| **Relational Sensitivity** | REL | — | tone bonus (warm) / penalty (hostile) | warmth-reciprocating; hurt by ultimatums |

Trait low/med/high behaviour, using PRU as the worked example:
- **Low PRU:** *"₹90,000 is fine — we should enjoy it, we only do this once."*
- **Med PRU:** *"Let's not overdo it, but this matters — somewhere sensible."*
- **High PRU:** *"₹90,000 is too much right now — protect the buffer first, celebrate within it."*

## 3. Ethics / Values

**Recommendation: ethics are NOT a separate vector — they are argument *receptivities derived from the five traits*.** A spouse who "believes family celebrations should be generous" is simply high **FAM**; one who "believes in prudence" is high **PRU**. Modelling ethics as a second authored vector would double-count the traits and double the balancing surface. Each *argument channel* the player can use has a fixed **resonance** with the traits:

| Player argument channel | Objective strength (engine reads the **real books**) | Resonates with |
|---|---|---|
| `necessity` (EF thin / debt / liquidity) | high when EF < target or debt is real | **PRU +**, STA − |
| `affordability` (cash flow can't take it) | high when the ask genuinely strains cash | **PRU +**, (STA/FAM resist) |
| `long_term_goal` (house / child / retirement) | high when a real goal is funded | **PRU +** |
| `fairness` (shared sacrifice / reasonable) | fixed-moderate | **REL +, PRU +** |
| `family_reallocation` (redirect to a real family need) | high if a family need exists | **FAM +** |
| `status_free` (tasteful, no one needs impressing) | fixed | **STA −, FAM −** (can backfire if high) |

**No value is universally good/bad:** the identical true statement ("cut it, our buffer is thin") *persuades* a prudent, low-status spouse and *offends* a status/family-driven one. That asymmetry is the educational core — you must read the person.

## 4. Background Variables

**Recommendation for v1: fold family background into the trait authoring — do not add separate demographic fields.** A "traditional, status-conscious family" spouse is simply authored with high FAM + high STA; the behavioural purpose (higher ask, higher floor, family-reallocation argument lands) is already fully served by the traits for a *single* festival. Adding `family_economic_level`, `urban/rural`, etc. as separate variables would be realism-for-its-own-sake with no distinct behavioural lever — which the brief forbids.

**Add a separate family-background block ONLY if** a future stage wants family pressure to vary *dynamically* (e.g., "the in-laws arrive" temporarily boosts FAM before a specific event). Designed seam: an optional `family_context` modifier that shifts FAM/STA for one event; **out of scope for v1.**

## 5. Economic Context (which live variables affect what)

Distinct from both the archetype (income/expense_mod/assets) and the traits (disposition), the **live household state** enters at three precise points — and *only* these:

| Live variable | 1. Initial expectation | 2. Willingness to compromise | 3. Arguments |
|---|---|---|---|
| Household **income** (HHI) | **Yes** (Stage-2 anchor) | no | no |
| **Cash** on hand | **No** (by design — would kill the conflict) | **Yes** (as argument strength) | **Yes** (`affordability`) |
| **Emergency fund** vs target | **No** | **Yes** | **Yes** (`necessity`) |
| **Debt** / obligations | **No** | **Yes** | **Yes** (`necessity`) |
| **Goals** (house/child) | **No** | **Yes** | **Yes** (`long_term_goal`) |

So the **initial expectation** is anchored to *income* + traits (STA/FAM) — never to current liquidity, so the spouse can over-ask and create the conflict. The player's *actual* cash/EF/debt enters only as the **objective strength of the arguments** during negotiation (you can't lie past the engine — it checks the books). No duplication of the archetype: archetype = who she economically is; traits = her disposition; live context = today's books.

## 6. Behaviour Rules (deterministic)

The character produces four outputs; **initial budget and floor use *different* trait weightings** (the brief's explicit requirement — not the same multiplier):

```
INITIAL BUDGET    ← economics (Posture, HHI) × CharAdj(STA, FAM, PRU)          [§7]
NEGOTIATION FLOOR ← archetype base ratio + FloorAdj(FLX↓, STA↑, FAM↑)          [§8]
FLEXIBILITY/COUNTER ← FLX (+ satisfaction, + round pressure)                   [§8]
ARGUMENT OUTCOME  ← Σ argument_strength(books) × resonance(traits)             [§8, phase 3c]
```

A spouse can therefore be **high-ask but flexible** (opens big, folds fast) or **modest-ask but immovable** (opens fair, won't budge) — decoupled, which the single archetype ratio could not express.

## 7. Initial-Budget Influence (`CharAdj` — ships with NO engine change)

Fills the Stage-2 placeholder:

```
CharAdj = clamp( 1 + 0.15×(STA−50)/50 + 0.15×(FAM−50)/50 − 0.08×(PRU−50)/50 , 0.85 , 1.25 )
```

Status and family push the ask up (~+15% each at VH); prudence pulls it gently down. This is computed in the future `festival_service`, multiplied into the Stage-2 formula — **`negotiation_service.py` untouched.** It directly fixes the Stage-2 finding that three archetypes clustered: character now separates them (see §10 numbers).

## 8. Negotiation Influence (needs a small, backward-compatible engine extension — phased)

- **Floor (Phase 3b):**
  `FloorAdj: char_floor_ratio = clamp( archetype_ratio + 0.15×(STA−50)/50 + 0.10×(FAM−50)/50 − 0.20×(FLX−50)/50 , 0.35 , 0.90 )`
  Flexibility lowers the floor (more room); status/family raise it. To reach `evaluate()`, this is passed **through the proposal dict** as an optional `floor_ratio_override`; `evaluate` uses it *if present*, else falls back to the current `negotiation_min_ratio` — a **backward-compatible** one-line read, designed here, approval-gated.
- **Counteroffer (Phase 3b):** reuse the existing counter math; `Movement` gains a `+FLX/α` term so flexible spouses travel further. Bounded by the floor, monotonic, non-random.
- **Arguments (Phase 3c):** the effective floor/threshold is reduced by a persuasion score `P = Σ argument_strength(books) × resonance(traits)`. This is where "arguments change her mind" becomes *mechanical* — and it requires the AI argument-tag extraction (§12) plus the persuasion term in the engine. Largest piece; last.

## 9. Four Example Spouses

Economic archetype (existing) × character trait vector (new). Note "frugal" in the brief maps to the **Saver economics**, not a trait — demonstrating the dedup.

| Spouse | Economic | PRU | STA | FAM | FLX | REL | CharAdj |
|---|---|---:|---:|---:|---:|---:|---:|
| **A** Saver + Traditional | Saver | 70 | 30 | 85 | 55 | 65 | 1.01 |
| **B** Earner + Status | Earner | 35 | 90 | 55 | 40 | 45 | 1.16 |
| **C** Investor + Prudent | Investor | 90 | 40 | 35 | 65 | 60 | 0.86 |
| **D** Anchor + Family | Anchor | 60 | 45 | 80 | 50 | 70 | 1.06 |

## 10. Example Conversations

Initial ask = `round500(0.62 × HHI × Posture × 1.08 × CharAdj)`. **Character is what finally separates the four** (compare to the Stage-2 no-character asks in parentheses — the Investor drops, the Earner jumps):

| Spouse | Initial ask (Stage-2 no-char) | Player proposal | Reaction | Counter | Final range | **Why it differs** |
|---|---:|---|---|---:|---:|---|
| **A** Saver+Trad | **₹65,500** (₹64,500) | ₹40,000, "let's keep it small" | FAM high → resists cutting the ritual; but Saver economics + moderate FLX | ~₹52,000 | ₹48–55k | Yields to **`family_reallocation`** ("honour it simply, send the rest to your parents") + respect — not to a cold cut |
| **B** Earner+Status | **₹103,500** (₹89,500) | ₹60,000, "we can't justify this" | STA 90, PRU 35 → affordability barely lands (books are fine); firm | ~₹92,000 | ₹88–95k | Only **`status_free`** ("tasteful, not showy") + warm tone dents her; hardest, smallest movement |
| **C** Investor+Prudent | **₹57,000** (₹66,000) | ₹40,000, "protect the buffer" | PRU 90 + engine confirms EF thin → strong resonance; FLX 65 | ~₹44,000 | ₹42–46k | She half-argues the cut herself; **`necessity`/`long_term_goal`** land hard; easiest |
| **D** Anchor+Family | **₹74,500** (₹70,500) | warm, "meaningful but modest" | REL 70 → tone lands; FAM 80 → family framing works | ~₹62,000 | ₹58–65k | Moves for **warmth + family meaning**, not for hard numbers |

Different keys for different locks: financial logic opens C, reputation-framing opens B, family-reallocation opens A, warmth opens D. That is the lesson and the replay value.

## 11. Deterministic Engine Interface

```
festival_service.generate_festival_budget(economic_state, event, traits)
    → proposal = { archetype_id, kind:'festival', ask:<CharAdj-adjusted>,
                   floor_ratio_override:<char_floor_ratio>,   # Phase 3b (optional key)
                   ... }
                                     │
player message ─▶ AI extract ─▶ { intent, amount, argument_tags[], tone }  (closed schema, §12)
                                     │
negotiation_service.evaluate(intent, params, proposal, round, satisfaction, player_cash [, persuasion])
    • Phase 3a: reads proposal.ask; floor from archetype (UNCHANGED engine)
    • Phase 3b: reads proposal.floor_ratio_override if present (1-line backward-compatible add)
    • Phase 3c: subtracts persuasion P from the effective threshold (arguments bite)
                                     │
    → { outcome: accept/counter/reject, agreed_amount, reason }
                                     │
AI narrate ─▶ spouse voices the ENGINE's decision, in character (§12)
```

**Phase 3a needs no `negotiation_service` edit.** 3b/3c need only *additive, backward-compatible* parameters (absent → today's behaviour). No rewrite, ever.

## 12. AI Interface

- **AI MAY:** read the player's free text → map to the closed schema `{ intent, amount, argument_tags ⊂ {necessity, affordability, long_term_goal, fairness, family_reallocation, status_free}, tone ∈ {warm, neutral, cold} }`; voice the spouse's personality; explain the engine's decision naturally.
- **AI MUST NOT:** invent or change any rupee amount, the floor, the persuasion score, or the outcome; write state; override a trait. Ambiguity is **rejected for clarification**; a **confirmation gate** shows the extracted offer before the engine runs. (Exactly the ADR-014 boundary.)
- **Objective strength stays with the engine** (it checks the books); the AI only *labels* which arguments were made. So a false "we're broke" gets a low strength regardless of eloquence — English fluency can't buy money.

## 13. Data Structure Proposal (no new DB table for v1)

Attach a character profile to each of the four marriage candidates, as constants alongside `ARCHETYPES` (the DB `spouse_archetypes` mirror can carry it later; no schema change now):

```python
CHARACTER_PROFILES = {           # keyed by the candidate the player marries
  "saver":    {"PRU":70,"STA":30,"FAM":85,"FLX":55,"REL":65},
  "earner":   {"PRU":35,"STA":90,"FAM":55,"FLX":40,"REL":45},
  "investor": {"PRU":90,"STA":40,"FAM":35,"FLX":65,"REL":60},
  "anchor":   {"PRU":60,"STA":45,"FAM":80,"FLX":50,"REL":70},
}
```

**v1 pairs one authored character per economic archetype** (4 candidates, no UI change). *Conceptually the layers are independent* — a later content expansion can decouple them (economic × character → more candidates, and true "two doctors differ" variety) by seeding a character pick separately at marriage. Storing traits as data (not code) keeps them authorable and EV-checkable.

## 14. Risks

1. **EV-balance gate (critical).** The festival + `CharAdj` add a *new* one-time cost that `marriage_ev_sim.py` does **not** currently model. Before shipping, the sim must include the festival, and character-inflated asks (e.g. Earner+Status ₹103.5k) must be checked so a high-status spouse isn't a **trap choice**. This is a hard gate, same standard as Stage 1B.
2. **Balancing surface grows.** 5 traits × 4 candidates × the festival is a bigger surface than the flat archetype. Author conservatively; keep `CharAdj` clamped (0.85–1.25) and floors clamped (0.35–0.90).
3. **Engine-edit boundary.** Full character negotiation needs the 3b/3c extensions; if you want *zero* `negotiation_service` change forever, character can only affect the **ask** (3a) — a weaker but real improvement. Decide the boundary explicitly.
4. **AI misread → money.** Mitigated by closed schema + confirmation gate + offline parser (existing) + engine-owned argument strength.
5. **Player "solves" a spouse.** Intended (financial-literacy lesson), *provided* arguments must be true (engine checks books) and no single phrase beats everyone (trait-varied resonance guarantees this).
6. **Cultural care.** Gender-neutral spouses; some spouses more prudent than the player (Investor+Prudent, Saver); festival positions are legitimate values trade-offs, not "spouse wants to waste money"; no dowry mechanics.

## 15. Recommended Minimal Model

- **5 traits:** PRU, STA, FAM, FLX, REL (drop REL to reach 4 if you want the absolute minimum; tone stops mattering).
- **Ethics = trait-derived argument receptivity** (no separate vector).
- **Family background folded into traits** for v1.
- **Ship in phases:**
  - **Phase 3a (recommended first, zero engine edit):** traits drive the **initial festival budget** via `CharAdj` in `festival_service`. Spouses now open at characterful, differentiated budgets; negotiation firmness stays archetype-based. Biggest felt improvement for the least risk.
  - **Phase 3b (small, backward-compatible):** `floor_ratio_override` in the proposal so traits (FLX/STA/FAM) drive the **floor** — decoupled from the ask.
  - **Phase 3c (largest, future):** AI argument-tags + engine **persuasion** so arguments mechanically move her — the full "read the person" negotiation.
- **Gate every phase on the extended EV sim.**

---

*STOP — design only. No code/DB/UI/AI/negotiation changes. Awaiting approval of the trait set (5 vs 4), the ethics/background decisions, the phase boundary (how far into 3b/3c you want to go), and confirmation that the festival must enter the EV sim before implementation.*
