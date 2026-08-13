# Money Master — Full Implementation Verification Audit

**Date:** 2026-08-13
**Scope:** Whole application — player routes, admin routes, month-processing RPC, engines (event/market/scoring/monthly), services, database, RLS/RPC security, determinism/fairness, persistence, UX.
**Method:** Static read of the actual code + live inspection of the Supabase project (`ujoqdsesfctxmzmlxewu`): `pg_policies`, function ACLs, schema.
**Status:** AUDIT ONLY. Nothing changed. Every defect below is confirmed with file/line or a live query, not inferred.

Severity key: **High** = money integrity / fairness, realistically reachable · **Medium** = reachable under concurrency or specific input, real consequence · **Low** = cosmetic, audit-only, or narrow-window.

---

## 0. Headline

The core is sound. Security, determinism, market fairness, money-conservation, and the month-processing transaction are all implemented correctly and I verified the security posture against the live database, not just the SQL files. The confirmed defects cluster in one real theme — **concurrency and state serialization between player actions** — plus a handful of smaller validation/consistency gaps. No new secret leak, no broken RLS, no client-side money mutation.

The single most important finding is **A-01: `player_state.cash` is mutated by read-modify-write in several endpoints with no row lock or version check, and the per-action idempotency keys do not serialize *across* different actions.** Two concurrent actions in the same month (e.g. take-loan + allocate) can lose or duplicate cash. Everything else is smaller.

---

## 1. Confirmed defects

### A. Concurrency / financial integrity

#### A-01 — Lost-update race on `player_state.cash` across endpoints — **High**
**Evidence:**
- `take_loan` reads `player.get('cash')` at request start and writes `cash + amount` — `backend/routes/player_routes.py:488, 545-548`.
- `allocate_month` derives `keep_cash` from the snapshot `available` and writes it — `player_routes.py:321, 388, 401-407`.
- `handle_relative` — `player_routes.py:962, 981-986`.
- `choice_service.execute_choice` — `backend/services/choice_service.py:24, 48, 69`.
- `negotiate_commit` applies `player.get(field, 0) + delta` — `player_routes.py:731-736`.
- `courtship_marry` — `player_routes.py` marry block.

Each path is a classic read-modify-write against the same row. The idempotency guard (`mark_action`) each uses is keyed **per action** (`loan:{m}`, `alloc:{m}`, `relative:{type}`, `choice:{id}`, `negotiate:{m}:{r}`), so it stops a *double-submit of the same action* but does **not** serialize *different* actions. Two requests in the same month (say take-loan and allocate-month fired from two tabs) both read cash = X; one writes `X + loan`, the other writes `X − invested`; whichever lands last wins and the other mutation is lost — which can either destroy money or, in the loan-lands-last ordering, leave invested assets **and** the un-decremented cash (net money creation).

Only two paths are safe by construction: `sell` (row-locking `sell_asset_atomic` RPC, `player_routes.py:891`) and month processing (`process_month_atomically`). 
**Impact:** money integrity + leaderboard fairness under concurrency. Reachable by a motivated student with two tabs or a script; not reachable by normal single-threaded play. This is why I rate it High-consequence / Medium-likelihood.

#### A-02 — Inconsistent `status=='waiting'` (turn-lock) enforcement — **Medium**
**Evidence:** `sell` (`player_routes.py:872`), `buy_choice` (`:925`), `handle_relative` (`:956`), `courtship_marry` (`:1109`) all reject a locked turn. `take_loan`, `allocate_month`, `set_insurance`, and both `negotiate` endpoints have **no** such check. Also, `next_month` never sets a "processing" state — `game_status` stays `active` throughout — so a player action can land between `get_all_players()` (`admin_routes.py:118`) and the atomic write (`:209`) and be silently overwritten by the computed month result.
**Impact:** a player who "locked" can still borrow / re-allocate / change cover / negotiate; and an action during the processing window is lost. State-consistency and fairness inconsistency; compounds A-01.

### B. State management / persistence

#### B-01 — `reset_player` leaves stale negotiation & allocation rows — **Medium**
**Evidence:** `start_game` deletes `player_negotiations` (`admin_routes.py:51`) but **not** `player_month_allocations`. `reset_player` deletes neither — its list omits both (`admin_routes.py:788-790`).
**Impact:** after an individual reset, old `player_negotiations` rows for months ≥6 make `_negotiation_context` return *"This month's conversation is already settled."* (`player_routes.py:628-630`), so negotiation silently never appears for a reset player. Stale `player_month_allocations` also make the dashboard show a previous game's allocation record (`get_month_allocation`, `game_service.py:91`). Confirmed inconsistency between the two wipe paths.

### C. Fairness / input validation

#### C-01 — `handle_relative` does not validate `relative_type` — **Medium**
**Evidence:** `relative_type = data.get('relative_type')` is used unchecked as the idempotency key `f"relative:{relative_type}"` (`player_routes.py:946, 973`). No allow-list.
**Impact:** the "one help per relative per month" cap (the stated design intent, `player_routes.py:965-968`) is bypassable — any new string is a new key, so a client can help unlimited times per month, each purchase converting cash → `trust_score`. Trust is not cosmetic: it raises windfall probability (`event_engine.py:223-226`, `+0.05` at trust>5, `+0.15` at month≥9 & trust>8) and avoids the social-isolation penalty (`event_engine.py:249-260`). So a knowledgeable player can buy an advantage the UI never exposes, bounded only by cash. Fairness defect.

### D. Logic / consistency

#### D-08 — Admin event category differs between auto and manual modes — **Low**
**Evidence:** in manual mode an admin event keeps its authored category (`event_engine.py:76`, `ev.get('category','general')`); in auto mode the same admin event is hard-coded to `'admin'` (`event_engine.py:274`). Insurance only reimburses insurable categories (`monthly_processor.py:216`).
**Impact:** an authored medical/emergency event is insurable when `auto_events` is off but uninsurable when it's on — the same event pays out differently depending on an unrelated global toggle. Inconsistent financial outcome.

#### D-09 — Admin `update-player` score omits the D-03 spouse terms — **Low**
**Evidence:** `update_player` passes only `spouse_income` to the scorer (`admin_routes.py:434-448`), not `spouse_assets`/`wedding_cost`.
**Impact:** after a manual admin correction, a married player's `financial_health_score` uses the pre-D-03 normalization until the next month reprocesses it. Minor divergence between the admin-correction path and the engine. (Honest note: surfaced by this session's D-03 change; the admin path already lagged the engine on other terms.)

#### D-10 — `allocate_month1` is check-then-upsert, not atomic — **Low**
**Evidence:** existence check (`player_routes.py:67-69`) then `upsert` (`:153`) + month-1 log insert (`:154`). Two concurrent first-allocations both pass the check; the state upsert is idempotent (overwrite) but two month-1 `player_month_log` rows can be written.
**Impact:** duplicate audit log rows only — no money effect (upsert overwrites). Cosmetic.

---

## 2. Verified CORRECT (positive findings)

Because this is a verification audit, what passed matters as much as what failed. I confirmed the following are implemented correctly:

- **Client cannot mutate financial state (live-verified).** `pg_policies` shows `player_state`, `player_loans`, `player_negotiations`, `player_month_allocations` each have exactly one policy — `read own` (`SELECT`, `auth.uid() = user_id`) — and no INSERT/UPDATE/DELETE policy, with RLS enabled. `player_month_actions` has RLS on and no policy (deny-all to clients). All writes go through the Flask backend on the `service_role` key (`supabase_client.py:8`). The old `FOR ALL` hole is closed (`security_fix_rls.sql`).
- **Month RPC is locked down (live-verified).** `process_month_atomically` and `sell_asset_atomic` ACLs are `service_role=X/postgres` only — `anon`/`authenticated` cannot execute. Matches `security_fix_rpc_grants.sql`.
- **No secret committed.** `.gitignore` excludes `backend/.env`, `.env`, `frontend/backend/`; `git ls-files` tracks only `backend/.env.example`. `frontend/js/config.js` uses the anon key (safe) and the service key is nowhere in the frontend.
- **Determinism & market fairness.** Global market is seeded by month only, identical for every player (`market_engine.py:16-26`), resolved once per month and passed to all players (`admin_routes.py:128`, `monthly_processor.py:183`). Regime selection and magnitude use separate seeded streams (`market_engine.py:29-33`), and regimes have post-shock memory (`:36-63`). Per-player events are seeded on `(user_id, month)` (`event_engine.py:12-17`); `fair_roll` is a deterministic hash (`game_service.py:149-154`). The double-volatility bug (QA-002) is genuinely removed (`event_engine.py:160-172`).
- **Money conservation & loans.** Allocation keeps the residual as cash by construction (`player_routes.py:338-357`); amortized EMI always exceeds monthly interest so balances converge to zero (`monthly_processor.py:16-31`); debt and EMI-to-income ceilings enforced (`player_routes.py:506-526`).
- **Idempotency where it counts.** Monthly allocation, voluntary loan, choice purchase, relative-help (per type), and — after this session — negotiation and marriage all claim atomically via the `player_month_actions` primary key (`game_service.py:188-213`).
- **Admin input validation.** Event type/target combos, choice cost/reward/probability ranges, and market-move bounds are all validated (`admin_routes.py:241-266, 299-337, 592-594`).

---

## 3. Informational / housekeeping (not defects)

- **Stray `frontend/backend/` folder still physically present.** It is git-ignored and contains only a deprecation warning (no key), so it can't ship a secret via git — but the documented F-05 cleanup (`git rm -r frontend/backend`) hasn't been done, so a *folder-drag* Netlify deploy would still upload the inert stub. Harmless today; finish the deletion.
- **`get_user_id` calls Supabase Auth over the network on every request** (`auth_service.py:49`). Correct, but it's a per-request latency cost and a hard dependency — every endpoint 401s if Auth is briefly unreachable. Consider local JWT verification if event-day load is a concern.
- **Dead imports:** `STOCK_VOLATILITY_MIN/MAX` in `market_engine.py:10`, `hmac` in `auth_service.py:6`. Cosmetic.

---

## 4. Suggested fix priority (for a later pass — not done here)

1. **A-01** — serialize cash mutations. Cleanest: move the read-modify-write for loan / allocate / relative / negotiate / marry into row-locking RPCs like `sell_asset_atomic` already does (`SELECT … FOR UPDATE`, re-read balance under lock, apply delta). Alternatively add an optimistic `version` column and retry. This is the one with real money stakes.
2. **B-01** — add `player_negotiations` and `player_month_allocations` to `reset_player`'s delete list, and `player_month_allocations` to `start_game`'s.
3. **C-01** — validate `relative_type` against a fixed allow-list.
4. **A-02** — apply a single consistent turn-lock (`status=='waiting'`) rule across all mutating player endpoints, and gate player actions while a month is processing.
5. **D-08 / D-09 / D-10** — low priority, fix opportunistically.

None of these are started. Tell me which to implement and I'll do them smallest-diff-first with tests, exactly as with the D-0x marriage fixes.
