# Money Master

Money Master is a live, admin-paced financial simulation for students. Players
start with Rs1,00,000 and manage 12 months of income, expenses, investments, debt,
insurance, emergencies, marriage and spouse negotiations. The winner is ranked by
Financial Health Score, with net worth used only to break ties.

## Current implementation

The static HTML/JavaScript frontend calls Flask routes. Python engines decide
financial outcomes. Supabase stores state and runs atomic database transactions.
Economic constants are authoritative in `backend/models/constants.py`.

Month 1 creates the initial allocation and locks the turn. For months 2-12,
players review the processed month, make decisions, allocate available cash
(including choosing to retain cash), and lock their turn. The administrator
cannot advance until every player is ready. Registered non-admin users who have
not completed their initial allocation are counted as unready.

Marriage is available in Month 4 when the administrator opens the round.
Players reveal candidates and select a spouse or stay single. Wedding cost is
Rs25,000. Three reveals are free; additional distinct reveals cost Rs5,000.
Spouse income, assets, expenses, satisfaction and negotiated household changes
remain on the player's existing state. Month 6 uses the family festival proposal.
Later conversations use authored proposals or built-in defaults. AI interprets
and narrates; the deterministic evaluator decides all financial effects.

Optional choices and relative-help APIs remain implemented. Optional choices
stay hidden in the player interface, following the organizer's recorded
2026-07-24 decision. This repair does not reactivate them.

## Monthly processing

1. Credit pending asset sales.
2. Add salary and applicable spouse income.
3. Deduct inflation-adjusted living costs, bike savings and household modifiers.
4. Deduct the selected insurance premium.
5. Apply the common market scenario and emergency-fund interest.
6. Apply events and eligible insurance reimbursements.
7. Deduct bike EMI and amortized loan repayments.
8. Cover deficits from the emergency fund, then an automatic loan if needed.
9. Persist all state, loan changes and logs; calculate Financial Health Score.

Base living expenses are Rs88,000 for City and Rs82,000 for Outer.
Inflation starts in Month 4. Emergency funds earn 0.5% monthly. Voluntary loans
use 1.2% monthly interest; automatic loans use 2.5%. Authored market scenarios
override automatic markets. Auto events and auto markets default to off.

At the end of Month 12, everyone locks before the final advancement command.
The backend refreshes scores from the final portfolios and ends the game
atomically. The separate manual End Game control remains available.

## Database installation and upgrade

`supabase.sql` is the authoritative schema path for this version. Run it as the
database owner in the Supabase SQL Editor, outside an active game. It creates
missing runtime objects and replaces the current transaction functions in one
transaction. Re-running it preserves existing player and authored-content rows.
It is tested on an empty database and on repeat installation.

Use a backup and a staging copy before applying to a live installation with
custom changes. This work has not inspected or upgraded the live database.

Do not replay historical migration files after the canonical file. Their older
function definitions can undo current repairs. They remain as historical records,
not an alternative installation sequence.

After installation, create an admin account and add its auth user UUID to
`public.admins`. The signup trigger maintains `public.users`. Financial writes
and transaction RPCs remain restricted to the backend service role.

Schema installation does not author the competition. The optional
`backend/tools/seed_content.py` contains the existing months 2-12 content pack;
running that script replaces existing event and choice rows. Review its contents
before using it on a staging game. Market scenarios remain admin-authored.

## Running locally

Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `backend/.env` for the intended
development database. Set the Supabase URL and public anon key in
`frontend/js/config.js` to that same project, then run:

```powershell
python -m pip install -r backend/requirements.txt
python backend/app.py
```

Serve the frontend from another terminal:

```powershell
python -m http.server 8080 --directory frontend
```

Open http://localhost:8080. The frontend automatically uses localhost:5000 when
served on localhost; deployed pages use the backend URL in `frontend/js/config.js`.

## Verification

Run the unit suite from the repository root:

```powershell
python -m unittest discover -s backend/tests -v
```

For the isolated SQL and API tests, install the test database runtime first:

```powershell
npm install --prefix .test-runtime --no-audit --no-fund @electric-sql/pglite@0.3.14
```

The API tests use the real Flask routes and canonical SQL with test-only
authentication and offline AI. They never connect to the configured Supabase.
PGlite runs PostgreSQL in WebAssembly; it is not a substitute for native
multi-client concurrency or deployed Supabase/Auth/PostgREST verification.
Native concurrency tests require `pgserver` and `psycopg` on a supported host.

Run the six-strategy comparison with:

```powershell
python backend/tools/strategy_simulation.py --output .test-runtime/strategies.json
```

See `IMPLEMENTATION_PLAN.md` for the dependency map and
`IMPLEMENTATION_REPORT.md` for results, changed files and remaining checks.
