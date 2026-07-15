# Household Foundation — Database Design & Migration Plan

**ADR-001 gate artifact — prerequisite for Marriage (ADR-002)**

- **Status:** Proposed — awaiting your ratification. No code until this is approved.
- **Change level:** L4 (Architecture — touches schema + RLS). Per ADR-013, deploy **between games only**.
- **Player-visible?** No. ADR-001 P5: households are invisible in V1. Zero gameplay/UI change.
- **Why now:** Marriage adds a *member to a household*. Households don't exist in the live schema yet (`supabase.sql` keys everything to `user_id`). This plan builds the walls before marriage puts on the roof.

---

## 1. Objective & constraints

Implement ADR-001: the **household** is the primary financial entity; every player is created as a household of exactly one member. This is pure data-model groundwork.

Binding constraints carried from prior decisions:
- **ADR-000 no-overwrite:** migration never destroys financial history. Additive columns first; the old `user_id` keys are *kept*, not dropped, in V1.
- **Determinism unaffected:** no engine math changes here. `monthly_processor`, `scoring`, `market_engine` are untouched.
- **Invisibility (ADR-001 P5):** gameplay stays user-centric in V1. `household_id` is written and maintained but the game loop still reads per user. The household layer only becomes load-bearing when ADR-002 ships.
- **Minimal surgical change:** no table is rewritten; we add tables and nullable columns, backfill, then constrain.

---

## 2. Target schema

### 2.1 New tables

```
households
  id            uuid  PK  default uuid_generate_v4()
  display_name  text                      -- e.g. player's name; cosmetic
  created_at    timestamptz default now()

household_members
  id            uuid  PK  default uuid_generate_v4()
  household_id  uuid  FK -> households(id) on delete cascade
  user_id       uuid  FK -> users(id)      on delete cascade
  member_role   text  check (member_role in ('self','spouse','dependent'))
  status        text  default 'active'     -- 'active','inactive'
  joined_month  int                        -- game month the member joined (1 for self)
  created_at    timestamptz default now()
  UNIQUE (user_id)                          -- V1: one household per user
  UNIQUE (household_id) WHERE member_role='self'   -- exactly one 'self' per household
```

In V1 every `household_members` row is `member_role='self'`. ADR-002 later inserts a `'spouse'` row into an existing household — no schema change required then, which is the entire point of doing this first.

### 2.2 Financial tables — add a household key

Add a nullable `household_id uuid REFERENCES households(id)` to each financial table, backfill it, then set `NOT NULL`:

`player_state`, `player_loans`, `player_sales`, `player_relative_score`, `player_relative_actions`, `player_month_log`, `player_month_actions` (the idempotency table added this session).

`user_id` columns **stay** — they remain the *Individual* owner (see 2.3) and make rollback trivial.

### 2.3 Ownership model (ADR-001 P3) — OPEN DECISION, yours

ADR-001 requires every financial record to declare an owner type (Individual / Household / Business / Organization), but explicitly deferred the *implementation* to this DB-design step. Three options:

- **(a) `owners` supertype table** — Individual/Household/Business rows extend a common `owners(id, owner_type)` table; financial rows FK to `owners`. Cleanest long-term, real FK integrity, extensible to Organization. Highest migration cost now.
- **(b) Nullable FK columns + CHECK** — each financial row has `individual_id` and `household_id`, CHECK enforces exactly one. Simpler, but every new owner type is a schema migration.
- **(c) V1-pragmatic (recommended):** keep `user_id` as the *Individual* owner and add `household_id` as the *aggregation* key. Do **not** build the polymorphic `owners` table until Business/Organization entities actually exist. Record the seam in the ADR so option (a) can be adopted later without rework.

**My recommendation: (c).** You have no Business or Organization entities in V1, so (a) is architecture you can't use yet — it violates ADR-000's "education/realism > feature convenience" only if we pretend future needs are present needs. (c) satisfies "every record has an explicit owner" (Individual = user_id, Household roll-up = household_id) with the least risk on a live product. This is the one decision I most need from you before writing migration SQL.

---

## 3. Migration plan (ordered, each step reversible)

Run between games, on a backup. Steps are additive-first so everything before Step 6 is trivially reversible.

1. **Create** `households` and `household_members` (no data yet). Reversible: `DROP TABLE`.
2. **Backfill households:** for each existing `users` row, insert one `households` row + one `household_members` row (`member_role='self'`, `joined_month=1`). Deterministic, idempotent (guard on existing membership).
3. **Add nullable `household_id`** to all seven financial tables. Reversible: `DROP COLUMN`.
4. **Backfill `household_id`** on every financial row by joining through `household_members` on `user_id`.
5. **Verify** (see §7) — zero NULL `household_id`, one household per user, one `self` per household.
6. **Constrain:** set `household_id NOT NULL`; add RLS policies (§3.1). This is the first non-trivial-to-reverse step → take the backup here.
7. **Deploy backend** reads/writes that maintain `household_id` on insert (§4).

### 3.1 RLS

New tables get RLS **enabled with server-only writes** (mirror the existing pattern: all writes go through the Flask backend on the service-role key). Read-own policy for `household_members`/`households`:

```
USING ( EXISTS (SELECT 1 FROM household_members m
                WHERE m.household_id = households.id
                  AND m.user_id = auth.uid()) )
```

Financial tables keep their existing "read own by user_id" policies in V1 (still correct, since one member). They move to household-membership reads only when ADR-002 introduces multi-member households.

---

## 4. File impact analysis

Because V1 is invisible, the code surface is deliberately tiny.

| File | Change | Level | Risk |
|---|---|---|---|
| `supabase.sql` | Add new tables + columns + RLS (or a new `household_migration.sql`) | L4 | Low — additive |
| `backend/routes/player_routes.py` — `/allocate` | On first insert, create/lookup household + membership; write `household_id` onto `player_state` and the month-1 log | L4 | Med — the one write path that mints a household |
| `backend/routes/admin_routes.py` — `start-game`, `reset-player` | Add `households`/`household_members` to the wipe/reset lists | L3 | Low |
| `backend/services/game_service.py` | Insert paths (`new_loans`, sales, logs, actions) carry `household_id`; add a `get_household_id(user_id)` helper | L3 | Med — many insert sites |
| `backend/routes/admin_routes.py` — `next-month` RPC payload | Include `household_id` on inserted loans/logs | L3 | Med — RPC validator + SQL function signature |
| `supabase.sql` — `process_month_atomically` | Accept/insert `household_id` on new loans + logs | L3 | Med — stored function change |

Engine files (`monthly_processor`, `scoring`, `market_engine`, `event_engine`) — **no change**. Frontend — **no change**.

---

## 5. Dependency graph

```
users
  └─ households (backfilled 1:1 in V1)
       └─ household_members (self)              ← ADR-002 inserts 'spouse' here
            └─ household_id on financial tables
                 └─ RLS read-own via membership
                 └─ process_month_atomically (RPC carries household_id)

Blocks: ADR-002 Marriage  (needs household_members multi-member)
        ADR-005 Ownership rollup (needs household_id aggregation key)
        ADR-008 scoring on household aggregates (future)
```

Deploy order = table order above. Nothing reads household as load-bearing until ADR-002.

---

## 6. Rollback strategy

- **Before Step 6:** everything is additive + nullable → rollback = `DROP` the new columns/tables. No data loss (old `user_id` untouched).
- **After Step 6 (NOT NULL + RLS):** restore from the pre-Step-6 backup, or run the reverse script: drop RLS policies → `ALTER COLUMN household_id DROP NOT NULL` → `DROP COLUMN household_id` → `DROP TABLE household_members, households`. Because `user_id` was never removed, the game runs identically after rollback.
- **Trigger:** any verification failure in §7, or regression in the smoke test (allocate → next-month → leaderboard).

---

## 7. Test strategy

**Data integrity (post-backfill, pre-constrain):**
- `COUNT(households) == COUNT(users)`; exactly one `self` membership per household; `UNIQUE(user_id)` holds.
- No financial row has NULL `household_id`; every `household_id` resolves to a real household.
- No orphan households (household with zero members) and no orphan memberships.

**RLS:** a signed-in user can read only their own household + members; cannot read another user's; cannot write any of it from the browser.

**Regression (gameplay unchanged — the acceptance bar for "invisible"):**
- Full smoke game: register → `/allocate` → `/next-month` ×N → `/leaderboard`, asserting identical cash/net-worth/score trajectories vs a pre-migration run with the same seeds. Determinism must be byte-identical since no engine math changed.
- Loan amortization + allocation-conservation checks from this session still pass.

**Migration idempotency:** re-running the migration script is a no-op (guards prevent duplicate households).

---

## 8. Open decisions (need your ruling before SQL)

1. **Ownership FK strategy** — (a) supertype / (b) nullable-FK+CHECK / (c) V1-pragmatic. *Recommend (c).*
2. **Keep `user_id` columns in V1?** *Recommend yes* (rollback safety + Individual ownership). Drop only in a later cleanup once households are load-bearing.
3. **`household_id` on the RPC + stored function now, or defer** until ADR-002 needs it? *Recommend now* — it's cheaper to thread it through once than to re-open `process_month_atomically` twice.
4. **`households.display_name` source** — player name, or leave null in V1? Cosmetic.

Once you rule on these (mainly #1), I can produce `household_migration.sql` + the code diffs as the *next* gate — not before.
