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

---

# V3 Changes (2026-07-21, same day)

## The allocation bug you hit

`Must allocate exactly your available cash of ₹8,118. Current total: ₹8,117`

**My bug, not yours.** Three mistakes compounded:

1. `cash` carries decimals from market growth (e.g. `8117.51`).
2. The frontend `formatINR` uses `Math.floor` → displays `₹8,117`. The backend used `round()` → error message said `₹8,118`.
3. My allocation code re-parsed its **own displayed string** back into a number. So the client believed `8117`, the server believed `8117.51`, the gap was `0.51`, and my tolerance was `0.5`. The player could not win.

**Fix — removed the rule, not just the rounding.** The server now derives the remainder:

```
invested = stocks + gold + ef + prepay
keep_cash = available - invested     # server-derived, money conserved by construction
```

The only failure left is investing more than you have. `allocAvailableRaw` is held as a number and never re-read from rendered text. The "Keep as Cash" input and "Put remainder in cash" button are gone — there is nothing left to balance.

## UI/UX simplification

- **One action per round.** News card → allocate panel → everything else collapsed under "More Options".
- Loans converted to a collapsed `<details>` panel.
- Allocation now reads "Remaining stays as cash: ₹X" instead of an error you had to clear.
- Trust badge hidden; dead `trustPoor`/`trustRich` DOM writes deleted (they would have thrown on every 5-second poll after the panel was removed).

## Real-world news library (`models/news_library.py`)

24 curated historical events with real headlines, real dates, real impacts, and the lesson each teaches. Admin picks one from a grouped dropdown; it writes a normal `market_scenarios` row, so there is exactly one engine path whether the source is the library, a preset, or hand-typed numbers.

Figures verified against sources, not invented:

- **2008 GFC** — Sensex 20,465 → 9,176 over the year (about −55%); gold about +6% in USD.
- **March 2020 COVID** — Sensex −13.15% on 23 March, its worst day ever; −28.6% for Q1.
- **2020 gold rally** — gold finished the year up roughly 25%, peaking near $2,070/oz in August.

Also included: Russia–Ukraine 2022, Gulf War 1990, Kargil 1999, demonetisation 2016, Harshad Mehta 1992, taper tantrum 2013, IL&FS 2018, 1991 liberalisation, 1973 oil shock, 2013 gold correction, monsoon failure, budget rally.

**Deliberate teaching detail:** gold *fell* in the March 2020 crash (margin-call selling) and *rallied* months later. `covid_crash_mar2020` and `covid_gold_rally_2020` are sequenced so players learn that "gold always rises when stocks fall" is false.

Live-feed option is **not** built — deferred as you chose. The library is the event-day-safe path.

## Insurance replaces Social Investment

Social Investment cost real money, fed almost nothing into the ADR-008 score, and taught nothing. Replaced with three insurance tiers:

| Plan | Premium/mo | Emergency cover | End cash after one ₹1,20,000 emergency |
|---|---:|---:|---:|
| No Cover | ₹0 | 0% | ₹41,118 |
| Basic Health | ₹2,500 | 50% | ₹98,618 |
| Comprehensive | ₹6,000 | 80% | ₹1,31,118 |

Market losses are **uninsurable** — you cannot buy protection from your own portfolio choices, only from misfortune. Comprehensive costs ₹72,000/year and saves ₹90,000 on one hit: correct if hit, wasted if not. That discomfort is the lesson.

## Database defect found and fixed

The `process_month_atomically` RPC's loan INSERT did not write `term_months`, `loan_type` or `emi`. Every auto-loan created during a month roll would have displayed **"EMI ₹0"** on the player dashboard. The RPC now writes all three, and preserves `spouse_archetype` / `insurance_plan` via COALESCE so a month roll can never blank them.

Migrations applied live: `v3_insurance_plan`, `v3_rpc_loan_columns_and_insurance`.

## Verification

`32 passed, 389 subtests passed`. 36 routes register cleanly.

## Still open (unchanged)

1. **The months 2–12 content pack is still the blocker.** The news library gives you 24 ready-made market scenarios, but `events` (emergencies, job loss, medical) is still empty — and the earlier simulation proved that without events, strategy spread collapses to 1.13x. **Insurance is worthless until emergency events exist to insure against.**
2. City vs outer lifestyle remains a fake choice.
3. Deploy to Render + Netlify.

---

# V4 Changes (2026-07-21) — content pack + real-time feel

## 12-month problem + opportunity schedule (`backend/tools/seed_content.py`)

The blocker I kept flagging is now cleared. Each month 2–12 has **one problem and one opportunity**, tuned to the V2 economy (a ~₹12–18k monthly surplus, so a ₹48k medical bill actually hurts) and applied to the live DB.

Problems: Lifestyle Creep, Phone Shatters, Rent Hike, **Medical Emergency (insurable)**, Family Wedding, Job-Switch Gap Month, Appliance+Vehicle Repair, **Family Illness (insurable)**, Tax Notice, **Road Accident (insurable)**, and a Year-End Bonus to finish. Opportunities span low/medium/high risk with honest expected value — the ₹20k side business has a 65% chance of losing everything and lands the same month your job is unstable.

Every event now carries a **category** (`v4_events_category` migration). Only `emergency`/`medical` events trigger insurance payouts — you cannot insure a rent hike, a market move, or your own lifestyle creep.

## The year now has real stakes

Running the actual content pack through the engine, a player faces **5–8 cash crises** across the year, versus **zero** before (empty events table). The year finally tests planning instead of rewarding passivity.

## Insurance verified +EV (my earlier table was wrong)

An intermediate simulation suggested insurance lost money. That was a bug in the throwaway sim harness (bad loan-carry accounting — it hung), not the game. A clean isolation (absorb losses from a large fund, market off, toggle only the plan) matches the hand calculation exactly:

| Plan | Premium/yr | Net worth vs no cover |
|---|---:|---:|
| Basic (50%) | ₹27,500 | **+₹43,000** |
| Comprehensive (80%) | ₹66,000 | **+₹46,800** |

Basic is the capital-efficient pick; comprehensive is for the risk-averse. A genuine decision, correctly balanced.

## Real-time visual layer (`css` effects block + `js/effects.js`)

- **Animated value counters** — cash, stocks, gold, EF, net worth tick between values with a green/red flash and a floating ±delta chip, instead of snapping.
- **Month-change drama** — the market card reveals with a scale-in; it **shakes** on a crash/war (stocks ≤ −10%) and **glows** on a strong bull (≥ +8%). Fires only when the month advances, never on the 5s poll.
- **Confetti** on an opportunity win and at game finish.
- **Emoji** throughout events and opportunities; **risk-coloured** opportunity cards (🟢 low / 🟡 medium / 🔴 high).
- Everything respects `prefers-reduced-motion` — all animation disables and counters snap to final values.

## Verification

`32 passed, 389 subtests`. All JS syntax-checked, HTML tags balanced, content pack live in Supabase (11 events + 11 choices confirmed).

## Still open

1. **`expense_increase` events are one-time, not recurring.** The engine subtracts the value once; it does not permanently raise monthly expenses. Descriptions were reworded to be honest, but if you want rent hikes to compound, that's a real engine feature to add.
2. City vs outer lifestyle still a fake choice.
3. Deploy to Render + Netlify — none of this is live for players until they rebuild.

---

# V5 Changes (2026-07-24) — claymorphism, tabs, mascot

## Theme: claymorphism light (sky blue)
Full flip of the design system to soft-clay 3D on a light sky palette — clay drop-shadows with inset highlights, sunken inputs, pill buttons that physically press. Done at the CSS-variable layer plus an appended clay component layer, so **no class names changed**. All inline dark-theme remnants (`rgba(255,255,255,x)`, `rgba(0,0,0,x)`) swept across every HTML/JS file. Applies to player pages AND admin. Reduced-motion respected.

Side effect: the ugly white full-screen dropdown from your screenshot was the native `<select>` fighting the dark theme — on the light theme it now matches the page.

## Tabs kill the long scroll
- **Player:** Net worth + portfolio always visible on top; below, tabs **🏠 Home | 📈 Invest | 🛡️ Loans & Cover | 📜 History**. The Invest tab shows a pulsing amber dot while allocation is pending; the action banner jumps straight to it.
- **Admin:** **🎮 Control | 📰 Market & News | ⚡ Events | 👥 Players**. No page reloads.

## Opportunities removed from player view
Hidden entirely, per your decision. The 11 seeded choices and backend routes remain dormant — re-enabling is a UI-only change. Note: the admin "Optional Choice Creator" still exists in the Events tab; it now authors content no player can see. Tell me if you want it hidden too.

## Monty 🪙 — the guide mascot
CSS-drawn coin character, bobbing and blinking in the corner, with a speech bubble. **State-driven, not random:** it reads the same payload the dashboard renders and speaks only when the situation changes — never on the 5-second poll. Priority order: negative net worth → unallocated cash (with the exact amount) → marriage round → market crash ("don't panic-sell — remember March 2020") → boom → heavy debt → no insurance → turn locked → idle flavour. Click Monty to replay the current tip.

## Verification
All JS syntax-checked, every page's div tree balanced, 32 backend tests still pass (no backend changes).

## Still open
1. `expense_increase` events remain one-time, not recurring.
2. City vs outer lifestyle remains a fake choice.
3. **Deploy to Netlify** — this is all local until you push and rebuild.

---

# V6 (2026-07-24) — real 3D anime guide

## Why not procedural 3D
A character built from three.js primitives (spheres, cylinders) looks like a mannequin, not anime. Every good 3D anime character on the web is an artist-made **VRM** model. So the code loads a real model rather than trying to draw one.

## What was built — `frontend/js/mascot3d.js`
three.js `0.180.0` + `@pixiv/three-vrm@3.5.5` (CDN paths and peer-dep range verified against the jsDelivr API, not assumed). Loads `frontend/assets/mira.vrm` and renders head-and-shoulders at 200×260.

- **Idle life:** breathing on the chest bone, slow spine sway, subtle head roll — small amplitudes; large ones look like a seizure.
- **Head-tracking:** she follows the mouse cursor via the VRM `lookAt` rig.
- **Expressions cross-fade** (eased, ~6/sec) into the five game moods, mapped onto VRM standard expressions: happy→happy, excited→happy(1.0), alert→surprised, worried→sad, sleepy→relaxed.
- **Irregular blinking** — fixed intervals read robotic.
- **VRM 0.x and 1.0 both work** via `VRMUtils.rotateVRM0()`.

## Fail-safe chain
The guide can degrade but must never take the dashboard down on event day:

1. VRM loads → 3D model, SVG hidden
2. No file / CDN blocked / not a VRM / **no WebGL** → quiet console note, hand-drawn 2D character stays
3. Any throw at all → caught, 2D stays

`mascot.js` hands face control to `MiraCore.on3D()` only once the model is actually live. Console tags are `[Mira] …` for diagnosis.

## What YOU must do
Drop a `.vrm` at `frontend/assets/mira.vrm`. See `frontend/assets/README.md`.
- **VRoid Studio** (free) — build your own in ~15 min, zero licence risk. Best for a college event.
- **VRoid Hub** — thousands of free downloadable models; check the licence.
- **Keep it under ~8 MB.** Export textures at 1024, not 2048. A 20 MB model on shared conference wifi takes 30+ seconds to appear.

## Verification
All JS parses, importmap correctly precedes the module script, every page's div tree balanced, 32 backend tests pass.

---

# V7 (2026-07-24) — marriage retuned (it was broken)

## What the concept is
At month 6 the admin opens the **marriage round**. Four candidate wives are shown face-down. You get **3 free dates** to reveal one trait each (income, expense impact, or assets); extra dates cost ₹5,000. Then you either **propose** or **stay single** — staying single is free and must remain competitive, or the round is fake.

A wife changes the rest of your game: monthly income, monthly household expense, and a one-off dowry of assets at the wedding. You pay your share of the wedding out of cash.

## The bug I introduced and did not catch
The V2 rebalance cut the player's monthly surplus from ~₹60,000 to ~₹12,000. **The spouse stat blocks were never retuned.** A wife earning ₹10–36k/month went from a marginal boost to a **1.8×–2.25× multiplier** on the player's entire surplus.

`marriage_ev_sim.py` — the tool written specifically to catch this — failed two of its own three gates:

- **GATE 2:** marrying beat staying single by **+10.2%** (tolerance ±4%). Marriage was near-mandatory.
- **GATE 1:** spread between options **11.1% / 11.8%** (tolerance ≤8%).

Root cause of the miss: the simulator kept its **own duplicate copy** of the archetype numbers, so it happily certified values the game no longer used.

## The fix — solved, not guessed
`tools/marriage_tuner.py` searches income / expense / dowry / wedding-cost space and evaluates all three gates in both market regimes. It found a zero-violation configuration:

| Wife | Income | Expense mod | Stocks | Gold | EF |
|---|---:|---:|---:|---:|---:|
| The Saver | 5,000 | −2,500 | 0 | 12,000 | 23,000 |
| The Earner | 16,000 | +3,500 | 0 | 0 | 5,000 |
| The Investor | 4,000 | −500 | 35,000 | 16,000 | 4,000 |
| The Anchor | 7,000 | −500 | 5,000 | 0 | 35,000 |

`WEDDING_COST` 88,000 → **25,000**, reframed as *your share after family contributions and cash gifts* — the old figure had become a 7.3-month liquidity landmine.

**Result — all gates PASS in both regimes:** spread 4.0% / 5.5%, single-gap +1.7% / +1.6%, dominance 0.4% / 0.6%.

The design intent survives and is sharper than before: **The Investor ranks above "stay single" when markets grow (+0.4%) and below it when they stall (−1.5%).** The wife you pick is a read on the economy the admin authors, not a coin flip.

`marriage_ev_sim.py` now **imports from `constants.py`** instead of duplicating it. That drift cannot recur.

## Month 6 is now the hardest month — confirm you want this
Your own wedding (−25,000) lands in the same month as the authored **Family Wedding Contribution** (−22,000). Combined −47,000 against a ₹12,000 surplus:

| Entering month 6 with | Outcome |
|---|---|
| No emergency fund | **Cash crisis** → penalty auto-loan |
| Small EF (₹25,000) | **Cash crisis** → penalty auto-loan |
| Healthy EF (₹60,000) | Survives, ₹31,973 EF left |

I left this as-is because it teaches the real lesson — build liquidity *before* a major life event. Say the word if you want the family-wedding event moved or reduced.

## Caveat
The gates were evaluated **without** the content-pack events (the simulator couldn't reach Supabase from my sandbox). Events hit married and single players equally, so the relative comparison holds, but re-run `marriage_ev_sim.py` from your machine — it will pull the real events — before the event day.

## Verification
32 backend tests pass. Live `spouse_archetypes` table updated to match.

---

# V8 (2026-07-24) — ADR-014 spouse negotiation, fully built

Ratified ADR is at `ADR-014_SPOUSE_NEGOTIATION.md`. Built rules-first, per the recommendation: the entire feature works offline; the LLM is additive.

## The pipeline (ADR-003 honoured)
```
player types  →  /negotiate       →  extract intent (LLM or offline parser)
                                  →  CONFIRMATION shown back to player
              →  /negotiate/commit→  negotiation_service.evaluate()   ← DECIDES THE MONEY
                                  →  audit row + state update
                                  →  ai_service.narrate()             ← words only
```
`negotiation_service.py` contains **no network reference at all** — a test asserts this by source inspection. The AI cannot influence a rupee.

## Your requirements, in code
- **"combine income"** — already live: spouse income and expenses fold into the household each month.
- **"wife arrange event and put in estimate"** — she raises one proposal per month with an amount, seeded per player+month so a refresh cannot reroll it.
- **"it will depend on spouse"** — proposal *type* is archetype-driven, and three of the four are financially **sound**: Investor pushes equity, Saver pushes a permanent budget cut, Anchor pushes emergency reserves. Only the Earner's is pure consumption. "Always haggle her down" is a losing strategy.
- **"player can try convince"** — free-text natural language, any phrasing.
- **"once start convince don't allow immediately"** — `NEGOTIATION_MIN_ROUND_TO_ACCEPT = 2`. A round-1 counter is **never** accepted, even at 99% of the ask. Test `test_round_one_never_accepts_even_at_full_ask` locks this.
- **"only allow the player satisfying his spouse"** — acceptance requires clearing `negotiation_min_ratio(archetype, satisfaction)`. A content wife compromises; an unhappy one holds out.

## Fairness (ADR-000)
Phrasing cannot change an outcome — `test_phrasing_cannot_change_outcome` proves "I can do 15,000" and "lets say Rs 15k" resolve identically. Ambiguous text is **rejected, never guessed**.

## Satisfaction
0–100, starts 60. Primary effect is conversational. Financial teeth bounded to **±₹3,000/month** and asserted by test across the full range. Does **not** enter the leaderboard score — a social stat should not dilute ADR-008.

## New surface
Backend: `models/negotiation_intents.py`, `services/negotiation_service.py`, `services/ai_service.py`, `POST /negotiate`, `POST /negotiate/commit`, admin proposal CRUD.
Frontend: `js/negotiation.js` + chat panel with satisfaction meter and confirmation gate.
DB: `spouse_satisfaction`, `household_expense_modifier`, `spouse_proposals`, `player_negotiations` (full audit), `spouse_dialogue`, `negotiation_enabled` flag. All applied live, all additive.

## Rollback
Admin → Control → **Spouse conversations** off. One toggle; marriage reverts to previous behaviour.

## Verification
**64 tests pass** (32 pre-existing + 32 new). End-to-end negotiation exercised. All page div trees balanced.

## Outstanding
1. **§8.1 unanswered — no LLM key.** `ANTHROPIC_API_KEY` on Render activates richer conversation; without it the offline parser and template bank run everything. Nothing is blocked.
2. Still not pushed to GitHub.

---

# V9 (2026-07-24) — PRE-DEPLOY AUDIT

## CRITICAL BUG FOUND AND FIXED — `/start-game` destroyed the content pack

`POST /admin/start-game` ran `DELETE FROM events; DELETE FROM optional_choices;`.

**Every press of "Start Game" wiped the entire authored 12-month content pack.** On event day the sequence would have been: press Start Game → all 11 problems deleted → 50 students play salary-minus-expenses with no narrative, no emergencies, and insurance protecting against nothing.

This was not hypothetical: the audit found `events = 0 rows`, having verified 11 rows seeded earlier. The button had already eaten them.

**Fix:** player data is still wiped on restart (and `player_negotiations` was *added* to the wipe — old rounds would otherwise read as already-settled in the new game). Authored content — `events`, `optional_choices`, `market_scenarios`, `spouse_proposals`, `spouse_dialogue` — is now preserved. Content is deleted deliberately from the admin Events tab, never as a side effect.

Content pack re-seeded: **11 events restored.**

## Second fix — RPC column landmine
The month-roll RPC did not list `spouse_satisfaction` or `household_expense_modifier`. Harmless today (unlisted columns keep their values), but the moment anyone makes the engine change satisfaction during a roll, the write would vanish with no error. Both columns added with COALESCE — behaviour identical, hole closed.

## Audit results

| Check | Result |
|---|---|
| Backend tests | **64 pass** |
| Routes register | 41, clean |
| JS syntax (7 files) | all parse |
| HTML div balance (7 pages) | all balanced |
| Script references resolve | yes |
| Engine-written columns exist in DB | yes |
| Content pack | **restored, 11 events** |
