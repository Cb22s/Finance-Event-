# Money Master V2 — Change Report (2026-07-21)

## What was actually wrong

| Reported | Reality |
|---|---|
| "Allocation only works first month" | Correct, and by design. `allocation.js` redirected to the dashboard if `/dashboard` returned OK, and `monthly_processor.py` had no allocation step at all. After month 1 cash accumulated untouched for 11 rounds. |
| "Loan shows but doesn't work" | Not a bug — the feature did not exist. `dashboard.html` rendered a `loanVal` display element; there was no `/loan` route, no borrow UI. The only loans were involuntary auto-loans on cash deficit. |
| "Assigned values small, easy profit" | **Backwards.** Values were far too generous: stocks grew **8%/month** (~150%/yr), gold 4%/mo, EF 2%/mo, and salary left a **Rs60,000/month** risk-free surplus. |
| "Stock and gold should change together with a reason" | Did not exist. `market_engine.py` drew stocks and gold from unrelated RNG ranges; no correlation, no cause, no narrative. |
| "Marriage missing" | Marriage **was built** (commit `014df12`). `marriage_migration.sql` had never been applied to the live Supabase — `spouse_archetypes` and `player_spouse_reveals` did not exist in the database. |

## Changes

### 1. Balance (`models/constants.py`)
- Stocks `0.08 -> 0.012`/mo, gold `0.04 -> 0.006`, EF `0.02 -> 0.005`.
- Volatility `-0.15/+0.20 -> -0.09/+0.09` (symmetric — the old range was a +2.5%/mo free lunch).
- Expenses raised: city `40,000 -> 88,000`, outer `25,000 -> 82,000`. Monthly surplus is now Rs12,000 (city) / Rs18,000 (outer), not Rs60,000.
- Loan rate `0.12/mo` (289%/yr!) split into `LOAN_INTEREST_RATE = 0.012` for planned borrowing and `AUTO_LOAN_INTEREST_RATE = 0.025` as the penalty for being forced into debt.

### 2. Correlated market scenarios (`engine/market_engine.py`)
`resolve_market_scenario(month, authored, auto_market)` is now the single source of truth. One scenario moves **both** stocks and gold with a stated cause. Eight regimes (war, crash, rate hike, inflation spike, steady, boom, recovery, correction). Precedence: admin-authored row > auto regime > flat.

Regimes chain with memory — a shock is followed by a recovery/drift, not a second independent crash. Still seeded by month only, so every player faces the identical market (ADR-009 preserved).

Sample month 8 auto output: *Geopolitical Conflict — stocks -12.1%, gold +14.1%.*

### 3. Monthly allocation — `POST /allocate-month`
Every month from 2 onward the player distributes available cash across stocks / gold / EF / loan prepayment / cash. Must total exactly the available cash. `lock-turn` is gated on it. Atomically claimed via the existing `player_month_actions` unique-violation pattern; audited in the new immutable `player_month_allocations` table.

### 4. Player-initiated loans — `POST /loan`, `POST /loan/quote`
Amount + 3/6/12-month term, amortized EMI, live quote before committing. Bounded by a Rs3,00,000 debt ceiling (`MAX_TOTAL_DEBT_MULTIPLE`) and a 40%-of-income EMI affordability gate — without these a player could leverage-farm the leaderboard, the exact failure ADR-008 exists to prevent.

### 5. Admin market editor — `/admin/market` (GET/POST/DELETE) + `/admin/market/preview`
Preset regimes to start from, required headline + reason, ±60% sanity bound, and a resolved 12-month path preview so the admin sees the arc before the event rather than discovering it live.

### 6. UI/UX
- **Action-required banner** — the old dashboard never told the player they owed a decision.
- **Market news card** — headline, reason, stock % and gold % side by side.
- **Allocation panel** with live remaining/over-budget feedback.
- **Loan panel** with per-loan EMI, rate, term, and auto-vs-planned labelling.
- **Fixed:** the 5s dashboard poll re-rendered inputs mid-keystroke and wiped whatever the player was typing.

### 7. Migrations applied to live Supabase
- `marriage_and_courtship` — the never-applied marriage migration. **Marriage now works.**
- `v2_monthly_allocation_market_scenarios_loans` — `player_month_allocations`, `market_scenarios`, and `term_months`/`loan_type`/`emi` on `player_loans`.

## Verification

`32 passed, 389 subtests passed`. Two tests were updated, both legitimately broken by the rebalance:
- `test_determinism` — approved the new seeded `_regime_rng` wrapper.
- `test_marriage` — expectation was hardcoded to a 40,000 city expense; now derived from constants so future rebalances don't silently break it.

### Balance simulation (`tools/balance_sim.py`)

**Without events (current live config — `events` table has 0 rows):**

| Strategy | Net worth | Score |
|---|---:|---:|
| All-in stocks | 221,185 | 42.8 |
| All-in gold | 251,036 | 48.9 |
| Balanced 40/30/30 | 231,706 | 49.1 |
| Conservative EF | 228,346 | 52.2 |
| Hoards cash | 222,199 | 48.0 |

Spread 1.13x. **Hoarding cash beats investing.** The game rewards passivity.

**With three shock events authored (months 4, 7, 10):**

| Strategy | Net worth | Score |
|---|---:|---:|
| All-in stocks | 171,647 | 35.6 |
| All-in gold | 193,489 | 41.5 |
| Balanced 40/30/30 | 152,406 | 37.9 |
| Conservative EF | 105,049 | 37.6 |
| Hoards cash | **85,627** | 35.9 |

Spread 4.29x. The cash hoarder finishes **last**.

Leveraged stocks (borrows the full ceiling): 366,948 net worth but score 29.4 with 9 cash crises — wins on wealth, loses on the leaderboard. ADR-008 working as designed.

## Still open

1. **The months 2-12 content pack is the load-bearing item.** The numbers above prove tuning growth rates cannot fix balance on its own. With `events` empty, nothing can punish a bad player. This was already blocker #1 in `PROJECT_STATE.md` and it still is.
2. **City vs outer is unbalanced.** Outer costs Rs6,000/month less and gives up nothing. City lifestyle needs a real upside (salary/career-event access) or the choice is fake. Not fixed — it needs a design decision.
3. **Deploy.** None of this is live until Render + Netlify rebuild.
4. **Re-run `marriage_ev_sim.py`** against the new constants; the spouse archetype balance was tuned against the old economy.
