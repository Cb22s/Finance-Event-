# Stage 1 Pre-Implementation — `MARRIAGE_MONTH` 6→4 Dependency Audit

**Status:** AUDIT ONLY. No file/DB/UI/AI/engine change. Verified against current code + live DB.
**Goal:** find every place marriage timing bites before flipping `MARRIAGE_MONTH` 6→4.
**Classification:** **A** = must change · **B** = verify only (already parameterized / behaves correctly) · **C** = must NOT change · **D** = doc/UI text only.

---

## Dependency Table

| File | Function / Line | Current month logic | Impact of Month 4 | Class |
|---|---|---|---|---|
| `backend/models/constants.py` | `:168 MARRIAGE_MONTH = 6` | the single source constant | change to `4`; propagates everywhere that reads it | **A** |
| `backend/routes/player_routes.py` | `courtship_reveal :1081` `player['month'] != 6` | reveal only allowed at month 6 | must become `!= MARRIAGE_MONTH` or reveals break at M4 | **A** |
| `backend/routes/player_routes.py` | `courtship_marry :1159` `player['month'] != 6` | marry only allowed at month 6 | must become `!= MARRIAGE_MONTH` | **A** |
| `backend/routes/player_routes.py` | `lock_turn :863` `player.get('month') == 6` | "must choose spouse before locking Month 6" guard | must become `== MARRIAGE_MONTH` | **A** |
| `backend/routes/player_routes.py` | `courtship_marry :1234` `calculate_financial_health_score(... month=6 ...)` | scores the marriage at literal month 6 | must become `month=MARRIAGE_MONTH` (wrong month = wrong transient score) | **A** |
| `backend/routes/player_routes.py` | `courtship_marry :1191` month-log `"month": 6` (single path) | logs the marriage under month 6 | must become `MARRIAGE_MONTH` | **A** |
| `backend/routes/player_routes.py` | `courtship_marry :1281` month-log `"month": 6` (archetype path) | logs the marriage under month 6 | must become `MARRIAGE_MONTH` | **A** |
| `frontend/js/dashboard.js` | `:246 if (p.month === 6 && marriage_round_active && !spouse_archetype)` | **gates the courtship UI visibility** | hardcoded — courtship panel will NOT render at M4. Recommend compare to `courtship.marriage_month` (backend already sends it) so it self-syncs | **A** |
| `frontend/js/mascot.js` | `:189 if (m === 6 && ... marriage_round_active && !spouse_archetype)` | mascot hint fires at month 6 | hardcoded; hint won't fire at M4 | **A** |
| `backend/tools/marriage_ev_sim.py` | `:71 month == MARRIAGE_MONTH` (inject), `:78 month >= MARRIAGE_MONTH` (income) | fairness sim keyed off the constant | **NO code edit**, but the EV RESULT changes — the spouse now contributes ~2 extra months of income/assets. **Must re-run; archetypes may need re-tuning.** This is the one non-mechanical dependency. | **A (gate)** |
| `backend/engine/scoring.py` | `:61-62 month >= MARRIAGE_MONTH; spouse_income*(month−MARRIAGE_MONTH+1)` | denominator already parameterized | invariant still holds (marry-month one-off + processor months 5..12 = `month−MARRIAGE_MONTH+1`); **verify** it matches | **B** |
| `backend/engine/monthly_processor.py` | `:102-150 spouse income/expense/drift` | keyed off `spouse_archetype` presence, **not** a month literal | month-agnostic → no change; **verify** | **B** |
| `backend/routes/player_routes.py` | `get_dashboard :211 "marriage_month": MARRIAGE_MONTH` | already parameterized | verify dashboard shows M4 | **B** |
| `backend/routes/player_routes.py` | `courtship_marry :1181/1253 action_key='marry', MARRIAGE_MONTH`; `:1226 inflation month=MARRIAGE_MONTH` | already parameterized | verify idempotency key + expense base track M4 | **B** |
| `backend/routes/player_routes.py` | `_negotiation_context :616` uses `player['month']`; negotiation gated by `negotiation_enabled` only, no month literal | negotiation available every married month | after re-timing it becomes available from **M5** (not M7). Expected; **Stage 2** will pin it to the festival month. **Verify**, don't change now | **B** |
| `backend/tests/test_marriage.py` | `:34 month−MARRIAGE_MONTH+1` (parameterized); `net_worth`/`processor` tests use explicit months 6/7 as scenario inputs | scenario months, not marriage-timing assertions | **verify** the suite still passes; update only if a test asserts month-6-specific marriage behaviour | **B** |
| Live DB — `spouse_proposals` / `spouse_dialogue` | month-scoped content | **0 rows; 0 month-scoped** (queried this audit) | nothing to migrate; no month constraint ties content to 6 | **B** |
| Live DB — `game_control.marriage_round_active` | admin bool flag, admin-toggled | no month constraint | timing-independent; admin opens the round manually | **B** |
| `backend/engine/event_engine.py` | `:249 month >= 6` (Social Isolation trust penalty) | **unrelated** to marriage | must NOT change — coincidental literal 6 | **C** |
| `backend/engine/event_engine.py` | `:225 month >= 9` (windfall trust bonus) | unrelated to marriage | must NOT change | **C** |
| `backend/services/negotiation_service.py` | entire deterministic engine | evaluation/floor/rounds | must NOT change (preserve engine) | **C** |
| `backend/models/constants.py` | `ARCHETYPES`, `WEDDING_COST=25000`, `SPOUSE_BASE_EXPENSE=9000`, floor ratios | economic layer (timing-independent values) | must NOT delete/replace; values may be *re-tuned* only if the EV sim demands it (see A-gate) | **C** |
| `frontend/dashboard.html` | `:210 "You are in Month 6…"`, `:204 comment "(Month 6 Special Event)"` | display text | copy → "Month 4" | **D** |
| `frontend/admin.html` | `:286 "players in Month 6 can choose to marry"` | admin help text | copy → "Month 4" | **D** |
| `backend/engine/scoring.py` | `:60 comment "apply from MARRIAGE_MONTH onward"` | comment | fine as-is | **D** |

---

## Cross-cutting invariant (why scoring stays correct)

Spouse-income months must equal the scoring denominator's `(month − MARRIAGE_MONTH + 1)`.
- Marriage completes **at** `MARRIAGE_MONTH` → `courtship_marry` applies **one** month of spouse flow for that month.
- `monthly_processor` then adds spouse income for **every subsequent** month (keyed off `spouse_archetype`, not a literal).
- At month 12 with marriage at 4: `1 (marry) + 8 (processor, m5–12) = 9` and `12 − 4 + 1 = 9`. ✅ Matches — same pattern as today, just shifted. This is a **B (verify)**, not a change.

---

## FINAL ANSWER

**Can `MARRIAGE_MONTH` safely become 4 with a small mechanical change?**

**Yes for the code — no hidden *code* dependency blocks it. But there is ONE non-mechanical dependency that is not optional: it moves the economy, so fairness must be re-proven.**

- **Mechanical (small, ~9 edits):** one constant, six literal-`6`s in `player_routes.py` (all in courtship/lock functions), and two frontend `=== 6` gates. Everything else that matters (`scoring`, `monthly_processor`, dashboard `marriage_month`, idempotency key, inflation base) already reads `MARRIAGE_MONTH` and needs only verification. No DB migration (no month-scoped spouse content; `marriage_round_active` is an admin flag).
- **The real dependency (design/fairness gate):** marrying at Month 4 instead of 6 gives the spouse **~2 extra months** of income and earlier asset compounding. The four archetypes were EV-certified **for marriage at Month 6**. `marriage_ev_sim.py` will produce **different** spread/single-viability numbers at Month 4. So Stage 1 is not "flip and ship" — it is **flip → re-run the EV sim → confirm the three fairness gates still pass → re-tune archetype stat blocks only if they don't.** If the gates fail, that's a balancing task, not a bug.
- **One expected behaviour shift to note (not fix in Stage 1):** negotiation becomes available from Month 5 (married earlier). Stage 2 pins it to the single festival month (`MARRIAGE_MONTH + 2 = 6`); until then, leave `negotiation_enabled` off outside the intended window.

### Exact minimal Stage-1 change set (for approval — not yet applied)

**Backend (`A`):**
1. `constants.py:168` → `MARRIAGE_MONTH = 4`
2. `player_routes.py` → replace literal `6` with `MARRIAGE_MONTH` at lines **863, 1081, 1159, 1191, 1234, 1281**

**Frontend (`A`, minimal — recommend self-syncing rather than hardcoding 4):**
3. `dashboard.js:246` → compare `p.month === (courtship.marriage_month)` instead of `=== 6` (backend already sends `courtship.marriage_month`)
4. `mascot.js:189` → same self-sync (or read from `data.game`/config)

**Text (`D`):**
5. `dashboard.html:210` + `:204`, `admin.html:286` → "Month 6" → "Month 4"

**Verification gate (`A`), no source change:**
6. Run full suite (`unittest discover`) + `marriage_ev_sim.py`. **Only proceed if the three EV gates pass.** If they don't, stop and treat archetype re-tuning as a separate, explicit step (never silent).

**Do NOT touch:** `negotiation_service.py`, the archetype economics (unless the EV gate forces a tune, and only then with your sign-off), `event_engine` month≥6/≥9, DB schema.

---

*STOP. No edits made. Awaiting approval before Stage 1. Note the EV-sim gate is mandatory, not optional — that is the only part of Stage 1 that could surface a real design decision.*
