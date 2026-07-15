# Money Master — RC3 Production-Readiness Audit

**Date:** 2026-07-14 · **Role:** Lead/Principal Engineer, QA, Security, Performance, DB, DevOps, Release Manager (single reviewer, Claude) · **Purpose:** independent, top-to-bottom release-candidate review of the whole repository. No code was changed in producing this report.
**Authority chain (frozen, cited throughout):** `PRD.md`, `ARCHITECTURE_DECISIONS.md` (ADR-000…013), `SRS.md`, `QA_REPORT_V1.md`, `V1_IMPLEMENTATION_PLAN.md`, `RC1_REPORT.md`, `RC2_READINESS_PLAN.md`.
**Method:** full static read of `backend/` (engine, routes, services, models, app, utils, client), `frontend/` (all HTML/JS/CSS), every root `.sql` file, deployment docs and `.env` templates, `.gitignore`, plus a live run of the existing `backend/tests/` suite (30 tests). The `QA_REPORT_V1.md` findings were used as a *starting point only* and every one was independently re-verified against current code, not trusted.

No new ADRs are proposed. Every issue below is a defect against, or gap in, an already-approved decision, classified per ADR-013. Nothing here expands scope, adds features, or redesigns anything.

---

## 0. Reconciliation — the QA report is partly stale (verified this pass)

The repository has moved ahead of `QA_REPORT_V1.md`. Confirmed by reading the actual code, not the report:

| QA ID | Report status | **Verified current state (this audit)** |
|---|---|---|
| QA-001 (public RPC) | Critical, open | **Fixed in repo.** `supabase.sql` and `security_fix_rpc_grants.sql` both `REVOKE EXECUTE … FROM PUBLIC/anon/authenticated` and grant only `service_role`. RC1 confirms it is live on `ujoqdsesfctxmzmlxewu`. Residual: re-confirm on the live DB (not verifiable from the repo alone). |
| QA-002 (double market hit) | High, open | **Fixed.** `event_engine.py` category 3 ("Market Fluctuation") removed; the code carries an explicit QA-002 comment. `market_engine` is now the single global market path. |
| QA-003 (sell race) | High, open | **Fixed.** `player_routes.sell_asset` now calls the `sell_asset_atomic` RPC (locks the row, re-checks under lock); RPC is REVOKE'd to `service_role`. |
| QA-004 (stale score on admin edit) | Medium, open | **Fixed.** `admin_routes.update_player` recomputes `risk_level` and `financial_health_score`. |
| QA-005 (no admin input validation) | Medium, open | **Fixed.** `/event` and `/choice-admin` now whitelist type/target and bound cost/probability/reward. |
| QA-014 (market fairness, zero-holding) | High, open | **Still open — confirmed by a failing test** (see F-01). |
| QA-006–013 | various, open | Still open except as noted below; re-verified individually. |

So the previously-approved Phase 1/2 fixes are present in the working tree. This audit therefore focuses on (a) the one still-open High from last cycle, and (b) **eight issues the QA report never covered**, most of which are deploy-integrity landmines that only bite on a fresh Supabase project.

**Test baseline (run this pass):** `python -m unittest` over `backend/tests/` → **29 passed, 1 failed**. The single failure is `test_zero_holding_players_do_not_break_fairness_for_others` — i.e. QA-014 / F-01, failing exactly as intended (zero-stock player observed gold rate 5.34% vs 2.37% for identical gold holdings).

---

## 1. Verified Findings

Numbering continues the QA series. F-01 = QA-014 (already logged); F-02…F-10 are new this audit; the remaining open QA-006…013 items are carried with re-verified status.

### F-01 — Conditional RNG stream consumption breaks market fairness (= QA-014)
- **Severity:** High · **ADR:** Level 3 (business logic; affects ranking) — violates ADR-009, ADR-000 §3, SRS §5 Inv. 2 & §8.
- **Description:** `market_engine.calculate_investment_growth` draws stock volatility inside `if stocks > 0:` and gold fluctuation inside `if gold > 0:`, both from one shared sequential `rng`. A player holding no stocks skips the stock draw, so their gold draw consumes the stock draw's stream position — identical gold holdings get different gold rates depending on whether the player also holds stocks.
- **Root Cause:** The `> 0` guards gate *stream consumption*, not just *application*, making the shared stream's position depend on per-player composition.
- **Files:** `backend/engine/market_engine.py` (lines 45–63).
- **Impact:** Two players with identical gold are ranked on different, uncorrelated gold returns. Direct competitive-fairness defect on a ranked leaderboard.
- **Risk:** High — silently mis-ranks; already reproducibly demonstrated by the suite.
- **Recommendation:** Draw both `rng.uniform()` values unconditionally right after seeding; keep the `> 0` guards around only the delta application + log line. (Already diagnosed and appended to `QA_REPORT_V1.md` as QA-014.)

### F-02 — Fresh deploy per DEPLOY_FRESH.md never creates `player_month_actions`; all optional-choice and relative-help actions silently break
- **Severity:** High · **ADR:** Level 3 (financial mutation path gating) + deployment.
- **Description:** `choice_service.execute_choice` and `player_routes.handle_relative` gate every purchase/help on `mark_action(...)`, which inserts into `public.player_month_actions`. That table is created **only** by `idempotency_migration.sql`. `DEPLOY_FRESH.md` never mentions that file (grep: zero hits for "idempotency"/"player_month_actions"). Step 2 tells the operator to run only `supabase.sql` + `supabase_signup_trigger.sql`.
- **Root Cause:** Deploy guide's run-order omits `idempotency_migration.sql` (and `admin_setup.sql` is only mentioned later, in the admin section). `supabase.sql` does not contain the `player_month_actions` (or `admins`) table.
- **Files:** `DEPLOY_FRESH.md` (§2 run order), `idempotency_migration.sql`, interaction with `backend/services/game_service.py:mark_action`.
- **Impact:** On a by-the-book fresh deploy, the table is absent → `mark_action` fails → returns `False` (see F-03) → every buy-choice and relative-help returns "you already did this." Two of the five PRD §4 player decision types are dead, and the failure is silent (no error, wrong message).
- **Risk:** High — event-blocking, silent, and easy to hit because the guide itself is the trap.
- **Recommendation:** Add `idempotency_migration.sql` and `admin_setup.sql` to the DEPLOY_FRESH §2 run order (or fold both tables into `supabase.sql` as the canonical schema). Cross-check every table the backend references is created by the documented order.

### F-03 — `mark_action` swallows all exceptions and reports "already done"
- **Severity:** Medium · **ADR:** Level 3 (guards a financial mutation).
- **Description:** `game_service.mark_action` wraps the insert in `try/except Exception: return False`. It cannot distinguish a PRIMARY-KEY unique violation (legit "already claimed") from any other failure (missing table, transient network error, RLS/permission issue). All map to `False`, which callers treat as "already acted."
- **Root Cause:** Over-broad `except` conflates the idempotency signal with generic failure.
- **Files:** `backend/services/game_service.py` (`mark_action`, lines ~141–155).
- **Impact:** A transient DB hiccup wrongly tells a player they already acted (lost turn). Combined with F-02, a missing table silently disables the whole mechanic. Masks real outages as gameplay messages.
- **Risk:** Medium — data-integrity-safe but reliability/UX defect; amplifies F-02 from "misconfig" to "invisible".
- **Recommendation:** Narrow the catch to the unique-violation case (inspect the error/PG code) → return `False` only for a genuine duplicate; re-raise/surface other errors as a 5xx so misconfiguration is loud, not silent.

### F-04 — Stale, conflicting migration files are deploy-ordering landmines (RLS + scoring regression)
- **Severity:** Medium (High if triggered) · **ADR:** Level 4 (security/RLS) + deployment.
- **Description:** Two superseded files still sit at repo root and, if run after the current fixes, silently regress security and scoring:
  - `supabase_migration.sql` re-creates policy `"Enable all for leaderboard read" ON public.player_state FOR SELECT USING (true)` — the exact public-read hole `security_fix_rls.sql` was written to remove. Re-running it lets any authenticated client read **every** player's full financial row via the anon key (portfolio spying / fairness break).
  - The same file (and `fairness_fixes_migration.sql`) `CREATE OR REPLACE` `process_month_atomically`; the `supabase_migration.sql` body omits `discipline_score` / `financial_health_score` persistence. Run last, the leaderboard score silently stops updating. (Postgres preserves EXECUTE grants across same-signature `CREATE OR REPLACE`, so the QA-001 revoke survives — but the *body* regression does not.)
- **Root Cause:** Superseded incremental migrations were never retired once `supabase.sql` became the canonical schema; nothing marks which files are current vs. historical.
- **Files:** `supabase_migration.sql` (fully superseded), `fairness_fixes_migration.sql` (RPC body now also in `supabase.sql`), vs. canonical `supabase.sql` + `security_fix_rls.sql`.
- **Impact:** A well-meaning operator re-running an old file to "make sure" reintroduces a Critical RLS hole and/or freezes scoring — with no error.
- **Risk:** Medium normally; High the moment someone runs the wrong file.
- **Recommendation:** Quarantine superseded migrations (move to `migrations/archive/` or add a bold "SUPERSEDED — DO NOT RUN, see supabase.sql" header) and document the single canonical fresh-install order + the between-games incremental order in one place. No live-DB change required.

### F-05 — `service_role`-shaped `.env` and a stray backend copy live inside the deployable `frontend/` tree
- **Severity:** Medium · **ADR:** Level 4 (security hygiene).
- **Description:** `frontend/backend/` contains `.env` (with `SUPABASE_SERVICE_KEY=…`) and `requirements.txt` — a stray duplicate of the real `backend/`. The `.env` currently holds only the placeholder (`PASTE-YOUR-SERVICE-ROLE-KEY-HERE`), so **no live secret is exposed today**. But `DEPLOY_FRESH.md` §"Deploying for real" instructs "drag the `frontend/` folder into Netlify," which would publish anything under it as world-readable static assets.
- **Root Cause:** Accidental nested `backend/` copy inside `frontend/`; `.gitignore`'s `.env` rule keeps it out of git but not out of a folder-drag deploy.
- **Files:** `frontend/backend/.env`, `frontend/backend/requirements.txt`.
- **Impact:** Latent footgun — if any operator ever fills that placeholder (or copies `backend/.env` there), the service-role key ships to the public CDN, bypassing all RLS. Currently a hazard, not an active leak.
- **Risk:** Medium — no current exposure, but a high-blast-radius trap on the documented deploy path.
- **Recommendation:** Delete `frontend/backend/` entirely. Add a deploy note that the Netlify publish dir must contain no `.env`. (If any real service key was ever placed there historically, rotate it.)

### F-06 — DEPLOY_FRESH.md contradicts the shipped auth flow (onboarding can't be followed as written)
- **Severity:** Medium · **ADR:** Level 1 (docs) — but event-blocking for a first-time operator.
- **Description:** `frontend/js/auth.js` is login-only: "accounts are pre-created by the admin… public signup is disabled," and the submit handler calls only `signInWithPassword` (no `signUp`). Yet `DEPLOY_FRESH.md` §6 step 1 says "Sign up a test student → Create an account," §3 configures email-confirmation for signups, and §6 step 2 says `admin.html` "prompts for the admin token — paste your ADMIN_TOKEN" (admin actually logs in with email/password at `admin-login.html`).
- **Root Cause:** Docs predate the auth rewrite (Google-OAuth → email/password, signup removed) and the admin-token → `admins`-table migration; never updated.
- **Files:** `DEPLOY_FRESH.md` (§3, §6, §"What changed"), reality in `frontend/js/auth.js`, `frontend/js/admin-login.js`.
- **Impact:** An operator following the guide cannot create a student account (no signup UI) and looks for a token prompt that doesn't exist → stuck at first smoke-test step.
- **Risk:** Medium — blocks setup, not code.
- **Recommendation:** Rewrite the affected DEPLOY_FRESH sections to match reality: admin pre-creates users in Supabase Auth; students log in only; admin uses email/password at `admin-login.html`; remove the token-prompt instructions. Folds naturally together with F-07/F-08.

### F-07 — `ADMIN_TOKEN` is dead, and the docs describing it are self-contradictory (= QA-007, broadened)
- **Severity:** Low · **ADR:** Level 1 (docs).
- **Description:** Re-verified: zero `.py` references to `ADMIN_TOKEN`; the frontend sends no `X-Admin-Token` header (grep: none). Auth is entirely Supabase JWT + `public.admins`. Yet `DEPLOY_FRESH.md` line 8 ("Admin actions are gated by a shared secret token"), §4, and `backend/.env.example` all present `ADMIN_TOKEN`/`X-Admin-Token` as the admin gate — while DEPLOY_FRESH's own admin section (lines 114–117) correctly says admins use the `admins` table "not the old `ADMIN_TOKEN`." The document contradicts itself.
- **Root Cause:** Same auth migration as F-06; `.env.example` and deploy doc never updated.
- **Files:** `DEPLOY_FRESH.md`, `backend/.env.example`.
- **Impact:** Operator configures a credential that does nothing and may believe it's a security boundary.
- **Risk:** Low — misleading, not exploitable.
- **Recommendation:** Delete `ADMIN_TOKEN`/`X-Admin-Token` from `.env.example` and DEPLOY_FRESH; replace with "grant admin = insert `auth.users.id` into `public.admins`."

### F-08 — `backend/utils.py` is dead duplicate code with a divergent, stale RPC validator (= partly new)
- **Severity:** Low · **ADR:** Level 1 (maintainability); ADR-007 (single source of truth for rules).
- **Description:** `backend/utils.py` re-implements `fair_roll`, an in-memory `_rate_limit`, `get_uid`, `get_player`, and `validate_rpc_payload` — none imported anywhere (grep: no `import utils`/`from utils`). Its `PLAYER_STATE_REQUIRED` is missing `discipline_score`/`financial_health_score` (the pre-ADR-008 set) and its loan sets differ from the live `game_service` validator.
- **Root Cause:** Superseded module left behind after logic moved into `services/`.
- **Files:** `backend/utils.py`.
- **Impact:** A future maintainer importing the wrong `validate_rpc_payload` would silently drop score-field validation; the in-memory rate-limit is exactly the bug `idempotency_migration.sql` replaced. Pure trap.
- **Risk:** Low.
- **Recommendation:** Delete `backend/utils.py` (confirm no dynamic import first — already grep-verified static).

### F-09 — Non-atomic cash read-modify-write in buy-choice and relative-help (cross-action lost update)
- **Severity:** Low · **ADR:** Level 3 (financial mutation).
- **Description:** `choice_service.execute_choice` and `player_routes.handle_relative` read `cash` from a state dict fetched at request start, then `UPDATE player_state SET cash = <recomputed>`. The `mark_action` claim prevents *same-action* double-apply, but two *different* concurrent actions by one player (e.g. buy-choice + help-relative, or double-submit across endpoints) each write an absolute cash value computed from the same stale read — one deduction is lost.
- **Root Cause:** Absolute-value writes instead of atomic conditional decrements (the pattern QA-003 fixed for `/sell` but not generalized).
- **Files:** `backend/services/choice_service.py` (line 69), `backend/routes/player_routes.py` (`handle_relative`, lines ~337–343).
- **Impact:** A player could occasionally keep cash they spent. Lower likelihood than QA-003 (needs concurrent *distinct* actions by the same user), but same class of defect.
- **Risk:** Low — narrow window, single-user, event context.
- **Recommendation:** Route these deductions through an atomic conditional SQL update (or a small RPC mirroring `sell_asset_atomic`) that decrements `cash` in-DB with a balance guard. Also note (informational): neither path recomputes `net_worth`/`financial_health_score`, so the dashboard shows stale figures until the month is processed — consistent with the "score reflects last processed month" design, so not itself a defect.

### F-10 — Content/seed inconsistencies: `case_study` buckets vs `constants`, and a dead `relative_events` table
- **Severity:** Low · **ADR:** Level 1 (content/cosmetic).
- **Description:** The seeded `case_study` row (`rent 20000, food 10000, transport 5000, family 5000`) doesn't match `constants.LIFESTYLE_COSTS` (city `rent 25000`, outer `rent 10000`). The case-study screen therefore shows numbers that don't correspond to the actual economy the player will face. Separately, `public.relative_events` is created but never read (relative help takes `relative_type` from the client, not this table).
- **Root Cause:** Seed data authored before the lifestyle constants were finalized; `relative_events` a vestige of an earlier design.
- **Files:** `supabase.sql` (case_study seed, `relative_events` table), `backend/models/constants.py`.
- **Impact:** Minor educational/accuracy nit on the intro screen; dead schema object.
- **Risk:** Low.
- **Recommendation:** Align the `case_study` seed to the real city/outer split (or make the screen render from `constants`); drop or document `relative_events`. Touch only between games (content = ADR-012 rules version discipline if it affects tuning; this is display only).

### Carried-forward open items (re-verified this pass)
- **QA-006 — Leaked-password protection disabled** · Low–Med · Level 4. Still a live Supabase Auth setting; not verifiable from the repo. One-toggle fix. (RC2 H2.)
- **QA-008 — Bike-lock-in sell warning is a dead `pass` stub** · Low · Level 1. Confirmed still present, `player_routes.py` ~237. No functional effect.
- **QA-009 — Fixed-value stocks/gold events emit no log line** · Low · Level 1. Confirmed in `event_engine.apply_event_to_state` (`fixed` branch logs cash only). Balances update correctly; only the summary line is missing.
- **QA-010 — Score component breakdown not exposed as structured data** · Informational · Level 2. Components are computed and logged as free text only.
- **QA-011 — `player_month_log` is a text summary, not a line-item ledger** · Informational · accepted V1 tradeoff, not a defect.
- **QA-012 — `/next-month` per-player sequential queries** · Medium (High if headcount > ~100) · Level 3. Confirmed still present (`admin_routes.next_month` loops `get_active_loans`/`get_pending_sales` per player). Safe ≤ ~50–100 players.
- **QA-013 — Admin recovery runbook missing** · Medium (event-blocking per plan) · Level 2. No runbook file exists.
- **QA-023 (informational) — Late auto-loans don't fully amortize by month 12.** `_amortized_emi` computes EMI from principal over `LOAN_TERM_MONTHS=6`; loans taken after ~month 7 carry residual balance at game end. Not a bug — the residual is correctly counted against net worth; noting so it's a conscious behavior.

### Explicitly verified correct (not issues)
Determinism suite green (seeded market/events/choices; no wall-clock/UUID nondeterminism; `import random` confined to approved files). Amortized EMI provably shrinks to zero. Discipline running-average is order-correct given sequential monthly calls. Server authority holds: frontend performs **zero** direct DB writes (grep confirms no `.update/.insert/.upsert/.delete` against Supabase); RLS is SELECT-own-row only in the canonical schema. `admin_required` gates every admin route; `process_month_atomically` locks + validates month transition + enforces idempotency. QA-001/002/003/004/005 fixes present and coherent.

---

## 2. Severity roll-up

| Severity | Open items |
|---|---|
| Critical | 0 (QA-001 fixed in repo; verify on live DB) |
| High | F-01 (QA-014 market fairness) · F-02 (deploy omits idempotency table) |
| Medium | F-03 · F-04 · F-05 · F-06 · QA-012 · QA-013 |
| Low | F-07 · F-08 · F-09 · F-10 · QA-006 · QA-008 · QA-009 |
| Informational | QA-010 · QA-011 · QA-023 |

---

## 3. Phased Implementation Plan

One issue implemented at a time; after each: run tests → verify → report (Objective / Files / DB impact / Rollback / Tests / Verification / Remaining risks) → **stop for approval**. No deploys (manual, by you). No mid-game changes (ADR-012/013).

### Phase 1 — Deploy integrity & security hygiene
**Issues:** F-02, F-03, F-04, F-05, F-07 (+ QA-006 is your Supabase console toggle).
**Requirement analysis:** These make a *fresh* deploy safe and correct. None change gameplay; they fix what breaks or regresses when the app is stood up on a clean project. Satisfies SRS §6 (security), §7 (deploy), ADR-013 rule 3 (security = Level 4), and closes the silent-failure path for PRD §4 player actions.
**Implementation plan:** (a) F-02: extend `DEPLOY_FRESH.md` §2 run-order to include `idempotency_migration.sql` + `admin_setup.sql` (or fold both tables into `supabase.sql`). (b) F-03: narrow `mark_action`'s except to unique-violation only. (c) F-04: quarantine `supabase_migration.sql` (and mark `fairness_fixes_migration.sql` historical), document the one canonical order. (d) F-05: delete `frontend/backend/`. (e) F-07: purge `ADMIN_TOKEN`/`X-Admin-Token` from docs + `.env.example`.
**Files:** `DEPLOY_FRESH.md`, `idempotency_migration.sql`/`admin_setup.sql` (referenced), `backend/services/game_service.py`, `supabase_migration.sql`, `fairness_fixes_migration.sql`, `frontend/backend/*`, `backend/.env.example`.
**DB impact:** None to live data. Only fresh-install ordering/wording (and, if F-02 folds tables into `supabase.sql`, an additive `CREATE TABLE IF NOT EXISTS`). **Migration:** no new migration against the running project; F-03 is a pure code change.
**Rollback:** `git revert` per file; deleted `frontend/backend/` restorable from history; no data migration to reverse.
**Test plan:** re-run `backend/tests/` (must stay 29/30 → then 30/30 after Phase 2); add a check (or manual) that a fresh schema built strictly from the documented order contains `player_month_actions` + `admins`; unit-check `mark_action` returns `False` on duplicate and *raises* on a simulated non-duplicate error.
**Verification:** dry-run the documented deploy order on a scratch project (or SQL lint) and confirm every backend-referenced table exists; grep confirms no `ADMIN_TOKEN`/`frontend/backend` remain.
**Expected risks:** Low. F-03 is the only behavioral code change; risk is mis-detecting the PG unique-violation code — mitigate by matching on `psycopg`/PostgREST error rather than message text.

### Phase 2 — Financial correctness & fairness
**Issues:** F-01 (QA-014), then F-09.
**Requirement analysis:** Restores ADR-009/ADR-000 fairness (F-01) and removes the residual cash race (F-09). Both are Level 3; deploy only between games.
**Implementation plan:** F-01 — draw both `rng.uniform()` unconditionally after seeding; guard only application. F-09 — move buy-choice/relative-help cash deduction to an atomic conditional decrement (small RPC or `UPDATE … WHERE cash >= cost`).
**Files:** `backend/engine/market_engine.py` (F-01); `backend/services/choice_service.py`, `backend/routes/player_routes.py`, possibly one new `*_atomic` SQL function mirroring `sell_asset_atomic` (F-09).
**DB impact:** F-01 none. F-09 adds one `SECURITY DEFINER` RPC (REVOKE to `service_role`, per the QA-001 lesson) **if** the RPC route is chosen. **Migration:** F-09 RPC = one additive migration + rollback `DROP FUNCTION`.
**Rollback:** `git revert` (F-01); `DROP FUNCTION` + revert route (F-09).
**Test plan:** F-01 flips `test_zero_holding_players_do_not_break_fairness_for_others` to pass → full suite 30/30; re-run determinism suite to prove players holding both assets are unchanged (same seed/order). F-09: add a concurrent-distinct-action test asserting no lost cash deduction.
**Verification:** 12-month replay determinism unchanged; fairness suite green; score bounds intact at edges.
**Expected risks:** F-01 must not alter draw order for populated players — the unconditional-draw approach preserves it exactly; determinism suite is the guard.

### Phase 3 — Business-logic & content polish
**Issues:** F-10, QA-008, QA-009 (and QA-010 if you elect to pick it up).
**Requirement analysis:** Cosmetic/log-completeness and content-accuracy items; Level 1 mostly (QA-010 Level 2). No ranking math changes.
**Implementation plan:** QA-009 add the missing `log +=` lines for `fixed` stocks/gold; QA-008 either emit a real `"warning"` field or remove the dead `pass`; F-10 align `case_study` seed to `constants` (or render from constants) and drop/annotate `relative_events`.
**Files:** `backend/engine/event_engine.py`, `backend/routes/player_routes.py`, `supabase.sql` (seed), optionally `frontend/js/case-study.js`.
**DB impact:** F-10 touches seed data only (between games). **Migration:** none beyond a seed correction.
**Rollback:** `git revert`.
**Test plan:** unit-assert a `fixed` stocks event now yields a log line; snapshot the case-study payload.
**Verification:** manual UI check of the case-study screen and a monthly log containing a fixed stocks/gold event.
**Expected risks:** Very low.

### Phase 4 — Performance
**Issue:** QA-012 (conditional on headcount, per RC2 C3).
**Requirement analysis:** Only triggered if confirmed headcount approaches/exceeds ~100. Level 3.
**Implementation plan:** batch-fetch loans + pending sales in two queries total, group in memory (exactly the fix SRS §9 / Plan T2.1 already specify). No behavior change to results.
**Files:** `backend/routes/admin_routes.py`, `backend/services/game_service.py`.
**DB impact:** read-pattern only; no schema change. **Migration:** none.
**Rollback:** `git revert`.
**Test plan:** 12-month replay must produce byte-identical results pre/post (determinism suite); time `/next-month` at target N.
**Verification:** processing-time measurement at the confirmed headcount.
**Expected risks:** Grouping bug could misattribute a loan/sale — determinism replay + a per-player reconciliation test guard against it.

### Phase 5 — Documentation & operations
**Issues:** F-06, QA-013 (runbook), F-08 (dead `utils.py` — could also sit in Phase 1; grouped here as pure debt), QA-006 confirmation.
**Requirement analysis:** Level 1–2. Event-blocking per the project's own checklist (runbook) but non-code.
**Implementation plan:** rewrite DEPLOY_FRESH auth/onboarding sections to match reality (F-06); author the admin recovery runbook (QA-013/T4.1); delete `backend/utils.py` (F-08); record QA-006 toggle state.
**Files:** `DEPLOY_FRESH.md`, new `RUNBOOK.md`, `backend/utils.py` (delete).
**DB impact:** none. **Migration:** none.
**Rollback:** `git revert`.
**Test plan:** doc walkthrough; runbook rehearsal (per RC2 Step 10).
**Verification:** a first-time operator can follow DEPLOY_FRESH end-to-end without hitting a contradiction.
**Expected risks:** none technical.

---

## 4. Production-Readiness Scorecard

Scores reflect the **repository** state today (fixes-in-tree), independent of the still-pending deploy/content/runbook work that RC1/RC2 already track.

| # | Dimension | Score | Basis |
|---|---|---|---|
| 1 | **Production Readiness** | **60 / 100** | Engine sound, QA-001–005 fixed in tree, test suite now exists (up from RC2's 55%). Still blocked by: F-01 failing test, deploy-integrity findings (F-02/F-04), and the standing non-code blockers (content pack, runbook, dry run, deploy of approved fixes). |
| 2 | **Security** | **75 / 100** | Critical RPC + RLS closed in canonical schema; server authority verified. Held back by deploy-order landmines (F-04), the `frontend/backend` footgun (F-05), and the open Auth toggle (QA-006). |
| 3 | **Financial Correctness** | **80 / 100** | Amortization, discipline average, scoring, idempotent month processing all verified correct and (mostly) tested. Deductions: F-01 fairness defect, F-09 cash race. |
| 4 | **Fairness** | **70 / 100** | Global market path correct by design and mostly tested, but F-01 is a live, reproduced violation. Rises to ~95 once F-01 lands. |
| 5 | **Performance** | **60 / 100** | Reads indexed/fast; `/next-month` is O(N) round-trips (QA-012), safe only ≤ ~100 players; no load test performed. |
| 6 | **Maintainability** | **70 / 100** | Clean engine/route/service separation (ADR-007 honored); growing test suite. Dragged by dead `utils.py` (F-08), stale migrations (F-04), doc drift (F-06/F-07). |
| 7 | **Educational Quality** | **85 / 100** | Composite score + compressed economy are pedagogically coherent and honest (PRD §5/§7). Minor: case-study number mismatch (F-10); thin authored content (event-blocking but not a code defect). |
| 8 | **Technical Debt** | **65 / 100** (moderate) | Contained but real: dead code, duplicate/stale SQL, documentation rot. No architectural debt. |

---

## 5. Remaining Risks

1. **Live-DB drift not verifiable from the repo.** QA-001/003 fixes are in the SQL; whether the *live* `ujoqdsesfctxmzmlxewu` still has them (and hasn't been touched by a stale-file re-run, F-04) needs a `get_advisors` / grant check on the actual project.
2. **F-02 + F-03 interaction is silent.** Until fixed, a fresh deploy can look healthy while two player mechanics are dead.
3. **F-01 is a *ranking* defect**, so its impact is invisible in casual play but decides winners.
4. **Non-code blockers still dominate the release** (RC1/RC2): approved fixes not yet committed/deployed, no months 2–12 content pack, no runbook, no full dry run, unconfirmed headcount.
5. **`frontend/backend/.env` footgun** is inert now but on the documented deploy path.

---

## 6. GO / NO-GO

**NO-GO for V1 release** (consistent with RC1/RC2).

The repository is in good structural shape and materially better than the QA report implies, but three code/deploy blockers plus the standing operational gaps remain:
- **F-01** — a live, test-proven fairness violation on the ranking metric (High).
- **F-02/F-04** — a fresh deploy per the current guide can silently break player actions and/or regress RLS and scoring (High / Medium-High-if-triggered).
- The RC2 critical set is still open: approved fixes uncommitted/undeployed, no content pack, no admin runbook, no full 12-month dry run, headcount unconfirmed.

**What flips it to GO:** land Phase 1 + Phase 2 (deploy integrity + F-01/F-09) with the suite at 30/30; complete the RC2 operational punch list (content pack, runbook, dry run, commit+deploy the approved fixes, headcount). None are large; all are scoped.

---

*End of RC3 audit. No code, schema, or documentation was modified in producing this report. Awaiting approval to begin Phase 1 — one issue at a time.*
