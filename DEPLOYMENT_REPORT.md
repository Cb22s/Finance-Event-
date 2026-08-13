# Money Master — Deployment Report

**Date:** 2026-08-13
**Basis:** A01_D_REPAIR_REPORT.md (ground truth). No redesign, no new features, no economic/formula changes.
**Target DB:** Supabase project `ujoqdsesfctxmzmlxewu`.
**Honesty rule:** anything not actually executed here is marked **NOT VERIFIED — CODE REVIEW ONLY** or **USER ACTION**.

---

## 1. Database migration status — ✅ APPLIED & VERIFIED (live)
- Applied `a01_atomic_player_txn_migration.sql` to the live DB via migration `a01_atomic_player_txn` → `{"success": true}`.
- Verified on the live catalog:
  - `public.player_apply_atomic(p_user_id uuid, p_month integer, p_action_key text, p_require_cash numeric, p_deltas jsonb, p_sets jsonb, p_clamp_satisfaction boolean, p_recompute_networth boolean, p_loan_inserts jsonb, p_loan_updates jsonb)` exists.
  - `security_definer = true`, `language = plpgsql`.
  - ACL = `postgres=X/postgres ; service_role=X/postgres` → EXECUTE for **service_role only**; anon/authenticated/PUBLIC revoked (confirmed it does NOT appear in the advisor's anon/authenticated-executable warnings).
- Function body confirms (source of truth = the migration file): `SELECT … FOR UPDATE` row lock, in-transaction idempotency claim (`INSERT player_month_actions` → `unique_violation` ⇒ `DUPLICATE_ACTION`), affordability check under the lock (`p_require_cash`), additive updates, transaction rollback on `RAISE` (Postgres aborts the function's transaction), correct grants, `SECURITY DEFINER` with fully schema-qualified names — matching the existing `sell_asset_atomic` / `process_month_atomically` pattern.
- Safe smoke test (non-existent player, no claim) raised `PLAYER_NOT_FOUND` and mutated nothing → function is callable in the service-role context.
- Migration file was **not modified** (no deployment error occurred).

## 2. Backend deployment status — ⛔ USER ACTION (not performed here)
I cannot deploy to your Render host from this environment. The code is verified ready:
- All six cash paths call the atomic helper — `apply_player_txn` at `player_routes.py` lines 395 (take_loan), 537 (allocate_month), 775 (negotiate_commit), 1002 (handle_relative), 1181 + 1252 (courtship_marry), and `choice_service.py:59` (buy_choice). `sell` uses its own `sell_asset_atomic`.
- Correct import present: `from services.game_service import … apply_player_txn, PlayerTxnError, require_playable`.
- The only remaining direct `player_state` cash write is `courtship_reveal` (the reported NEW FINDING, intentionally untouched). The other two direct `player_state.update` calls are non-cash (insurance plan; lock-turn status).
**Action for you:** deploy the backend on Render **after** step 1 (done). Until deployed, the live site runs the old code (which still works — the RPC is additive and unused by old code).

## 3. Test results — ✅ 69 / 69 PASSED / 0 FAILED / 0 SKIPPED
`python -m unittest discover -s tests` → `Ran 69 tests … OK`.

## 4. Concurrency test results — ✅ PASS (real PostgreSQL)
`python -m unittest tests.test_a01_concurrency` → `Ran 2 tests … OK`:
- 80 concurrent threads (40 loan +₹5,000 / 40 allocate −₹3,000) on one row → cash/loans/stocks exact, **no lost updates**, 0 errors.
- 25 threads, same action key → **exactly one applied**, 24 `DUPLICATE_ACTION`.
- Affordability rejected under the lock with no mutation.

## 5. EV simulation result — ✅ UNCHANGED
BEFORE: Gate 1 spread 4.0% (market ON) / 5.5% (market OFF) — PASS.
AFTER: 4.0% / 5.5% — PASS. Economic model unchanged.

## 6. A-02 verification (turn-lock + processing) — ✅ CODE PRESENT / ⚠ HTTP-level CODE REVIEW ONLY
- `require_playable` is applied at 10 mutating call sites (loan, allocate_month, insurance, sell, buy_choice, handle_relative, negotiate, negotiate_commit, courtship_reveal, courtship_marry); `lock_turn` rejects during processing.
- `admin next_month` sets `game_status='processing'` (line 126) and `_restore_active()` runs on all four exits: no-players (134), validation error (212), RPC error (227), success (231).
- **NOT VERIFIED — CODE REVIEW ONLY:** live HTTP WAITING/LOCKED/PROCESSING rejection (no Flask+live-DB harness here). The rule is a single shared function and its money-path locking is covered by §4.

## 7. Reset verification — ✅ CODE PRESENT / ⚠ live delete CODE REVIEW ONLY
- `start_game` deletes `player_negotiations` (line 51) and `player_month_allocations` (line 54).
- `reset_player` list includes both `player_negotiations` and `player_month_allocations` (line 812). No unrelated/global tables added.
- **NOT VERIFIED — CODE REVIEW ONLY:** executing the deletes against the live DB (not run to avoid touching data).

## 8. Relative validation verification — ✅ CODE PRESENT
- `VALID_RELATIVE_TYPES = {"parents", "sibling", "in_laws"}` (`constants.py:110`), imported and enforced in `handle_relative` (`player_routes.py:983`). Input is lower-cased; invalid/empty/`null` values are rejected **before** any idempotency action can be created.
- **NOT VERIFIED — CODE REVIEW ONLY:** the live HTTP rejection cases.

## 9. Scoring consistency verification — ✅
- `spouse_score_inputs(...)` is used by `monthly_processor` (line 338) and admin `update_player` (line 456) — the latter was the D-09 gap.
- `courtship_marry` passes the **same three inputs** (income, injected-assets, wedding cost) computed inline from the identical `ARCHETYPES` data — numerically identical to the helper (contract consistent; noted for transparency that it doesn't literally call the helper).
- The scoring **formula** (`net_worth_component`, `calculate_financial_health_score`) is unchanged apart from the already-approved D-03 parameters.

## 10. Event-category verification — ✅ CODE PRESENT
- Manual mode (`event_engine.py:76`) and auto mode (`:279`) both use `ev.get('category', 'general')`, so an authored event's category — and therefore insurance eligibility — is identical in both paths.
- **NOT VERIFIED — CODE REVIEW ONLY:** live insurance-payout comparison across modes (both branches now read the same field by inspection).

## 11. Month-1 allocation verification — ✅ CODE PRESENT
- `allocate_month1` claims `mark_action(user_id, 1, allocation_key(1))` (i.e. `alloc:1`) before the writes (`player_routes.py:157`), so concurrent first allocations cannot write duplicate month-1 audit logs. Financial behaviour unchanged.

## 12. Remaining known risks
1. **Backend not yet deployed** (§2) — your Render deploy is the final step; the DB is ready and backward-compatible.
2. **`function_search_path_mutable` (WARN)** — the advisor flags `player_apply_atomic` for a mutable `search_path`. The **existing** `sell_asset_atomic` and `process_month_atomically` carry the identical warning, so the new function matches convention and is not a regression. Hardening (`SET search_path = public, pg_temp` on all three) is a security improvement but **outside the approved audit scope**, so it was not changed. Ref: https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
3. **HTTP-level tests are code-review-only** for A-02/B-01/C-01/D-08/D-10 (no Flask+live-DB harness). Underlying primitives are empirically proven (§4).
4. **Phase 2 skipped intentionally:** the live `spouse_archetypes` seed already equals `constants.ARCHETYPES` (re-verified this deploy), so `marriage_migration.sql` was **not** re-applied — no valid production data overwritten.
5. **Pre-existing, out-of-scope advisor items** (unchanged by this work): RLS-enabled-no-policy on `admins`/`player_month_actions` (intentional deny-all), `handle_new_user`/`rls_auto_enable` executable by anon/authenticated, leaked-password protection disabled.

---

## NEW FINDING — NOT FIXED (awaiting explicit instruction)
`courtship_reveal` — the ₹5,000 "extra date" charge is still a read-modify-write on `player_state.cash` (`player_routes.py:1111`), outside the original A-01 path list. Low severity (Month-6 only, 4th+ reveal, `player_spouse_reveals` PK dedupes the reveal). Recommended one-line fix: route the deduction through `apply_player_txn(... action_key=f"reveal:{archetype_id}:{trait_key}", require_cash=cost, deltas={"cash": -cost})`. **Not changed** per instruction. The A-02 gate was applied to this route.

---

## DEPLOYMENT DECISION

**Database migration: SUCCESSFUL and verified. Tests 69/69. Concurrency PASS. EV unchanged.**

➡ **READY — proceed to deploy the backend on Render.** Every condition within my control passed; the one remaining step (backend deploy) is a USER ACTION I cannot perform from here. Nothing failed. Once the backend is deployed, re-run §3–§5 against your stack to close the loop.
