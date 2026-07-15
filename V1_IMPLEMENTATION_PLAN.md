# Money Master — Version 1 Implementation Plan

**Role:** Chief Technical Planner · **Date:** 2026-07-13 · **Status:** Execution plan (no new architecture)
**Authoritative sources:** `ARCHITECTURE_DECISIONS.md` (ADR-000…013), `PRD.md`, `SRS.md`. This plan converts the *approved* architecture into an executable roadmap. It introduces no new ADRs, abstractions, or subsystems, and writes no code. Where required information is missing, it is listed as a **BLOCKER**, never assumed.

---

## 1. Executive Summary

### 1.1 Current project maturity

Money Master V1 is **built and largely functional, but not release-verified**. The three tiers exist and the core loop runs end to end (per `DEPLOY_FRESH.md` smoke test): auth → case study → allocation → dashboard → admin month-advance → leaderboard.

- **Backend (mature):** modular Flask app — `engine/` (pure game logic), `services/`, `routes/`, `models/constants.py` (single tuning source). Core loop `monthly_processor.process_month_for_player` implements the full ADR-aligned sequence. Composite scoring (ADR-008) and global market path (ADR-009) are implemented.
- **Database (mostly mature):** Supabase schema in `supabase.sql` with RLS, append-only audit (`player_month_log`), and the atomic `process_month_atomically` RPC. Still `user_id`-keyed; the household model (ADR-001) is **not implemented** (SRS §4).
- **Frontend (functional):** vanilla HTML/JS pages (not React — a deliberate, documented V1 reality, SRS §1) calling the Flask API.
- **Correctness (improved this cycle, undeployed):** four logic defects were fixed in code — loan amortization (was a non-repayable death spiral), trust double-write, durable purchase idempotency, and vanishing allocation / month-1 net worth. These are **not yet deployed** and one requires a new migration (`idempotency_migration.sql`).

**Maturity verdict:** feature-complete for the V1 game as specified in PRD §3–8; **not** operationally verified for a live event (no automated test suite, no load test at target size, no admin runbook).

### 1.2 Critical blockers

Ordered by how hard they block the first event. Items marked **[NEEDS INPUT]** require a decision or fact from the owner and cannot be resolved by planning.

- **B1 — Deployment state unknown [NEEDS INPUT].** It is not established whether the live Supabase project is on the latest schema, whether the prior fairness-fix pair (`fairness_fixes_migration.sql` + backend, SRS §7 "pending pair") is deployed, or whether this cycle's four fixes are deployed. The entire roadmap starts from this fact. *Resolution: confirm the live project's current schema + backend commit before Milestone 0 exit.*
- **B2 — Target participant count unknown [NEEDS INPUT].** SRS §9 states honest capacity is ~50–100 players; month processing degrades to ~50–100 s at 500 due to per-player sequential queries. Whether performance hardening is on the critical path depends entirely on the expected headcount. *Resolution: owner states max concurrent players for the first event.*
- **B3 — Event content not confirmed authored [NEEDS INPUT].** The game needs a case study plus a curated set of admin events and optional choices across months 2–12. `case_study` ships with one seed row; `events`/`optional_choices` are authored at runtime via admin endpoints. No evidence the 12-month content pack exists. *Resolution: owner confirms whether content is authored; if not, it is Milestone 3 work.*
- **B4 — Household (ADR-001) scope for the event [NEEDS INPUT].** ADR-001 is approved as V1 *architectural foundation*, but PRD §10 lists it under "Future Versions … design pending," its only consumer (marriage) is V2, and the game runs without it. Building it is an L4 migration that adds risk to the event with no player-visible benefit. *Recommendation: defer to post-event. Needs owner ruling; if ruled in-scope, B5 applies.*
- **B5 — Ownership FK strategy [NEEDS INPUT, only if B4 = in-scope].** The household DB design has one open decision (supertype table vs nullable-FK+CHECK vs V1-pragmatic). It blocks any household migration SQL.
- **B6 — No automated verification suite.** SRS §8 mandates determinism, fairness, score-bounds, and full-12-month checks before any L3+ deploy; today these exist only as the ad-hoc 9-check run from 2026-07-12. This blocks *safe* deployment of the undeployed fixes. *Resolution: Milestone 1.*
- **B7 — Admin recovery runbook missing.** SRS §9 flags this as a required, currently-absent artifact for a live event. *Resolution: Milestone 4.*

### 1.3 Assumptions

These are working assumptions for the plan; each is called out so it can be corrected rather than silently relied on.

- **A1 — No calendar in estimates.** Team size and velocity are unknown, so effort is given as **relative complexity (XS/S/M/L/XL)**, not hours or dates. Converting to a schedule requires the owner's available person-days.
- **A2 — V1 is the deterministic, rule-based game only.** No conversational AI (ADR-003) ships in V1; it is explicitly future in PRD §10. The "AI" in the product vision is not a V1 deliverable.
- **A3 — Single game instance.** `game_control` is a singleton (SRS §9). V1 runs one event at a time; multi-game (`game_id`) is future.
- **A4 — Frontend stays vanilla HTML/JS.** React migration is out of V1 scope (SRS §1).
- **A5 — Hosting is Netlify (frontend) + Render (backend) + Supabase**, per `DEPLOY_FRESH.md` / README, unless the owner states otherwise.
- **A6 — "Between-games" deploy rule holds (Invariant 6).** All L3+ deploys and migrations happen before the event, never during.

---

## 2. Version 1 Scope

### 2.1 Included (authority: PRD §3–8, SRS §2–5)

- 12-month game loop: month 1 allocation; months 2–12 admin-advanced processing.
- Fixed ₹1,00,000 starting budget (exact-total validation) and ₹1,00,000/month salary.
- Player decisions: initial allocation, lifestyle (City/Outer), bike purchase (down payment, EMI, lock-in, transport discount), optional choices (deterministic `fair_roll`), asset sales (10% penalty, next-month credit), relative-help / trust decisions.
- Seven state-driven life-event categories + admin-injected global events (PRD §6).
- Composite Financial Health Score ranking (ADR-008), public formula.
- Global market path (ADR-009) — identical returns per month for all players.
- Admin control surface: start/restart, advance month (atomic, race-protected), publish events + optional choices, manual player correction (audit-logged), reset player, end game.
- Determinism, fairness, atomicity, append-only history, server authority (SRS §5 invariants).
- Supabase Auth (email/password), RLS, admin gating via `admins` table.
- The four correctness fixes from this cycle (loan amortization, trust unification, durable idempotency, allocation conservation) — pending deploy.

### 2.2 Excluded from V1 (present-but-out, or explicitly not built)

- **Conversational / negotiation AI** (ADR-003, ADR-010) — future.
- **Household entity & financial ownership model** (ADR-001, ADR-005) — approved as foundation, not implemented; recommended deferred past the first event (see B4).
- **Marriage & life partner system** (ADR-002) — future.
- **Team play** — referenced in original project brief but has no schema, no ADR, and no PRD/SRS presence; treated as **not in V1** and unclassified for future (see §10.2).
- **React frontend** — SRS §1, out of scope.
- **Multi-game / `game_id` dimension** — SRS §9, future.
- **Event Definition/Impact DSL, formal Business Rules Engine, Economic Engine extensions, admin event lifecycle states** (ADRs 006/007/009-ext/011, status *Proposed*, not ratified) — not V1.
- **Scenario / mode / provider layers** — design-dialogue only, no ratified ADR; not part of frozen V1 architecture.

### 2.3 Deferred to Version 2 and beyond

Dependency-ordered list only — see §10. No design work in V1.

---

## 3. Dependency Graph

### 3.1 Component-level blocking (what must exist before what)

```
[Confirm live deployment state] ──► everything
        │
        ▼
[Deploy pending fixes + idempotency migration]  ◄── needs verification suite to be SAFE
        │
        ├──► [Verification suite: determinism / fairness / score-bounds / 12-month sim]
        │           │
        │           ▼
        │     [Performance hardening]* ── conditional on participant count (B2)
        │           │
        ▼           ▼
[Event content pack] ─────────────► [Operational readiness: runbook + dry run + rollback drill]
                                              │
                                              ▼
                                        [College Event]

[Household foundation (ADR-001)] ── OFF critical path; deferred (B4). Blocks only V2 features.
```
`*` Performance hardening joins the critical path only if B2 (participant count) exceeds the ~100-player safe ceiling (SRS §9).

### 3.2 Critical path

**Confirm deploy state → Verification suite → Deploy pending fixes → Content pack → Operational readiness → Event.**

- Verification suite (M1) gates a *safe* deploy of the fixes (SRS §8), so it precedes the deploy even though the code is already written.
- Content pack (M3) does not gate software correctness but *does* gate the event — you cannot run a game with no events/choices — so it sits on the critical path to "event ready," runnable in parallel with M1/M2.
- Household (ADR-001) is deliberately off the critical path.

### 3.3 What blocks what (summary table)

| Component | Blocked by | Blocks |
|---|---|---|
| Deploy pending fixes | B1 (deploy state), M1 verification | Everything downstream |
| Verification suite (M1) | Test environment / seed data | Safe deploy, perf validation |
| Performance hardening (M2) | B2 (headcount), M1 baseline | Event *if* headcount > ~100 |
| Content pack (M3) | B3 (authoring) | Event readiness |
| Operational readiness (M4) | M0–M3, B7 runbook | Event go/no-go |
| Household (ADR-001) | B4 ruling, B5 FK choice | Only V2 (marriage, ownership) |

---

## 4. Development Roadmap (Milestones)

Complexity scale: XS < S < M < L < XL (relative effort, per A1 — not calendar).

### M0 — Baseline stabilization & deploy the pending correctness fixes
- **Objective:** get the live environment onto a known-good, corrected baseline.
- **Deliverables:** confirmed deploy state (resolves B1); `idempotency_migration.sql` run; this cycle's backend fixes deployed; prior pending fairness pair confirmed live; full smoke test (`DEPLOY_FRESH.md` §6) green.
- **Dependencies:** B1 answered; M1 verification passing (deploy only after verified — see sequencing note in §3.2).
- **Complexity:** M.
- **Exit criteria:** live backend commit + Supabase schema match the repo; smoke test passes on the live project; buy-choice/handle-relative work against the new `player_month_actions` table; no console/DB errors across the five smoke steps.

### M1 — Verification suite
- **Objective:** make SRS §8 verification runnable and repeatable, not ad-hoc.
- **Deliverables:** an executable check set covering determinism (same seeds twice → identical outputs), cross-player market fairness (ADR-009), score bounds 0–100 at edges (bankruptcy, extreme wealth, deep debt), a full 12-month multi-player simulation with no error, and RPC payload validation. Reuses the logic already validated in this cycle (loan amortization + allocation conservation checks).
- **Dependencies:** representative seed data; engine importable in isolation (already true — `engine/` has no DB coupling).
- **Complexity:** M.
- **Exit criteria:** all checks pass on the corrected engine; the suite is re-runnable on demand and is the gate M0's deploy must clear.

### M2 — Performance hardening (CONDITIONAL on B2)
- **Objective:** meet processing time for the actual event headcount.
- **Deliverables:** the SRS-identified fix — batch-fetch loans/sales in `/next-month` (2 queries total, grouped in memory) instead of per-player sequential queries; multi-worker backend (`gunicorn`) sizing; a load test at the target player count (SRS §8 requires this before any perf claim is marked ✅).
- **Dependencies:** B2 (headcount); M1 baseline to prove no behavioral change.
- **Complexity:** M (S if headcount ≤ ~100 and only the load test is needed).
- **Exit criteria:** month processing completes within target at the stated headcount; determinism unchanged (M1 re-passes); load test recorded.

### M3 — Event content pack
- **Objective:** the actual game content for the event exists and is reviewed.
- **Deliverables:** case-study text; a curated set of admin `events` and `optional_choices` for months 2–12 authored via existing admin endpoints; economy tuning reviewed against `constants.py` (PRD §5). Content only — no engine change.
- **Dependencies:** B3; admin panel working (M0).
- **Complexity:** M (mostly authoring/balancing effort, not engineering).
- **Exit criteria:** a dry-run game plays all 12 months with the real content; no dead/duplicate/broken choices; scoreboard tells a coherent pedagogical story.

### M4 — Operational readiness
- **Objective:** the event can be run and recovered by a human under pressure.
- **Deliverables:** admin recovery runbook (resolves B7) covering backend-down, wrong-event-published, month-advanced-early, and player-correction procedures; a full event dry run with test players; a rollback drill (restore-from-backup rehearsal).
- **Dependencies:** M0–M3.
- **Complexity:** M.
- **Exit criteria:** runbook exists and was followed successfully in the dry run; rollback rehearsed once end to end; go/no-go checklist (§9) all green.

### M-H — Household foundation (ADR-001) — DEFERRED / off critical path
- **Objective:** implement the approved household data foundation (only if the owner rules it into V1 per B4).
- **Deliverables:** per the separately-produced `HOUSEHOLD_MIGRATION_PLAN.md` (schema, migration, rollback, tests).
- **Dependencies:** B4 ruling; B5 FK-strategy decision; must deploy between games (L4).
- **Complexity:** L.
- **Exit criteria:** migration verified per that plan's §7; gameplay provably unchanged (invisible per ADR-001 P5). **Recommended: after the first event, not before.**

---

## 5. Task Breakdown

Effort uses the XS–XL scale (A1). "Files affected" names the real repo paths. Priority: P0 (event-blocking) · P1 (event-quality) · P2 (nice-to-have).

### Milestone 0 — Baseline & deploy

| ID | Description | Files affected | Deps | Priority | Effort | Definition of Done |
|---|---|---|---|---|---|---|
| T0.1 | Establish live deploy state: current Supabase schema + backend commit vs repo | (investigation) | B1 | P0 | S | Written statement of what is live; delta vs repo identified |
| T0.2 | Run `idempotency_migration.sql` on the target project | `idempotency_migration.sql` | T0.1 | P0 | XS | `player_month_actions` table exists with RLS; no client access |
| T0.3 | Confirm/deploy prior fairness pair (backend + `fairness_fixes_migration.sql`) | `fairness_fixes_migration.sql`, backend | T0.1 | P0 | S | Fairness pair confirmed live (SRS §7) |
| T0.4 | Deploy this cycle's fixes (loan, trust, idempotency wiring, allocation) | `backend/engine/monthly_processor.py`, `models/constants.py`, `services/game_service.py`, `services/choice_service.py`, `routes/player_routes.py`, `routes/admin_routes.py` | M1, T0.2 | P0 | S | Live backend == repo; smoke test green |
| T0.5 | Full smoke test on live (`DEPLOY_FRESH.md` §6, all 5 steps) | — | T0.2–T0.4 | P0 | S | 5/5 steps pass incl. buy-choice + handle-relative |

### Milestone 1 — Verification suite

| ID | Description | Files affected | Deps | Priority | Effort | Definition of Done |
|---|---|---|---|---|---|---|
| T1.1 | Determinism check: same seeds twice → byte-identical state | new `tests/` (no engine change) | — | P0 | S | Identical outputs asserted across two runs |
| T1.2 | Market fairness check: all players see identical monthly returns (ADR-009) | `tests/` | T1.1 | P0 | S | Cross-player equality asserted per month |
| T1.3 | Score-bounds check: 0–100 at bankruptcy / extreme wealth / deep debt | `tests/` | — | P0 | S | Components clamp correctly at edges |
| T1.4 | Full 12-month, multi-player simulation, zero errors | `tests/` | T1.1 | P0 | M | 12 months × N players complete; no exception |
| T1.5 | Loan-amortization + allocation-conservation regression (this cycle) | `tests/` | — | P0 | XS | Loans clear; money conserved (already validated) |
| T1.6 | RPC payload validation check (`validate_rpc_payload`) | `tests/` | — | P1 | XS | Malformed payloads rejected pre-RPC |

### Milestone 2 — Performance (conditional on B2)

| ID | Description | Files affected | Deps | Priority | Effort | Definition of Done |
|---|---|---|---|---|---|---|
| T2.1 | Batch-fetch loans + sales in `/next-month` (2 queries, group in memory) | `backend/routes/admin_routes.py`, `backend/services/game_service.py` | M1 | P0-if-large | M | Same outputs as sequential; query count O(1) per month |
| T2.2 | Multi-worker backend sizing (`gunicorn` workers) | `run_backend.bat` / Render config | — | P1 | S | Worker count set for headcount; idempotency still holds (DB-backed) |
| T2.3 | Load test at target headcount; record month-processing time | — | B2, T2.1 | P0-if-large | S | Processing within target; result recorded (SRS §8) |

### Milestone 3 — Content pack

| ID | Description | Files affected | Deps | Priority | Effort | Definition of Done |
|---|---|---|---|---|---|---|
| T3.1 | Author case-study briefing | `case_study` (DB) | M0 | P0 | S | Case study displays on the case-study screen |
| T3.2 | Author months 2–12 admin events (`/event`) | `events` (DB) | M0 | P0 | M | Each month has intended global events; deletable |
| T3.3 | Author optional choices per month (`/choice-admin`) | `optional_choices` (DB) | M0 | P0 | M | Choices priced, probability-set, reward-set; `fair_roll` verified |
| T3.4 | Balance pass vs `constants.py` tuning (PRD §5) | content only | T3.1–T3.3 | P1 | M | Dry-run scoreboard is pedagogically coherent |

### Milestone 4 — Operational readiness

| ID | Description | Files affected | Deps | Priority | Effort | Definition of Done |
|---|---|---|---|---|---|---|
| T4.1 | Write admin recovery runbook (backend-down, wrong event, early advance, corrections) | new ops doc | M0 | P0 | M | Runbook covers each failure with exact steps |
| T4.2 | Full event dry run with test players across all 12 months | — | M0–M3 | P0 | M | A complete game played; issues logged & fixed |
| T4.3 | Rollback drill (restore Supabase backup; redeploy prior backend) | — | M0 | P0 | S | Rollback performed once successfully |
| T4.4 | Pre-event backup + config check (email-confirm off, admin account, ADMIN gating) | — | M0 | P0 | XS | Backup taken; checklist §9 green |

---

## 6. Testing Plan

Reference standard: SRS §8. Current state: **no automated suite exists** — closing that is M1. Tests live in a new `tests/` directory and add no architecture.

**engine/monthly_processor**
- *Unit:* each step in isolation (salary, inflation-adjusted expense, bike discount + EMI, loan interest+amortized EMI, safety-net → EF rescue vs auto-loan, discipline grade). Assert amortized loans clear and never grow.
- *Integration:* full month with events + loans + sales credit; state out matches hand-computed expectation.
- *Regression:* loan death-spiral and allocation-vanishing fixes stay fixed (T1.5).
- *Acceptance:* a 12-month arc produces sane, monotonic-where-expected trajectories.

**engine/market_engine + event_engine**
- *Unit:* seeded RNG reproducibility; risk score bounds; inflation start month 4.
- *Integration:* market events identical across players in a month (fairness); personal events vary only by that player's own state.
- *Regression:* global-path seeding unchanged (ADR-009).
- *Acceptance:* no unseeded randomness anywhere touches ranking.

**engine/scoring**
- *Unit:* each component 0–100 at edges; weights sum to 1; discipline running average.
- *Integration:* composite matches components·weights; ties break by net worth.
- *Acceptance:* scoreboard rewards balance, not leverage (PRD §7).

**services + routes**
- *Unit:* `fair_roll` determinism; `validate_rpc_payload`; allocation total/negatives/lifestyle validation; durable idempotency (`action_done`/`mark_action`) blocks double buy and repeat relative-help.
- *Integration:* `/allocate` → `/dashboard`; `/next-month` atomic (all-or-nothing; refuses reprocessing a logged month); admin correction recomputes net worth + audit-logs.
- *Regression:* idempotency survives a simulated restart (DB-backed, not in-memory).
- *Acceptance:* server authority — client-supplied financials never trusted.

**System / event-day**
- *Acceptance:* full `DEPLOY_FRESH.md` smoke test; multi-player dry run (T4.2); leaderboard renders under load at headcount.

---

## 7. Deployment Plan

Binding rule (Invariant 6 / ADR-012): backend code and its migration deploy **as a pair, between games only**.

### 7.1 Database install (F-02: one canonical path)

**Fresh install (empty Supabase project) — run ONE file:**

1. `supabase.sql` — the complete install. Creates every table (incl. `admins`
   and `player_month_actions`), all RLS policies (SELECT-own-row; writes via
   `service_role` only), both RPCs (`process_month_atomically`,
   `sell_asset_atomic`) already revoked from public roles, the
   `handle_new_user`/`on_auth_user_created` signup trigger, and seeds. Nothing
   else is needed. Post-install, grant a specific admin (data step) per
   `DEPLOY_FRESH.md` §4a.

That is the whole fresh path. Verified complete: every table/RPC/trigger the
backend references is created by this one file (F-02 deployment verification).

**Retrofitting an OLDER live project** (predating these fixes) — the individual
patch files are retained for this only; each is idempotent and each carries a
header explaining it is already folded into `supabase.sql`:
`supabase_signup_trigger.sql`, `admin_setup.sql`, `idempotency_migration.sql`,
`fairness_fixes_migration.sql`, `security_fix_rls.sql`,
`security_fix_rpc_grants.sql`, `sell_asset_atomic_migration.sql`. Confirm against
the live project which are already applied — do not re-run destructively.

> `supabase_migration.sql` is **SUPERSEDED — do not run it** on any project (it
> re-opens a public `player_state` read policy and reverts the scoring RPC).

### 7.2 Backend deployment (Render)
- Build `pip install -r requirements.txt`; start `gunicorn app:app` from `backend/`.
- Env: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (service key never in frontend). No `ADMIN_TOKEN` — admin access is via the `public.admins` table (QA-007).
- Deploy the backend as the paired half of the §7.1 database install (code + schema deploy together, between games — Invariant 6 / ADR-012).

### 7.3 Frontend deployment (Netlify)
- Publish `frontend/`; set non-local `API_BASE_URL` in `frontend/js/config.js` to the Render URL; set `SUPABASE_URL` + anon key.

### 7.4 Verification checklist (post-deploy, pre-event)
- Smoke test 5/5 (§6 system).
- Buy-choice + handle-relative succeed and are idempotent (new table live).
- Month advance atomic; re-advance of a processed month refused.
- Leaderboard ranks by health score, net-worth tiebreak.
- Determinism spot-check: same seeds → same result (M1).

### 7.5 Rollback strategy
- **Backend:** redeploy previous Render build (keep the prior image/commit pinned).
- **Database:** restore the pre-deploy Supabase backup (take one immediately before §7.1 step 6). `idempotency_migration.sql` is additive → reverse = `DROP TABLE player_month_actions` (buy-choice/handle-relative revert to prior behavior only if paired backend is also rolled back).
- **Trigger:** any §7.4 item red, or dry-run failure. Never roll back mid-game — finish or abort the game first (Invariant 6).

---

## 8. Risk Register

Impact × Probability on Low/Med/High.

| # | Risk | Type | Impact | Prob | Mitigation |
|---|---|---|---|---|---|
| R1 | Live project not on latest schema; deploy assumptions wrong | Deployment | High | Med | T0.1 audit before any deploy; take backup first |
| R2 | Event headcount exceeds ~100 → month processing stalls | Technical | High | Med | Resolve B2 early; M2 batch-fetch + load test if large |
| R3 | Content pack incomplete/unbalanced at event time | Product | High | Med | M3 early + dry-run balance pass (T3.4) |
| R4 | No runbook → unrecoverable mid-event failure | Deployment | High | Med→Low | T4.1 runbook + T4.3 rollback drill |
| R5 | Undeployed fixes deployed without verification → new regressions | Technical | High | Low | M1 gates M0 deploy (sequencing in §3.2) |
| R6 | Idempotency migration forgotten → buy-choice/relative 500s live | Deployment | High | Low | Pinned as P0 T0.2; in §7.1 + §7.4 checks |
| R7 | Admin misclicks (start-game wipes data; early advance) | User | High | Med | Runbook + confirm-dialogs already in admin flow; brief the admin |
| R8 | Household work pulled into V1 and destabilizes the event | Product | High | Low | B4 recommendation: defer; keep off critical path |
| R9 | Single Flask worker + per-request auth calls under load | Technical | Med | Med | T2.2 gunicorn workers; load test (T2.3) |
| R10 | Players confused by allocation labels (rent/food now retained as cash) | User | Low | Med | Brief players; optional post-event UI copy fix (not V1-blocking) |
| R11 | Supabase auth/email-confirm misconfig blocks mass login | Deployment | High | Low | `DEPLOY_FRESH.md` §3 (confirm off); test signup in dry run |

---

## 9. College Event Readiness Checklist

Everything that must be true before the first real event. All P0 unless noted.

**Software & data**
- [ ] Live schema audited; all required migrations applied incl. `idempotency_migration.sql` (T0.1–T0.2)
- [ ] Four-fix backend deployed and matching repo (T0.4)
- [ ] Verification suite green (M1)
- [ ] Load test passed at confirmed headcount, or headcount confirmed ≤ ~100 (M2/B2)

**Content**
- [ ] Case study authored and displaying (T3.1)
- [ ] Months 2–12 events + optional choices authored and balanced (T3.2–T3.4)

**Operations**
- [ ] Admin recovery runbook written and rehearsed (T4.1)
- [ ] Full 12-month dry run completed with test players (T4.2)
- [ ] Rollback drill performed once (T4.3)
- [ ] Fresh Supabase backup taken immediately pre-event (T4.4)

**Configuration**
- [ ] Email confirmation OFF (`DEPLOY_FRESH.md` §3)
- [ ] Admin account created and in `admins` table; admin login works
- [ ] Backend running, pointed at the correct project, multi-worker if needed
- [ ] `game_control` reset to month 1 / status ready for the real game
- [ ] Leaderboard display tested on the room's projector/screen

**People**
- [ ] Organizer trained on start/advance/correct/end + the runbook
- [ ] Emcee has the round-by-round narration matching the content pack

---

## 10. Version 2 Backlog

Per instructions: **list only, no design.** Dependency-ordered.

### 10.1 Approved future features (ADR-backed)
1. **Household foundation** (ADR-001) — data-model groundwork; blocks everything below.
2. **Financial ownership model** (ADR-005) — Individual/Household/Business/Organization; depends on 1.
3. **Marriage & life partner system** (ADR-002) — depends on 1 (and 2 for spouse ownership).
4. **Conversational AI pipeline** (ADR-003) — NL→intent→rules→AI; depends on stable engine + 1.
5. **AI memory** (ADR-010) — deterministic-history vs conversational-memory split; depends on 4.

### 10.2 Proposed-but-not-ratified (need ratification before entering a version)
- Event Definition/Impact DSL (ADR-006), Business Rules Engine formalization (ADR-007), Economic Engine extensions (ADR-009-ext), Admin event lifecycle states (ADR-011), Versioning + multi-game `game_id` (ADR-012). Status: *Proposed* in the ADR set — must be ratified before scheduling.

### 10.3 Unclassified backlog (require ADR-013 triage before any version)
- Team play, React frontend migration, 500-player performance target, and any Scenario/mode/provider concept from prior design discussion. None are approved architecture; each must be classified per ADR-013 before it becomes real scope.

---

*End of Version 1 Implementation Plan. Blockers B1–B7 require owner input; the critical path cannot be scheduled until B1 (deploy state), B2 (headcount), and B3 (content) are answered.*
