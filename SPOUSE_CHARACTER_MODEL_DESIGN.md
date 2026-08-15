# Money Master — Spouse Characterization & AI Negotiation: Design Specification

**Status:** DESIGN ONLY. No code, schema, or economics changed. Awaiting approval of the character model before any implementation.
**Grounding:** This design deliberately sits on top of what already exists — `ADR-014` (spouse negotiation: rules decide money, AI only narrates), `MARRIAGE_SYSTEM_DESIGN.md` (EV-balanced archetypes, deterministic reveal), and the shipped deterministic `negotiation_service`. It **extends** those, it does not replace their principles.

---

## 0. Two decisions I need you to make (surfaced, not assumed)

Before the model matters, two facts in your brief conflict with the live game. I am not silently resolving them.

1. **Marriage timing.** Your brief says *marriage at Month 4, festival ~Month 6*. The live game marries at **Month 6** (`MARRIAGE_MONTH = 6`) with a monthly negotiation from `MARRIAGE_MONTH+1`. The character/negotiation model below is **timing-agnostic** — it works whether marriage is M4+festival M6, or marriage M6+festival M7. Pick the timeline; nothing in the model changes.
2. **Replace vs. layer.** The live game has 4 EV-balanced economic archetypes (saver/earner/investor/anchor) that a fairness simulation already certified. This richer character model can either (a) **replace** them with a larger content set, or (b) **layer** a personality/negotiation profile onto the existing 4 economic stat blocks. (b) is far cheaper and lower-risk to prove fair. My recommendation is (b) for v1; see §18.

**The non-negotiable constraint that governs everything below:** Money Master is a *ranked, competitive* simulation. Two players in the identical situation making the identical offer **must** get the identical rupee outcome, regardless of who writes better English or who got a "nicer" spouse. That means: **characters may be rich and varied for flavor, but every financial number is deterministic, seeded, and drawn from an EV-balanced content set — never invented by an LLM.** This is the whole reason the architecture in §16 wins.

---

## 1. Spouse Character Model

A spouse is a **static profile** (fixed the moment marriage completes, seeded so every player faces the same fair choice set) plus a **dynamic state** that evolves during play. Behaviour = static profile × dynamic context (see §13).

A profile is four decoupled blocks — the decoupling is the point, because it lets two doctors behave oppositely:

| Block | Purpose | Feeds |
|---|---|---|
| **Identity & background** | flavor + labels (name, occupation label, one-line story) | narration only, never math |
| **Psychological traits (§2)** | how they *behave* in a negotiation | budget, floor, movement |
| **Economic profile (§3)** | what they *bring and can afford* | budget anchor, household finances |
| **Family background (§4)** | external pressure & expectations | budget, floor |

**Occupation is a label, not a driver.** It appears in identity/background and is *one weak prior* the content author may use when picking trait values, but it is never read by the decision engine. Two "Doctor" profiles can have opposite trait vectors (§14 shows exactly this).

Full field list per profile:
- **A. Demographic/background:** display name, age band, occupation label, short backstory string.
- **B. Occupation:** label only (flavor).
- **C. Economic (§3):** income, brought net assets, lifestyle expectation, financial independence, security-buffer expectation.
- **D. Family background (§4):** family economic level, festival importance, involvement, status expectation.
- **E. Financial philosophy:** emergent — read it off Frugality + Prudence (§2), not stored separately.
- **F. Psychological traits (§2):** the 6-trait vector.
- **G. Ethics/values (§5):** modelled as *argument receptivities derived from the traits* (§5) — not a second authored vector, to avoid redundancy.
- **H. Social expectations:** Status Sensitivity (§2) + family status expectation (§4).
- **I. Spending behaviour:** emergent from Frugality + economic profile.
- **J. Negotiation behaviour:** Flexibility + Relational Sensitivity (§2) + floor (§9).
- **K. Relationship behaviour:** reuses the existing `spouse_satisfaction` state.
- **L. Festival/event expectations:** the deterministic budget (§7).
- **M. Negotiation thresholds:** floor ratio + accept threshold (§9), derived from traits.

---

## 2. Psychological Dimensions (evaluated and pruned)

Your brief listed 16 candidate dimensions. Most are redundant for *this* mechanic (a budget negotiation). I evaluated each and collapsed to **six orthogonal traits**, because every extra dimension multiplies the EV-balancing surface (your own `MARRIAGE_SYSTEM_DESIGN.md §3` warns of this) and adds little behavioural distinctness.

**Pruning decisions (explicit):**
- *Financial responsibility, long-term orientation, security preference, short-term enjoyment* → collapse into **Financial Prudence** (they are the same axis: future/security vs. now).
- *Spending orientation, quality orientation* → collapse into **Frugality** (inverse of baseline spend appetite).
- *Family orientation + tradition orientation* → merge into **Family & Tradition Weight** (in practice they co-move and drive the same resistance).
- *Flexibility + negotiation openness* → identical concept → **Flexibility**.
- *Emotional sensitivity* → **Relational Sensitivity** (responsiveness to tone/warmth).
- *Risk tolerance* → **dropped as a standalone trait**; for a festival budget it acts through Prudence (a low-prudence spouse already discounts the "we need the buffer" argument). Keeping it separate double-counts.
- *Fairness sensitivity* → **not a trait**; modelled as an argument *channel* (§8) whose effectiveness is a function of Prudence + Relational Sensitivity, so it needs no own dimension.

**The final 6 traits** (each earns its place by driving a *distinct* lever):

| Trait | Code | 0 means | 100 means | Primary lever it controls |
|---|---|---|---|---|
| Frugality | FRG | loves to spend | extremely thrifty | lowers the initial budget, lowers the floor |
| Financial Prudence | PRU | live-for-now | planner, security-first | how strongly necessity/affordability/goal arguments land |
| Status Sensitivity | STA | indifferent to opinion | reputation-critical | raises budget, raises floor, resists visible cuts |
| Family & Tradition Weight | FAM | self-directed/modern | defers to family & ritual | raises floor, makes "family will understand" backfire or land |
| Flexibility | FLX | rigid/stubborn | very movable | how far a counteroffer travels; accept threshold |
| Relational Sensitivity | REL | transactional | responds to warmth | tone bonus; hostile tone penalty |

Six is enough to make characters feel distinct, and small enough to balance and to explain a decision in one sentence.

---

## 3. Economic Dimensions (kept separate from psychology)

Economics answers *"what do they bring and what can the household afford?"* — never *"how much do they want to spend?"* (that's psychology). Decoupling produces the interesting cases: a low-income, high-status spouse who wants a festival the household can't easily fund (tension), or a high-income, high-frugality spouse who resists spending money they clearly have (also tension).

| Field | Meaning | Maps to existing |
|---|---|---|
| `income_monthly` | spouse's monthly income into the household | archetype `income` |
| `brought_net_assets` | one-time net worth injection = stocks+gold+ef − loan | archetype `stocks/gold/ef/loan` |
| `lifestyle_expense_modifier` | recurring household expense shift | archetype `expense_mod` |
| `financial_independence` (IND 0–100) | how self-sufficient they are | **new** |
| `security_buffer_expectation` | emergency-fund level they're comfortable with | **new (soft)** |

**How economics interacts with psychology (the rule):** economics sets the *anchor and the affordability reality*; psychology sets *how far above/below that anchor they push and how movable they are*. `financial_independence` is the one genuinely new economic lever: a high-IND spouse can **self-fund part of the festival** (reducing the player's exposure) *and* negotiates from strength (concedes a little less, because they don't need the player's cash); a low-IND spouse leans entirely on household cash, so a real "we can't afford it" argument (engine-verified) hits harder. IND is optional for v1.

---

## 4. Family Background Dimensions

Family background is largely *what makes two same-occupation spouses differ*, so it is a first-class block, not flavor. Four fields, all 0–100:

| Field | Code | Drives |
|---|---|---|
| Family economic level | FEL | baseline scale expectation of the event |
| Family festival importance | FFI | how much *this specific* event matters → budget ↑, floor ↑ |
| Family involvement | FIV | how much family pressure amplifies STA/FAM in the floor |
| Family status expectation | FSE | reputation stakes → resists status-threatening cuts |

FFI is **event-scoped** (a wedding-season festival ≠ a minor one), so it can vary per event while the rest of the profile stays fixed. Family background is authored per profile, never stereotyped from occupation.

---

## 5. Ethics / Values Model — and the scale

**Values are modelled as *argument receptivities derived from the six traits*, not as a second authored vector.** This is deliberate: a separate values vector would double-count (a "status value" and a Status trait are the same thing) and double the balancing surface. Instead, each *argument channel* (§8) has a fixed **resonance function** of the traits. Examples of the mapping (full table in §8):

- A **financial-necessity** argument (low emergency fund, real debt) resonates with **PRU** — a prudent spouse *supports* the cut; a low-prudence spouse shrugs.
- A **status/social** justification for spending resonates with **STA + FSE** — cutting it is *harder* for a status-sensitive spouse.
- A **"the family will understand"** argument resonates **inversely** with **FAM** — it lands for a modern spouse, backfires for a tradition-weighted one.
- A **warm, collaborative tone** resonates with **REL**.

Crucially, **no value is universally good or bad.** The identical argument ("cut the festival, our buffer is thin") is *persuasive* to a prudent, low-status spouse and *offensive* to a status-driven, family-weighted one. That asymmetry is the educational core: the player must read the character, not memorise one winning line.

### Scaling system: use 0–100 internally, author in 5 bands

**Recommendation: store and compute on a 0–100 integer scale; author and display in five labelled bands.** Reasoning:
- **0–100 beats 1–5 for computation.** Negotiation thresholds, floor ratios, and persuasion sums need fine gradation; on a 1–5 scale you get cliff effects and frequent ties (two spouses at "4" behave identically), and the counteroffer math rounds badly. 0–100 gives smooth, tunable thresholds and headroom to rebalance without reshuffling content.
- **1–5 beats 0–100 for humans.** Authors and testers reason in "High / Very High," not "72 vs 78." So author in bands and map to a representative value:

| Band | Range | Representative value | Meaning of a trait at this band |
|---|---|---|---|
| Very Low | 0–20 | 10 | trait barely present |
| Low | 21–40 | 30 | present but weak |
| Moderate | 41–60 | 50 | balanced / situational |
| High | 61–80 | 70 | strong, usually decisive |
| Very High | 81–100 | 90 | dominant driver of behaviour |

Every stored number must have a written behavioural interpretation. Example: **Financial Prudence = 85** means *"weights the household's future and safety above present enjoyment; a genuine emergency-fund or debt argument is highly persuasive; resists spending that isn't demonstrably affordable, even money they have."* A number without such a sentence is not allowed into the content set.

---

## 6. Ethics / Values in Negotiation (how they bite)

(Consolidated with §5.) Values enter **only** through the persuasion score (§9): each argument the player makes is scored for *objective strength* by the engine (does the emergency fund actually look thin? does the household actually lack the cash?) and then *multiplied by the spouse's resonance* for that channel (derived from traits). So the same true statement moves different spouses by different amounts, and a **false** argument (claiming poverty when the books are healthy) has low objective strength for everyone — you cannot lie your way past the engine, because the engine checks the books, not the rhetoric.

---

## 7. Festival Budget Model (deterministic, reproducible)

The spouse's opening ask is **computed by the engine, seeded, and reproducible** — the AI never invents it.

**Necessary inputs (after pruning):**
1. `HHI` — household monthly income (player + spouse). *Necessary:* the ask must scale with real capacity.
2. Event importance = blend(spouse-event-importance, `FFI`). *Necessary:* the whole point of the event.
3. `STA` + `FSE`. *Necessary:* status/reputation stakes scale the ask up.
4. `FRG`. *Necessary:* dampens the ask down.

**Dropped as budget inputs** (they belong to *negotiation*, not the *opening ask*): Flexibility, Relational Sensitivity, Prudence-as-such, risk. Including them here would blur budget with bargaining.

**Conceptual formula (illustrative constants; final values set by the EV-balance sim, not by me here):**

```
INPUTS:  HHI, event_k (per-event scale constant), FFI/importance, STA, FSE, FRG
CALC:
  BaseAnchor      = event_k × HHI                       # e.g. event_k ≈ 0.9 for a major festival
  ImportanceMult  = 0.7 + 0.6 × importance/100          # 0.70 … 1.30
  StatusMult      = 0.85 + 0.40 × (STA + FSE)/200        # 0.85 … 1.25
  FrugalityDamper = 1.15 − 0.40 × FRG/100                # 0.75 … 1.15
  Raw             = BaseAnchor × ImportanceMult × StatusMult × FrugalityDamper
  InitialBudget   = round_to_500( Raw × (1 ± jitter) )   # jitter ≤ 2%, SEEDED on (user_id, spouse_id, event_id)
  clamp to [MinReasonable, AffordabilityCap]
OUTPUT:  INITIAL BUDGET  (the spouse's opening ask)
```

The `± jitter` is **deterministic** (hash-seeded, identical for any two players in the same state), so a page refresh cannot reroll it — mirroring the existing `negotiation_service._seed`. Reproducibility is a hard requirement (ADR-000).

---

## 8. Negotiation Variables (minimum useful set)

The AI extracts these from the player's free-text message; anything it cannot map with confidence is **rejected and handed back** (closed schema, per ADR-003). Objective *strength* of each argument is scored by the **engine**, not the AI.

| Variable | Source | Type | Engine use |
|---|---|---|---|
| `proposed_budget` | AI, explicit number | ₹ int | the offer |
| `reduction_pct` | derived | 0–1 | ask severity |
| `argument_tags` | AI, from a **closed set** | multi-label | persuasion channels |
| `tone` | AI | {collaborative, neutral, cold} | REL bonus / hostility penalty |
| `concession_offered` | AI | bool/typed | small credit if a real trade is offered |

**Closed argument set** (each has an engine-computed objective strength and a trait resonance):

| Tag | Objective strength = f(real books) | Resonates with |
|---|---|---|
| `necessity` (emergency fund / debt / liquidity) | higher when EF < target or debt is real | **PRU** (+), STA (−, mild) |
| `affordability` (cash flow can't take it) | higher when the ask genuinely strains cash | **PRU, FRG** (+) |
| `long_term_goal` (house/child/retirement fund) | higher when a real goal is being funded | **PRU** (+) |
| `fairness` (shared sacrifice / reasonable) | fixed-moderate if present | **REL, PRU** (+) |
| `family_reallocation` (redirect to a real family need) | higher if a family need exists | **FAM** (+) |
| `status_free` (we don't need to impress anyone) | fixed | **STA, FSE, FAM** (−) — can backfire |

Pruned from your example list: "consistency with previous decisions" (nice-to-have, deferred — needs a decision-history model), and standalone "emotional tone" is folded into `tone`. Six channels is the minimum that still lets *different* characters be beaten by *different* true arguments.

---

## 9. Accept / Counter / Reject Logic (mostly deterministic)

Reuses the shipped mechanics: **no instant accept on round 1**, **max 3 rounds**, **floor-based acceptance**, **`spouse_satisfaction` state**. The character model supplies the *floor* and *thresholds* that were previously flat.

```
FLOOR      = InitialBudget × floorRatio
floorRatio = clamp( 0.45 + 0.40×(STA+FAM+FFI)/300 − 0.20×FRG/100 , 0.40, 0.90 )
             # status/family/importance → won't cut much; frugality → will

P (persuasion 0–100) =
     Σ over present tags [ objective_strength_tag × resonance_tag(traits) ]
   + tone_term( tone, REL )
   + satisfaction_term( spouse_satisfaction )
   − ask_severity_term( reduction_pct, floor_violation )
   (+ small seeded jitter, ≤ ±5)

ACCEPT_THRESHOLD = clamp( 70 − 0.3×FLX − 0.2×satisfaction , 35, 80 )
```

**Decision (round r, player proposes `proposed`):**
- **r = 1:** never final-accept. Respond, reveal a hint about the floor, nudge satisfaction slightly. (Existing rule.)
- **r ≥ 2:**
  - `proposed ≥ FLOOR` **and** `P ≥ ACCEPT_THRESHOLD` → **ACCEPT** at `proposed`.
  - hostile tone, **or** (`proposed ≪ FLOOR` **and** `P` low), **or** satisfaction critically low → **REJECT** (event proceeds at the current ask; satisfaction penalty).
  - otherwise → **COUNTER** (§10).
- **r = 3 (final):** must resolve. `proposed ≥ FLOOR` → accept; else settle at a P-weighted point between `FLOOR` and `proposed` (never below `FLOOR`), with a satisfaction consequence.

Result is **80–90% deterministic** (per ADR-014): the only randomness is bounded, seeded jitter that colours but never decides. Every outcome is explainable in one line ("she accepted: your emergency-fund argument was real and she's prudent" / "she won't go below ₹62,000: the family's status expectation sets a hard floor").

---

## 10. Counteroffer Model (explainable, not random)

A counteroffer is the spouse meeting the player partway, bounded by the floor and driven by Flexibility + persuasion + how many rounds remain:

```
Movement = clamp( 0.15 + 0.45×FLX/100 + P/300 + round_pressure(r) + satisfaction/400 , 0, 1 )
Counter  = max( FLOOR, CurrentAsk − (CurrentAsk − proposed) × Movement )
Counter  = round_to_500(Counter)
```

- **Never below the floor**, never below the player's number, always inside `[proposed, CurrentAsk]`.
- **Monotonic and legible:** higher Flexibility, stronger true arguments, higher satisfaction, and later rounds all move the counter *toward the player*. A rigid, status-driven spouse with a weak argument barely moves; a flexible, happy spouse facing a strong necessity argument moves a lot.
- `round_pressure` rises each round so an unresolved negotiation converges instead of dragging — reusing the existing "runs out of rounds" behaviour.

Worked example: Initial ₹80,000, player offers ₹50,000, FLOOR ₹62,000, Movement 0.5 → Counter = max(62,000, 80,000 − 30,000×0.5) = max(62,000, 65,000) = **₹65,000**. Explanation: "she came down to ₹65,000 — she's moderately flexible and your point landed, but the family's expectations won't let her go under ₹62,000."

---

## 11. AI Role (tight boundary)

**AI MAY:** understand natural language; map it to the closed argument set; extract `proposed_budget`, `argument_tags`, `tone`, `concession`; generate in-character spouse dialogue; express the personality; explain *why* the engine accepted/countered/rejected in natural, emotional language.

**AI MUST NOT:** invent or alter any rupee value; compute the budget, floor, persuasion, or counteroffer; read or write the database; decide the outcome; override the character profile or the content set; introduce a spouse trait that wasn't authored. Ambiguous input is **rejected for clarification**, never guessed (money is at stake). A **confirmation gate** shows the player the extracted offer before the engine runs — already in the codebase.

This is exactly the ADR-003/ADR-014 boundary; the new work only adds `argument_tags` to the closed schema and richer narration.

---

## 12. Game Engine Role (source of truth)

The deterministic engine owns: the seeded budget, the floor and thresholds (from the profile), the objective argument strengths (from the real books), the persuasion score, the accept/counter/reject decision, the counteroffer, the satisfaction update, and every write to state. It is pure, seeded, testable, and offline-capable (works with template dialogue if the LLM is down). The leaderboard therefore measures **financial judgement, not English fluency** — the entire justification for the architecture (§16).

---

## 13. Character Consistency Mechanism

```
STATIC PROFILE (fixed at marriage, seeded)  ×  DYNAMIC CONTEXT  =  BEHAVIOUR
```

- **Static:** the 6 traits, economic profile, family background. Chosen at marriage by a **seeded** draw from a **versioned, EV-balanced content set** so every player faces the identical fair choice set (mirrors the existing archetype approach). Immutable for the game.
- **Dynamic:** `spouse_satisfaction` (existing), current household finances (the real books), event importance (per-event), negotiation round. These change; the static traits do not.
- **Consequence:** same profile + same context + same offer → same outcome (reproducible, testable). A prudent spouse is *always* receptive to a genuine necessity argument, but *whether it lands this month* depends on whether the books actually look thin — static character, dynamic circumstance.

---

## 14. Example Spouse Archetypes (personality ≠ occupation)

Trait vectors as bands (VL/L/M/H/VH). Economic figures illustrative; final values must pass the EV-balance sim. **Two doctors are included to prove occupation does not determine behaviour.**

**1. Dr. Meera — "the planner"** · Doctor · income High
FRG H · PRU VH · STA L · FAM L · FLX H · REL H · family: FEL H, FFI L, FIV L, FSE L
→ Opens *modest*; a real emergency-fund or goal argument lands hard; low floor; moves readily with a warm tone. **Easy to negotiate down with a true financial case.**

**2. Dr. Rajan — "the family face"** · Doctor · income High
FRG L · PRU M · STA VH · FAM VH · FLX L · REL M · family: FEL H, FFI VH, FIV VH, FSE VH
→ Opens *large*; high floor; "we can't afford it" barely moves him (they can); only a *necessity* argument plus a respectful tone shifts him, and not far. **Same occupation and income as Meera, opposite negotiation.** The lesson: read the person, not the profession.

**3. Aarav — "the operator"** · Entrepreneur · income Variable (Medium avg), brought assets High, IND High
FRG L · PRU L · STA H · FLX H · REL M · FAM M · family: FFI M, FSE H
→ Comfortable with big numbers and risk; *affordability* arguments bounce (he'll "make it back"); *long-term goal* arguments land better; high flexibility means he'll deal — but from a high anchor. Can self-fund part of the event (high IND).

**4. Kavya — "the household economist"** · Homemaker · income Low, brought assets Moderate (savings/gold), lifestyle_mod negative
FRG VH · PRU VH · STA L · FAM H · FLX M · REL H · family: FEL M, FFI M, FIV M, FSE L
→ *She often argues for the cut herself.* Not an obstacle: her frugality lowers the household's baseline expenses and her opening ask is already lean. Beware the stereotype trap — a homemaker here is the most financially disciplined spouse in the set, and her positions are frequently the correct ones.

**5. Farhan — "the modern professional"** · IT professional · income High, IND High
FRG M · PRU M · STA M · FAM L · FLX VH · REL VH · family: FFI L, FIV L, FSE L
→ The easiest negotiation in the set: very flexible, very responsive to collaborative tone, low family pressure. The risk is he's *too* easy — a v1 balancing watch-item so he isn't the dominant pick (see §17).

Optional 6th — **Ishita — "the teacher"** · modest income, PRU H, REL H, FAM H, fairness-receptive: rewards *fair, honest, shared-sacrifice* framing more than hard numbers.

---

## 15. Example Negotiation Scenarios

Household illustrative: player ₹70,000 + spouse income → HHI shown per case. Event: a major festival, `event_k ≈ 0.9`.

### Scenario A — right argument, right person (ACCEPT)
- **Spouse:** Dr. Meera (PRU VH, STA L, FLX H). HHI ≈ ₹1,20,000.
- **Initial Budget:** ~₹72,000 (lean: low status, high frugality damper).
- **Player (round 2):** *"Let's do ₹55,000 — our emergency fund is only one month of expenses and I'd rather build that buffer first."* (collaborative)
- **AI interpretation:** proposed ₹55,000; tags {`necessity`, `long_term_goal`}; tone collaborative.
- **Character evaluation:** engine confirms EF *is* thin → `necessity` strength high; Meera's PRU makes resonance high; warm tone × high REL adds a bonus. P well above ACCEPT_THRESHOLD; ₹55,000 ≥ FLOOR (~₹40,000).
- **Decision:** **ACCEPT at ₹55,000.**
- **Final budget:** ₹55,000. **Spouse response:** *"You're right — a thin buffer scares me more than a smaller function. Let's keep it sensible and put the rest aside."* Satisfaction ↑.

### Scenario B — same argument, wrong person (COUNTER)
- **Spouse:** Dr. Rajan (STA VH, FAM VH, FLX L). HHI ≈ ₹1,20,000.
- **Initial Budget:** ~₹1,05,000 (status + family importance push it up). FLOOR ~₹84,000.
- **Player (round 2):** identical line, ₹55,000, collaborative.
- **AI interpretation:** same tags, same tone.
- **Character evaluation:** `necessity` is real, but Rajan's STA/FAM resonance for cutting is low and the `status_free` undertone slightly *backfires*; ₹55,000 ≪ FLOOR. P moderate. Movement small (FLX L).
- **Decision:** **COUNTER.** Counter = max(84,000, 1,05,000 − (1,05,000−55,000)×0.28) = **₹91,000**.
- **Final budget (if player accepts the counter):** ₹91,000. **Spouse response:** *"I hear you about savings, but my family has one expectation of this event and I won't embarrass them. ₹91,000 is as lean as I can face them with."* The lesson for the player: this character needed a *different* lever (a genuine affordability wall or a family-need reallocation), not a savings appeal.

### Scenario C — weak/pushy argument (REJECT → floor)
- **Spouse:** Kavya (FRG VH, but FAM H, REL H). Initial ~₹48,000 (already lean). FLOOR ~₹34,000.
- **Player (round 2):** *"₹20,000, final. We're not wasting money on this."* (cold ultimatum, no financial substance)
- **AI interpretation:** proposed ₹20,000; tags {`status_free`}; tone cold.
- **Character evaluation:** no `necessity`/`affordability` substance (books are fine) → objective strength low; cold tone × high REL → penalty; ₹20,000 ≪ FLOOR.
- **Decision:** **REJECT** (proceeds near the floor); satisfaction ↓.
- **Final budget:** ~₹34,000. **Spouse response:** *"That's not about money and you know it. I've already kept this small — I'm not cutting it to the bone to make a point."* Lesson: even the most frugal spouse rejects a hostile, substance-free demand — tone and truth matter.

---

## 16. Recommended Architecture

**Recommendation: B — Character-model + deterministic decision engine + LLM conversation.** Unambiguously, for a ranked competitive game. (And it is already the codebase's chosen architecture, so this is consistency, not a pivot.)

| Axis | A: Pure LLM decides | B: Character model + deterministic engine + LLM talks |
|---|---|---|
| Consistency | low — same input drifts | **high — same input, same output** |
| Reproducibility | none (nondeterministic) | **exact (seeded)** |
| Testing | can't unit-test money | **fully unit-testable, offline** |
| Fairness (ranked) | **broken** — English fluency & luck decide rupees | **preserved** — identical situations resolve identically |
| Game balancing | untunable | **tunable knobs (floors, thresholds, EV sim)** |
| Explainability | "the model felt like it" | **one-line causal reason every time** |
| Cost | every decision = LLM call | **decisions are free; LLM only for words (and skippable)** |
| Hallucination control | invents rupees, breaks rules | **cannot touch money; closed schema; confirmation gate** |
| Extensibility | reprompt-and-pray | **add traits/events as data; sim proves fairness** |

Pure LLM wins only on raw effort-to-build and surface "naturalness" — both irrelevant against a broken leaderboard. B keeps the AI where it's genuinely good (understanding language, voicing personality) and keeps money where it must be (deterministic, seeded, testable). This is the same reasoning ADR-003/ADR-014 already committed to.

---

## 17. Risks and Limitations

1. **EV-balance is the hard part, and it gets harder with richer characters.** More traits × more archetypes = a much larger surface to prove "no dominant spouse, staying single still viable" (your `MARRIAGE_SYSTEM_DESIGN.md §3` flagged exactly this). Farhan (§14) being "too easy" is a concrete example. *Mitigation:* extend `marriage_ev_sim.py` to include negotiation outcomes across representative player strategies; ratify only a content set that passes the existing three fairness gates. Prefer layering personality onto the already-balanced 4 economic stat blocks (§0 decision 2) so the *economic* EV is unchanged and only the *negotiation* surface is new.
2. **Cultural sensitivity.** Arranged marriage, a "homemaker" spouse, festival/status spending, and family pressure are real and easy to render as tired or gendered tropes. *Mitigation:* spouses are gender-neutral in the model; make some spouses **more** frugal/disciplined than the player (Kavya); never frame a spouse as "wanting to waste money" — every position is a legitimate values trade-off, and some spouse positions are financially *correct* (ADR-014's "she is not merely an obstacle" principle). No dowry mechanics.
3. **LLM extraction errors.** A misread number could move real money. *Mitigation:* closed schema + confirmation gate + offline numeric parser (all already exist); ambiguity is rejected, never guessed.
4. **Player "solving" a character.** Once a player learns which true argument beats which spouse, they win reliably — but that *is* the intended financial-literacy lesson, provided (a) the argument must be *true* (engine checks the books, so lying fails) and (b) no single phrase beats everyone (guaranteed by trait-varied resonance + the affordability-reality check).
5. **Determinism vs. "feels alive."** Fully deterministic can feel scripted. *Mitigation:* bounded seeded jitter (≤5%) that colours phrasing/counter without deciding outcomes.
6. **Scope creep.** This is materially bigger than the shipped negotiation. *Mitigation:* the phased build in §18; ship the deterministic core with templates before any LLM dependency.
7. **Timing/integration ambiguity** (the §0 decisions) — unresolved, could cause rework if picked late.

---

## 18. What Should Be Implemented First

Strict order; each stage is shippable and fair on its own (mirrors ADR-014's proven build order):

1. **Ratify the model & the two §0 decisions** (timing; replace-vs-layer). *Recommend: layer personality on the existing 4 economic archetypes for v1.* Nothing built yet.
2. **Author the content set as DATA** — the 6-trait vectors + family background for each spouse, in bands, with a written behavioural meaning per number. No engine change.
3. **Prove fairness** — extend `marriage_ev_sim.py` to run the negotiation and confirm the three gates still pass. **Hard gate before any code ships.**
4. **Deterministic engine, offline** — festival budget + floor + persuasion score + accept/counter/reject + counteroffer, extending `negotiation_service`, with **template dialogue only**. Full unit + concurrency + determinism + cross-player-fairness tests. No LLM yet.
5. **Extend the closed intent schema** with `argument_tags` + the offline parser; keep the confirmation gate.
6. **LLM layer last, behind the existing flag** — narration and richer extraction, with the template fallback intact, so a fair, reproducible, offline-capable negotiation exists *before* any network dependency.

**Do not** touch UI, schema, economics, or existing game logic until the model above is approved and the fairness gate (step 3) is green.

---

*End of design specification. Stopping here per instruction — no implementation until you approve the character model. Tell me your calls on the two §0 decisions and I'll refine before anyone writes code.*
