# Money Master — Product Requirements Document

**Version 1.0** · 2026-07-12 · Owner: A. Patchaiyappan
Architecture decisions are **not** restated here — see `ARCHITECTURE_DECISIONS.md` (ADR-000…013). This document covers only what lives nowhere else: game content, product rationale, and event operations.

---

## 1. Product Vision

Money Master is a financial life-simulation event platform. College students live 12 simulated months of salary, expenses, investments, emergencies, and social obligations, competing on a ranked leaderboard. The product teaches financial decision-making through consequences, not quizzes. Guiding priorities and conflict-resolution rules: **see ADR-000.**

## 2. Audience & Context

Primary: college students at a live, admin-paced competition event. Players need no finance background; the game is the curriculum. Secondary: the event organizer (admin), who controls pacing from a dashboard while an emcee narrates rounds.

## 3. Game Structure (V1)

- **Duration:** 12 months. Month 1 is allocation; months 2–12 are processed rounds.
- **Starting budget:** ₹1,00,000, allocated exactly (validation enforces the total) across cash, stocks, gold, emergency fund, and optional bike down payment.
- **Salary:** ₹1,00,000 per month, every month, for every player (equal footing by design).
- **Rounds:** the admin advances months one at a time. Players cannot see future events. Round release and locking: **see ADR-011.**

## 4. Player Decisions

- **Initial allocation** — the foundational strategy decision. Includes lifestyle choice: City (₹40,000/mo total) vs. Outer (₹25,000/mo total), trading cost against nothing else in V1 (a deliberate simplification).
- **Bike purchase** — ₹10,000 down, ₹5,000 EMI, 3-month lock-in, halves transport cost. Teaches EMI trade-offs at small scale.
- **Optional choices** — admin-published per-month opportunities with probabilistic outcomes (deterministic per-player roll for fairness).
- **Asset sales** — players may liquidate stocks/gold at a 10% penalty, credited the following month. Teaches liquidity cost and panic-selling consequences.
- **Relative help decisions** — periodic requests to help family (none/medium ₹2,000/high ₹5,000) building a trust score with delayed payoffs. Teaches social capital as a financial asset.

## 5. Economy Parameters (V1 tuning)

Single source of truth: `backend/models/constants.py`. Headline values: stocks 8%/mo base growth with −15%…+20% volatility; gold 4%/mo with minor fluctuation; emergency fund 2%/mo interest; inflation 0.5%/mo on expenses from month 4; loans at 12%/mo interest with EMI = 10% of principal; auto-loan on cash crisis. Market movements follow one **global path** — every player faces identical returns in the same month: **see ADR-009.**

**Design intent:** rates are compressed (monthly ≈ annual real-world) so 12 months produce a visible lifetime arc. They are pedagogically honest in *relative* terms — stocks > gold > savings in return and risk — not numerically realistic.

## 6. Life Events

Seven categories with state-driven probabilities (base rates in constants):

| Category | Base | Design purpose |
|---|---|---|
| Financial emergency | 25% (+20% if EF < ₹5k, +10% if in debt) | Punishes being unprepared, not being unlucky |
| Investment opportunity | 30% (+ if cash-rich) | Rewards liquidity |
| Market fluctuation | 40%, global | Shared macro reality (ADR-009) |
| Social responsibility | 20% | Feeds trust score |
| Expense spike | 20% | Cost-of-living noise |
| Windfall | 10% (+ with high trust, late-game) | Delayed karma payoff |
| Trust penalty | conditional (month ≥ 6, trust < 2) | Consequence of ignoring social events |

Personal event probabilities depend on the player's own state — consequences of choices, not lottery. Admins can inject additional global events any month. Event architecture: **see ADR-004, ADR-006, ADR-011.**

## 7. Winning: Financial Health Score

Ranking uses a composite score, not net worth: 40% net worth (normalized to resources received, capped), 15% liquidity (months of expenses in emergency fund, target 6), 15% debt control, 15% risk protection, 15% discipline (running average; cash crises graded down). Formula is **public to players** — the scoreboard is itself teaching material. Full decision and anti-gaming rationale: **see ADR-008.**

**Why not net worth?** Net-worth-only ranking crowns the luckiest gambler and teaches exactly the wrong lesson. The composite makes the boring virtues — liquidity, low debt, insurance-mindedness, consistency — visibly count.

## 8. Roles

**Player:** allocate, decide monthly, watch consequences, climb leaderboard.
**Admin:** start/restart game, advance months, publish events and optional choices, manually correct player records (audit-logged), reset individual players, end game. Admin actions are the event's pacing mechanism.

## 9. Event-Day Operations

1. Players register/login (Supabase Auth) and read the case study screen.
2. Allocation window opens; emcee explains the economy; players lock month 1.
3. Each round: emcee narrates the month's theme → admin advances month → players review results and make decisions → repeat.
4. Leaderboard displayed publicly between rounds (score in points, net worth visible).
5. After month 12: game ends, final standings shown, top 3 on podium display.

**Operational rules:** never deploy code or run migrations mid-game (ADR-012/013); admin corrections are audit-logged to `player_month_log`.

## 10. Future Versions (references only)

Household foundation: **ADR-001** (approved V1 architecture, design pending). Marriage & life partner: **ADR-002** (approved, future). Conversational AI pipeline: **ADR-003**. Financial ownership model: **ADR-005**. AI memory: **ADR-010**. New feature proposals follow the evaluation framework and classify per **ADR-013**.

## 11. Change Management

Every change is classified before work begins: **see ADR-013.** This PRD updates when Level 5 features land or game content/tuning materially changes; it never restates architecture.
