# Marriage & Spouse Negotiation — Forensic Audit

**Date:** 2026-08-13
**Scope:** Marriage life-state + Spouse Negotiation subsystem, across UI → frontend → routes → services → engine → DB → scoring.
**Status:** AUDIT ONLY. No code or schema changed. Fixes proposed, not applied — awaiting your ruling.

---

## 0. Headline (read this first, it corrects the brief)

Your brief assumes marriage is *"an isolated event / decorative feature"* with negotiation *"unclear or not working."* **That assumption is mostly wrong, and it matters because it would send us rebuilding something that already exists.** The forensic finding:

- Marriage **is** a persistent life-state, not a one-click event. `player_state.spouse_archetype` is the single source of truth; it survives refresh/logout; the monthly engine reads it **every month** and applies recurring spouse income, spouse expense, relationship-driven expense drift, and permanently-negotiated household savings. (`monthly_processor.py` lines 100–150.)
- Negotiation **is** a real, deterministic, multi-round decision system with a two-step confirmation gate, seeded proposals, satisfaction-driven acceptance floors, counter-offers, alternatives, delays, refusals, plain-language reasons, and a full audit log. (`negotiation_service.py`, `negotiation_intents.py`, `player_routes.py` 596–775, `negotiation.js`.)
- It already meets a large fraction of your §36 acceptance criteria.

So this is **not** a "build marriage properly" job. It is a **repair-and-reconcile** job. The genuine defects are narrower, and three of them are serious. The single biggest problem is **not in the game logic — it is that three different definitions of the spouse disagree, and the engine silently trusts only one of them.**

**One more honest point:** roughly a third of your brief (children, divorce, joint-goal tables, contribution-ratio models, counter-proposal richness) describes features this codebase **deliberately deferred** by its own architecture decisions (ADR-002 §1, ADR-014). Your own §21 and §33 say *don't add divorce/children unless needed, don't over-engineer.* Those two instructions are in tension. I am treating the deferral as correct and will **not** build them unless you overrule. Fixing the real bugs matters more than adding surface area.

---

## A. Current Marriage Architecture

**Files**
- `backend/models/constants.py` — `ARCHETYPES` (the **de facto** spouse stat blocks), `MARRIAGE_MONTH=6`, `WEDDING_COST=25000`, `SPOUSE_BASE_EXPENSE=9000`, all negotiation constants.
- `backend/routes/player_routes.py` — `/courtship/reveal`, `/courtship/marry`, `/negotiate`, `/negotiate/commit`, `/dashboard` (spouse + negotiation panels), `/lock-turn` (Month-6 gate).
- `backend/services/negotiation_service.py` — deterministic rules engine (decides the money).
- `backend/models/negotiation_intents.py` — closed intent schema + offline parser.
- `backend/services/ai_service.py` — intent extraction + narration (never decides money).
- `backend/engine/monthly_processor.py` — applies spouse income/expense/drift/modifier each month.
- `backend/engine/scoring.py` — `net_worth_component(..., spouse_income)` normalization.
- `frontend/js/negotiation.js`, `frontend/js/dashboard.js`, `frontend/dashboard.html` — UI.
- `marriage_migration.sql`, `ADR-014` migration block — schema.

**Tables (live, verified in Supabase `ujoqdsesfctxmzmlxewu`)**
- `player_state.spouse_archetype` (text, nullable) — **authoritative relationship state**.
- `player_state.spouse_satisfaction` (int, default 60), `player_state.household_expense_modifier` (numeric, default 0).
- `spouse_archetypes` (9 cols, seeded 4 rows) — **present but NOT read by the backend engine** (dead as far as money is concerned).
- `player_spouse_reveals` — deterministic courtship trait reveals.
- `player_negotiations` (13 cols) — negotiation audit log.
- `spouse_proposals` (10 cols) — admin proposal catalogue — **0 rows (unseeded)**.
- `spouse_dialogue` (6 cols) — templated lines — **0 rows (unseeded)**.
- `game_control.marriage_round_active` (bool), `game_control.negotiation_enabled` (bool).
- **Unrelated:** `player_relative_score` / `player_relative_actions` / `relative_events` are the *"help your relatives for trust"* mechanic — a **separate** feature, not the spouse. It is *not* a duplicate marriage state (a real risk you flagged in §27); I checked. Naming collision only.

**Functions / engine**
- `negsvc.generate_proposal()` (seeded, refresh-proof), `negsvc.evaluate()` (the only money-deciding function), `negsvc.clamp_satisfaction()`.
- `process_month_for_player()` — recurring household math.
- `net_worth_component()` — household-aware normalization (partial; see D-03).

**State variables:** `spouse_archetype` (SINGLE = `'single'`, MARRIED = archetype id, ENGAGED/DIVORCED = **not modeled**), `spouse_satisfaction` (0–100), `household_expense_modifier` (permanent ₹/month).

---

## B. Current Marriage Flow (as actually coded)

```
Month 6 reached  →  admin sets game_control.marriage_round_active = true
        ↓
Player opens dashboard  →  courtship panel shows 4 archetypes + reveal actions
        ↓
POST /courtship/reveal (repeatable, deterministic)  →  writes player_spouse_reveals
        ↓
POST /courtship/marry { choice }
   ├─ guard: month==6 AND marriage_round_active   (else 400)
   ├─ guard: spouse_archetype already set → 400  (single-attempt — but see D-04)
   ├─ choice == 'single' → set 'single', log, done (staying single is viable)
   └─ choice == archetype:
         ├─ require cash >= WEDDING_COST (25,000)
         ├─ cash -= 25,000; inject arc stocks/gold/ef; create spouse loan if any
         ├─ apply ONE month of spouse net flow (income - expense) for Month 6
         ├─ recompute net worth / risk / score
         └─ persist spouse_archetype  → PERSISTENT MARRIED STATE
        ↓
/lock-turn  (Month 6 refuses to lock until a marriage decision is made)
        ↓
Every subsequent month: process_month_for_player() adds spouse income,
     spouse expense, satisfaction drift, negotiated household modifier.
```

Persistent, non-repeatable in the normal path, and genuinely wired into the core loop. This is the part your brief assumed was missing. It isn't.

---

## C. Current Spouse Negotiation Flow (as actually coded)

```
Gate: spouse_archetype ∉ {null,'single'}  AND  game_control.negotiation_enabled = true
        ↓
generate_proposal(user_id, month, archetype)   ← seeded; refresh cannot reroll it
        ↓  (proposal has kind, title, description, ev_note, ask amount)
STEP 1  POST /negotiate { message: freetext }
   ├─ ai_service.extract_intent()  (LLM if configured, else offline regex parser)
   ├─ closed-schema validate(); ambiguous → 400 needs_rephrase (never guessed)
   ├─ write audit row (confirmed=false, outcome=pending)
   └─ return interpretation + confirmation prompt   ← NO money moves
        ↓  player sees "Offer her ₹18,000 …?" and confirms
STEP 2  POST /negotiate/commit { intent, params }
   ├─ negsvc.evaluate()  ← DETERMINISTIC, no network; the only money decision
   │     • round 1 counter NEVER auto-accepts ("can't convince instantly")
   │     • from round 2: accept iff offer >= ask × min_ratio(archetype, satisfaction)
   │     • max 3 rounds → auto-resolve at her floor
   │     • effects by KIND: investment→stocks, protection→EF, saving→permanent
   │       expense cut, lifestyle→pure consumption
   ├─ update player_state (satisfaction + effect fields)
   ├─ write audit row (confirmed=true, full rule_input/rule_output, outcome)
   └─ ai_service.narrate() voices the result (template if no LLM) — no money effect
        ↓
Dashboard shows outcome, reason, satisfaction bar, round x/3.
```

Reasons ARE surfaced (`result['reason']` + `spouse_line`). Outcomes are financially meaningful and flow into next month. This satisfies most of your §8–§14 and §36 "Negotiation" criteria **already**.

---

## D. Problems Found

| ID | Problem | Location | Severity | Why it's wrong |
|----|---------|----------|----------|----------------|
| **D-01** | **Three divergent spouse definitions; engine reads only one.** `marriage_migration.sql` seeds one set of archetype numbers, the live `spouse_archetypes` table holds another, and Python `constants.ARCHETYPES` holds a third. The engine uses **only** `constants.ARCHETYPES`. The DB table is dead weight. | `marriage_migration.sql` L23-36 vs live DB vs `constants.py` L165 | **Critical** | Live DB + constants currently agree, but `marriage_migration.sql` is stale (e.g. Earner income 36,000 vs live 16,000; Saver −9,000 vs −2,500). Its `ON CONFLICT DO UPDATE` means **re-running the migration silently overwrites the tuned live values with wrong ones**, corrupting balance mid-event. And any UI that reads the DB table would show numbers the engine never applies. No single source of truth (your §4/§27 requirement). |
| **D-02** | **Docs say the feature is unbuilt; it is shipped.** `MARRIAGE_SYSTEM_DESIGN.md` ("Proposed, future version… not scheduled"), `HOUSEHOLD_MIGRATION_PLAN.md` ("No code until approved"), `ADR-014` ("PROPOSED — awaiting ratification") all describe a system that is in fact live in code and DB. | design docs vs code | **High** (governance) | The team is flying blind: the authoritative design record contradicts production. Whoever next touches this will either rebuild what exists or break it. Also, the shipped model is `household_id`-free (keyed on `user_id` + a `spouse_archetype` column), i.e. the "household foundation" the docs call a hard prerequisite was **skipped**. That may be a fine V1 call — but it was never written down. |
| **D-03** | **Scoring normalization is only half household-aware.** `net_worth_component` adds spouse *income* to the "expected resources" denominator, but not the spouse's **injected assets** (stocks/gold/EF) nor the **wedding cost**. | `scoring.py` L20-33 | **High** (fairness) | Numerator (net worth) includes injected assets − 25,000 wedding; denominator does not. Result: marrying an **asset-heavy** archetype (Investor injects ~55k, Anchor ~40k) **inflates** the net-worth score; marrying the **income-heavy** Earner (injects ~5k, pays 25k) **deflates** it. `MARRIAGE_SYSTEM_DESIGN.md` §5 explicitly warned this must be re-derived; it was implemented only for income. Directly threatens the "EV-balanced, no dominant archetype, viable single" fairness promise (§24, ADR-000). *Needs confirming against `marriage_ev_sim.py`'s assumptions — flagged, not yet proven exploitable.* |
| **D-04** | **Negotiation commit and marriage have no idempotency/concurrency guard** — unlike every other money route (`/allocate-month`, `/sell`, `/handle-relative` all use `mark_action`). | `player_routes.py` `negotiate_commit` L699-751; `courtship_marry` L1099-1216 | **High** | `_negotiation_context` decides "already settled" by reading rows, then commit writes — a classic TOCTOU. Two tabs / a double-click / a replayed request can both pass the check and both apply effects. For a **saving** proposal this stacks a permanent `household_expense_modifier` cut for one-off cash — a **money exploit**. `courtship_marry`'s "already married?" check is likewise read-then-write: concurrent calls can double-inject spouse assets and double-charge/again the wedding. Your §25 exploit checklist calls these out by name. |
| **D-05** | **Confirmation gate is advisory, not enforced.** `/negotiate/commit` trusts `intent`+`params` from the request body and never verifies a matching `confirmed=false` interpretation row exists. | `player_routes.py` L714-726 | Medium | A client can skip Step 1 entirely. Not a money exploit (evaluate() is deterministic and server-side), but it breaks the ADR-003 audit chain: `rule_input` doesn't reference the interpretation, so "what the player was shown vs what ran" isn't provable. Your §28 wants the backend authoritative *and* auditable. |
| **D-06** | **Admin content layer is unseeded and effectively unused.** `spouse_proposals` and `spouse_dialogue` are empty; the system silently falls back to hardcoded `DEFAULT_PROPOSALS` and template lines. | live DB (0 rows) | Medium | Works, but the "admin authors proposals/dialogue" capability (ADR-014 §2, your §6 event-engine parallel) is dormant. Every player sees the same 4 hardcoded proposals. Fine for a first event; a gap against the design's admin-control goal. |
| **D-07** | **`courtship_marry` recomputes the score with the wrong monthly-expense base.** It passes `monthly_expense = spouse_expense` (~6.5k) instead of full household expense (~78k) to the scorer. | `player_routes.py` L1190-1196 | Low | Produces a transiently inflated liquidity/score between marriage and the next month's processing (which recomputes correctly). Cosmetic but misleading during the marriage round. |
| **D-08** | **No ENGAGED/DIVORCED states despite the brief's state machine.** `spouse_archetype` encodes only null/`single`/archetype. | `constants`/`player_state` | Low (by design) | Matches ADR-002's deliberate deferral of divorce. Listed so the SINGLE→ENGAGED→MARRIED→DIVORCED model in your §4 isn't mistaken for a bug. Recommend **keep deferred**. |

---

## E. Hidden Bugs (targeted search per your §34.E)

- **Duplicate transactions:** D-04 — no idempotency key on negotiation commit or marriage; other routes have it. Confirmed gap.
- **State mismatch:** D-01 (three archetype sources) and D-02 (docs vs code). The most dangerous is the DB `spouse_archetypes` table diverging from `constants.ARCHETYPES` — today they match by luck, nothing enforces it.
- **Race conditions:** D-04 read-then-write in `negotiate_commit` and `courtship_marry`. The monthly RPC (`process_month_atomically`) and `expected_month` guard protect the main loop, but these two spouse paths sit outside that protection.
- **Frontend manipulation:** Low risk. `evaluate()` derives all effects server-side from `proposal.kind`; the client cannot inject effect fields or amounts beyond a counter-offer integer, which is validated (`amount >= 0`, `<= cash`). D-05 is the residual (skippable confirmation), not a money hole.
- **Incorrect calculations:** D-03 (normalization) and D-07 (marry-time score). D-03 is the one with competitive-fairness consequences.
- **Missing persistence:** None found — spouse state, satisfaction, modifier, reveals, and negotiation history all persist and reload correctly.
- **Orphaned spouse / duplicate household records:** N/A — no `household` rows in this shipped model (D-02). Spouse is a column, so there's nothing to orphan. (This is also *why* several of your §26 fields — `household_id`, `event_id` on transactions — don't exist yet.)
- **Inconsistent relationship status:** Single source (`spouse_archetype`), read identically by dashboard, negotiation, monthly processor, and scoring. Consistent.
- **Negative/zero/huge amounts:** Guarded in `validate()` (negative counter rejected) and `evaluate()` (offer > cash rejected). Zero is accepted as a counter — harmless (round-1 never accepts; round-2+ zero is below floor). Huge amounts are cash-capped.

---

## F. Proposed Correct Architecture (target after repair — mostly already true)

```
player_state.spouse_archetype   ← SINGLE SOURCE OF TRUTH (already)
        ↓
Spouse stat block  ← ONE definition. Fix D-01: make constants.ARCHETYPES the
                     canonical source and either (a) delete the DB table, or
                     (b) generate/seed it FROM constants and have the engine read it.
        ↓
Household math (monthly_processor)  ← recurring income/expense/drift/modifier (already)
        ↓
Negotiation (negotiate → confirm → commit)
   + idempotency key per (user, month)      ← fix D-04
   + commit verifies a prior interpretation ← fix D-05
        ↓
Financial effects (server-derived by kind)  ← already safe
        ↓
Scoring: denominator = INITIAL_BUDGET + salary·m + spouse_income·m
                       + spouse_injected_assets − wedding_cost   ← fix D-03
        ↓
Leaderboard  ← rewards management quality, not just "two incomes" (your §24)
```

---

## Recommended fix order (surgical — no rewrite; honors your minimal-edit rule)

1. **D-01 (Critical, ~1 file):** Make `constants.ARCHETYPES` canonical. Either delete the unused `spouse_archetypes` table or regenerate its rows from constants, and **fix or delete `marriage_migration.sql`'s stale seed** so no one can re-run it and corrupt balance. Add a tiny startup assert that DB == constants if you keep the table.
2. **D-04 (High, 2 endpoints):** Add the existing `mark_action` idempotency pattern to `negotiate_commit` (key `negotiate:{month}`) and `courtship_marry` (key `marry`). This closes the only real money exploit.
3. **D-03 (High, 1 function):** Extend `net_worth_component`'s denominator to include spouse-injected assets and the wedding cost. **First** read `marriage_ev_sim.py` to confirm the intended balance target, then re-run the EV sim as the acceptance gate (per ADR-002 §8.3).
4. **D-05 / D-07 (Medium/Low):** Enforce the confirmation-row lookup in commit; pass full expense to the marry-time scorer.
5. **D-02 (governance):** Update the three design docs to "IMPLEMENTED (V1, household-less)" so the record matches reality. Cheap, prevents the next person breaking it.
6. **D-06 (optional):** Seed `spouse_proposals` / `spouse_dialogue` from `DEFAULT_PROPOSALS` if you want the admin layer live for the event.

**Explicitly NOT doing** (deferred by design; your §21/§33 forbid over-engineering): divorce, children, in-law events, joint-goal tables, contribution-ratio models, ENGAGED state. Say so if you want any of these reopened — each is an L4/L5 change with its own EV-balance gate.

---

## Test cases to add (map to your §32)

- `test_archetype_source_consistency` — DB `spouse_archetypes` == `constants.ARCHETYPES` (guards D-01).
- `test_negotiate_commit_idempotent` — replayed/concurrent commit applies effects once (D-04).
- `test_marry_idempotent` — double marry never double-injects assets or double-charges wedding (D-04).
- `test_nw_normalization_includes_injected_assets` — two archetypes with equal total resources but different asset/income split score equally for equal management (D-03).
- `test_commit_requires_prior_interpretation` — commit without a confirmed interpretation is rejected (D-05).
- Keep the existing determinism / cross-player-fairness / no-LLM-dependency suites green.

---

*Nothing above has been applied. On your go-ahead I'll implement in the order above, smallest diffs first, one fix per commit, tests alongside — and re-run `marriage_ev_sim.py` before touching the scorer.*
