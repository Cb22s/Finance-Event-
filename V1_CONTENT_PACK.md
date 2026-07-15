# Money Master — Version 1 Content Pack

**Date:** 2026-07-13 · **Role:** Lead Game Content Designer · **Purpose:** removes release blocker C2 (RC2_READINESS_PLAN.md §2) — a complete, balanced 12-month content set, authored entirely through the existing event and optional-choice systems.
**Constraint compliance:** no business rules changed, no gameplay redesigned, no new mechanics. Every item below is data for the existing `events` and `optional_choices` tables, enterable through the existing `POST /event` and `POST /choice-admin` admin endpoints exactly as they work today (including the QA-005 validation: `event_type` ∈ {fixed, percentage}, `impact_target` ∈ {cash, stocks, gold, expense_increase} — `expense_increase` only valid for `fixed` — `reward_type` ∈ {cash, stocks, gold, emergency_fund}, `probability` ∈ [0,100], `cost`/`reward_value` ≥ 0).

---

## Scope note: Month 1

Month 1 is allocation-only by existing design (PRD §3: "Month 1 is allocation; months 2–12 are processed rounds"). The engine does not process admin events during month 1 — `event_engine`/`market_engine` only run from month 2 onward. Month 1's "meaningful player decision" is already the existing allocation mechanic (lifestyle choice, investment split, bike purchase) — that is not new content, it's the existing `/allocate` flow, and is not re-authored here. This content pack covers the 11 admin-content months, **2 through 12**, per the existing processed-round structure.

## How admin content layers on the automatic engine (context, not new behavior)

Every month, regardless of this content pack, `market_engine.py` already applies the ADR-009 global market return, and `event_engine.py` already generates per-player state-driven events (emergency, opportunity, social, expense spike, windfall, trust penalty — PRD §6's seven categories). The content below is the **admin-authored layer** on top of that baseline — the mechanism ADR-004 designates as a first-class event source and ADR-009 explicitly anticipates ("Admin capability: choose or preview the economic scenario... supports designed learning arcs"). This is not a repeat of the QA-002 defect (that was two *automatic, unprompted* systems both moving the market every month); this is the *deliberate, sparse, curated* layer the architecture always intended admins to control. Because of that, market-moving admin events are used sparingly here — three designed beats (months 5, 8, 10) — rather than every month, so the designed arc stays legible against the baseline instead of adding a second unexplained layer of noise.

---

## Month 2 — First Paycheck Reality

**1. Mandatory event**
`event_name`: "Bank Account Setup Fees" · `event_type`: fixed · `impact_target`: cash · `value`: -1500 · `description`: "New account maintenance and debit card issuance fees are deducted automatically."

**2. Optional choice**
`name`: "Professional Certification Course" · `cost`: 8000 · `risk_type`: low · `reward_type`: cash · `reward_value`: 20000 · `probability`: 70

**3. Learning objective:** distinguish discretionary spending from unavoidable fixed costs, and recognize investing in earning capacity as a legitimate early-game move.
**4. Financial concepts:** fixed vs. variable costs; human-capital investment; expected value of a skills investment.
**5. Expected trade-offs:** the mandatory fee is a forced lesson that "free" accounts aren't free. The choice trades ₹8,000 now for a 70% chance at ₹20,000 — a deliberately favorable bet (EV +₹6,000) to reward players who engage with growth-oriented decisions early, before the game's harder trade-offs arrive.
**6. Difficulty:** Easy.
**7. Event category:** Expense (mandatory) / Investment opportunity (choice) — PRD §6.
**8. Balance justification:** ₹1,500 is trivial against a ₹1,00,000 salary (1.5%) — it teaches without punishing. The choice's positive EV (+₹6,000) is intentional for month 2: early-game choices should reward engagement, not punish inexperience: this is the easiest, most clearly "correct" choice in the pack.

---

## Month 3 — Subscription Creep

**1. Mandatory event**
`event_name`: "Subscription Creep" · `event_type`: fixed · `impact_target`: expense_increase · `value`: -1200 · `description`: "Streaming, app, and cloud subscriptions taken out on autopay quietly add up."

**2. Optional choice**
`name`: "Hot Stock Tip From a Friend" · `cost`: 5000 · `risk_type`: high · `reward_type`: stocks · `reward_value`: 6000 · `probability`: 45

**3. Learning objective:** recognize that small recurring costs compound, and that not every "insider" investment tip is worth taking.
**4. Financial concepts:** recurring/subscription cost drift; unverified-information risk; expected value below cost.
**5. Expected trade-offs:** the mandatory event is a quiet, easy-to-miss cost — deliberately small so it teaches vigilance rather than pain. The choice is this month's deliberate "trap": EV is slightly negative (-₹2,300), rewarding skepticism over impulse.
**6. Difficulty:** Easy.
**7. Event category:** Expense spike (mandatory) / Investment opportunity (choice) — PRD §6.
**8. Balance justification:** the negative-EV choice is intentional and necessary for balance — a content pack where every optional choice is profitable teaches "always click yes," not judgment. This is the first of four deliberately unfavorable choices spread through the pack (months 3, 8, 11, 12) so skipping a bad bet is as valid a lesson as taking a good one.

---

## Month 4 — Rising Costs

**1. Mandatory event**
`event_name`: "Utility Deposit Increase" · `event_type`: fixed · `impact_target`: expense_increase · `value`: -2000 · `description`: "Utility providers raise the standard deposit as citywide costs climb — the first sign inflation has arrived."

**2. Optional choice**
`name`: "Lock-In Fixed-Rate Utility Plan" · `cost`: 3000 · `risk_type`: low · `reward_type`: cash · `reward_value`: 6500 · `probability`: 60

**3. Learning objective:** connect the game's built-in inflation mechanic (`INFLATION_START_MONTH = 4` in `constants.py` — already active from this month regardless of this content pack) to a concrete, felt decision, and understand hedging against a known future cost increase.
**4. Financial concepts:** inflation; rate-locking / hedging; present cost to avoid future variable cost.
**5. Expected trade-offs:** the mandatory event is a one-time notice cost layered on top of the ongoing automatic inflation adjustment (which continues silently every month from here on) — it marks the moment, it doesn't duplicate the mechanism. The choice offers a modest positive-EV hedge (+₹900) for players paying attention to the inflation cue.
**6. Difficulty:** Easy–Medium.
**7. Event category:** Expense spike (mandatory) / Investment opportunity (choice) — PRD §6.
**8. Balance justification:** kept deliberately small (₹2,000 one-time vs. the ongoing 0.5%/month automatic inflation on living costs) so it doesn't double-count with the engine's own inflation math — it's a narrative marker, not a second inflation charge.

---

## Month 5 — Market Correction

**1. Mandatory event**
`event_name`: "Market Correction" · `event_type`: percentage · `impact_target`: stocks · `value`: -8 · `description`: "A broad market pullback trims stock valuations across the board. Every player faces the identical move this month (ADR-009)."

**2. Optional choice**
`name`: "Emergency Fund Top-Up Drive" · `cost`: 5000 · `risk_type`: low · `reward_type`: emergency_fund · `reward_value`: 6000 · `probability`: 80

**3. Learning objective:** experience a real (if moderate) market drawdown, and see the emergency fund choice pay off one month before it's tested directly.
**4. Financial concepts:** market volatility; sequencing risk; liquidity as insurance against the next shock (setting up month 6).
**5. Expected trade-offs:** the correction hits stock-heavy players harder — a direct, felt consequence of the allocation made back in month 1. The choice is near-breakeven (-₹200 EV) by design: it's framed as "forced savings with a small match," not a gamble — the real payoff is structural (more liquidity), which the score's liquidity component (ADR-008, 15% weight) rewards directly, and which month 6 validates narratively.
**6. Difficulty:** Medium.
**7. Event category:** Market fluctuation (mandatory, admin-designed per ADR-009) / Investment opportunity (choice).
**8. Balance justification:** -8% is meaningfully felt without being catastrophic (compare to the automatic engine's own -15%…+20% stock volatility range) — this is a *designed* dip, not a duplicate of the automatic one, deliberately smaller so month 10's crash reads as the bigger, later test.

---

## Month 6 — Medical Scare

**1. Mandatory event**
`event_name`: "Medical Emergency" · `event_type`: fixed · `impact_target`: cash · `value`: -15000 · `description`: "An unexpected hospital visit requires immediate payment."

**2. Optional choice**
`name`: "Health Insurance Enrollment" · `cost`: 4000 · `risk_type`: medium · `reward_type`: cash · `reward_value`: 12000 · `probability`: 50

**3. Learning objective:** feel the direct, immediate value of liquidity (or its absence) built up through months 1 and 5, and weigh insurance as a hedge against exactly this kind of shock.
**4. Financial concepts:** emergency preparedness; the safety-net mechanic (emergency fund → auto-loan cascade, already in `monthly_processor`); insurance as a probabilistic hedge.
**5. Expected trade-offs:** this is the month where under-preparedness has consequences — a player with a thin emergency fund gets pushed toward the engine's existing auto-loan mechanism (12%/month interest, per `constants.py`) and a discipline-score hit, while a prepared player absorbs it cleanly. The insurance choice is positive-EV (+₹2,000): a deliberate reward for players who engage with risk-protection thinking, mirroring the score's risk-protection component (ADR-008).
**6. Difficulty:** Hard.
**7. Event category:** Financial emergency — PRD §6's flagship category, and the month's central teaching moment.
**8. Balance justification:** ₹15,000 sits at the "severe" end of the automatic engine's own emergency range (₹15,000–₹25,000, per `event_engine.py`'s severity tiers) — large enough to matter against a ₹1,00,000 salary, not large enough to be unrecoverable in a single month for anyone who saved.

---

## Month 7 — Career Crossroads

**1. Mandatory event**
`event_name`: "Team Outing" · `event_type`: fixed · `impact_target`: cash · `value`: -2000 · `description`: "A work social event carries a modest but expected cost."

**2. Optional choice**
`name`: "Apply for Internal Promotion" · `cost`: 2000 · `risk_type`: high · `reward_type`: cash · `reward_value`: 25000 · `probability`: 40

**3. Learning objective:** weigh a genuine career risk — a real chance of a large payoff against a real chance of nothing but the prep cost.
**4. Financial concepts:** career capital as an investment; variance vs. expected value; risk tolerance as a personal (not just numeric) decision.
**5. Expected trade-offs:** this is the highest-variance choice in the pack — 60% of players who try it get nothing back for their ₹2,000, 40% get a substantial ₹25,000 bump. High positive EV (+₹8,000) rewards the average risk-taker, but the *spread* is the real lesson: expected value isn't the same as a guaranteed outcome.
**6. Difficulty:** Medium.
**7. Event category:** Expense (mandatory) / Investment opportunity (choice) — PRD §6.
**8. Balance justification:** the small mandatory cost keeps this month light so the choice's variance is the clear focus; ₹25,000 reward is deliberately the single largest choice payoff in the pack, reserved for the single highest-risk choice, keeping risk and reward visibly correlated across the set rather than arbitrary.

---

## Month 8 — Sector Rally

**1. Mandatory event**
`event_name`: "Sector Rally" · `event_type`: percentage · `impact_target`: stocks · `value`: 12 · `description`: "A strong earnings season lifts stock valuations broadly. Every player faces the identical move this month (ADR-009)."

**2. Optional choice**
`name`: "Gold Accumulation Plan" · `cost`: 6000 · `risk_type`: medium · `reward_type`: gold · `reward_value`: 7500 · `probability`: 65

**3. Learning objective:** experience a designed reward for having stayed invested through month 5's correction, and consider diversification even during a rally.
**4. Financial concepts:** riding out volatility; diversification as risk management rather than pure return-maximization.
**5. Expected trade-offs:** the rally directly rewards players who didn't panic-sell in month 5 — a felt consequence of an earlier decision, not a new one. The gold choice is mildly negative-EV (-₹1,125): diversifying into gold during a stock rally is *not* the highest-return move, and the choice is priced that way on purpose — it teaches that diversification's value is risk reduction, not return-chasing.
**6. Difficulty:** Medium.
**7. Event category:** Market fluctuation (mandatory, admin-designed) / Investment opportunity (choice).
**8. Balance justification:** +12% is a deliberate, felt positive counterweight to month 5's -8%, keeping the market arc from reading as relentlessly negative — the score's net-worth component (40% weight, ADR-008) needs real upside moments too, not just tests.

---

## Month 9 — Family Ties

**1. Mandatory event**
`event_name`: "Family Gathering Contribution" · `event_type`: fixed · `impact_target`: cash · `value`: -3000 · `description`: "A family gathering carries an expected contribution."

**2. Optional choice**
`name`: "Community Investment Circle" · `cost`: 5000 · `risk_type`: medium · `reward_type`: cash · `reward_value`: 9000 · `probability`: 55

**3. Learning objective:** connect social/family obligations (already modeled by the existing relative-help/trust mechanic) to a broader theme of community and pooled financial decisions.
**4. Financial concepts:** social capital as a financial asset (PRD §4's existing relative-help mechanic); informal/pooled investment vehicles and their uncertainty.
**5. Expected trade-offs:** the mandatory cost reinforces that social obligations are a recurring, real budget line, not a one-off — echoing the existing relative-help decisions players make independently each month. The choice is essentially breakeven (-₹50 EV): deliberately neutral, so the decision hinges on risk appetite rather than an obvious "correct" answer.
**6. Difficulty:** Medium.
**7. Event category:** Social responsibility — PRD §6.
**8. Balance justification:** ₹3,000 matches the scale of the automatic engine's own social-responsibility events (₹2,000–₹5,000 range in `event_engine.py`), so this admin event reads as consistent with the game's established social-cost baseline rather than an outlier.

---

## Month 10 — Stress Test

**1. Mandatory event**
`event_name`: "Market Stress Test" · `event_type`: percentage · `impact_target`: stocks · `value`: -15 · `description`: "A sharp downturn tests every portfolio at once. Every player faces the identical move this month (ADR-009)."

**2. Optional choice**
`name`: "Defensive Rebalancing Seminar" · `cost`: 3000 · `risk_type`: low · `reward_type`: emergency_fund · `reward_value`: 5500 · `probability`: 70

**3. Learning objective:** the pack's central "stress test" — see directly how liquidity, discipline, and risk protection (not just raw stock returns) determine who comes through a downturn intact, which is the entire premise of ADR-008's composite score over net-worth-only ranking.
**4. Financial concepts:** portfolio stress-testing; the value of the emergency-fund/liquidity score component under real pressure; defensive positioning.
**5. Expected trade-offs:** this is the month where the composite Financial Health Score (PRD §7) diverges hardest from a naive net-worth ranking — a heavily-leveraged, all-stocks player takes a large net-worth hit and a discipline hit if it forces a cash crisis, while a diversified, liquid player barely feels it. The choice is modestly positive-EV (+₹850) and reinforces liquidity right when it matters most.
**6. Difficulty:** Hard.
**7. Event category:** Market fluctuation (mandatory, admin-designed) / Investment opportunity (choice).
**8. Balance justification:** -15% is the largest single designed market move in the pack — intentionally the pack's "final exam" for risk management, timed late enough (month 10 of 12) that it tests accumulated decisions rather than early inexperience, but early enough (2 months before the end) that recovery and course-correction are still possible.

---

## Month 11 — Settling Accounts

**1. Mandatory event**
`event_name`: "Tax Settlement" · `event_type`: fixed · `impact_target`: cash · `value`: -5000 · `description`: "Annual tax obligations come due."

**2. Optional choice**
`name`: "Tax-Saving Investment" · `cost`: 8000 · `risk_type`: medium · `reward_type`: stocks · `reward_value`: 10500 · `probability`: 60

**3. Learning objective:** plan for a known, predictable future obligation (unlike the game's random emergencies) and evaluate a tax-advantaged investment vehicle on its own terms.
**4. Financial concepts:** obligation planning for known future costs; tax-advantaged investing; the difference between a random risk and a scheduled one.
**5. Expected trade-offs:** the mandatory cost is entirely predictable — a different kind of financial-planning lesson than the pack's random emergencies (players who kept a cash buffer for exactly this won't be surprised). The choice is mildly negative-EV standalone (-₹1,700), reflecting that tax-saving vehicles are usually justified by the tax benefit itself (outside this model's scope) rather than by raw pre-tax expected return — noted here so the number isn't mistaken for a design error.
**6. Difficulty:** Medium.
**7. Event category:** Expense (mandatory) / Investment opportunity (choice) — PRD §6.
**8. Balance justification:** a predictable, schedulable cost this late in the game rewards players who've been tracking their trajectory, distinguishing "planning for the knowable" from "handling the random" as two separate skills the game tests.

---

## Month 12 — Closing the Year

**1. Mandatory event**
`event_name`: "Year-End Performance Bonus" · `event_type`: fixed · `impact_target`: cash · `value`: 10000 · `description`: "A full year of consistent work is rewarded with a year-end bonus."

**2. Optional choice**
`name`: "Charitable Giving / Legacy Contribution" · `cost`: 5000 · `risk_type`: low · `reward_type`: cash · `reward_value`: 5500 · `probability`: 50

**3. Learning objective:** close the 12-month arc on a values-based note — not every financial decision should be judged purely by expected value, and the game's own scoring (ADR-008) is explicitly designed to resist last-round score-gaming.
**4. Financial concepts:** values-aligned spending; the limits of pure EV-optimization as a life philosophy; discipline as a trait measured across the whole game, not the final round.
**5. Expected trade-offs:** the bonus is a clean, positive close after month 10's stress test. The final choice is deliberately negative-EV (-₹2,250) and low-stakes — it cannot meaningfully move a player's rank (ADR-008's components are round-averages, not final-round snapshots, exactly so a last-minute flourish here "moves the score marginally, not decisively," per the ADR's own anti-gaming design), so it's safe to frame purely as a values question rather than a strategic one.
**6. Difficulty:** Easy.
**7. Event category:** Windfall (mandatory) / Social responsibility in spirit, structured as an investment-opportunity choice for schema purposes — PRD §6.
**8. Balance justification:** intentionally the lowest-stakes choice in the pack and explicitly non-decisive by design (per ADR-008), so the game's last decision teaches a values lesson instead of being one more optimization problem.

---

## Balance Summary

| Month | Mandatory event Δ | Choice cost | Choice EV | Difficulty |
|---|---|---|---|---|
| 2 | -₹1,500 (cash) | ₹8,000 | **+₹6,000** | Easy |
| 3 | -₹1,200 (expense) | ₹5,000 | **-₹2,300** | Easy |
| 4 | -₹2,000 (expense) | ₹3,000 | **+₹900** | Easy–Medium |
| 5 | -8% stocks | ₹5,000 | **-₹200** | Medium |
| 6 | -₹15,000 (cash) | ₹4,000 | **+₹2,000** | Hard |
| 7 | -₹2,000 (cash) | ₹2,000 | **+₹8,000** | Medium |
| 8 | +12% stocks | ₹6,000 | **-₹1,125** | Medium |
| 9 | -₹3,000 (cash) | ₹5,000 | **-₹50** | Medium |
| 10 | -15% stocks | ₹3,000 | **+₹850** | Hard |
| 11 | -₹5,000 (cash) | ₹8,000 | **-₹1,700** | Medium |
| 12 | +₹10,000 (cash) | ₹5,000 | **-₹2,250** | Easy |

**Balance rationale for the set as a whole:**
- **Mix of favorable and unfavorable choices (7 positive-EV-adjacent, 4 negative-EV):** a content pack where every choice is profitable teaches "always say yes." Four deliberately negative-EV choices (months 3, 8, 11, 12) exist specifically so declining is sometimes the financially correct answer — this mirrors PRD §7's own point about the composite score rewarding judgment, not just participation.
- **Market beats spaced, not constant:** only 3 of 11 months carry an admin-designed market-percentage event (5, 8, 10), each distinct in size and direction (-8%, +12%, -15%), forming a legible arc (dip → recovery → stress test) rather than noise layered on the engine's own automatic monthly market movement.
- **Difficulty ramps toward the middle-to-late game, not linearly:** month 6 (medical) and month 10 (stress test) are the two "Hard" moments, positioned so players have had time to build (or fail to build) the buffers that determine how those months land — this is deliberate pacing, not an oversight.
- **Reward magnitudes stay within the existing engine's established scale:** every mandatory-event value and choice reward sits inside the range already established by the automatic engine's own event categories in `event_engine.py`/`constants.py` (minor ₹1,200–4,000, moderate ₹5,000–15,000, severe up to ₹25,000; stock moves within or near the -15%…+20% automatic volatility band) — nothing in this pack introduces a magnitude the existing economy hasn't already established as normal.
- **Supports PRD's stated testing goals directly:** financial planning (months 4, 11), risk management (months 5, 8, 10), investment strategy (months 2, 3, 7, 8, 11), emergency handling (month 6), and decision-making under uncertainty (every optional choice, by construction — every one is probabilistic).

---

*End of Version 1 Content Pack. 11 months of admin-authored content (months 2–12), ready to enter through the existing `/event` and `/choice-admin` admin endpoints. No code, business rules, or architecture changed in producing this document.*
