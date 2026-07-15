# Money Master — Admin Recovery Runbook

**Audience:** the event organizer/admin running a live game. **Purpose:** exact steps for the failure modes that can happen mid-event. Closes QA-013 / Plan B7·T4.1.
**Golden rule (ADR-012 / SRS Invariant 6):** **never deploy code or run a migration mid-game.** If something is broken at the code/schema level, finish or formally abort the current game first. Everything in this runbook is an *operational* recovery — no code, no migrations.

Keep these open on event day: the Supabase dashboard (SQL Editor + Table Editor), the Render dashboard (backend logs), and the admin panel (`/admin-login.html`).

---

## 0. Pre-flight (do this before players arrive)

- [ ] Backend up: `GET /health` returns `{"status":"ok"}`.
- [ ] Admin login works at `/admin-login.html`; your account is in `public.admins`.
- [ ] `game_control` is at **month 1 / `waiting`** (Table Editor) — not left `ended` from a test.
- [ ] Content present: `events` and `optional_choices` have rows for months 2–12.
- [ ] **Fresh Supabase backup taken** (Database → Backups). This is your rollback point.
- [ ] Email confirmation OFF; all student accounts pre-created and can log in.

---

## 1. Backend is down / unreachable (admin panel bounces to login or 401s)

**Symptom:** admin actions fail; `/health` doesn't respond; students can log in (Supabase) but the dashboard won't load data.

1. Check Render → your service → **Logs**. Confirm the process is running and not crash-looping.
2. Confirm env vars are set: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. A missing service key makes every backend call fail (the app raises on boot).
3. Confirm the backend points at the **correct** Supabase project (`SUPABASE_URL` matches the project the students/data are on).
4. If crashed, **Restart** the Render service (Manual Deploy → Restart, *not* a new build/deploy — no code changes mid-game).
5. While down, **do not advance the month.** Player financial state is safe in Postgres; nothing is lost. Resume once `/health` is green.

**Do not** redeploy new code to "fix" it mid-game. Restart only.

---

## 2. Wrong event published for a month

**Symptom:** you added an admin event to the wrong month, or with wrong values, and players haven't been processed for that month yet.

Admin events live in the `events` table and are only applied when you run **Next Month**. As long as you have **not** advanced into that month:

1. Admin panel → delete the event (`DELETE /event/<id>`), or Table Editor → `events` → delete the row.
2. Re-add it correctly for the intended month.
3. Then advance.

**If the month was already processed** (players already took the hit): do **not** edit history. A released/processed event is immutable (ADR-011). Compensate by adding a *new* corrective event for the **next** month, or use a per-player admin correction (§4). Never rewrite the processed `player_month_log` rows.

---

## 3. Advanced the month too early / by mistake

**Symptom:** you clicked **Next Month** before players were ready.

Month processing is **atomic and idempotent** — the RPC refuses to reprocess a month that already has `player_month_log` rows, and it validates the transition (`next = current + 1`). So you cannot "double-advance" or corrupt a month by clicking twice.

- **You cannot un-advance via the app.** There is no "previous month" button by design (history is append-only).
- If the early advance is harmless (players were mostly ready), **continue** — explain to the room and proceed.
- If it genuinely must be undone, that is a **rollback** (§6): restore the pre-event/last-good backup and replay from there. Weigh this heavily — it discards all progress since the backup.
- Prevention: the panel sends `expected_month`; if it ever mismatches you'll get a "Race condition blocked" 409 rather than a wrong advance. Read the number in the error before retrying.

---

## 4. Fix one player's data (typo, missed action, dispute)

**Symptom:** a single player's cash/stocks/gold/emergency_fund/loans is wrong.

1. Admin panel → **Players** → edit the player. Only whitelisted fields are editable.
2. On save, the backend **recomputes** `net_worth`, `risk_level`, and `financial_health_score` from the corrected components (you cannot type a fake net worth), and writes an audit row to `player_month_log` ("🛠️ Admin manual adjustment").
3. The leaderboard reflects the corrected rank immediately (no need to advance a month).

Do this for individual corrections. Do **not** use it to rewrite an entire month for everyone — that's what processing is for.

**Reset one player** (let them re-allocate from scratch): Players → **Reset**. This wipes only that player's rows (state, loans, sales, relatives, logs, month-actions). Irreversible for that player.

---

## 5. "Start Game" was clicked by accident (data wipe)

**Symptom:** `POST /start-game` ran — it **wipes all player data** and resets to month 1. This is intentional and destructive (SRS §3).

- There is **no in-app undo.** All `player_*` data is gone.
- Recovery = **restore the most recent backup** (§6). This is exactly why the pre-event backup (Pre-flight) is mandatory.
- Prevention: only the admin should have panel access; brief anyone near the machine that "Start Game" = full reset.

---

## 6. Full rollback (last resort)

Use only when a single-player or event-level fix can't recover the situation (accidental Start Game, corruption, an early advance that must be undone).

1. **Announce a pause.** Rollback discards all progress since the backup.
2. Supabase → Database → **Backups** → restore the pre-event (or last known-good) snapshot.
3. Do **not** redeploy backend code as part of this — the running backend is unchanged; only data is restored.
4. Verify after restore: `game_control` month/status is what you expect; `player_state` row count matches; leaderboard renders.
5. Resume the game from the restored month.

**Never roll back mid-game without first pausing the whole room** — players acting against soon-to-be-reverted state will lose those actions.

---

## 7. Quick reference

| Situation | Action | Reversible? |
|---|---|---|
| Backend down | Render → Restart (no redeploy) | n/a — data safe |
| Wrong event, not yet processed | Delete + re-add event, then advance | Yes |
| Wrong event, already processed | Add corrective event next month / §4 | History immutable |
| Advanced too early | Continue if harmless, else §6 rollback | Only via backup |
| One player wrong | Panel → edit (auto-recomputes score) | Audit-logged |
| One player restart | Panel → Reset | No (that player) |
| Start Game misclick | §6 restore backup | Only via backup |
| Anything code/schema-level | **Finish/abort game first**, then fix between games | — |

**Escalation:** if a fix would require a code change or migration, stop — do not change code mid-game. Abort or complete the current game, apply the fix between games per `DEPLOY_FRESH.md` / Plan §7, and re-run the smoke test before restarting.
