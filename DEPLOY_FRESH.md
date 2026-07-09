# Money Master — Fresh Supabase Deployment Guide

Everything needed to bring the existing app up on a **brand-new Supabase project**
with **email + password** login. Follow top to bottom. ~15 minutes.

Stack (unchanged): vanilla HTML/JS frontend · Flask backend · Supabase (Postgres +
Auth). The backend writes all financial state with the service-role key; the browser
only ever reads its own rows (RLS). Admin actions are gated by a shared secret token.

---

## 1. Create the Supabase project

1. supabase.com → **New project**. Pick a region near your campus. Save the
   database password somewhere safe.
2. Wait for it to finish provisioning.

## 2. Deploy the database (SQL Editor → New query → paste → Run)

Run these **two files in order**:

1. `supabase.sql` — all tables, RLS policies, seed rows, and the atomic
   month-processing function.
2. `supabase_signup_trigger.sql` — **required.** Creates a `public.users` row
   automatically whenever someone signs up. Without it the first `/allocate`
   call fails with a foreign-key error (this trigger existed on the old project
   but was never in the SQL files — it's the one thing a fresh deploy was missing).

After both run, **Table Editor** should list `users`, `player_state`, `events`,
`game_control`, etc.

## 3. Turn off email confirmation (recommended for an event)

Authentication → **Providers → Email** → turn **OFF** "Confirm email" → Save.

Why: with it ON, every student must click a link in their inbox before they can
log in — painful during a live event. With it OFF, signup logs them straight in.
(The login page still handles the confirm-ON case gracefully if you leave it on.)

## 4. Wire the keys

Supabase → **Project Settings → API**. You need three values:

| Value | Goes in | Secret? |
|-------|---------|---------|
| Project URL | `frontend/js/config.js` **and** `backend/.env` | no |
| `anon` public key | `frontend/js/config.js` | no (browser-safe) |
| `service_role` key | `backend/.env` only | **YES — never in frontend** |

**Frontend** — edit `frontend/js/config.js`, replace the two placeholders:
```js
const SUPABASE_URL = "https://YOUR-NEW-PROJECT-REF.supabase.co";
const SUPABASE_ANON_KEY = "PASTE-YOUR-NEW-ANON-PUBLIC-KEY-HERE";
```

**Backend** — copy `backend/.env.example` to `backend/.env` and fill:
```
SUPABASE_URL=https://YOUR-NEW-PROJECT-REF.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
ADMIN_TOKEN=choose-a-long-random-string
```
`ADMIN_TOKEN` is your admin password — anyone with it can control the game. Make
it long and random, and share it only with organizers.

## 5. Run it (local)

Two terminals (or just double-click the .bat files on Windows):

```
run_backend.bat     # http://localhost:5000  (creates venv, installs, runs Flask)
run_frontend.bat    # http://localhost:5500  (static server)
```

Open **http://localhost:5500** in a browser. `config.js` auto-detects localhost and
points the frontend at the local backend on :5000 — no editing needed for local play.

## 6. Smoke test the whole loop

1. **Sign up** a test student at http://localhost:5500 → "Create an account".
   → In Supabase, Table Editor → `users` should now show that person (trigger works).
2. **Admin: start the game.** Open http://localhost:5500/admin.html. It prompts for
   the admin token — paste your `ADMIN_TOKEN`. Start the game.
3. As the student, go through **case study → allocation** (must total exactly
   ₹1,00,000) → **dashboard**.
4. **Admin: advance the month.** The Python engine processes market/events/loans and
   commits atomically via `process_month_atomically`.
5. Check the **leaderboard**.

If all five work, the fresh deployment is good.

---

## Deploying for real (optional, later)

- **Frontend** → Netlify: drag the `frontend/` folder in, or connect the repo with
  publish directory `frontend`. Then in `config.js` update the non-local
  `API_BASE_URL` to your deployed backend URL.
- **Backend** → Render: it's already set up (`requirements.txt`, `runtime.txt`,
  gunicorn). Set the same three env vars in the Render dashboard. Start command:
  `gunicorn app:app` (from the `backend/` directory).

## What changed in this session

- `supabase_signup_trigger.sql` — **new**, fixes the fresh-deploy FK break.
- `frontend/index.html` + `frontend/js/auth.js` — **rewritten** for email/password
  (Google OAuth removed).
- `frontend/js/config.js` — now points at your new project (placeholders to fill).
- `backend/.env.example` — **new** template for the backend secrets.
- Backend Python (routes/engine/services) — **untouched**; its auth already accepts
  any Supabase JWT, so the login switch needed no backend edits.

## Troubleshooting

- **First allocation errors with a foreign-key / "users" message** → you skipped
  step 2's second file. Run `supabase_signup_trigger.sql`.
- **Login says "Account created, check your email"** → email confirmation is ON
  (step 3). Either confirm via the email link, or turn it off.
- **Admin routes return 401** → the token you typed doesn't match `ADMIN_TOKEN` in
  `backend/.env`, or the backend was started before you set it. Restart the backend.
- **Browser console: "Supabase not initialised"** → `config.js` still has the
  placeholder URL/key.
- **CORS / network errors** → make sure the backend terminal is running on :5000.
