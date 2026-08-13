# Money Master — Confirmed Defect Repair Report

**Date:** 2026-08-13
**Basis:** FULL_SYSTEM_AUDIT.md (2026-08-13) as ground truth. No redesign, no new features.
**Deployment model (your choice):** migration files only — nothing was applied to your live Supabase.
**Verification honesty:** where an HTTP/runtime path could not be exercised here (no Flask + live DB in this environment) it is marked **NOT VERIFIED — CODE REVIEW ONLY**. The A-01 lock, by contrast, was proven on a real Postgres.

---

## A-01 — Cross-action cash race
**Status:** FIXED — empirically verified against a real Postgres.
**Files changed:**
- `a01_atomic_player_txn_migration.sql` (NEW — the RPC + grants)
- `backend/services/game_service.py` (`apply_player_txn`, `PlayerTxnError`)
- `backend/routes/player_routes.py` (`take_loan`, `allocate_month`, `handle_relative`, `negotiate_commit`, `courtship_marry`)
- `backend/services/choice_service.py` (`execute_choice`)
- `backend/tests/test_a01_concurrency.py` (NEW — the proof)

**Concurrency mechanism:** one primitive, `public.player_apply_atomic(...)`, following the exact `sell_asset_atomic` / `process_month_atomically` pattern:
1. Claims the idempotency key **inside** the transaction (`INSERT … player_month_actions`; `unique_violation` ⇒ `DUPLICATE_ACTION`).
2. `SELECT … FROM player_state WHERE user_id = … FOR UPDATE` — a concurrent action on the same player blocks here.
3. Re-checks affordability under the lock (`p_require_cash`).
4. Applies **additive deltas** (`cash = cash + Δ`, never an absolute value from a stale read), then child loan inserts/updates, in the same transaction.

Every cash route now computes its economic result in **Python** (EMI, negotiation outcome, marriage injection, scoring — all unchanged) and hands the RPC only deltas + guards. Because writes are additive under a row lock, two concurrent different actions compose correctly (`X + loan − invested`) instead of last-write-wins.

**Concurrent test result (real Postgres, `tests/test_a01_concurrency.py`):**
- 80 threads on ONE player row — 40 × loan(+₹5,000) and 40 × allocate(−₹3,000), shuffled: final `cash = 1,080,000` (exact), `loans = 200,000` (exact), `stocks = 120,000` (exact), **0 errors**. A lost-update bug would corrupt these totals; it did not.
- 25 threads with the SAME `action_key`: **exactly 1 applied, 24 got DUPLICATE_ACTION**, cash moved once.
- Also single-session: delta apply, affordability rejection (no mutation), satisfaction clamp, loan-child insert, marriage net-worth recompute — all pass.

**Financial result:** economy identical. EV simulation unchanged (below); full suite green; deltas reproduce each route's prior arithmetic (allocate's `max(0, available−invested)` tolerance preserved via a sub-₹2 cash floor; marriage's intentional negative-cash-then-safety-net preserved).

---

## A-02 — Consistent turn-lock + processing lock
**Status:** FIXED.
**Routes protected (one rule, `game_service.require_playable` = game ACTIVE and player not `waiting`):** `take_loan`, `allocate_month`, `set_insurance`, `sell`, `buy_choice`, `handle_relative`, `negotiate`, `negotiate_commit`, `courtship_reveal`, `courtship_marry`. `lock_turn` additionally refuses while processing.
**Processing-state protection:** `admin next_month` sets `game_control.game_status = 'processing'` for the WHOLE read → compute → write cycle and restores `'active'` on every exit path (success, no-players, validation error, RPC error). While `processing`, `require_playable` rejects (409), so no player action can land between `get_all_players()` and the atomic write and be overwritten.
**Tests:** the rule is a single shared function; the money paths' locking is covered by A-01's tests. HTTP-status behaviour per route (WAITING/LOCKED/PROCESSING → rejected) is **NOT VERIFIED — CODE REVIEW ONLY** (no Flask harness in this environment).

---

## B-01 — Complete reset cleanup
**Status:** FIXED.
**Tables cleared:** `reset_player` now also deletes `player_negotiations` and `player_month_allocations`; `start_game` now also deletes `player_month_allocations`. (Both previously omitted allocations; reset also omitted negotiations, which made a reset player unable to negotiate and showed stale allocation records.)
**Reset tests:** **NOT VERIFIED — CODE REVIEW ONLY** (requires live DB writes; deletes are blocked in this sandbox). The delete lists are now a superset of every per-game, player-scoped table.

---

## C-01 — Validate relative_type
**Status:** FIXED.
**Allow-list:** `VALID_RELATIVE_TYPES = {"parents", "sibling", "in_laws"}` in `models/constants.py`; `handle_relative` lower-cases the input and rejects anything not in the set (backend authoritative). Note: the relative-help UI is retired, so this endpoint is reachable only by direct API calls; the list keeps it bounded. If the mechanic is revived from `public.relative_events`, source the set there.
**Exploit test:** **NOT VERIFIED — CODE REVIEW ONLY** (route-level). By construction, an invented/empty/null `relative_type` no longer produces a fresh idempotency key, so trust can no longer be farmed via fabricated relatives.

---

## D-09 — Scoring consistency
**Status:** FIXED.
**Scorer callers now share ONE contract** via `engine.scoring.spouse_score_inputs(spouse_arch_id) → (income, injected_assets, wedding_cost)`: `monthly_processor`, `courtship_marry`, and `admin update_player` (the gap) all feed the same three inputs; `allocate_month1` is single ⇒ zeros. No scoring formula is duplicated — only the shared input helper.
**Consistency tests:** the 69-test suite (incl. `test_marriage`, `test_capital_preservation_scores_equally_across_archetypes`) passes; a capital-preserving player now scores identically across archetypes, and the admin-corrected married player uses the same normalization as the monthly engine.

---

## D-08 — Event category consistency
**Status:** FIXED.
**Category propagation:** in `event_engine.generate_events_for_player`, auto-mode admin events now use `ev.get('category', 'general')` — identical to manual mode — instead of the hard-coded `'admin'`. An authored event's category (hence insurance eligibility) is now the same whether `auto_events` is on or off.
**Insurance test:** **NOT VERIFIED — CODE REVIEW ONLY** (engine-level); both code branches now read the same authored field, verified by inspection.

---

## D-10 — Month-1 duplicate audit log
**Status:** FIXED.
**Mechanism:** `allocate_month1` now claims `mark_action(user_id, 1, 'alloc:1')` before writing; the `player_month_actions` primary key makes a concurrent second first-allocation lose the claim, so only one month-1 `player_month_log` row is written. Financial behaviour unchanged (the state `upsert` was already idempotent).
**Duplicate-log test:** **NOT VERIFIED — CODE REVIEW ONLY** (route-level); the claim is the same atomic primitive proven in A-01's concurrency test.

---

## Totals

```
TOTAL TESTS   69   (67 prior + 2 new real-Postgres concurrency tests)
PASSED        69
FAILED         0
SKIPPED        0   (concurrency test runs here; auto-skips only where pgserver/psycopg absent)

EV SIMULATION
BEFORE:  GATE1 spread 4.0% (market ON) / 5.5% (market OFF) — PASS; single-viability & no-dominance PASS
AFTER:   identical — 4.0% / 5.5% — PASS

ECONOMIC MODEL CHANGED?   NO
SCHEMA CHANGED?           YES — one NEW additive function (player_apply_atomic). No table/column
                          changes. Reversible with DROP FUNCTION. (marriage_migration.sql seed was
                          also corrected earlier for D-01; still additive.)
NEW FEATURES ADDED?       NO
```

**REMAINING KNOWN RISKS**
1. **Deployment coupling.** The rewritten routes call `player_apply_atomic`, which does not yet exist in your DB (you chose migration-files-only). Apply `a01_atomic_player_txn_migration.sql` in the Supabase SQL editor **before** deploying this backend, or the money routes will 500.
2. **HTTP-level tests are code-review-only** for A-02/B-01/C-01/D-08/D-10 — no Flask+live-DB harness here. The underlying primitives (row-lock RPC, `player_month_actions` claim) are empirically proven; the per-route wiring is verified by inspection.
3. **New finding below** is intentionally left unfixed pending your approval.

---

## NEW FINDING (not in A-01…D-10 — reported, NOT fixed)

**Finding:** `courtship_reveal` "extra date" cash charge is an unserialised read-modify-write on `player_state.cash`.
**Evidence:** `backend/routes/player_routes.py` — after the 3rd reveal, `cash = float(player.get('cash',0)); … new_cash = cash - cost; supabase.table('player_state').update({'cash': new_cash})…`. Same pattern as A-01, but `courtship_reveal` was **not** in the audit's A-01 path list (which named take_loan, allocate_month, handle_relative, choice_service, negotiate_commit, courtship_marry).
**Severity:** Low. The charge is ₹5,000 and only on the 4th+ reveal in Month 6; exploiting the race needs concurrent identical reveal requests, and the `player_spouse_reveals` PK already dedupes the reveal row.
**Why it matters:** for full consistency, this is the one remaining cash mutation not behind `player_apply_atomic`; a concurrent duplicate could double-charge (or, with the reveal-row PK, charge once but race the balance write).
**Recommended fix (one line of routing):** deduct via `apply_player_txn(user_id, player['month'], action_key=f"reveal:{archetype_id}:{trait_key}", require_cash=cost, deltas={"cash": -cost})`, then insert the reveal row. ~6 lines, no new RPC.
**I did not change this** per your instruction to report new findings and await approval. I did apply the A-02 gate (`require_playable`) to this route, since A-02 explicitly requires the turn-lock on all mutating endpoints.

Say the word and I'll apply the one-line reveal fix.

---

## How to deploy
1. Supabase SQL editor → run `a01_atomic_player_txn_migration.sql` (additive; safe to re-run).
2. (If not already applied) run the corrected `marriage_migration.sql` seed — or skip, since your live archetype rows already match constants.
3. Deploy the backend.
4. Optional: in a staging project, run `python -m unittest tests.test_a01_concurrency` (after `pip install pgserver "psycopg[binary]"`) or point a load test at `/loan` + `/allocate-month` concurrently to reproduce the empirical proof against your own stack.
