# Money Master — V1 QA Review

**Date:** 2026-07-13 · **Reviewer:** Lead Software Engineer (Claude) · **Scope:** current implementation vs. `PRD.md`, `SRS.md`, `ARCHITECTURE_DECISIONS.md` (ADR-000…013), `V1_IMPLEMENTATION_PLAN.md`.
**Method:** static code review of `backend/` (engine, routes, services, models), `frontend/`, `supabase.sql` + migrations, and live-database inspection (project `ujoqdsesfctxmzmlxewu`: schema, RLS policies, security advisors). No fixes applied. No architecture, features, or business rules changed or proposed.

No new ADRs were created — every issue below is a defect against or gap in the *existing* approved decisions, classified per ADR-013.

---

## Summary

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 3 |
| Medium | 2 |
| Low | 5 |
| Informational / carry-forward from existing docs | 3 |

QA-014 (High) was added on 2026-07-14 during T1.2 (Cross-player Fairness verification); it was discovered by the verification suite itself, not by static review, and is the reason the High count moved from 2 to 3.

Two items already tracked in `V1_IMPLEMENTATION_PLAN.md` (B1/T0.1–T0.3) were **verified resolved this session** (M0.1/M0.2): the ADR-008/009 fairness fixes and the idempotency migration are confirmed live on the correct Supabase project. That work is not re-listed as an issue below; see QA-012 for the one part of B1 that remains genuinely unverifiable from the repo (backend deploy commit on Render).

---

## QA-001 — Admin-only financial mutation RPC has no authorization check and is publicly callable

**Severity:** Critical
**Risk Classification (ADR-013):** Level 4 (auth/permissions — binding rule 3: "Security is Level 4")

**Description:** `public.process_month_atomically` — the sole function permitted to mutate player financial state and advance the game month — is declared `SECURITY DEFINER` with no `REVOKE` anywhere in the codebase (confirmed by grep across all `.sql` files: zero `REVOKE`/`GRANT EXECUTE` statements exist). Supabase's live security advisor confirms this function is currently executable by both the `anon` and `authenticated` Postgres roles via `POST /rest/v1/rpc/process_month_atomically` — i.e., directly through Supabase's REST API, with no involvement of the Flask backend or its `admin_required` decorator at all.

The function body performs no `auth.uid()` / admin-membership check of its own — it only validates month-sequencing and idempotency. This means anyone holding the public anon key (which is intentionally embedded in `frontend/js/config.js`, as it must be) can call this RPC directly with an arbitrary JSON payload and: overwrite any player's cash/stocks/gold/loans/net worth/score, insert fabricated loans, insert fabricated `player_month_log` audit rows, and advance `game_control.current_month` — completely bypassing the entire admin-authorization model the rest of the app relies on.

**Root Cause:** `admin_required` (Flask-layer) was implemented as the sole authorization gate; the underlying Postgres RPC it calls was never independently locked down (no `REVOKE EXECUTE ... FROM anon, authenticated`, no internal role check). Defense-in-depth was assumed but not built.

**Files Affected:** `supabase.sql` (lines 185–286, function definition), `fairness_fixes_migration.sql` (same function, `CREATE OR REPLACE`) — both need the fix; live DB function.

**Recommended Fix:** Add `REVOKE EXECUTE ON FUNCTION public.process_month_atomically(...) FROM PUBLIC, anon, authenticated;` (keep it callable only by `service_role`, which the Flask backend uses) as a migration. Apply the same audit to any other `SECURITY DEFINER` function before the next live event. Must deploy between games per ADR-012/013.

---

## QA-002 — Stock/gold market returns are applied twice per month through two independent mechanisms

**Severity:** High
**Risk Classification (ADR-013):** Level 3 (business logic / economic calculation — discriminator rule: mutates financial records)

**Description:** Every month, `monthly_processor.process_month_for_player` STEP 4 calls `market_engine.calculate_investment_growth`, which applies the ADR-009 global-seeded stock/gold return (base growth ± volatility, seeded `GLOBAL:{month}:market`). Then STEP 5 calls `event_engine.generate_events_for_player`, whose category 3 ("MARKET FLUCTUATION") independently rolls a *second*, separately-seeded (`GLOBAL:{month}:market_events`) stock swing of −12%…+15% (40% chance/month) and an optional gold swing, which then gets applied multiplicatively on top of the already-updated stock/gold balance via `apply_event_to_state`.

Net effect: in months the event fires (~40% of the time), a player's stock position receives two independent, additive-in-effect market shocks in the same month — e.g., an 8% base month could become roughly `(1.08+volatility) × (1 + event_swing) − 1`, materially exceeding the −15%…+20% range documented as the complete picture in PRD §5. This isn't a fairness violation (both paths are globally seeded, identical across all players), but it silently doubles effective volatility beyond the tuned/documented economy and produces a redundant, confusing pair of log lines ("📈 Stocks: +X%" and "⚡ Market Rose: +Y%") in the same month's summary.

**Root Cause:** `event_engine.py`'s "Market Fluctuation" category appears to predate the ADR-009 fairness fix (which introduced the dedicated global path in `market_engine.py`) and was never removed or reconciled once `market_engine.py` took over that responsibility.

**Files Affected:** `backend/engine/event_engine.py` (lines 138–173, category 3 block), `backend/engine/monthly_processor.py` (STEP 4/5 sequencing).

**Recommended Fix:** Decide which mechanism is canonical (recommend keeping `market_engine.py`'s ADR-009 global path as the single source of stock/gold market movement) and remove the duplicate "Market Fluctuation" event category from `event_engine.py`, or explicitly document why both are intended and retune PRD §5's stated volatility range to match reality. This is a business-logic correctness fix referencing existing ADR-009 — no new ADR needed.

---

## QA-003 — `/sell` has a read-then-write race that can duplicate cash credit for a single asset sale

**Severity:** High
**Risk Classification (ADR-013):** Level 3 (business logic — financial mutation)

**Description:** `player_routes.sell_asset` reads `current_val = player[asset_type]`, validates `amount_to_sell <= current_val`, then issues an independent `UPDATE player_state SET {asset_type} = new_val` and a separate `INSERT INTO player_sales`. There is no idempotency guard (unlike `/buy-choice` and `/handle-relative`, which now claim a `player_month_actions` row *before* touching money) and no atomic/conditional update (e.g., `UPDATE ... WHERE stocks >= amount`). Two concurrent identical sell requests (double-click, retry-on-timeout, or a scripted replay) will both pass the balance check against the same stale `current_val`, both write, and — critically — both insert a `player_sales` row, crediting the player cash **twice** next month for a single physical reduction in the asset balance. This mints money the design never intended to exist.

**Root Cause:** The sell endpoint was not brought in line with the same durable-claim pattern applied to buy-choice/relative-help during the "durable idempotency" fix this cycle — it was evidently out of scope for that fix, but the underlying race is the same shape.

**Files Affected:** `backend/routes/player_routes.py` (lines 209–263, `sell_asset`).

**Recommended Fix:** Make the balance decrement atomic and conditional (e.g., a single `UPDATE ... SET {asset} = {asset} - :amt WHERE user_id = :uid AND {asset} >= :amt`, checking rows-affected before inserting the sale/credit row), or route sells through the same `player_month_actions`-style claim keyed on a client-supplied idempotency token. Test plan: fire two concurrent identical sell requests in the verification suite (M1) and assert exactly one credit row is produced.

---

## QA-004 — Admin manual correction recomputes net worth but leaves the ranking score stale

**Severity:** Medium
**Risk Classification (ADR-013):** Level 3 (business logic — affects ranking, discriminator rule)

**Description:** `/admin/update-player` recomputes `net_worth` from the edited components (correctly — "never trust a typed value," per its own comment) but does not recompute `financial_health_score` or `discipline_score`. Since the public leaderboard ranks by `financial_health_score` first (`ORDER BY financial_health_score DESC, net_worth DESC`), any admin correction to cash/stocks/gold/emergency_fund/loans silently desyncs the displayed rank from the player's actual corrected state until the next month is processed and the engine recomputes it. In a live event, an admin fixing a data-entry mistake mid-round could produce a visibly wrong leaderboard for the remainder of that round.

**Root Cause:** `admin_routes.update_player` only imports/uses the net-worth arithmetic; it never calls `engine.scoring.calculate_financial_health_score`, unlike `player_routes.allocate_month1`, which does.

**Files Affected:** `backend/routes/admin_routes.py` (lines 261–307, `update_player`).

**Recommended Fix:** After merging edited fields, also recompute `risk_level` (`market_engine.calculate_risk_score`) and `financial_health_score` (`engine.scoring.calculate_financial_health_score`) the same way `allocate_month1` does, and persist both alongside `net_worth`. Small, contained change; same audit-log line covers it.

---

## QA-005 — Admin-authored events and optional choices are inserted with no server-side validation

**Severity:** Medium
**Risk Classification (ADR-013):** Level 3 (discriminator rule: "validation on a financial mutation path is Level 3, not Level 2")

**Description:** `POST /event` and `POST /choice-admin` insert `request.json` into `events`/`optional_choices` verbatim, with no checks that `impact_target` is one of the values the engine actually understands (`cash`/`stocks`/`gold`/`expense_increase`), that `event_type`/`reward_type` are valid, that `probability` is within 0–100, or that `cost`/`reward_value` are non-negative. A typo in `impact_target` silently no-ops (the engine's `apply_event_to_state` only handles the known targets and otherwise does nothing — no error surfaces to the admin). A negative `cost` on an optional choice would pay players to "buy" it every month, and isn't caught anywhere downstream. This is admin-only input (a trusted actor, not a player-facing exploit), but it's exactly the kind of live-event data-entry mistake ADR-013's discriminator rule flags as Level 3 because it sits on a financial mutation path.

**Root Cause:** Content-authoring endpoints were built as thin pass-throughs; no schema/bounds validation layer was added when `execute_choice`/`apply_event_to_state` were hardened.

**Files Affected:** `backend/routes/admin_routes.py` (`add_event` lines 200–207, `add_choice` lines 220–227).

**Recommended Fix:** Add field whitelisting + type/range validation before insert (mirrors the pattern already used in `admin_routes.update_player`'s `_EDITABLE`/`_NUMERIC` whitelist and `player_routes.allocate_month1`'s validation). Relevant ahead of Milestone 3 (content authoring) — worth fixing before that content pack is built, so bad content isn't authored against a silently-broken validator.

---

## QA-006 — Leaked-password protection disabled on Supabase Auth

**Severity:** Low–Medium
**Risk Classification (ADR-013):** Level 4 (security — binding rule 3)

**Description:** The live project's Supabase Auth security advisor reports `auth_leaked_password_protection` as disabled — Supabase Auth is not checking new passwords against the HaveIBeenPwned breach corpus. For a short-lived college event with throwaway credentials this is lower-stakes than it would be for a persistent product, but it's a live, currently-real gap with a one-setting fix.

**Root Cause:** Default-off Supabase Auth setting, never enabled.

**Files Affected:** none (Supabase Auth dashboard setting, no repo file).

**Recommended Fix:** Enable "leaked password protection" in Supabase Auth settings before the event. No code or migration required — pure config, Level 4 only because it's a security setting, not because it's hard.

---

## QA-007 — `ADMIN_TOKEN` is documented as required but is dead, unused configuration

**Severity:** Low
**Risk Classification (ADR-013):** Level 1 (documentation/cosmetic — no code path reads it)

**Description:** `DEPLOY_FRESH.md`, `V1_IMPLEMENTATION_PLAN.md` §7.2, and `backend/.env.example` all instruct the operator to set `ADMIN_TOKEN` and describe it as "your admin password." Grep across every `.py` file in the repo finds zero references to `ADMIN_TOKEN` — admin authorization is actually implemented entirely via Supabase JWT + membership in the `public.admins` table (`auth_service.admin_required`/`is_admin_user`). An operator following the deploy doc verbatim would configure a credential that does nothing and could reasonably believe it provides a security boundary it does not.

**Root Cause:** Admin auth was migrated from a shared-token model to the JWT+`admins`-table model at some point; the operational docs and `.env.example` were never updated to match.

**Files Affected:** `DEPLOY_FRESH.md`, `V1_IMPLEMENTATION_PLAN.md`, `backend/.env.example` (docs only — no backend code touches this).

**Recommended Fix:** Remove `ADMIN_TOKEN` from the deploy doc and `.env.example`, and replace the setup instructions with "grant admin: insert the user's `auth.users.id` into `public.admins`."

---

## QA-008 — Emergency-fund bike-lock-in warning is a no-op stub

**Severity:** Low
**Risk Classification (ADR-013):** Level 1 (cosmetic — UX text only)

**Description:** `sell_asset` contains:
```python
if asset_type == 'emergency_fund' and player.get('bike_lock_in_months', 0) > 0:
    # Allow but warn
    pass
```
The comment promises a warning; none is ever produced (no field added to the response, no log line). The sale proceeds identically to any other sale. Not a financial defect — the sale is allowed either way, per the comment's own intent — just dead code that reads as if a warning exists when it doesn't.

**Root Cause:** Stub left in place after an earlier design intent was not completed.

**Files Affected:** `backend/routes/player_routes.py` (lines 236–239).

**Recommended Fix:** Either implement the warning in the JSON response (`"warning": "..."` field, since this doesn't block the sale) or remove the dead conditional and comment.

---

## QA-009 — Some fixed-value events produce no log line for stocks/gold impacts

**Severity:** Low
**Risk Classification (ADR-013):** Level 1 (cosmetic — display/log completeness)

**Description:** `event_engine.apply_event_to_state`, in the `etype == 'fixed'` branch, appends a log message for `target == 'cash'` but not for `target == 'stocks'` or `target == 'gold'` (the balance is updated correctly; only the human-readable log line is missing). A player receiving a fixed stocks/gold event won't see a corresponding line in their monthly summary explaining the change, unlike every other event category.

**Root Cause:** Log-string construction was written cash-first and not completed for the other two fixed-value branches.

**Files Affected:** `backend/engine/event_engine.py` (lines 304–314).

**Recommended Fix:** Add the missing `log +=` lines for the `stocks`/`gold` fixed branches, matching the existing cash branch's format.

---

## QA-010 — Financial Health Score component breakdown is not exposed as structured data

**Severity:** Informational
**Risk Classification (ADR-013):** Level 2 (read-only display enhancement, no financial mutation)

**Description:** ADR-008/ADR-000 make "formula is public to players" a design goal, and `scoring.calculate_financial_health_score` does compute and return a full component breakdown (net worth / liquidity / debt control / risk protection / discipline). But only the final composite `financial_health_score` is persisted to `player_state` and shown on the leaderboard; the component breakdown only ever reaches the player as one line embedded in that month's free-text `event_log` summary. There's no dashboard element or API field a player can check at any time to see "why" their score is what it is — only a scroll back through monthly text logs.

**Root Cause:** Not a bug — the components are computed and were never wired to a persistent/queryable field, just to the log line.

**Files Affected:** `backend/engine/monthly_processor.py` (score computed, only `.score` persisted), `backend/routes/player_routes.py` (`/dashboard`), `frontend/dashboard.html`/`leaderboard.html`.

**Recommended Fix (not urgent, Level 2 if picked up):** Persist the components dict (e.g., a JSON column or a small companion table) and surface it on the dashboard, so "public formula" is a standing, checkable fact rather than something inferable only from scrollback text.

---

## QA-011 — `player_month_log` is a coarse per-month text summary, not a structured transaction ledger

**Severity:** Informational
**Risk Classification (ADR-013):** N/A — accepted V1 architecture, not a defect

**Description:** The project's original data-model brief calls for a `transactions` table maintaining granular, never-overwritten financial history. What's actually implemented is `player_month_log`: one append-only row per player per month, with a single free-text `summary` string concatenating that month's events. This satisfies SRS Invariant 4 at month granularity (nothing is ever overwritten, one row per month, admin corrections get their own row) but doesn't give a queryable, line-item transaction trail — e.g., proving exactly which line item produced a specific ₹-delta requires parsing the summary string, not querying structured rows. This is flagged for awareness, not as a regression — it's consistent with the rest of the V1 architecture and isn't called out as a blocker anywhere in the existing docs.

**Files Affected:** `supabase.sql` (`player_month_log` table), all writers of it.

**Recommended Fix:** None proposed — this would be an architecture-level change (new table, new writers throughout the engine) and is explicitly out of scope for a QA pass. Noting it so it's a conscious tradeoff, not an unconsidered one.

---

## QA-012 — Per-player sequential queries in `/next-month` (confirmed still present)

**Severity:** Medium (High if headcount exceeds ~100 — unresolved blocker B2)
**Risk Classification (ADR-013):** Level 3 (business logic / scalability of the core processing loop)

**Description:** This is a carry-forward, not a new finding — SRS §9 and `V1_IMPLEMENTATION_PLAN.md` (T2.1) already document it. Confirming it's still true in the current code: `admin_routes.next_month` loops over every player and calls `get_active_loans(uid)` and `get_pending_sales(uid, next_m)` individually per player (two DB round-trips × N players), rather than the documented fix (batch-fetch both in two queries total, group in memory). SRS's own honest capacity estimate stands: ~50–100 players safe, ~50–100s processing time at 500 players.

**Root Cause:** Documented and already understood by the team (SRS §9, Plan T2.1) — not a new discovery, included here only to confirm current-code status as part of this review's completeness.

**Files Affected:** `backend/routes/admin_routes.py` (lines 104–118), `backend/services/game_service.py`.

**Recommended Fix:** As already specified in `V1_IMPLEMENTATION_PLAN.md` T2.1 — batch-fetch loans/sales for all players in 2 queries, group by `user_id` in memory. Conditional on confirmed event headcount (B2), per the existing plan.

---

## QA-013 — Admin recovery runbook still missing

**Severity:** Medium (event-blocking per the plan's own checklist, not code-blocking)
**Risk Classification (ADR-013):** Level 2 (operational documentation, no financial mutation)

**Description:** Carry-forward confirmation, not a new finding — SRS §9 and Plan B7/T4.1 already flag this as a required, currently-absent artifact. Confirmed: no runbook file exists anywhere in the repo (searched for anything resembling ops/runbook/recovery docs — only `DEPLOY_FRESH.md`, which covers first-time setup, not mid-event failure recovery).

**Files Affected:** none yet — new doc required.

**Recommended Fix:** As already scoped in the plan (T4.1) — out of this QA pass's remit to write, just confirming it's still open.

---

## QA-014 — Conditional RNG stream consumption breaks market fairness for zero-holding players

**Severity:** High
**Risk Classification (ADR-013):** Level 3 (business logic — affects ranking/financial computation; discriminator rule: mutates financial records and the market rate that ranks players)

**Description:** `market_engine.calculate_investment_growth` draws from a single shared sequential RNG — `rng = _seeded_rng(month)`, one `random.Random` seeded `GLOBAL:{month}:market` per call (ADR-009's global market path). It then draws the stock volatility via `rng.uniform(STOCK_VOLATILITY_MIN, STOCK_VOLATILITY_MAX)` **inside** the `if stocks > 0:` block, and the gold fluctuation via `rng.uniform(-0.02, 0.03)` **inside** the `if gold > 0:` block. Because both draws advance the same sequential stream, a player who holds no stocks skips the stock draw entirely — so their gold draw consumes the stream position that a stock-holding player's *stock* draw would have consumed, and every subsequent draw is shifted by one. The result: two players with identical gold holdings in the same month can receive **different** gold growth rates purely because one of them also happens to hold stocks and the other does not.

This directly violates ADR-009 / SRS §5 Invariant 2 ("market outcomes identical for all players in a month") and SRS §8's cross-player market-fairness guarantee: the market rate a player experiences must depend only on the month, never on their own portfolio composition. Here, portfolio composition (specifically, whether stocks == 0) silently changes the gold rate, so an otherwise-identical gold position is ranked unfairly. Under the ranked leaderboard this is a genuine competitive-fairness defect, not merely cosmetic — a zero-stock player's gold return is computed off a different, uncorrelated draw than everyone else's.

**Root Cause:** The two `rng.uniform()` draws are gated by the same `> 0` guards that gate *applying* the growth. Guarding stream consumption on per-player state makes the draw sequence position-dependent on that state, so the shared stream desynchronizes across players whose holdings differ in which assets are zero. The intent of the `> 0` checks is only to avoid applying growth to an empty position — they were never meant to also change which random value each remaining position receives.

**Files Affected:** `backend/engine/market_engine.py` (lines 45–63, the `STOCKS` and `GOLD` blocks of `calculate_investment_growth`). No other file consumes this RNG stream. `backend/tests/test_cross_player_fairness.py::test_zero_holding_players_do_not_break_fairness_for_others` (lines 141–155) already fails against the current code, correctly demonstrating the defect (12/13 tests pass; this one fails as intended and must not be modified).

**Recommended Fix:** Draw both `rng.uniform()` values unconditionally, once, immediately after seeding — before either `> 0` guard — so the stream is advanced identically for every player regardless of holdings. Keep the existing `if stocks > 0:` / `if gold > 0:` guards, but let them gate only the *application* of the already-drawn delta to the balance and the log line, not the draw itself. This preserves every existing behavior for players who do hold the asset (same seed, same draw order, same rates) while removing the composition dependence. Business-logic correctness fix referencing existing ADR-009 — no new ADR needed. Verified by the existing fairness suite going 13/13.

---

## Verified — not issues (confirmed correct, included for completeness)

- **Loan amortization fix:** `monthly_processor._amortized_emi` correctly implements a standard amortization formula; EMI always exceeds interest, balance provably shrinks to zero over the loan term. Verified against the code, matches the documented fix.
- **Trust score double-write fix:** `handle_relative` now applies trust as a delta to `player_state.trust_score` and no longer overwrites it from summed `player_relative_score` rows. Verified.
- **Idempotency wiring (buy-choice / relative-help):** both claim a `player_month_actions` row via the primary-key-enforced `mark_action` *before* touching money — correct atomic-claim pattern, confirmed in `choice_service.execute_choice` and `player_routes.handle_relative`.
- **Allocation conservation fix:** `allocate_month1` now correctly retains rent/food/transport/family buckets as cash rather than silently discarding them; month-1 net worth reflects actual held assets. Verified.
- **RLS lockdown:** live database policies confirmed — all `player_*` tables are `SELECT`-only on own row for authenticated clients, no write policies exist for `anon`/`authenticated`; all writes correctly require the backend's `service_role` key. `security_fix_rls.sql` is confirmed live (this makes QA-001 the more serious finding — the RLS lockdown that closes the *table-level* write hole doesn't close the *RPC* hole).
- **ADR-008/009 fairness fixes + idempotency migration:** confirmed live on project `ujoqdsesfctxmzmlxewu` this session (M0.1/M0.2) — not re-flagged here.

---

*End of original QA report.*

---

# Addendum — RC3 Audit Findings & RC4 Hardening Session (2026-07-15)

An independent full-repository audit (see `RC3_PRODUCTION_AUDIT.md`) first reconciled the original findings, then hunted for new ones. **Reconciliation:** QA-001, QA-002, QA-003, QA-004, QA-005 were verified **already fixed** in the working tree (RPC revoked, market double-hit removed, atomic sell, admin-edit score recompute, admin input validation). New findings were logged as F-01…F-10. This addendum records their status after the RC4 hardening session.

| ID | Title | Severity | ADR | Status |
|---|---|---|---|---|
| F-01 (=QA-014) | Conditional RNG stream consumption breaks market fairness | High | L3 | **FIXED** — `market_engine.calculate_investment_growth` draws both `rng.uniform` values unconditionally in fixed order; guards gate application only. Test `test_zero_holding_players_do_not_break_fairness_for_others` now passes; suite 30/30; determinism unchanged. |
| F-02 | Fresh deploy per DEPLOY_FRESH never creates `player_month_actions` → buy-choice/relative-help silently break | High | L3/deploy | **FIXED (canonical, one-file).** `supabase.sql` now folds in `admins`, `player_month_actions`, and the `handle_new_user`/`on_auth_user_created` signup trigger, so a fresh install is a single idempotent file that creates every backend dependency (13 tables + 2 RPCs + trigger). All 7 standalone SQL files marked "NOT REQUIRED FOR A FRESH INSTALL / retrofit-only"; `supabase_migration.sql` marked SUPERSEDED. `DEPLOY_FRESH.md` §2, README, and `V1_IMPLEMENTATION_PLAN.md` §7.1 rewritten to the single canonical path. Deployment verification: backend deps ⊆ objects created by `supabase.sql`; no doc references a multi-file or `supabase_migration` fresh path. |
| F-03 | `mark_action` swallows all exceptions and reports "already done" | Medium | L3 | **FIXED** — narrowed to unique-violation via `_is_unique_violation`; all other errors re-raise (loud). Verified by unit check of the helper. |
| F-04 | Stale migrations (`supabase_migration.sql`) re-open public RLS + freeze scoring | Medium (High if run) | L4/deploy | **FIXED** — `supabase_migration.sql` given a bold SUPERSEDED/DO-NOT-RUN header; README's "run supabase_migration.sql" instruction removed and replaced with the canonical four-file order. |
| F-05 | `service_role`-shaped `.env` + stray backend copy inside deployable `frontend/` | Medium | L4 | **MITIGATED** — service-key field stripped, files replaced with deprecation warnings, `frontend/backend/` added to `.gitignore`. **Manual step:** `git rm -r "frontend/backend"` (editor tooling cannot delete). |
| F-06 | DEPLOY_FRESH contradicts the shipped login-only auth flow | Medium (doc) | L1 | **FIXED** — §3/§4a/§6 rewritten for admin-created accounts, login-only students, email/password admin at `/admin-login.html`. |
| F-07 | `ADMIN_TOKEN` dead + self-contradictory docs | Low | L1 | **FIXED** — removed from `DEPLOY_FRESH.md`, `backend/.env.example`, and `V1_IMPLEMENTATION_PLAN.md §7.2`. |
| F-08 | Dead `backend/utils.py` duplicate with divergent validator | Low | L1 | **MITIGATED** (RC5). Reduced to a deprecation stub — the divergent `validate_rpc_payload` and duplicate helpers removed so no one can import the wrong copy. File deletion unavailable in-environment; safe to `git rm backend/utils.py`. |
| F-11 | Stored XSS via player-editable `users.name` rendered unescaped in `innerHTML` | High | L4 (security) | **FIXED** (RC5). `public.users` has a `FOR ALL` RLS policy, so a logged-in student can set their own `name` via the anon key; that name was interpolated unescaped into the public leaderboard (`leaderboard.html`) and admin standings (`admin.js`), executing JS in viewers'/admin's browsers. Added an `escapeHtml()` helper and applied it to every player-name render site. Verified: payload `<img onerror=...>` is neutralized; legitimate names unchanged. Schema unchanged (frozen); fix is output-escaping only. |
| F-09 | Non-atomic cash read-modify-write in buy-choice/relative-help | Low | L3 | **DOCUMENTED** (Low). Narrow single-user concurrent-distinct-action window; recommend routing through an atomic decrement (mirroring `sell_asset_atomic`) in a future between-games change. |
| F-10 | `case_study` seed vs `constants` mismatch; dead `relative_events` table | Low | L1 | **DOCUMENTED** (cosmetic/content). Align seed to lifestyle constants between games. |

**Carried-forward, still open after this session:** QA-006 (leaked-password toggle — one Supabase console setting, also noted in `DEPLOY_FRESH.md` §3), QA-008 (bike-warning stub, cosmetic), QA-009 (missing log line for fixed stocks/gold, cosmetic), QA-010/QA-011 (informational), **QA-012** (per-player sequential queries in `/next-month`) — **deliberately not implemented this session:** it is a conditional Medium (only matters above ~100 players) touching the financial hot path, and it cannot be integration-tested against a live DB in this environment; shipping it unverified would violate the "low-risk / don't weaken verification" rule. The pre-specified batch-fetch fix (SRS §9 / Plan T2.1) remains ready for a future between-games change once headcount is confirmed. QA-013 (admin runbook) is now **FIXED** — see `RUNBOOK.md`.

*End of addendum. Code fixes above are in the working tree, verified by the test suite; deploy is manual and between-games per ADR-012.*
