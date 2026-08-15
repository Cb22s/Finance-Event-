# Money Master — Stage 2 Design: Month-6 Festival Event & Initial Spouse Budget

**Status:** DESIGN / AUDIT ONLY. No code, DB, UI, AI, psychology, or negotiation changes. Awaiting approval.
**Fixed context:** marriage Month 4; festival ≈ Month 6 (`MARRIAGE_MONTH + 2`); four rebalanced economic archetypes; EV gates PASS. Player salary `MONTHLY_INCOME = 100,000`; `SPOUSE_BASE_EXPENSE = 9,000`; `WEDDING_COST = 25,000`.
**Guiding principle:** reuse the existing deterministic engine; the festival is *one instance* of the proposal mechanic that already works. Do not rebuild.

---

## A. Existing Festival/Event Audit

- **`backend/engine/event_engine.py`** — generates *random monthly* events (emergency, opportunity, social, expense spike, windfall, penalty) and applies admin-authored `events` rows. **No festival, not spouse-linked.** The only "festival" string is a generic −₹2,000 "Community Festival" random event (unrelated).
- **`backend/services/negotiation_service.py`** — `generate_proposal(user_id, month, archetype_id, catalogue)` produces a **seeded** monthly spouse "ask" from `DEFAULT_PROPOSALS[archetype]` flat `amount_min/amount_max` ranges (kinds: lifestyle/investment/saving/protection). `evaluate(...)` is the deterministic accept/counter/reject engine; floor = `negotiation_min_ratio(archetype, satisfaction)`. **This is the reusable interface.**
- **`constants.NEGOTIATION_FLOOR_RATIO`** — earner 0.70, investor 0.60, anchor 0.55, saver 0.50 (per-archetype negotiation firmness). Reusable as-is.
- **DB tables** `spouse_proposals` (archetype_id, month, kind, title, description, amount_min, amount_max, floor_ratio, ev_note) and `spouse_dialogue` — **both exist, both empty.** `spouse_proposals` is already an admin-authorable proposal catalogue.
- **`monthly_processor.py`** — applies spouse income/expense/satisfaction-drift/`household_expense_modifier` each month; keyed off `spouse_archetype` presence, not a month literal.
- **Frontend** — `negotiation.js` + the Home-tab negotiation panel already render a proposal, an ask, rounds, satisfaction; two-step `/negotiate` + `/negotiate/commit` endpoints exist behind `game_control.negotiation_enabled`.

## B. What Already Exists (reusable — do NOT duplicate)

1. Seeded, reproducible proposal generation (`generate_proposal`) → the **budget-generator slot**.
2. The full deterministic **negotiation engine** (`evaluate`) with rounds, floor, accept/counter/reject → the **hand-off target**.
3. Per-archetype **floor ratios** and the satisfaction-adjusted `negotiation_min_ratio`.
4. **Proposal dict shape** `{archetype_id, kind, title, description, ev_note, ask, month}` that `evaluate` consumes via `proposal['ask']` + `proposal['archetype_id']`.
5. `spouse_proposals` content table + satisfaction state + negotiation UI + `negotiation_enabled` flag.

## C. What Is Missing

1. A **festival event definition** anchored to Month 6 (identity, importance, base scale).
2. A **household/event-scaled budget formula** — the current ask is a *flat per-archetype range*, blind to household income and event importance.
3. **Single-festival gating** — negotiation is currently monthly; the festival should be one event at Month 6.
4. A **character-model plug point** (`CharAdj`) so the future trait model attaches without a rebuild.

## D. Festival Event Model (minimum structure)

There is **one** festival in v1, so the minimum is a **constant**, not a new table (no schema change):

```
FESTIVAL_EVENT = {
    "id":         "festival_m6",              # stable id → seed + audit
    "month":      MARRIAGE_MONTH + 2,          # = 6 (auto-tracks marriage timing)
    "title":      "The family festival",
    "importance": 1.10,                        # authored scale, ~0.7–1.3 (family/social weight, folded)
    "base_k":     0.65,                        # festival size as a share of a month's household income
    "kind":       "festival"                   # so evaluate/UI treat it like the existing 'lifestyle' kind
}
```

Event attributes map to the brief: *identity* = id/title; *month* = 6; *importance* = `importance` (which, for v1, absorbs "family/social relevance" and "family expectations" until the character/family model supplies them); *base expenditure* = `base_k × household income`; *spouse participation & budget expectation* = the generated ask (§F). If multiple festivals are ever needed, promote this constant to rows in the **existing** `spouse_proposals` table (kind='festival', carrying `importance`/`base_k`) — no new table then either.

## E. Required Inputs (each evaluated per the brief)

| Candidate variable | Necessary? | What it represents | How it affects budget | Exists? | Redundant? |
|---|---|---|---|---|---|
| **A. Economic archetype** | **Yes** | who the spouse economically is | drives income (HHI) + posture (expense_mod) | Yes (`ARCHETYPES`) | No |
| **B1. Spouse income** | **Yes** | earning power → household capacity anchor | sets the base scale (HHI) | Yes | No |
| B2. Spouse assets (stocks/gold/ef) | **No** | net worth she brought | net worth ≠ *spend appetite* for a festival | Yes | **Yes — exclude** |
| **C. Household cash / EF / debt** | **No (by design)** | current liquidity | would let the ask auto-fit affordability and **kill the conflict** (§7) | Yes | **Exclude from the ask; belongs to negotiation** |
| **D. Event importance** | **Yes** | how big this event is socially | scales the base up/down | New (small constant) | No |
| E. Family expectations | **Defer** | family/status pressure | raises the ask | Future | Fold into `importance` now; character model later |
| **F. Lifestyle/spend preference** | **Yes (proxy now)** | how freely she spends | posture multiplier | **Represented by `expense_mod` today**; richer version = future traits | Use `expense_mod`; don't add a field (would double-count) |

**Minimum input set:** spouse **income** (→ HHI), spouse **expense_mod** (→ posture), event **importance** + **base_k**, and a **seed**. Household cash/EF/debt and spouse assets are deliberately **excluded** from the initial ask.

## F. Initial Budget Model

```
Economic Context (HHI, expense_mod)  +  Event Context (base_k, importance)  +  CharAdj(=1.0 now)
        ↓  deterministic, seeded
INITIAL FESTIVAL BUDGET  (a proposal dict: { ask, archetype_id, kind:'festival', ... })
        ↓  (Stage 3)
Existing evaluate() negotiation  →  Negotiated Budget
```

- **HHI** = `MONTHLY_INCOME + spouse.income` (capacity anchor). Note: with a ₹100k player salary, HHI is ~104–116k across archetypes, so archetype differentiation comes mostly from **posture** (expense_mod) and later from **character**, not from HHI — a deliberate, honest consequence of the current economy.
- **Posture** = economic spend-lean from `expense_mod`, the only spend signal that exists today.
- **CharAdj = 1.0** — the reserved multiplier the future trait model fills (status/tradition ↑, frugality ↓).

## G. Proposed Formula (transparent, reproducible)

```
HHI       = MONTHLY_INCOME + spouse_income
Base      = FESTIVAL_EVENT.base_k × HHI
Posture   = clamp( 1 + expense_mod / POSTURE_SCALE , 0.85 , 1.20 )    # POSTURE_SCALE = 30,000
Importance= FESTIVAL_EVENT.importance
CharAdj   = 1.0                                                       # PLACEHOLDER → future trait model
Raw       = Base × Posture × Importance × CharAdj
Jitter    = ±2%, SEEDED on hash(user_id, spouse_archetype, event_id)  # reproducible; refresh-proof
Ask       = round_to_500( Raw × (1 + Jitter) )
Ask       = clamp( Ask , MIN_FESTIVAL = 0.25×HHI , SOFT_CAP = 1.5×HHI )
```

Every term is explainable in one sentence — the engine can always answer *"why this budget?"* (e.g., *"₹95,500 = 0.65 × ₹116k household × 1.15 spender-posture × 1.10 festival importance"*). No LLM, no unbounded guess; randomness is a bounded, seeded ±2% cosmetic jitter that never decides the game.

## H. Decision Rules

1. Festival fires **once**, at `FESTIVAL_EVENT.month` (=6), only if the player is married and `negotiation_enabled`. (Stage 3 pins the month; today negotiation is monthly.)
2. The budget is computed **once** and cached in the seeded proposal (refresh cannot reroll it — same rule as `generate_proposal` today).
3. The **negotiation floor** is unchanged: `floor = Ask × negotiation_min_ratio(archetype, satisfaction)` using the **existing** ratios (Saver most negotiable at 0.50, Earner firmest at 0.70).
4. Accept/counter/reject and rounds are the **existing** `evaluate()` — untouched.

## I. Economic Constraints (safety)

- The ask is anchored to **income (capacity)**, not to current **cash/EF/debt** — so the spouse **can** ask for more than is comfortable, creating the intended negotiation conflict. The player's real affordability is argued *during* negotiation (and `evaluate` already checks `player_cash` before it will let the player *accept* an amount).
- `SOFT_CAP = 1.5 × HHI` prevents absurd asks; `MIN_FESTIVAL = 0.25 × HHI` prevents a trivial one. Both are guardrails, not affordability-fitting.
- The festival spend is a **one-time** cash outflow at settlement (like `WEDDING_COST`), not a recurring modifier — so it does **not** perturb the EV-balanced monthly economics or the fairness gates.

## J. Future Character-Model Integration Point

The formula is pre-shaped for the approved `SPOUSE_CHARACTER_MODEL_DESIGN.md`:
- **`CharAdj`** (currently `1.0`) → supplied by traits: `status_sensitivity`/`family_tradition` raise it, `frugality` lowers it.
- **`Posture`** (currently from `expense_mod`) → later *replaced* by a trait-derived spend function; the formula shape is identical, so no rebuild.
- **`FESTIVAL_EVENT.importance`** → later blended with the spouse's/family's `festival_importance` trait.
- **floor ratio** → later refined per character (flexibility), still via `negotiation_min_ratio`'s signature.

## K. Interface to the Existing Negotiation Engine

The festival budget generator is a **new function** (e.g., `festival_service.generate_festival_budget(economic_state, event, char_adj=1.0)`) that returns **the same proposal dict shape** `generate_proposal` already returns:

```
{ "archetype_id": <id>, "kind": "festival", "title": ..., "description": ...,
  "ev_note": ..., "ask": <InitialBudget>, "event_id": "festival_m6", "month": 6 }
```

`evaluate(intent, params, proposal, round_no, satisfaction, player_cash)` consumes it **unchanged** (reads `proposal['ask']` + `proposal['archetype_id']`). **`negotiation_service.py` is not modified** — the new generator lives outside it and simply feeds it. Initial budget = `proposal['ask']`; negotiated budget = `evaluate(...)['agreed_amount']`.

## L. Example Calculations (same festival, comparable state)

Festival: `base_k = 0.65`, `importance = 1.10`, `POSTURE_SCALE = 30,000`, jitter shown as 0 for clarity, satisfaction = 60 (start). Player salary 100,000.

| Spouse | Income → HHI | expense_mod → Posture | Base (0.65×HHI) | **Initial Ask** | Floor ratio (sat 60) | **Negotiable floor** |
|---|---|---|---:|---:|---|---:|
| **Saver** | 5,000 → 105,000 | −2,500 → 0.917 | 68,250 | **₹69,000** | 0.50→0.66 | ~₹45,500 |
| **Earner** | 16,000 → 116,000 | +4,500 → 1.150 | 75,400 | **₹95,500** | 0.70→0.796 | ~₹76,000 |
| **Investor** | 4,000 → 104,000 | −1,500 → 0.950 | 67,600 | **₹70,500** | 0.60→0.728 | ~₹51,500 |

Reading it: the **Earner** asks the most (₹95,500) and holds firmest (won't go below ~₹76,000) — her income + lifestyle. The **Saver** asks least (₹69,000) and is the easiest to trim (down to ~₹45,500) — frugal by identity. The **Investor** sits in between. All deterministic, all explainable, all from **existing** economic data + two small event constants. Against a ₹100k salary these are real strains → genuine negotiation stakes.

*(`negotiation_min_ratio = floor + (1−floor)·((100−sat)/100)·0.8`; at sat 60 the `(100−60)/100·0.8 = 0.32` term lifts each base ratio.)*

## M. Risks / Limitations

1. **Weak archetype differentiation on income** — because the player salary (100k) dwarfs spouse income, HHI barely varies, so today's spread comes almost entirely from `expense_mod`. That's fine now, but the festival will feel *much* more characterful once the trait model supplies `CharAdj`/status/tradition. Flag, not a blocker.
2. **`base_k`/`importance` are new tuning knobs** — set conservatively (0.65 / 1.10) and sanity-check that festival asks stay in a sensible band vs. salary; they do not touch the monthly EV gates (one-time outflow), but pick them deliberately.
3. **Reusing `expense_mod` as a spend proxy** slightly overloads that parameter (it already drives monthly household expense). Acceptable as an interim proxy; the trait model removes the overload later. Do **not** change `expense_mod` values for this (they're EV-locked from Stage 1B).
4. **Single-festival gating** is a Stage-3 route concern; until then, keep `negotiation_enabled` off outside Month 6 so the monthly cadence doesn't leak.
5. **DB vs constants** — if the festival is authored in `spouse_proposals` later, keep the constants↔seed mirror discipline (the D-01 guard test).

## N. Recommended Minimum Implementation (for Stage 3 approval — NOT built now)

1. Add `FESTIVAL_EVENT` + `POSTURE_SCALE`/`base_k`/`importance` constants to `constants.py` (data only, no schema).
2. New `festival_service.generate_festival_budget(...)` returning the existing proposal-dict shape — **no edit to `negotiation_service.py`**.
3. Gate the festival to `FESTIVAL_EVENT.month`; feed its proposal into the existing `evaluate()` and the existing negotiation UI/endpoints.
4. Tests: determinism (same inputs → same ask), reproducibility across refresh, the three worked examples above, and a guard that the festival is a one-time outflow that does **not** shift the EV gates.
5. Character model and the actual conversation remain **future stages**; only the `CharAdj=1.0` seam ships now.

---

*STOP — design only. No code/DB/UI/AI/negotiation changes. Awaiting approval of the festival event model and the initial-budget formula before Stage 3 implementation. Two knobs I'd like your call on at approval: `base_k` (festival size as a share of household income; proposed 0.65) and `importance` (proposed 1.10).*
