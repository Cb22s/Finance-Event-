# Money Master — RC2 Readiness Plan

**Date:** 2026-07-13 · **Role:** Release Manager · **Status:** Development frozen — this document plans and tracks release readiness only. No code or architecture changes are proposed or performed here.
**Authority chain:** PRD.md, ARCHITECTURE_DECISIONS.md (ADR-000…013), SRS.md, QA_REPORT_V1.md, V1_IMPLEMENTATION_PLAN.md, RC1_REPORT.md. Every item below cites one of these.

---

## 1. Review of RC1 Report

RC1 issued **No-Go**. Nothing has been committed, deployed, or otherwise changed since RC1 was written — no code action has occurred without your explicit approval, per the freeze. RC1's five reasons stand exactly as written:

1. This QA cycle's five approved fixes (QA-001–005) exist only in the working tree — three files remain uncommitted.
2. No event content pack exists (2 `events` rows, 1 `optional_choices` row, 1 `case_study` row, live on the production project).
3. No automated verification suite exists (SRS §8 / B6 / M1 — still just the ad-hoc 2026-07-12 check run).
4. No admin recovery runbook exists (QA-013 / B7).
5. Event headcount (B2) is still unconfirmed.

This RC2 plan takes those five as the starting punch list and adds the items RC1 flagged in §2/§3 but didn't formally sequence (QA-006 security config, the unexplained uncommitted frontend file, rollback drill, backup, game reset).

---

## 2. Blocker Categorization

**Critical — must complete before release**

| ID | Blocker | Cited authority |
|---|---|---|
| C1 | Commit + deploy this cycle's approved backend fixes (QA-002, QA-003 route half, QA-004, QA-005) | RC1_REPORT.md §1, §4 |
| C2 | Author minimum viable event content, months 2–12 | V1_IMPLEMENTATION_PLAN.md B3/M3; RC1_REPORT.md §3 |
| C3 | Confirm event headcount; resolve or explicitly accept QA-012 (per-player sequential query performance gap) | V1_IMPLEMENTATION_PLAN.md B2/M2; QA_REPORT_V1.md QA-012 |
| C4 | Write and rehearse the admin recovery runbook | QA_REPORT_V1.md QA-013; V1_IMPLEMENTATION_PLAN.md B7/T4.1 |
| C5 | Run full smoke test (baseline 5-step + this cycle's 5 fix-specific checks) against the **redeployed** backend | RC1_REPORT.md §6 |
| C6 | Take pre-event Supabase backup; reset `game_control` to month 1 / `waiting` | V1_IMPLEMENTATION_PLAN.md T4.4; current live state is month 12 / `ended` from this cycle's testing |
| C7 | Full 12-month dry run with test players against real content | V1_IMPLEMENTATION_PLAN.md T4.2, M3 exit criteria |
| C8 | Rollback drill performed at least once | V1_IMPLEMENTATION_PLAN.md T4.3 |

**High — strongly recommended**

| ID | Blocker | Cited authority |
|---|---|---|
| H1 | Re-verify determinism / fairness / score-bounds behavior against the redeployed backend (minimum viable substitute for the still-missing formal M1 suite) | SRS.md §8; V1_IMPLEMENTATION_PLAN.md B6/M1 |
| H2 | Enable Supabase leaked-password protection | QA_REPORT_V1.md QA-006 |
| H3 | Review the unrelated, already-uncommitted `frontend/js/case-study.js` change before freezing the release branch — provenance not established by this QA cycle | RC1_REPORT.md §3 |
| H4 | Confirm multi-worker (gunicorn) backend sizing if C3's headcount answer is large | SRS.md §9; V1_IMPLEMENTATION_PLAN.md T2.2 |

**Medium — can be completed after release**

| ID | Blocker | Cited authority |
|---|---|---|
| M1 | Fix `ADMIN_TOKEN` documentation drift | QA_REPORT_V1.md QA-007 |
| M2 | Implement or remove the dead bike-lock-in warning stub | QA_REPORT_V1.md QA-008 |
| M3 | Add missing log lines for fixed-value stocks/gold events | QA_REPORT_V1.md QA-009 |
| M4 | Expose the score component breakdown as structured, queryable data | QA_REPORT_V1.md QA-010 |

**Low — technical debt**

| ID | Blocker | Cited authority |
|---|---|---|
| L1 | `player_month_log` granularity (line-item ledger vs. text summary) — accepted V1 tradeoff, not a defect | QA_REPORT_V1.md QA-011 |
| L2 | Build the full formal M1 automated verification suite (beyond the minimum viable check in H1) | V1_IMPLEMENTATION_PLAN.md B6/M1 |

---

## 3. Release Checklist (Execution Order)

**Step 1 — Review and commit pending code**
*Purpose:* Capture the five approved QA fixes (QA-001–005) in version control so they can be deployed and rolled back cleanly.
*Expected result:* Clean commit; working tree matches what was individually tested during Phase 1/2 approval.
*Estimated time:* 15–20 min.
*Who:* Claude prepares the diff/commit — requires your explicit go-ahead per the code freeze before it executes.

**Step 2 — Push to GitHub**
*Purpose:* Make the committed fixes available to the deployment target.
*Expected result:* Remote branch up to date with local commit.
*Estimated time:* 5 min.
*Who:* Manual (Patch) unless you authorize Claude to push with existing credentials.

**Step 3 — Deploy Render backend**
*Purpose:* Get the committed code fixes actually running in production, closing the gap RC1 flagged in §1.
*Expected result:* Render build succeeds; new backend serving traffic.
*Estimated time:* 10–15 min (Render build time).
*Who:* Manual (Patch, via Render dashboard — no deployment access available to Claude).

**Step 4 — Verify deployment**
*Purpose:* Confirm the live backend is actually running the code just deployed, not a stale build.
*Expected result:* Live backend commit/version matches what was pushed in Step 2.
*Estimated time:* 5 min.
*Who:* Manual (Patch checks Render dashboard) or Claude if a version/health endpoint is reachable.

**Step 5 — Confirm SQL migration state (no re-run expected)**
*Purpose:* Verify the QA-001/QA-003 database fixes already live on `ujoqdsesfctxmzmlxewu` are still correctly in place after any deploy activity.
*Expected result:* `process_month_atomically` and `sell_asset_atomic` EXECUTE grants remain restricted to `service_role` only.
*Estimated time:* 5 min.
*Who:* Claude (Supabase access available) — verification only, no migration re-run without your approval.

**Step 6 — Run smoke tests**
*Purpose:* Confirm the redeployed backend behaves correctly end-to-end — baseline flow plus the five fix-specific checks from RC1_REPORT.md §6.
*Expected result:* All 5 baseline steps pass; all 5 fix-specific checks pass (RPC lockdown doesn't break the legitimate admin path, `/sell` works end-to-end, no duplicate market log lines, admin correction updates the leaderboard rank, bad event/choice input is now rejected).
*Estimated time:* 30–45 min.
*Who:* Manual (Patch, visual/UI confirmation) with Claude assisting on any API-level checks that can be automated.

**Step 7 — Security hardening: enable leaked-password protection**
*Purpose:* Close QA-006 — a live, currently-real Supabase Auth gap.
*Expected result:* Setting enabled in Supabase Auth dashboard; confirmed via advisor re-scan.
*Estimated time:* 5 min.
*Who:* Manual (Patch, Supabase dashboard setting) or Claude if you approve making the change via the Supabase connection.

**Step 8 — Author missing game content**
*Purpose:* Close B3/C2 — give months 2–12 actual events and optional choices instead of the current 2 events / 1 choice.
*Expected result:* A reviewed, balanced content set for all 11 remaining months, matching PRD §6's seven event categories and the `constants.py` tuning.
*Estimated time:* Largest remaining item — hours, not minutes (content authoring + balance review, per Implementation Plan M3 "mostly authoring/balancing effort, not engineering").
*Who:* Manual (Patch) — this is game-design/pedagogical judgment, not something Claude should generate unilaterally; Claude can assist drafting specific event text if you request it.

**Step 9 — Confirm headcount and resolve performance gap**
*Purpose:* Answer B2 and decide whether QA-012 (per-player sequential queries in `/next-month`) needs the batch-fetch fix before the event, or whether headcount stays under the ~50–100 safe ceiling.
*Expected result:* A stated max concurrent player count, and either a documented "no action needed" or a scoped, separately-approved follow-up task for the batch-fetch fix.
*Estimated time:* 5 min to answer; hours if the fix is triggered (out of this plan's scope — would need its own approval).
*Who:* Me (you hold this fact) → Claude documents the decision.

**Step 10 — Write and rehearse the admin recovery runbook**
*Purpose:* Close QA-013/B7 — give the event organizer exact steps for backend-down, wrong-event-published, early-advance, and correction scenarios.
*Expected result:* A runbook document, walked through once by whoever will be admin on event day.
*Estimated time:* 1–2 hours to write, 30 min to rehearse.
*Who:* Manual (Patch) to define procedures and event-day realities; Claude can draft the document structure/content if requested as a separately-approved task.

**Step 11 — Pre-event backup and rollback drill**
*Purpose:* Close C6/C8/T4.3/T4.4 — prove the rollback path actually works before you need it live, and have a clean restore point.
*Expected result:* Supabase backup taken; one full rollback (restore backup + redeploy prior backend build) rehearsed successfully.
*Estimated time:* 30–45 min.
*Who:* Manual (Patch) — destructive/restore actions on the live project should not be automated without you directly supervising.

**Step 12 — Reset game state for the real event**
*Purpose:* `game_control` is currently at month 12 / `ended` from this session's testing — must be reset before real players touch it.
*Expected result:* `game_control` at month 1, status `waiting`; no leftover test-player data in `player_state`/related tables.
*Estimated time:* 5 min.
*Who:* Claude (via admin `/start-game`, which is designed for exactly this — destructive and intentional per SRS §3) — requires your explicit approval to execute since it wipes data.

**Step 13 — Full 12-month dry run**
*Purpose:* Prove the whole system — content, engine, admin flow, leaderboard — works together under real-ish conditions before the actual event.
*Expected result:* A complete 12-month game played with test players; scoreboard tells a coherent story; no errors, no dead/broken content.
*Estimated time:* Depends on pacing — could be compressed to under an hour with rapid admin advances, or run at intended event pacing for a fuller rehearsal.
*Who:* Manual (Patch + test players) with Claude available to monitor logs/DB state during the run if useful.

**Step 14 — RC2 review**
*Purpose:* Re-assess readiness against this checklist once Steps 1–13 are complete or explicitly deferred.
*Expected result:* Updated Production Readiness Dashboard and Release Readiness percentage.
*Estimated time:* 30 min.
*Who:* Claude produces the review; Me confirms.

**Step 15 — Issue GO / NO-GO**
*Purpose:* Final release decision.
*Expected result:* A recorded decision with reasoning.
*Estimated time:* Immediate, once Step 14 is in hand.
*Who:* Me (final authority) — Claude provides the data-driven recommendation (see §6 below), you make the call.

---

## 4. Production Readiness Dashboard

| Category | Status | Basis |
|---|---|---|
| Architecture | ✅ Complete | ADR-000–013 approved and frozen; ADR-001 (household) deliberately deferred off critical path per B4 — not a gap for V1 |
| Development | 🟡 In Progress | Core game loop feature-complete per Implementation Plan §1.1; this cycle's 5 fixes written but **uncommitted** |
| Database | ✅ Complete | Schema, RLS, and this cycle's two DB-side fixes (QA-001, QA-003) all confirmed **live** on the production project |
| Backend | 🔴 Blocked | Running production backend does not yet include QA-002/003(route)/004/005 — code exists locally only |
| Frontend | 🟡 In Progress | Functional per SRS §1; one unrelated uncommitted change (H3) not yet reviewed |
| Security | 🟡 In Progress | QA-001 (critical RPC bypass) closed and verified live; QA-006 (leaked-password protection) still open |
| Testing | 🔴 Blocked | No automated verification suite exists (SRS §8/B6); this cycle's fixes were hand-tested individually, not via a repeatable suite |
| Content | 🔴 Blocked | 2 events, 1 optional choice, 1 case-study row live for a 12-month game (B3) |
| Deployment | 🔴 Blocked | This cycle's fixes not committed or redeployed; game state not reset for a real event |
| Documentation | 🟡 In Progress | PRD/SRS/ADRs/QA/RC1 all current and consistent; QA-007 (ADMIN_TOKEN drift) and the runbook (QA-013) are the open gaps |
| Operations | 🔴 Blocked | No admin runbook, no rollback drill performed, no pre-event backup taken, headcount (B2) unconfirmed |
| Release | 🔴 Blocked | RC1 issued No-Go; RC2 gate (this plan) not yet executed |

---

## 5. Release Burn-down List

Remaining work only — nothing already complete is listed.

- [ ] Commit the three pending backend files (QA-002, QA-003, QA-004, QA-005 code)
- [ ] Push to GitHub
- [ ] Deploy backend to Render
- [ ] Verify live deployment matches pushed commit
- [ ] Confirm QA-001/QA-003 DB-level grants are still correctly restricted post-deploy
- [ ] Run baseline 5-step smoke test
- [ ] Run the 5 fix-specific smoke tests (RC1 §6)
- [ ] Enable Supabase leaked-password protection (QA-006)
- [ ] Review the unexplained uncommitted `frontend/js/case-study.js` change
- [ ] Author months 2–12 event/choice content pack
- [ ] Confirm max concurrent player headcount
- [ ] Decide on / scope the QA-012 batch-fetch performance fix if headcount requires it
- [ ] Write the admin recovery runbook
- [ ] Rehearse the runbook once
- [ ] Take a fresh pre-event Supabase backup
- [ ] Perform one rollback drill
- [ ] Reset `game_control` to month 1 / `waiting` and clear test-player data
- [ ] Run a full 12-month dry run with test players
- [ ] Re-run RC2 review against this list
- [ ] Issue final GO / NO-GO

---

## 6. Recommendation

Release Readiness:
**55%**

Recommendation:
**NO-GO**

Reason:
Remaining critical blockers:
- This cycle's approved code fixes are not committed or deployed — the production backend does not yet run what was tested and approved
- Event content for months 2–12 is effectively unauthored (2 events, 1 choice on the live project)
- No admin recovery runbook exists
- No full dry run has been performed
- Event headcount is unconfirmed, leaving the QA-012 performance gap unresolved
