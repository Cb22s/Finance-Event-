# Money Master - Controlled Implementation Report

Date: 2026-09-08. Branch: main. Changes are uncommitted.
Starting working tree was clean. No production data or deployed application was changed.

## Verdict

**PARTIALLY READY**

The canonical database installation and the isolated 12-month API/database run
pass. The game concept, score weights, spouse economics and optional-choice
visibility are preserved. A real Supabase/Auth/PostgREST browser rehearsal and
native concurrent-client verification remain outstanding, so this is not a pilot
sign-off.

## 1. Files changed

| File | Reason |
| --- | --- |
| .gitignore | Exclude downloaded dependencies and generated verification output in .test-runtime. |
| IMPLEMENTATION_PLAN.md | Implementation sequence and runtime database dependency map. |
| supabase.sql | Repeatable canonical installation, missing runtime schema, secure transaction contracts and finalization. |
| backend/engine/monthly_processor.py | Share the current expense calculation with the API; preserve zero satisfaction. |
| backend/engine/scoring.py | Recalculate final scores from final portfolios using the unchanged formula. |
| backend/routes/admin_routes.py | Database readiness gate, processing cleanup, final scoring, event-category persistence. |
| backend/routes/player_routes.py | Atomic initial allocation, insurance, reveals, locking and negotiation persistence; authoritative display data. |
| backend/services/game_service.py | Validate every monthly state field and recognize database gate errors. |
| backend/tests/test_a01_concurrency.py | Point native concurrency tests at the current canonical schema. |
| backend/tests/test_archetype_consistency.py | Fix imports when tests are discovered from the repository root. |
| backend/tests/postgres_bridge.mjs | Isolated PostgreSQL-in-WebAssembly test transport. |
| backend/tests/local_database.py | Test-only SQL adapter for the PostgREST calls made by Flask routes. |
| backend/tests/test_runtime_database.py | Installation, RLS coverage, transaction rollback, readiness and persistence regressions. |
| backend/tests/test_api_lifecycle.py | Actual API routes through Month 12; event, roster, cleanup and leaderboard checks. |
| backend/tests/frontend_contracts.mjs | Execute wedding/reveal rendering and lifestyle selection with backend fixtures. |
| backend/tests/test_frontend_contracts.py | Run frontend contract checks through unittest. |
| backend/tests/test_strategy_simulation.py | Six-strategy repeatability, conservation and unchanged-weight checks. |
| backend/tools/strategy_simulation.py | Reproducible baseline and event-pack strategy comparisons. |
| frontend/admin.html | Category selector in the existing event form. |
| frontend/js/admin.js | Submit the selected event category. |
| frontend/allocation.html | Remove stale lifestyle expense descriptions. |
| frontend/js/allocation.js | Load current costs, balance initial defaults and repair selector callback scope. |
| frontend/case-study.html | Correct base-expense labels. |
| frontend/js/case-study.js | Render current backend living costs instead of old fallback figures. |
| frontend/dashboard.html | Base/current household expense summary. |
| frontend/js/dashboard.js | API wedding cost and revealed traits; current expense display. |
| README.md | Current game flow, canonical setup path and reproducible verification instructions. |
| PRD.md | Actual current mechanics, timing, costs, scoring and operational behavior. |
| PROJECT_STATE.md | Replace obsolete deployment/mechanics claims with current local facts. |
| IMPLEMENTATION_REPORT.md | This report and acceptance evidence. |

Generated outputs are .test-runtime/dry_run.json and .test-runtime/strategies.json.
They contain no live player data. Downloaded test dependencies are also isolated
under .test-runtime and are not application changes.

## 2. Database changes

### Tables added to the canonical path

- spouse_archetypes and player_spouse_reveals, previously only in the marriage migration.
- market_scenarios and player_month_allocations, previously only in the V2 migration.
- player_negotiations, spouse_proposals and spouse_dialogue, derived from backend reads and writes.

The single sentinel is now valid in spouse_archetypes. Existing archetype rows
are retained rather than overwritten. Python ARCHETYPES remains authoritative.

### Columns and defaults

- events.category, defaulting unspecified existing events to a non-insurable admin category.
- game_control.marriage_round_active and negotiation_enabled; retain automatic-mode flags.
- player_state.spouse_archetype, spouse_satisfaction, household_expense_modifier and insurance_plan.
- Retain/add discipline_score and financial_health_score for older installations.
- player_loans.term_months, loan_type and emi. Future default interest is 0.012;
  existing loan amounts and rates are not rewritten.

### Transaction functions

| Function | Contract |
| --- | --- |
| player_apply_atomic | Same ten Python arguments; game then player locks; additive balances and action claim; atomic reveal and confirmed-negotiation writes; returns fresh state. |
| process_month_atomically | Same five arguments; validates the full player batch and transition; persists every engine state field, loan terms and logs. |
| sell_asset_atomic | Same five arguments; rechecks current playable turn under the shared game/player locks. |
| begin_month_transition | Checks current month, all locks, required allocation/marriage decisions and unallocated roster users; freezes only when ready. |
| initialize_player | Initial state, allocation claim and initial log commit together. |
| finish_game_atomically | Validates locked Month 12 states, applies Python-calculated final scores and ends the game together. |

Economic formulas remain in Python. SQL performs serialization, validation and
persistence. A duplicate or failed financial transaction does not leave a partial
action claim or child record. Negotiation commits must match saved intent parameters.

### Policies, grants and indexes

All runtime tables have RLS enabled. Player reveals, allocations and negotiations
have read-own policies. Financial transaction functions deny PUBLIC, anon and
authenticated execution and grant service_role execution. Service-role table and
sequence access is explicit. Functions use a fixed search_path.

Known obsolete financial FOR ALL policies are removed; canonical read-own policies
remain. The spouse catalogue is not publicly readable through its old policy,
which would bypass paid reveals. Market reads are limited to released months.
Proposal/dialogue catalogues remain backend-managed.

Indexes cover player/month/round negotiation reads, one confirmed result per
round, proposal archetype/month lookup and dialogue archetype lookup.

The canonical file uses a transaction, idempotent DDL and non-destructive seed
inserts. Fresh and repeat installation are verified. Compatibility with unknown
custom live schemas/data still requires a staging upgrade; historical migrations
must not be replayed afterward.

## 3. Verified bugs fixed

1. Missing canonical tables, household columns, event category and player transaction RPC.
2. Monthly SQL omitted current spouse/insurance state and new-loan metadata.
3. Admin advancement skipped unlocked players, including final-month decisions.
4. Player requests checked playability only before a database race; transaction-time checks now serialize with advancement.
5. Initial allocation could claim the action but fail to create state or its log.
6. A confirmed negotiation could move money and then lose its result record.
7. Negotiation confirmation checked intent but did not require matching saved parameters.
8. Extra-date cash deduction and reveal insertion could fail independently or race.
9. Insurance selection was outside the shared transaction gate.
10. Stay-single selection violated the marriage foreign key.
11. Wedding text and candidate values in the UI were stale and hardcoded.
12. Expense descriptions were stale, and lifestyle selection called functions outside their scope.
13. Admin event creation discarded category even when supplied, breaking insurance classification.
14. Zero satisfaction was treated as missing and reset to the default.
15. Month 12 completion could retain scores calculated before the final player actions.
16. A processing exception before the old RPC try-block could leave the game frozen.
17. Repository-root test discovery failed on the archetype consistency import.

The repository search classified remaining 88,000 references: the City living
expense is current; old wedding values in historical calibration/change reports
are historical; current UI no longer hardcodes wedding cost. WEDDING_COST remains
25,000 in the unchanged constants.

## 4. Tests

| Run | Passed | Skipped | Errors/failures |
| --- | ---: | ---: | ---: |
| Previous audit: 95 tests | 92 | 2 | 1 import error |
| Current: 111 tests | 109 | 2 | 0 |

Command: python -m unittest discover -s backend/tests -q

The 16 added tests cover nine database cases, five API cases, one frontend
contract test and one six-strategy simulation test. The existing import error is
resolved. Python compilation, changed JavaScript syntax checks and git diff
whitespace checks also pass.

The two skips are native pgserver/psycopg concurrency tests. PGlite executes the
actual canonical PostgreSQL SQL, including rollback failures injected with
database triggers. It is a single-session embedded engine; these passing tests
do not establish native simultaneous-client behavior.

The API adapter uses real SQL and Flask routes, with local authentication and
offline AI. It deliberately does not use production credentials or Supabase
network services. Frontend tests execute JavaScript with DOM fixtures; they are
not a browser layout or real-login rehearsal.

## 5. Twelve-month dry run

**Isolated API/database simulation: SUCCEEDED.**

One deterministic player completes initial allocation, every monthly advance,
available-cash allocations, turn locking, basic insurance, asset sale/next-month
credit, a voluntary loan, Month 4 Saver marriage, Month 5 negotiation, Month 6
festival and Month 8 refusal. All months use the authored event seed pack and a
fixed shared market path. No live database is used.

For each processed month, the test compares every engine state field against
the persisted row. The trace records balances, loans, insurance, spouse state,
score, status and month, plus reports for salary, expenses, market, events and
safety-net effects. Separate tests force automatic loans and verify their terms,
insurance classification, zero satisfaction and household-modifier persistence.

| Month | Cash after decisions | Debt | Recorded monthly score |
| --- | ---: | ---: | ---: |
| 1 | 65,000.00 | 0.00 | 75.35 |
| 2 | 78,000.00 | 0.00 | 61.69 |
| 3 | 99,400.00 | 20,000.00 | 55.91 |
| 4 | 78,515.28 | 16,765.28 | 53.77 |
| 5 | 47,818.51 | 13,491.74 | 51.30 |
| 6 | 32,447.63 | 10,178.92 | 48.78 |
| 7 | 9,520.57 | 6,826.35 | 46.59 |
| 8 | 0.00 | 3,433.55 | 44.42 |
| 9 | 0.00 | 0.03 | 42.47 |
| 10 | 0.00 | 0.00 | 38.95 |
| 11 | 0.00 | 0.00 | 35.88 |
| 12 | 37,535.33 | 0.00 | 39.02 |

Final net worth: Rs77,038.99. Final Financial Health Score: 39.02.
Game state: ended, month 12. Further advancement is rejected. A separate
three-player leaderboard case verifies score ordering and net-worth tie-breaking.

The monthly scores above are those calculated at monthly processing/marriage;
ordinary actions do not universally recalculate the live score. Finalization
explicitly refreshes it. The Rs0.03 Month 9 loan residue is an existing rounded-EMI
behavior; it is cleared in the following month, not changed by this repair.

## Strategy comparison

Both scenarios use identical market paths across players, City living, no spouse,
no insurance and fixed allocation fractions. D borrows Rs120,000 in Month 2.
The baseline has no personal events; stress uses the unchanged authored event
pack. These are reproducible hypothetical strategies, not optimal-play claims.

### Baseline

Liquidity is emergency-fund months of expenses. Amounts below are rupees.

| Rank | Strategy | Net worth | Liquidity | Debt | Risk | Discipline | FHS |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | B: Strong emergency fund | 228,778.89 | 1.724 | 0.00 | 18 | 100.00 | 52.73 |
| 2 | E: Balanced | 239,450.21 | 0.663 | 0.00 | 31 | 100.00 | 48.40 |
| 3 | C: Cash heavy | 222,702.31 | 0.000 | 0.00 | 20 | 100.00 | 47.92 |
| 4 | A: High risk | 249,767.61 | 0.000 | 0.00 | 79 | 100.00 | 39.83 |
| 5 | F: All remaining cash invested | 250,970.88 | 0.000 | 0.00 | 80 | 100.00 | 39.68 |
| 6 | D: Debt and investment | 254,056.17 | 0.000 | 31,941.54 | 78 | 41.66 | 29.63 |

### Authored event-pack stress

| Rank | Strategy | Net worth | Liquidity | Debt | Risk | Discipline | FHS |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | C: Cash heavy | -41,443.85 | 0.000 | 95,869.78 | 40 | 58.34 | 17.74 |
| 2 | B: Strong emergency fund | -36,666.02 | 0.066 | 84,780.16 | 78 | 46.67 | 10.47 |
| 3 | E: Balanced | -34,718.73 | 0.000 | 133,622.85 | 82 | 28.33 | 6.95 |
| 4 | A: High risk | -32,244.55 | 0.000 | 170,658.97 | 100 | 33.34 | 4.99 |
| 5 | D: Debt and investment | -28,751.05 | 0.000 | 292,443.48 | 96 | 25.00 | 4.35 |
| 6 | F: Repeated emergency borrowing | -31,556.39 | 0.000 | 173,922.72 | 100 | 25.00 | 3.75 |

F needs nine automatic loans in stress, and none in the baseline. Strong liquidity
beats greater risky wealth in the baseline, supporting the current score's
financial-health objective. The stress results identify content/balance pressure,
but do not establish a scoring-weight bug. No weights or content were changed.

## 6. Remaining issues

### BLOCKING pilot sign-off

- Run a staging Supabase installation with real Auth, PostgREST RPC calls and a
  deployed browser 12-month rehearsal. Local SQL/API verification is complete;
  this external integration is unverified.
- Run the two native concurrency tests and a multiple-player simultaneous-action
  rehearsal on a supported PostgreSQL host.

### IMPORTANT

- Review the event pack with adaptive play, insurance and spouse strategies before
  choosing the pilot content. The six fixed stress strategies all finish in debt.
- All provisioned non-admin accounts count in the readiness gate. Prepare the
  event roster deliberately; unused accounts can prevent advancement.
- Existing administrative restart/reset/correction workflows are retained. Do not
  run competing administrative operations during month processing. Forced worker
  termination after freezing a month still needs organizer/database recovery;
  handled application exceptions restore active state.
- Ordinary action audit rows outside the repaired initial-allocation, reveal and
  negotiation transactions remain best-effort. Live score freshness still follows
  existing monthly/marriage refresh points, with final completion now guaranteed.

### OPTIONAL

- Revisit the small final-installment rounding residue in loan amortization.
- Reactivate optional choices only as a controlled product/content follow-up.
- Add browser layout regression coverage and broader performance/load testing.

## 7. Final verdict

**PARTIALLY READY**. The requested local repairs and deterministic verification
are implemented. Remaining acceptance work concerns the real deployment,
concurrent users and pilot content validation, not a redesign of Money Master.
