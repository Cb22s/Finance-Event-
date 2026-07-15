# Money Master — Release Candidate 1 (RC1) Report

**Date:** 2026-07-13 · **Prepared by:** Lead Software Engineer (Claude) · **Purpose:** release approval only — no code changed in producing this report.
**Inputs:** `QA_REPORT_V1.md` (13 findings), Phase 1 approval (QA-001, QA-003, QA-002) and Phase 2 approval (QA-004, QA-005), live inspection of Supabase project `ujoqdsesfctxmzmlxewu`, current git working-tree state.

---

## 1. Summary of Approved Fixes

Five findings were approved and implemented across two phases. **Their deployment status is not uniform** — this is the single most important fact in this report, so it's stated plainly rather than buried in a checklist:

| ID | Fix | DB layer | Backend code layer |
|---|---|---|---|
| QA-001 | Revoked public EXECUTE on `process_month_atomically` | ✅ **Live now** on the production project — verified via advisor scan and a direct `anon`-role exploit attempt (now `permission denied`) | N/A — pure DB fix, no Python change |
| QA-003 | New `sell_asset_atomic` RPC (locked-row atomic sell) | ✅ **Live now** — function exists, locked to `service_role`, tested via rolled-back transaction | ⚠️ **Not yet deployed** — `player_routes.py sell_asset` now calls this RPC, but that code change is only on disk, not committed or redeployed |
| QA-002 | Removed duplicate market-volatility event category | N/A — pure Python change | ⚠️ **Not yet deployed** — `event_engine.py` edited, not committed or redeployed |
| QA-004 | Admin correction now recomputes `financial_health_score`/`risk_level` | N/A — pure Python change | ⚠️ **Not yet deployed** — `admin_routes.py` edited, not committed or redeployed |
| QA-005 | Server-side validation on `/event` and `/choice-admin` | N/A — pure Python change | ⚠️ **Not yet deployed** — `admin_routes.py` edited, not committed or redeployed |

**In plain terms:** the two database-side changes (QA-001, half of QA-003) are protecting the live project right now, regardless of what backend is running. The four Python code changes (QA-002, QA-004, QA-005, and the other half of QA-003 — the Flask route that calls the new RPC) exist only in this working directory. `git status` confirms three modified, uncommitted files: `backend/engine/event_engine.py`, `backend/routes/admin_routes.py`, `backend/routes/player_routes.py`. **Until these are committed and the backend is redeployed, the running application still has the QA-002/QA-003(route)/QA-004/QA-005 defects in production, even though the code fixing them exists.** This is identical in shape to the "pending pair" pattern already established in this project (SRS §7) — it should be tracked the same way.

New/modified repo artifacts this cycle: `security_fix_rpc_grants.sql`, `sell_asset_atomic_migration.sql` (new standalone migrations, mirroring the existing `fairness_fixes_migration.sql`/`idempotency_migration.sql` pattern), `supabase.sql` (updated for fresh installs), `V1_IMPLEMENTATION_PLAN.md` §7.1 (migration order extended to steps 7–8), `QA_REPORT_V1.md` (this cycle's QA findings).

---

## 2. Remaining Open QA Findings (QA-006 – QA-013)

Per your instruction, none of these were touched. Carried forward from `QA_REPORT_V1.md`:

| ID | Severity | Summary | Status |
|---|---|---|---|
| QA-006 | Low–Medium | Supabase Auth leaked-password protection disabled | Open — one-setting fix, no code |
| QA-007 | Low | `ADMIN_TOKEN` documented as required but unused dead config | Open — docs-only fix |
| QA-008 | Low | Bike-lock-in sell warning is a dead `pass` stub | Open |
| QA-009 | Low | Fixed-value stocks/gold events produce no log line | Open |
| QA-010 | Informational | Score component breakdown never exposed as structured data, only free text | Open |
| QA-011 | Informational | `player_month_log` is a coarse text summary, not a line-item transaction ledger | Open — accepted V1 tradeoff, not a defect |
| QA-012 | Medium (High if headcount > ~100) | `/next-month` still does per-player sequential DB queries — **confirmed still present in current code**, matches SRS §9's own documented ❌ | Open — conditional on event headcount (B2) |
| QA-013 | Medium (event-blocking per the plan's own checklist) | Admin recovery runbook still does not exist — confirmed, no file found in repo | Open |

None of these block the *fixes already approved* from being safely deployed. Several of them (QA-012, QA-013) do block the *event itself* per the project's own existing readiness checklist — see §7.

---

## 3. Known Limitations

Stated honestly, per this project's own standard (SRS §9 does the same):

- **This session's Python fixes are not yet in production.** Covered in §1 — this is the most immediate limitation, not a pre-existing one.
- **No automated verification suite exists.** `find` for a `tests/` directory returned nothing. SRS §8 requires determinism, cross-player fairness, score-bounds, and full-12-month checks before any Level 3+ deploy; today that's still only the ad-hoc 2026-07-12 check run, per the Implementation Plan's own B6/M1. This session's fixes were verified individually (see each fix's "Tests performed" in the Phase 1/2 approvals) but **not** run through a repeatable regression suite, because none exists yet.
- **Event content is not authored.** Live counts on the production project: `events` = 2 rows, `optional_choices` = 1 row, `case_study` = 1 row (the default seed, "The First Job"). This matches blocker B3 exactly — there is no evidence a 12-month content pack exists. Running the event today would mean months 2–12 have essentially no admin-authored events or choices.
- **Only one player row exists on the live project** (`player_count = 1`). No multi-player dry run has been performed on this data.
- **Admin recovery runbook does not exist** (QA-013 / B7) — no procedure for backend-down, wrong-event-published, or early-advance recovery mid-event.
- **Event headcount (B2) is still unconfirmed.** Whether QA-012's per-player query pattern matters depends entirely on this; SRS's own honest estimate is a safe ceiling of ~50–100 players.
- **Household foundation (ADR-001) remains unimplemented** — this is an intentional, already-approved deferral (B4), not a new gap; noted for completeness only.
- **Working tree has other uncommitted/untracked material** beyond this cycle's fixes: `frontend/js/case-study.js` (modified, unrelated to this cycle), and untracked `HOUSEHOLD_MIGRATION_PLAN.md`, `MARRIAGE_SYSTEM_DESIGN.md` (future-scope planning docs, not V1 code — harmless to leave untracked, but worth knowing they're sitting there uncommitted if a clean commit history matters to you).

---

## 4. Deployment Checklist

In order. Nothing here has been executed as part of producing this report.

**Code**
- [ ] Review the diff on `backend/engine/event_engine.py`, `backend/routes/admin_routes.py`, `backend/routes/player_routes.py` (all currently modified, uncommitted)
- [ ] Commit the three modified files + new SQL migrations (`security_fix_rpc_grants.sql`, `sell_asset_atomic_migration.sql`) + updated `supabase.sql`
- [ ] Deploy the committed backend to Render (per `V1_IMPLEMENTATION_PLAN.md` §7.2)
- [ ] Confirm the live Render deployment's commit hash matches the repo HEAD you just pushed (closes the "is the DB fix and the code fix actually paired" gap flagged in §1)

**Database** (both already applied live on `ujoqdsesfctxmzmlxewu` — verify, don't re-run destructively)
- [ ] Confirm `security_fix_rpc_grants.sql` effect is still in place: only `postgres`/`service_role` have EXECUTE on `process_month_atomically`
- [ ] Confirm `sell_asset_atomic_migration.sql` effect is still in place: `sell_asset_atomic` exists, locked to `service_role`
- [ ] If deploying to a *different* or fresh Supabase project: run the full migration order in `V1_IMPLEMENTATION_PLAN.md` §7.1 (now 8 steps) in sequence

**Content & readiness** (not part of this cycle's fixes, but block the event per the existing plan)
- [ ] Author the months 2–12 event/choice content pack (B3/M3) — currently only 2 events + 1 choice exist
- [ ] Confirm expected event headcount (B2) — determines whether QA-012 is on the critical path
- [ ] Write the admin recovery runbook (QA-013/B7/T4.1)
- [ ] Take a fresh Supabase backup immediately before the event (T4.4)
- [ ] Confirm `game_control` is reset to month 1 / `waiting` before the real event (it is currently at month 12 / `ended` from this session's testing/prior game)

---

## 5. Rollback Checklist

Each fix rolls back independently; none depend on each other.

| Fix | Rollback action |
|---|---|
| QA-001 | `GRANT EXECUTE ON FUNCTION public.process_month_atomically(json,json,json,json,integer) TO PUBLIC;` |
| QA-003 | `DROP FUNCTION public.sell_asset_atomic(uuid,text,numeric,int,numeric);` and revert `player_routes.py` to the prior read/write block |
| QA-002 | `git revert` on `backend/engine/event_engine.py` |
| QA-004 | `git revert` on `backend/routes/admin_routes.py` (or the relevant hunk) |
| QA-005 | `git revert` on `backend/routes/admin_routes.py` (or the relevant hunk) |

**Backend-level:** redeploy the previous Render build/commit (standard rollback per `V1_IMPLEMENTATION_PLAN.md` §7.5).
**Database-level:** restore the pre-deploy Supabase backup — take one immediately before committing/redeploying, per the project's own standing rule (§7.5, "take one immediately before §7.1 step 6" — extend that habit to steps 7–8 now).
**Trigger conditions:** any smoke-test item in §6 fails, or a dry run surfaces a regression. **Never roll back mid-game** — finish or formally abort the current game first (Invariant 6 / ADR-012), same rule as every prior deploy in this project.

---

## 6. Smoke-Test Checklist

Baseline (existing, `DEPLOY_FRESH.md` §6) — all 5 steps must still pass:
- [ ] Signup/login
- [ ] Case study loads
- [ ] Month-1 allocation
- [ ] Admin advances a month
- [ ] Leaderboard renders

**Additional checks specific to this cycle's fixes:**
- [ ] **QA-001:** with the redeployed backend, confirm `/admin/next-month` still works end-to-end (proves the legitimate `service_role` path wasn't broken by the revoke) — this session's DB-level test already confirmed the `anon` exploit path is blocked; this step confirms the *legitimate* path still works after a real backend redeploy, which wasn't tested end-to-end this session (no live backend server available in this environment)
- [ ] **QA-003:** perform a real `/sell` call through the redeployed backend (not just the DB-level test done this session) and confirm the response shape (`message`, `penalty`, `credited_next_month`) matches what the frontend expects
- [ ] **QA-002:** advance a month with an admin-authored market-triggering scenario and confirm only one stock-return line appears in that month's log, not two
- [ ] **QA-004:** make an admin correction via `/admin/update-player` and confirm the leaderboard rank reflects the correction immediately, not just `net_worth`
- [ ] **QA-005:** attempt to author an event with an invalid `impact_target` and a choice with a negative `cost` via the admin UI — confirm both are now rejected with a clear error instead of silently succeeding
- [ ] Confirm `game_control` reset to month 1 / `waiting` before treating any of the above as a pre-event dry run rather than a repeat of this session's testing

---

## 7. Go / No-Go Recommendation

**No-Go, as of this report.**

Not because the five approved fixes are wrong — they're tested and sound at the layer each was tested at. The reasons are all pre-existing, already-documented gaps that this report is not the first to raise, plus one new one this cycle introduced:

1. **This cycle's own fixes aren't deployed yet** (§1). Shipping RC1 today means the production backend still has the QA-002/004/005 defects and half of QA-003 live, QA report or no QA report.
2. **No content pack exists** (§3) — 2 events and 1 choice across a 12-month game is not an event, it's a schema with seed data.
3. **No verification suite** (§3) — every fix this cycle was hand-tested individually; there is still no repeatable check that a future change won't silently reintroduce QA-001-class bugs.
4. **No admin recovery runbook** (§3/QA-013) — this project's own checklist has treated this as P0 event-blocking since before this session started; nothing here changes that.
5. **Headcount unconfirmed** (B2) — QA-012 either matters a lot or not at all depending on an answer only you have.

**What flips this to Go:** commit + redeploy this cycle's code fixes and run the full §6 smoke test against that live deployment; author the content pack; write the runbook; answer the headcount question. None of these are large — the plan already scoped them (M1/M3/M4) before this QA cycle started, and this cycle didn't add new blockers to that list, only found and fixed five defects that were sitting underneath it.

---

*End of RC1 report. No code was modified in producing this document.*
