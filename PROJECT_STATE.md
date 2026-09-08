# Money Master - Current Project State

Updated 2026-09-08 after controlled implementation.
This replaces the obsolete July handoff; old RC/audit documents remain historical.

## Scope and repository

The work began on a clean main branch. Changes are uncommitted and are limited
to implementation consistency, verification and current documentation.
No live database, Render deployment or Netlify deployment was changed or inspected.

The existing concept is preserved: 12 admin-paced months, recurring allocation,
insurance, loans, Month 4 marriage, Month 6 festival, spouse negotiations and
Financial Health Score. No score weights or spouse archetype economics changed.

## Database

Use supabase.sql as the canonical installation/upgrade path. It now includes all
runtime tables, household/insurance/loan fields, event categories and transaction
functions. The file is repeatable and transactional. Existing rows are retained.
Historical migrations must not be applied after it.

Fresh installation, repeat installation, rollback behavior, runtime table/RPC
coverage and monthly state persistence have local PostgreSQL test coverage.
The dependency map is in IMPLEMENTATION_PLAN.md.

## Repairs

- Database-backed readiness gate counts unlocked and not-yet-allocated players.
  A shared game lock serializes player transactions against month freezing.
- Initial allocation writes state, action claim and log in one transaction.
- Month processing persists all fields returned by the engine, including spouse,
  satisfaction, household modifiers, insurance and new-loan terms.
- Negotiation confirmation and financial effects commit together; confirmation
  must match the saved intent parameters.
- Reveal charging and the reveal record are atomic. Insurance uses the existing
  atomic player transaction.
- Staying single is valid under the spouse foreign key.
- Month 12 finalization recalculates final scores and then ends the game atomically.
- Wedding and revealed traits render backend data. Expense displays use current
  backend values; the lifestyle-selector callback scope is repaired.
- Event entry preserves its category, with category selection in the admin form.
- Zero spouse satisfaction is retained instead of resetting to the default.

Optional choices intentionally remain hidden. Backend functionality is preserved.

## Verification and limits

The isolated lifecycle exercises the actual Flask routes and canonical SQL through
12 months, including marriage, insurance, a voluntary loan, sale credits, the
festival and a later spouse conversation. Authentication is a local test fixture;
AI uses its supported offline path. This is not a deployed Supabase/browser test.

PGlite supplies a local PostgreSQL engine. Native simultaneous-client tests require
pgserver/psycopg and remain skipped on this machine. They now reference the
canonical schema rather than the historical atomic migration.

The six-strategy simulation compares a baseline and the existing event pack.
Healthy liquidity wins over greater risky wealth in the baseline. The event-pack
stress path drives all six fixed, uninsured, single strategies into debt. This is
a content/balance review signal, not proof that no adaptive strategy can succeed.
Weights and event content were left unchanged.

## Next acceptance checks

1. Apply the canonical schema to an isolated Supabase staging project and verify
   real account login, RLS, PostgREST RPC discovery and the deployed UI.
2. Run native PostgreSQL concurrency checks and a multi-player rehearsal.
3. Review authored content using insurance, spouse choices and adaptive strategies
   before selecting the actual pilot schedule.
4. Deploy only after those checks; live version and data are currently unverified.

Detailed results, per-file changes and the verdict are in IMPLEMENTATION_REPORT.md.
