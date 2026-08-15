# Money Master — Marriage System: Concept-Alignment Audit

**Status:** AUDIT ONLY. No file, schema, formula, or Supabase change. Verified against current code (line numbers as of this audit).
**Question:** does the CURRENT implementation match the INTENDED concept (Month-4 arranged marriage → Month-6 festival negotiation, character-driven)?
**Short answer:** the *negotiation machinery* is real, deterministic, and correct (accept/counter/reject, AI boundary, satisfaction, EV-balanced economics). But the *concept alignment* is off on three axes: **timing (Month 6, not 4)**, **festival (there is none — negotiation is monthly)**, and **character depth (economic archetypes only, no personality/ethics/family)**. None of this requires a rewrite.

---

## A. Current Marriage Flow (actual code)

```
Admin advances months via admin_routes.next_month  (game_control.current_month)
        │
        ▼
CURRENT MONTH = 6                       ← constants.MARRIAGE_MONTH = 6 (constants.py:168)
        │
        ▼
CURRENT TRIGGER: admin toggles game_control.marriage_round_active = true
        │        (admin_routes.update_settings :714-715). No automatic Month-4 trigger.
        ▼
CURRENT "SPOUSE OFFER": dashboard renders a candidates grid of the 4 ECONOMIC
        │  archetypes (frontend/dashboard.html:210,224 "You are in Month 6…";
        │  dashboard.js:258 candidatesGrid). Copy: "Spend dates to reveal candidate traits".
        ▼
CURRENT "CONVERSATION" (courtship): POST /courtship/reveal (player_routes.courtship_reveal
        │  :1058) reveals ONE economic trait per date — income / expense_mod / assets
        │  (dashboard.js:260-262). 4 free dates, then ₹5,000 each. NOT a personality chat.
        ▼
CURRENT MARRIAGE: POST /courtship/marry (player_routes.courtship_marry :1143), gated
        │  `player['month'] != 6 or not marriage_round_active` (:1159). Player picks an
        │  archetype or 'single'. Pays WEDDING_COST=25,000; spouse assets/loan injected;
        │  one month of spouse net flow applied; state written atomically via
        │  player_apply_atomic. Completes IN MONTH 6.
        ▼
CURRENT "FESTIVAL": NONE as a discrete event. (The only "festival" in code is a generic
        │  random −₹2,000 "Community Festival" event in event_engine.py:182, unrelated to
        │  the spouse.)
        ▼
CURRENT NEGOTIATION: a MONTHLY spouse proposal, available every month the player is
        │  married AND game_control.negotiation_enabled = true. Two-step, deterministic:
        │    • generate_proposal(user_id, month, archetype) → seeded ask (negotiation_service.py:71)
        │    • POST /negotiate  (player_routes.negotiate_interpret :638) — AI extracts intent only
        │    • POST /negotiate/commit (:697) — negotiation_service.evaluate() DECIDES the money
        │  Rounds ≤3, "no instant accept round 1", floor = negotiation_min_ratio(archetype,
        │  satisfaction). _negotiation_context uses player['month'] (:616) → per-month.
        ▼
CURRENT FINANCIAL RESULT: evaluate() returns effects {cash/stocks/emergency_fund/
           household_expense_modifier} + satisfaction delta, applied atomically via
           apply_player_txn; recurring effects flow through monthly_processor each month.
```

**Net:** everything happens at/after **Month 6**, selection is among **economic archetypes**, and the negotiation is a **recurring monthly proposal**, not a one-off **festival budget**.

---

## B. Intended vs Current Matrix

Marked strictly — ⚠ = the mechanic exists but does not match the intended concept; ❌ = absent/contradicts.

| Component | Intended | Current Implementation | Match? | Problem |
|---|---|---|---|---|
| Marriage trigger | Month 4 | Month 6, admin-gated (`MARRIAGE_MONTH=6`, `marriage_round_active`) | ❌ | Wrong month; manual toggle, not a Month-4 family offer |
| Family offer | Month 4 | Month-6 courtship round (candidates grid) | ⚠ | Concept exists (candidate cards) but at Month 6 and not framed as a family offer |
| Multiple spouse types | Yes (Doctor, Entrepreneur, Homemaker, IT, Teacher…) | 4 **economic** archetypes: saver/earner/investor/anchor (`constants.ARCHETYPES`) | ⚠ | Types are economic stat-blocks, not occupations/people |
| Individual characteristics | personality, ethics, values, family, negotiation | economic vars (income, expense_mod, stocks, gold, ef, loan) + per-archetype floor ratio + satisfaction | ⚠ | No personality/ethics/family dimensions |
| Marriage completion | Month 4 | Month 6 (`courtship_marry`, gate `month != 6`) | ❌ | Wrong month |
| Festival timing | ~Month 6 (a discrete event) | No discrete festival; negotiation is monthly | ❌ | The festival event does not exist |
| Spouse budget estimation | from background/economics/family/importance/household | seeded pick from per-kind `amount_min/amount_max` (`generate_proposal` + `DEFAULT_PROPOSALS`) | ⚠ | Deterministic budget exists, but inputs are archetype+seed only — not family/economics/importance/household |
| Player negotiation | Yes | Yes — two-step, deterministic, rounds ≤3 | ✅ | — |
| Character-based response | multi-dimensional | archetype + satisfaction → floor ratio (`negotiation_min_ratio`) | ⚠ | Response keys off one economic archetype, not a character |
| Accept | Yes | `accepted_full` / `accepted_counter` (`evaluate`) | ✅ | — |
| Counteroffer | Yes | `_counter()` with floor-based accept, hint on gap | ✅ | — |
| Reject | Yes | `refused` / `auto_resolved` (out of rounds) | ✅ | — |
| Financial consequence | Yes | effects applied atomically; recur via monthly_processor | ✅ | — |

**Reading:** the **decision mechanics** (accept/counter/reject, deterministic evaluation, financial consequence) are ✅. The **concept framing** (timing, festival, character, budget inputs) is ⚠/❌.

---

## C. Existing Archetypes (report only — do NOT delete)

1. **Where defined:** `backend/models/constants.py` → `ARCHETYPES` (saver/earner/investor/anchor); mirrored in the live DB table `public.spouse_archetypes` (values match constants exactly).
2. **What they control (economic vars):** `income` (monthly, into household), `expense_mod` (household expense shift), `stocks` / `gold` / `ef` (one-time asset injection at marriage), `loan` (brought liability). Also drive the negotiation floor via `NEGOTIATION_FLOOR_RATIO[archetype]` (constants) and each archetype's default monthly proposal (`DEFAULT_PROPOSALS`).
3. **EV-balanced?** Yes — `tools/marriage_ev_sim.py` passes all three fairness gates (spread 4.0% market-ON / 5.5% market-OFF; single viable; no dominance), re-verified this session.
4. **Where they enter the flow:** `courtship_marry` (Month 6) — the chosen archetype's stat block is injected; thereafter `monthly_processor` reads `spouse_archetype` every month for recurring income/expense, and `negotiation_service` reads it for the proposal + floor.
5. **Keep as the economic layer?** **Yes.** They are the certified-fair economic substrate. The intended richer character model (already specified in `SPOUSE_CHARACTER_MODEL_DESIGN.md`) should **layer on top** of these, not replace them — which is also DECISION 6.

---

## D. Existing Spouse Conversation (audited)

- **When it starts / who initiates / trigger:** the *courtship* (trait reveal) is player-initiated at Month 6 while `marriage_round_active`. The *negotiation* is available every married month while `negotiation_enabled`; the **spouse initiates** by raising the month's proposal (`generate_proposal`), and the player replies.
- **What the player can say:** free text, mapped to a **closed intent set** — `ACCEPT_PROPOSAL, COUNTER_OFFER(amount), REQUEST_DELAY, PROPOSE_ALTERNATIVE, ASK_QUESTION, REFUSE` (`models/negotiation_intents.py`). Ambiguous text is **rejected for rephrase**, never guessed.
- **How the spouse responds / deterministic?** Fully deterministic and seeded (`negotiation_service.evaluate` + `_seed(user_id, month)`); a refresh cannot reroll. Same inputs → same outcome (tests: `test_determinism`, `test_cross_player_fairness`).
- **Is AI used / does AI control money?** AI (`services/ai_service.py`) is used **only** to extract intent and to narrate the reply, behind the `negotiation_enabled` flag, with an **offline regex parser fallback**. **AI does not decide money** — `evaluate()` does. This is correct.
- **Satisfaction:** `player_state.spouse_satisfaction` (0–100, starts 60); `evaluate` returns a delta, applied (clamped) atomically; it also drifts household expense ±₹3,000 in `monthly_processor` and shifts the negotiation floor.
- **Rounds / counteroffers / final budget:** ≤3 rounds; round-1 never final-accepts; from round 2 accept iff `offer ≥ ask × min_ratio(archetype, satisfaction)`; unresolved at round 3 auto-resolves at the ask. Counter logic in `_counter()` with a "close / not close" hint.

**Separation of concerns (as required):** the **natural-language conversation** (`ai_service`) and the **financial decision logic** (`negotiation_service` → `player_apply_atomic`) are already two distinct systems. That boundary is intact and correct.

---

## E. Festival Budget — the existing "budget" formula

There is **no festival budget**. The nearest existing thing is the **monthly proposal ask**:

- **Function:** `negotiation_service.generate_proposal(user_id, month, archetype_id, catalogue)`.
- **Inputs:** `archetype_id` (selects a `DEFAULT_PROPOSALS[archetype]` entry, or an admin `spouse_proposals` row), and `(user_id, month)` as the **seed**.
- **Formula:** `ask = round500( amount_min + rand() × (amount_max − amount_min) )` where `rand()` comes from `_seed(user_id, month, "proposal")` (deterministic).
- **Constants:** per-archetype `amount_min` / `amount_max` in `DEFAULT_PROPOSALS` (e.g., earner lifestyle 28,000–42,000).
- **Randomness / seed:** seeded on `(user_id, month)` — reproducible, refresh-proof.
- **Economic / spouse / family / event inputs:** **none** beyond the archetype. The ask does **not** scale with household income, family expectations, event importance, or the player's actual financial situation.

So the intended festival-budget formula (background × economics × family × importance × household) **does not exist yet**; the current ask is an archetype+seed lookup.

---

## F. AI Boundary

The intended principle — **AI understands/generates conversation; the deterministic engine decides money** — **already exists and is correctly enforced** (ADR-003/ADR-014): closed intent schema, confirmation gate, `negotiation_service.evaluate` as the sole money authority, offline fallback, `ai_source` audit field, and the `negotiation_enabled` kill-switch. **Preserve it. Do not replace the deterministic logic with an LLM.**

---

## FINAL VERDICT

### 1. What is already CORRECT
- Deterministic, seeded, reproducible negotiation with real **accept / counter / reject** and rounds (`negotiation_service`).
- **AI boundary** intact — AI never decides money; offline-capable; flagged.
- **Spouse satisfaction** state and its financial drift.
- **EV-balanced economic archetypes** (fairness gates pass) as the economic layer.
- **Financial consequence** wired into the monthly engine and applied atomically (post A-01).
- Multiple selectable spouse options with a reveal/"dating" mechanic (concept seed already present).

### 2. What is WRONG (vs the fixed decisions)
- **Marriage timing: Month 6, must be Month 4** (`MARRIAGE_MONTH=6`; hardcoded `!= 6` gates in `courtship_marry`/`courtship_reveal`; Month-6 text in `dashboard.html:210`).
- **No discrete festival event ~Month 6** — negotiation is *monthly*, not a one-off festival.
- **Candidate framing is economic, not personal** — saver/earner/investor/anchor, not Doctor/Entrepreneur/etc.

### 3. What is MISSING
- A **Month-4 family-arranged-offer trigger** (currently a manual admin toggle at Month 6).
- A **festival event** at ~Month 6 with a **budget derived from background/economics/family/importance/household** (the intended formula in `SPOUSE_CHARACTER_MODEL_DESIGN.md §7`).
- The **multi-dimensional character model** (personality/ethics/values/family) — already *designed* but **not implemented** (and out of scope for this task).

### 4. What must be CHANGED (to hit the fixed decisions)
- Re-time marriage to **Month 4** (parameterize the hardcoded `6`s; `scoring.net_worth_component` already keys off `MARRIAGE_MONTH`, and `monthly_processor` keys off `spouse_archetype` presence not a literal month, so the blast radius is small).
- Introduce a **single festival month (~Month 6 = marriage_month+2)** and make the negotiation fire **once for the festival**, rather than every month (e.g., gate the proposal to that month instead of "every married month").
- Make the festival ask depend on **household finances + spouse economics + (later) character** rather than a flat per-archetype range.

### 5. What must NOT be changed
- The deterministic `negotiation_service.evaluate` engine and the AI boundary.
- The 4 EV-balanced economic archetypes (DECISION 6).
- The satisfaction model, the atomic `player_apply_atomic` write path, and monthly-processor integration.
- UI structure, DB schema, and game formulas (per this task's constraints).

### 6. MINIMUM REPAIR PLAN (no rewrite; staged; nothing built until you approve)

**Stage 0 — decisions to confirm (yours):** keep the 4 economic archetypes as the layer (recommended), and confirm the festival is a *single* Month-6 event (not the current monthly cadence).

**Stage 1 — Re-time (small, mechanical):** set `MARRIAGE_MONTH = 4`; replace the literal `6`s in `courtship_marry` / `courtship_reveal` / `lock_turn` Month-6 guards and the `dashboard.html` copy with `MARRIAGE_MONTH`. Verify `scoring` and `monthly_processor` remain correct (they already use `MARRIAGE_MONTH` / archetype-presence). **Re-run the full suite + EV sim as the gate.**

**Stage 2 — Festival framing (small):** designate a festival month = `MARRIAGE_MONTH + 2` (≈ Month 6). Gate the spouse proposal to fire **once** at the festival month (add a month filter to `generate_proposal` selection / restrict `negotiation_enabled` semantics) instead of every married month. Reuse the *entire* existing negotiation engine unchanged — the festival is just a single instance of the proposal mechanic that already works.

**Stage 3 — Budget inputs (moderate, deferred until the character model is approved):** replace the flat `amount_min/max` ask with the deterministic festival-budget formula (household income × importance × status × frugality) from the approved design — still seeded, still engine-decided, still EV-gated.

**Stage 4 — Character depth (separate approved project):** layer the 6-trait character model onto the archetypes per `SPOUSE_CHARACTER_MODEL_DESIGN.md`. **Not part of this alignment; do not start until §18 of that spec is approved and the EV gate is green.**

Stages 1–2 alone bring the *timeline and festival* into concept alignment with the smallest possible change, reusing the certified engine. Stages 3–4 add the character depth later, gated by fairness.

---

*End of audit. No changes made. Awaiting your approval (and the Stage-0 confirmations) before any repair.*
