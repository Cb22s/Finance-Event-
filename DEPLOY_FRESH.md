# Money Master — Fresh Supabase Deployment Guide

Everything a brand-new developer needs to stand up Money Master on an empty
Supabase project, end to end, without asking any questions. Follow top to bottom.

| Field | Value |
|---|---|
| **Guide version** | 2.0 |
| **Last updated** | 2026-07-15 |
| **Compatible backend** | Flask app at repo HEAD · Python 3.11 (`runtime.txt` = python-3.11.8) · reads only `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` |
| **Compatible schema** | `supabase.sql` — single-file canonical schema (includes `admins`, `player_month_actions`, and the signup trigger) |
| **Compatible frontend** | vanilla HTML/JS at repo HEAD · email + password login (no public signup) · `frontend/js/config.js` |

**Stack:** vanilla HTML/JS frontend → Flask backend → Supabase (Postgres + Auth).
The backend performs **all** financial writes with the `service_role` key; the
browser only ever *reads its own rows* (RLS). Admin access is gated by Supabase
Auth (JWT) plus membership in the server-only `public.admins` table — there is
**no** shared admin token.

---

## SQL file classification

Only one file is needed for a fresh install. Every other `.sql` file is either a
retrofit patch for an older project or is deprecated. Each file carries a header
banner stating its class.

| File | Class | When to run |
|---|---|---|
| `supabase.sql` | **Fresh Install** | Run once on a new project. Creates *everything*. |
| `supabase_signup_trigger.sql` | Existing Project Migration | Only to retrofit an older project missing the signup trigger. Folded into `supabase.sql`. |
| `admin_setup.sql` | Existing Project Migration + admin-grant snippet | Table folded into `supabase.sql`; file kept for the admin-grant SQL and old-project retrofits. |
| `idempotency_migration.sql` | Existing Project Migration | Only to add `player_month_actions` to an older project. Folded into `supabase.sql`. |
| `fairness_fixes_migration.sql` | Existing Project Migration | ADR-008/009 retrofit for an older project. Folded into `supabase.sql`. |
| `security_fix_rls.sql` | Existing Project Migration | RLS lockdown retrofit for an older project. Folded into `supabase.sql`. |
| `security_fix_rpc_grants.sql` | Existing Project Migration | RPC grant lockdown retrofit. Folded into `supabase.sql`. |
| `sell_asset_atomic_migration.sql` | Existing Project Migration | Atomic-sell RPC retrofit. Folded into `supabase.sql`. |
| `supabase_migration.sql` | **Deprecated — never run** | Re-opens a public read policy and reverts scoring. |

> **For a fresh install, run only `supabase.sql`.** Do not run any of the others.

---

## Pre-deployment checklist

Confirm all of these before you start:

- [ ] You have a Supabase account and can create a new project.
- [ ] You have the repository checked out locally.
- [ ] Python 3.11+ is installed (`py --version` / `python --version`).
- [ ] (Local run) Windows with the `.bat` files, or you can run Flask + a static server manually.
- [ ] (Real deploy) A Render account (backend) and Netlify account (frontend).
- [ ] You know which email addresses will be the **admin(s)**.
- [ ] `backend/.env` does **not** exist yet, or you are ready to overwrite it (it is git-ignored).
- [ ] You will **not** be deploying over a game that is already in progress (ADR-012).

---

## 1. Create the Supabase project

1. supabase.com → **New project**. Pick a region near your users. Save the database password.
2. Wait for provisioning to finish.

**Expected result:** the project dashboard loads; **Project Settings → API** shows a Project URL, an `anon` public key, and a `service_role` key.

---

## 2. Deploy the database — ONE file

SQL Editor → **New query** → paste the entire contents of **`supabase.sql`** → **Run**.

This one idempotent script creates every backend dependency:
- **Tables (14):** `users`, `player_state`, `player_loans`, `player_sales`,
  `player_relative_score`, `player_relative_actions`, `player_month_log`,
  `game_control`, `events`, `optional_choices`, `case_study`, `admins`,
  `player_month_actions`, and `relative_events` (legacy, present but unused).
- **RLS policies:** clients get SELECT-own-row only; `admins` and
  `player_month_actions` have RLS on with **no** client policy (fully server-only);
  reference tables (`case_study`, `events`, `optional_choices`, `game_control`) are
  public-read. All writes go through the backend's `service_role` key.
- **RPCs (2):** `process_month_atomically` and `sell_asset_atomic`, each `REVOKE`d
  from `PUBLIC`/`anon`/`authenticated` and granted only to `service_role`.
- **Function + trigger:** `handle_new_user()` + `on_auth_user_created` — auto-creates
  a `public.users` row on signup (without it the first `/allocate` FK-fails).
- **Seeds:** one `case_study` row ("The First Job") and one `game_control` row
  (id=1, month 1, status `waiting`).

**Expected result:** "Success. No rows returned." **Table Editor** lists all the
tables above.

**Verification SQL** (run in a new query; results should match the notes):
```sql
-- 14 tables in public (incl. legacy relative_events)
select tablename from pg_tables where schemaname = 'public' order by 1;

-- Both RPCs + the trigger function exist (expect 3 rows)
select proname from pg_proc
where proname in ('process_month_atomically','sell_asset_atomic','handle_new_user');

-- Signup trigger exists (expect 1 row: on_auth_user_created)
select tgname from pg_trigger where tgname = 'on_auth_user_created';

-- RPC execute is locked to service_role only (anon/authenticated must NOT appear)
select routine_name, grantee, privilege_type
from information_schema.routine_privileges
where routine_name in ('process_month_atomically','sell_asset_atomic')
order by 1, 2;

-- Every player_* table is SELECT-only for clients; admins/player_month_actions have NO policy
select tablename, policyname, cmd from pg_policies
where schemaname = 'public' order by tablename, cmd;

-- Seeds present (expect case_study = 1 row; game_control = 1 row at month 1 / waiting)
select count(*) as case_study_rows from public.case_study;
select id, current_month, game_status from public.game_control;
```

**Rollback (step 2):** the script is additive/idempotent — re-running it is safe and
is itself the fix for a partial run. To fully undo on a throwaway project, drop and
recreate the `public` schema, or delete the project. Never drop tables on a project
that holds a real game's data.

---

## 3. Auth settings (recommended for an event)

Authentication → **Providers → Email** → turn **OFF** "Confirm email" → Save.
While here, enable **leaked-password protection** (Password policy) — one-toggle hardening.

**Why:** the frontend is **login-only** — public self-signup is disabled, so you
(the admin) pre-create each account (§4a). Confirm-email ON would force every
pre-created user to click an inbox link before their first login.

**Expected result:** the Email provider shows "Confirm email" **off**; leaked-password
protection **on**.

---

## 4. Wire the keys

Supabase → **Project Settings → API**. Three values:

| Value | Goes in | Secret? |
|-------|---------|---------|
| Project URL | `frontend/js/config.js` **and** `backend/.env` | no |
| `anon` public key | `frontend/js/config.js` | no (browser-safe; RLS protects data) |
| `service_role` key | `backend/.env` **only** | **YES — never in frontend, never in git** |

**Frontend** — edit `frontend/js/config.js`, replace the two placeholders:
```js
const SUPABASE_URL = "https://YOUR-NEW-PROJECT-REF.supabase.co";
const SUPABASE_ANON_KEY = "PASTE-YOUR-NEW-ANON-PUBLIC-KEY-HERE";
```

**Backend** — copy `backend/.env.example` to `backend/.env` and fill exactly these two:
```
SUPABASE_URL=https://YOUR-NEW-PROJECT-REF.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```
These are the **only** variables the backend reads (`backend/supabase_client.py`).
There is **no `ADMIN_TOKEN`**. The backend refuses to start if either is missing.

**Expected result:** `config.js` has your real URL + anon key; `backend/.env` exists
with the URL + service_role key and is not tracked by git.

---

## 4a. Create accounts (students + admin)

Public self-signup is disabled, so you create accounts in Supabase.

- **Students:** Authentication → **Users → Add user** (email + password, tick
  **Auto Confirm User**). The `on_auth_user_created` trigger auto-creates the matching
  `public.users` row. Students log in at the site root `/` (`index.html`).
- **Admin:** create the login the same way, then grant admin rights:
  ```sql
  insert into public.admins (user_id)
  select id from auth.users where email = 'your-admin@email.com'
  on conflict (user_id) do nothing;
  ```
  The admin logs in at **`/admin-login.html`**. Non-admins are rejected and signed out.

**Expected result / verification SQL:**
```sql
-- The student's profile row exists (trigger worked)
select id, email from public.users where email = 'your-student@email.com';
-- The admin is registered (expect 1 row)
select u.email from public.admins a join auth.users u on u.id = a.user_id;
```

---

## 5. Run it locally

Two terminals (or double-click the `.bat` files on Windows):
```
run_backend.bat     # creates backend/.venv, installs, runs Flask on http://localhost:5000
run_frontend.bat    # serves frontend on http://localhost:5500 (python -m http.server)
```

Open **http://localhost:5500**. `config.js` auto-detects localhost and points the
frontend at the local backend on `:5000` — no editing needed for local play.

**Expected result:** the backend window shows "Backend running at http://localhost:5000";
visiting `http://localhost:5000/health` returns `{"status":"ok", ...}`; the frontend
login page loads at `http://localhost:5500`.

---

## 6. Smoke test the core loop

1. **Log in as a test student** (created in §4a) at http://localhost:5500.
   → Table Editor → `users` shows that person (trigger works).
2. **Admin: start the game** — log in at http://localhost:5500/admin-login.html, open
   the panel, **Start Game**. → `game_control.game_status` = `active`, `current_month` = 1.
3. **Student: case study → allocation** (must total exactly ₹1,00,000) → **dashboard**.
   → a `player_state` row exists for the student; a `player_month_log` row for month 1.
4. **Admin: Next Month.** The engine processes market/events/loans and commits via
   `process_month_atomically`. → `game_control.current_month` = 2; new `player_month_log` rows.
5. **Leaderboard** renders, ranked by Financial Health Score.

If all five pass, the fresh deployment is good. For a full feature pass, use the
**Final deployment verification checklist** below.

---

## 7. Deploy for real (optional)

- **Backend → Render:** already set up (`requirements.txt`, `runtime.txt`, gunicorn).
  Set the two env vars (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) in the Render dashboard.
  Build: `pip install -r requirements.txt`. Start: `gunicorn app:app` (from `backend/`).
  **Expected:** Render build succeeds; `https://<your-service>.onrender.com/health` returns ok.
- **Frontend → Netlify:** publish the `frontend/` folder (drag-drop or repo connect,
  publish directory `frontend`).
  - **Before publishing, delete the stray `frontend/backend/` folder** (`git rm -r "frontend/backend"`) — nothing under `frontend/` should contain a backend `.env`.
  - In `frontend/js/config.js`, the non-local `API_BASE_URL` is currently hardcoded to
    `https://finance-event.onrender.com`. **Change it to your own Render URL.**
  - **Expected:** the deployed site loads; login works; the dashboard fetches data from your Render backend (check the browser Network tab hits your Render URL, not localhost).

---

## Final deployment verification checklist

Run through every feature once against the deployed (or local) stack. Each maps to a
verified endpoint/page.

- [ ] **Student login** — `index.html` → Supabase Auth sign-in succeeds; redirects to case study.
- [ ] **Admin login** — `admin-login.html` → admin (in `public.admins`) reaches the panel; a non-admin is rejected.
- [ ] **Allocation** — `allocation.html` → `POST /allocate`; rejects totals ≠ ₹1,00,000 and negatives; writes one `player_state` + one month-1 `player_month_log`.
- [ ] **Dashboard** — `dashboard.html` → `GET /dashboard` returns state + choices + trust + logs.
- [ ] **Leaderboard** — `leaderboard.html` → `GET /leaderboard` ranks by `financial_health_score` (net-worth tiebreak).
- [ ] **Month processing** — admin **Next Month** → `POST /next-month` → `process_month_atomically`; advancing an already-processed month is refused (idempotent).
- [ ] **Optional choices** — dashboard → `POST /buy-choice`; buying the same choice twice in a month is blocked; cash deducts once.
- [ ] **Relative help** — dashboard → `POST /handle-relative`; helping the same relative twice in a month is blocked; trust increases.
- [ ] **Asset selling** — dashboard → `POST /sell` → `sell_asset_atomic`; 10% penalty; credit appears next month; double-submit does not double-credit.
- [ ] **Admin panel** — `admin.html` → `GET /admin/players`; `POST /admin/update-player` recomputes net worth + health score and audit-logs; `POST /admin/reset-player` clears one player.
- [ ] **End game** — admin **End Game** → `POST /end-game`; `game_control.game_status` = `ended`; leaderboard shows final standings.

---

## Rollback instructions (per critical step)

| Step | If it goes wrong | Rollback |
|---|---|---|
| 2 — DB install | Partial/failed run | Re-run `supabase.sql` (idempotent). On a throwaway project only, recreate the `public` schema. **Never** drop tables on a project holding real game data. |
| 4 — keys | Wrong/leaked `service_role` key | In Supabase → Project Settings → API, **rotate** the `service_role` key; update `backend/.env` / Render env; redeploy backend. |
| 4a — admin grant | Wrong user granted admin | `delete from public.admins where user_id = (select id from auth.users where email = 'wrong@email.com');` |
| 7 — backend deploy | Bad Render build | Render → **Rollback** to the previous deploy (keep the prior commit pinned). |
| 7 — frontend deploy | Bad Netlify publish | Netlify → **Deploys** → publish the previous deploy. |
| Any live-game issue | — | Do **not** roll back mid-game. Finish or abort the game first (ADR-012). See `RUNBOOK.md`. |

---

## Recovery from a partial failure

- **`supabase.sql` stopped halfway** (e.g. editor timeout): just **re-run the whole
  file**. Every statement is `CREATE ... IF NOT EXISTS` / `CREATE OR REPLACE` /
  idempotent `REVOKE`/`GRANT`, so a second run completes what the first missed and
  changes nothing already correct. Then re-run the §2 verification SQL.
- **Some objects missing after install** (verification SQL shows a gap): re-run
  `supabase.sql`. If a *single* object is missing on an older project you don't want
  to fully re-run, the matching retrofit file (see the classification table) recreates
  just that object.
- **Backend boots but every call 500s:** almost always a bad/missing
  `SUPABASE_SERVICE_KEY` or wrong `SUPABASE_URL`. Fix `.env` / Render env and restart.
- **Students exist in Auth but not in `public.users`:** the trigger wasn't installed
  when they signed up. Re-run `supabase.sql` (it includes a backfill `INSERT ... SELECT
  FROM auth.users ON CONFLICT DO NOTHING`), then re-check.

---

## Troubleshooting (matched to the actual code)

- **First allocation errors with a foreign-key / "users" message** → the signup
  trigger didn't run. Re-run `supabase.sql` (idempotent) — it recreates the trigger
  and backfills missing `public.users` rows.
- **Buy-choice or relative-help says "you already did this" for a first attempt** →
  `player_month_actions` is missing (older project) or the DB is erroring. On a fresh
  install this can't happen (the table is in `supabase.sql`). Re-run `supabase.sql`
  and check the backend logs — non-duplicate DB errors now surface loudly (they are no
  longer silently swallowed).
- **Admin login says "Admin authorization required." (401)** → the signed-in user is
  not in `public.admins`. Run the §4a grant for that email.
- **Admin page bounces to `/admin-login` or 401s** → the backend is unreachable, is on
  a different project, or `.env` is wrong. Confirm `/health` responds and `SUPABASE_URL`
  matches the project the admin was granted on.
- **Browser console: "Supabase not initialised"** → `config.js` still has the
  placeholder URL/key.
- **CORS / network errors locally** → the backend isn't running on `:5000`, or the
  frontend isn't on `localhost`/`127.0.0.1` (config only auto-selects the local API for
  those hostnames).
- **Deployed frontend calls `localhost`** → you're serving from `localhost`; on a real
  domain `config.js` uses `API_BASE_URL`, which you must set to your Render URL.
- **Leaderboard/dashboard shows another player's data or is empty** → never expected:
  clients are SELECT-own-row; the leaderboard comes from the backend (`service_role`).
  If wrong, verify RLS with the §2 policy query — a public `USING (true)` write/read
  policy on `player_state` means a deprecated file was run (see "Never Do These").

---

## Never do these

- **Never expose the `service_role` key.** It bypasses RLS entirely. It belongs only
  in `backend/.env` / the Render env — never in `frontend/`, `config.js`, git, or any
  file under the Netlify publish directory.
- **Never deploy code or run a migration during a live game.** Level 3+ changes and all
  migrations happen only between games (ADR-012 / SRS Invariant 6). Finish or abort first.
- **Never run deprecated SQL.** `supabase_migration.sql` is deprecated (it re-opens a
  public read policy and reverts scoring). For a fresh install run **only** `supabase.sql`.
- **Never modify financial tables by hand** in the Supabase Table Editor
  (`player_state`, `player_loans`, `player_sales`, `player_month_log`, ...). Use the
  admin panel's player edit, which recomputes net worth + health score and audit-logs
  the change. Hand-edits desync the score and break the append-only history invariant.
- **Never bypass backend validation.** All financial writes must go through the Flask
  backend (`service_role`). Do not add client-side write policies or call the RPCs from
  the browser — the RLS lockdown and RPC `REVOKE`s exist to prevent exactly that.
- **Never commit `backend/.env`.** It is git-ignored; keep it that way.

---

## Appendix — full verification SQL

Paste into the SQL Editor after §2 for a complete health check:
```sql
-- Tables (expect 14, incl. legacy relative_events)
select count(*) as public_tables from pg_tables where schemaname = 'public';

-- RLS enabled on every player/admin table (relrowsecurity must be true)
select relname, relrowsecurity
from pg_class
where relname in ('player_state','player_loans','player_sales','player_relative_score',
                  'player_relative_actions','player_month_log','admins','player_month_actions')
order by 1;

-- No write policy on player_state (expect only a single SELECT policy)
select policyname, cmd from pg_policies
where schemaname = 'public' and tablename = 'player_state';

-- RPC grants restricted to service_role (anon/authenticated must be absent)
select routine_name, grantee, privilege_type
from information_schema.routine_privileges
where routine_name in ('process_month_atomically','sell_asset_atomic')
order by 1, 2;

-- Trigger present
select tgname, tgenabled from pg_trigger where tgname = 'on_auth_user_created';

-- Game control singleton at a sane starting state
select id, current_month, game_status from public.game_control;
```
