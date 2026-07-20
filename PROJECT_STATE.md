# Money Master — Project State (handoff)

**Written:** 2026-07-20. Read this first. It replaces guessing across the 20+ RC/QA docs.

---

## 1. Where things actually stand

| Layer | State |
|---|---|
| Code (local folder) | V1 + this session's changes. Compiles, tests **30/30 PASS**. |
| Supabase (live) | Schema live. `game_control.auto_events` / `auto_market` migration **APPLIED**. |
| Render (backend) | **RUNNING OLD CODE.** None of this session's backend changes are deployed. |
| Netlify (frontend) | **RUNNING OLD CODE.** Toggle UI not visible yet. |
| Git | This session's work is **UNCOMMITTED**. Index has a stuck lock + duplicate entries. |

**The single most important fact:** the live game still behaves the old way because the
backend was never redeployed. Editing files does nothing until Render rebuilds.

---

## 2. Changes made this session (all uncommitted)

1. **Create Player** — `POST /admin/create-player` + admin form. Admin provisions logins
   (username + password) via the Supabase service_role admin API. Supabase Auth and all
   RLS left intact — auth was NOT replaced.
2. **Username login** — players log in with a plain username; internally mapped to
   `<username>@event.local`. `index.html` + `auth.js`.
3. **Player Roster** — `GET /admin/roster` + admin card. Shows every provisioned login as
   "Playing" (has a `player_state` row) or "Waiting" (created, not yet allocated).
4. **Manual control toggles** — `game_control.auto_events` and `auto_market`, both
   default **false**. Gated in `event_engine` / `market_engine` / `monthly_processor`;
   `POST /admin/settings` + Game Controls card. Function defaults stay `True` so the
   existing test suite is unaffected.
   - Verified: both off + no authored events => 0 events fire, stocks do not move.
     Admin "Stock Crash -30%" => only that fires (50,000 -> 35,000).
5. **Marriage EV-balance simulator** — `backend/tools/marriage_ev_sim.py`. Balance tool
   only; touches no production code.

---

## 3. Recovery note (environment)

The Cowork mount corrupted files 3x this session (truncation + null bytes):
`monthly_processor.py`, `utils.py`, `admin_routes.py`. All were restored from git HEAD.
Deletes were blocked ("Operation not permitted"), which is why `.git/index.lock` is stuck.
**This problem does not exist in a local IDE.** In a real terminal, run:

```
del .git\index.lock        (Windows)
git reset                  # clears the duplicate D/?? index entries
git add -A
git commit -m "create-player, roster, manual control toggles, marriage EV simulator"
```

---

## 4. Blockers before the event (unchanged since RC1)

1. **Months 2-12 content pack unwritten.** Now load-bearing: with auto_events and
   auto_market OFF, an unauthored month = salary minus expenses and nothing else,
   and investing does nothing because prices never move.
2. **Deploy this session's code** to Render + Netlify, then hard-refresh.
3. **Full 12-month dry run** — never performed. Do it from a fresh clone.
4. **Headcount** — gates QA-012 (perf safe to ~50-100 players).

---

## 5. Marriage (ADR-002) — status

**Decision (2026-07-20):** build the *real* system, marriage offered mid-game.
Architecture re-ratified: **direct spouse on `player_state`**, NOT the ADR-001 household
refactor. Rationale: one NPC spouse, with divorce/children/in-laws deferred, does not
justify refactoring 7 financial tables + re-deriving ADR-008 scoring. Migrate to
households later if children/divorce arrive.

**Fairness gate: CLEARED (provisionally).** `marriage_ev_sim.py` proves the 4 archetypes
and "stay single" sit in one tolerance band under both market regimes:

- Market ON : spread 2.0%, single +0.9% vs archetype mean, no dominance — PASS
- Market OFF: spread 2.2%, single +1.7% vs archetype mean, no dominance — PASS

Ranking *flips* between regimes (Investor best when markets grow, Anchor when flat), so
spouse choice is a genuine read on the economy the admin authors.

Balanced stat blocks (marriage month 6, wedding cost Rs88,000, spouse +Rs9,000/mo):

| Archetype | income | expense_mod | stocks | gold | ef |
|---|---|---|---|---|---|
| The Saver | 10,000 | -9,000 | 0 | 8,000 | 22,000 |
| The Earner | 36,000 | +12,000 | 0 | 0 | 0 |
| The Investor | 9,000 | -1,000 | 44,000 | 20,000 | 24,000 |
| The Anchor | 14,000 | -2,000 | 8,000 | 0 | 45,000 |

**Caveats:** first-order model (no random events, volatility, loans, trust, sell
penalties). Balance is provisional while auto_market is OFF — **re-run the simulator once
the months 2-12 content pack exists**, since archetype value depends on the market you author.

**Not yet built:** `spouse_archetypes` table, spouse fields on `player_state`,
`player_spouse_reveals` (deterministic trait reveal), spouse income/expense in
`monthly_processor`, admin "open marriage round" control, player spouse-choice UI.

---

## 6. Do these in order

1. Commit + push (section 3).
2. Redeploy Render backend, then Netlify frontend; hard-refresh.
3. Start a game; confirm Next Month fires 0 events and stocks hold => manual control live.
4. Author the months 2-12 content pack (events + market moves).
5. Re-run `python3 backend/tools/marriage_ev_sim.py` against that content.
6. Then build marriage (section 5).
7. Full 12-month dry run from a fresh clone.
