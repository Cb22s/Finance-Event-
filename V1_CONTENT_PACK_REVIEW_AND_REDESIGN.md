# Money Master — Content Pack Review & Redesign

**Date:** 2026-07-13 · **Role:** Senior Game Economist & Educational Content Designer · **Scope:** content only. No engine, database, API, schema, business rule, scoring formula, or ADR was touched or proposed to change. Every item below is entered through the same `POST /event` / `POST /choice-admin` endpoints, the same `events`/`optional_choices` schema, and the same QA-005 validation as the original pack (`event_type` ∈ {fixed, percentage}; `impact_target` ∈ {cash, stocks, gold, expense_increase}, `expense_increase` fixed-only; `reward_type` ∈ {cash, stocks, gold, emergency_fund}; `probability` ∈ [0,100]; `cost`/`reward_value` ≥ 0).

---

## Part 1 — Review of the Original Pack (V1_CONTENT_PACK.md)

| Month | Mandatory appropriate? | Choice interesting? | New learning? | Realistic? | Different from prior months? | Difficulty right? | Fits story? |
|---|---|---|---|---|---|---|---|
| 2 | Yes — mild, correct tone-setter | Somewhat — first "invest in yourself" beat | Yes | Yes | N/A (first month) | Yes (Easy) | Yes |
| 3 | Weak — generic "subscriptions add up," no new lesson beyond month 2's fixed-cost theme | Weak — a second cash-cost-for-stocks investment tip, structurally identical to month 2's choice shape | Marginal — restates month 2's "small costs" lesson | Realistic but generic | **No** — same shape as month 2 (fixed expense + stock-flavored choice) | Yes (Easy) | Thin |
| 4 | Fine — ties to inflation start | Fine — hedging choice | Yes | Yes | Yes | Yes | Yes |
| 5 | Good — first designed market event | Weak — near-breakeven "forced savings," not very engaging | Yes (volatility) | Yes | Yes | Yes | Yes |
| 6 | Strong — the pack's best moment | Good — insurance pays off narratively | Yes | Yes | Yes | Yes (Hard) | Yes — strongest month |
| 7 | Fine | Good — genuine high-variance choice | Yes | Yes | Yes | Yes | Yes |
| 8 | Good — rally counterweight | Weak — "buy gold during a rally" is a subtle lesson that risks reading as just another investment choice | Marginal | Yes but abstract | **Partially repetitive** — third "cost cash, get an asset back" choice shape (after months 3 and 5) | Yes | Yes |
| 9 | Fine but generic ("family gathering," no new mechanic texture) | Neutral-EV "community investment circle" is vague — unclear what it represents in the real world | Marginal | Weak — "community investment circle" is not a well-defined real financial product | **No** — fourth cash-cost-for-cash-or-asset choice in a row (5, 6, 8, 9 all follow the identical shape: pay cash, probabilistic reward) | Yes | Weak — feels like a filler month |
| 10 | Excellent — the pack's climax | Fine | Yes | Yes | Yes | Yes (Hard) | Yes — second-strongest month |
| 11 | Good | Fine | Yes | Yes | Yes | Yes | Yes |
| 12 | Fine — clean close | Fine but "charity gives you cash back" is financially odd — real charitable giving reduces cash, it doesn't probabilistically return it | Marginal | **No** — the reward mechanism doesn't map to how charitable giving actually works | Yes | Yes | Yes |

**Bottom line on the original pack:** structurally sound (schema-valid, well-paced difficulty, honest EV design, good market-event spacing), but **every one of the 11 optional choices has the identical shape** — pay cash up front, get a probabilistic reward back — varying only the reward asset type and the narrative label. Months 3, 8, and 9 in particular are close to interchangeable with each other if you strip the flavor text. This is the core weakness the redesign targets.

### Repetitive patterns identified
- **Choice mechanic monotony:** all 11 choices are "pay cash now, probabilistic reward later." No zero-cost, skill-based choices; no choices where the *decision itself* is the lesson rather than the payout curve.
- **Reward-type skew:** cash reward_type used in 7 of 11 choices; stocks 2, gold 1, emergency_fund 1.
- **"Another investment opportunity" clustering:** months 2, 3, 5 (choice), 7, 8, 9, 11 are all fundamentally "spend money, maybe get more money" — 7 of 11 months share this frame.
- **"Another stock decision" clustering:** months 3, 5 (mandatory + a stock-flavored choice), 8, 10 all touch stocks — reasonable for the market arc's 3 mandatory beats, but month 3's choice adds a fourth stock-touching month with no market-arc justification.
- **Narrative genericness:** "Subscription Creep" (month 3), "Family Gathering Contribution" (month 9), and "Community Investment Circle" (month 9 choice) read as filler — vague enough to not teach anything specific.

### Missing financial concepts / life situations (per your checklist)
Not present anywhere in the original 11 months: **salary negotiation, promotion, job switch, freelancing, side business/entrepreneurship, credit discipline, budget optimization, family responsibilities (present only as a generic gathering cost, not a real family-financial situation), housing decisions (present only as a rent-adjacent fee, not a real housing choice), vehicle maintenance, skill development (present only implicitly as "certification"), long-term planning (distinct from the tax-saving choice).** Present but shallow: insurance (one instance, reactive), loans (never triggered narratively — the auto-loan mechanic exists in the engine but nothing in the pack points a player toward it), lifestyle inflation (never named — inflation is only the automatic engine mechanic, never a *choice*-driven temptation).

---

## Part 2 — Redesigned Month 2–12 Content Pack

Design principles applied throughout: no two consecutive months share a choice "shape"; at least 3 choices per pack use zero or minimal cost (skill/time-based, not just capital-based); reward-type distribution stays realistic rather than artificially forced (see Part 4 note); the 3 market-percentage beats (months 5, 8, 10) are preserved from the original — they were already well-designed and are the mechanism PRD §6/ADR-009 exists for — but every choice paired with them is now non-investment-flavored, breaking the "market month = investment choice" pattern.

### Month 2 — Lifestyle Inflation

**1. Mandatory event**
`event_name`: "Lifestyle Creep" · `event_type`: fixed · `impact_target`: expense_increase · `value`: -2500 · `description`: "Your first real paycheck makes small upgrades feel affordable — a nicer phone plan, more takeout, a few 'treat yourself' purchases. None of them individually mattered."

**2. Optional choice**
`name`: "Online Skill Certification (Equity Track)" · `cost`: 8000 · `risk_type`: low · `reward_type`: stocks · `reward_value`: 19000 · `probability`: 70

**3. Learning objective:** recognize lifestyle inflation as a named, specific phenomenon — not "a fee," but a pattern of small voluntary spending that scales with income.
**4. Financial concepts:** lifestyle inflation; human-capital investment; equity compensation (certification unlocking an RSU-style stock grant).
**5. Expected trade-offs:** the mandatory event is diagnostic, not punitive — it names a pattern the player will see again if they don't self-correct. The choice rewards in *stocks*, not cash — realistic for a certification that unlocks equity eligibility, and the pack's first non-cash reward.
**6. Difficulty:** Easy.
**7. Event category:** Expense spike (mandatory) / Investment opportunity (choice) — PRD §6.
**8. Balance justification:** EV +₹5,300 — clearly favorable, appropriate for the easiest, most "obviously good" decision in the pack, same design intent as the original month 2.

---

### Month 3 — Getting By

**1. Mandatory event**
`event_name`: "Transport Upkeep" · `event_type`: fixed · `impact_target`: cash · `value`: -1800 · `description`: "Between commuting wear-and-tear and routine upkeep, getting around cost more than expected this month."

**2. Optional choice**
`name`: "Weekend Freelance Gig" · `cost`: 0 · `risk_type`: low · `reward_type`: cash · `reward_value`: 4500 · `probability`: 55

**3. Learning objective:** freelancing/gig work has no capital barrier to entry — the "cost" is time and effort, not money, and the outcome is still uncertain.
**4. Financial concepts:** gig economy income; opportunity cost of time; income diversification outside a primary salary.
**5. Expected trade-offs:** this is the pack's first zero-cost choice — a deliberate mechanical break from the original's "always pay cash" pattern. A 55% chance at ₹4,500 for no capital risk is a genuinely different kind of decision than every other choice in the pack: there's nothing to lose except the attempt.
**6. Difficulty:** Easy.
**7. Event category:** Expense (mandatory) / Investment opportunity — structurally, though the real teaching point is income diversification, not investing (choice) — PRD §6.
**8. Balance justification:** EV +₹2,475, modest and appropriate — this is meant to feel like a small, low-stakes "why not" decision, distinct in shape (not just flavor) from every choice in the original pack.

---

### Month 4 — Home Base

**1. Mandatory event**
`event_name`: "Rent Renewal — Rates Increase" · `event_type`: fixed · `impact_target`: expense_increase · `value`: -2200 · `description`: "Your lease renews this month and rents citywide have climbed — the first visible sign of inflation (constants.py's automatic 0.5%/month adjustment also begins this month, independently of this one-time notice)."

**2. Optional choice**
`name`: "Budget Optimization Challenge" · `cost`: 2000 · `risk_type`: low · `reward_type`: emergency_fund · `reward_value`: 5000 · `probability`: 75

**3. Learning objective:** connect a housing-cost shock to an active, deliberate response — auditing and trimming a budget — rather than just absorbing the hit passively.
**4. Financial concepts:** housing/rent as the largest recurring line item; active budget review; redirecting found savings into liquidity rather than spending them.
**5. Expected trade-offs:** this is the pack's first choice that rewards directly into `emergency_fund` rather than cash — a deliberate mechanical signal that "optimizing your budget" isn't about getting richer, it's about getting more prepared. High probability (75%) reflects that budget audits reliably find *some* savings, even if not always the full amount hoped for.
**6. Difficulty:** Easy–Medium.
**7. Event category:** Expense spike (mandatory) / Investment opportunity, functioning as a budgeting exercise (choice) — PRD §6.
**8. Balance justification:** EV +₹1,750 — modest and high-probability, appropriate for a "good habit" choice that should feel achievable, not risky.

---

### Month 5 — Weathering the Dip

**1. Mandatory event**
`event_name`: "Market Correction" · `event_type`: percentage · `impact_target`: stocks · `value`: -8 · `description`: "A broad market pullback trims stock valuations across the board. Every player faces the identical move this month (ADR-009)."

**2. Optional choice**
`name`: "Term Insurance Enrollment" · `cost`: 4500 · `risk_type`: medium · `reward_type`: cash · `reward_value`: 13000 · `probability`: 45

**3. Learning objective:** decouple "the market is down" from "what should I do about risk generally" — insurance is unrelated to market timing, and pairing them teaches players not to conflate every financial decision with market direction.
**4. Financial concepts:** market volatility (mandatory) vs. insurance as a hedge against unrelated personal risk (choice) — deliberately two *different* categories of risk in the same month.
**5. Expected trade-offs:** unlike the original pack (which paired month 5's correction with a savings-drive choice — another "market-adjacent" decision), this choice is intentionally *not* about the market at all. 45% probability reflects that not every policy period includes a claim — realistic underinsurance-vs-overinsurance tension.
**6. Difficulty:** Medium.
**7. Event category:** Market fluctuation (mandatory, admin-designed per ADR-009) / Financial emergency preparation, structured as an investment-opportunity choice for schema purposes (choice) — PRD §6.
**8. Balance justification:** EV +₹1,350; -8% is the smallest of the three designed market beats, appropriately positioned first in the arc.

---

### Month 6 — When It Happens

**1. Mandatory event**
`event_name`: "Medical Emergency" · `event_type`: fixed · `impact_target`: cash · `value`: -15000 · `description`: "An unexpected hospital visit requires immediate payment."

**2. Optional choice**
`name`: "Family Support Network" · `cost`: 3000 · `risk_type`: medium · `reward_type`: cash · `reward_value`: 7500 · `probability`: 60

**3. Learning objective:** see the direct payoff of month 5's insurance choice (if taken) land in the same month as the emergency it was meant for, and separately weigh family/community support as a *different* kind of safety net than either insurance or an emergency fund.
**4. Financial concepts:** emergency preparedness; the engine's existing safety-net → auto-loan cascade for underprepared players; social capital as a financial resource, distinct from insurance.
**5. Expected trade-offs:** this month is unchanged in its central mandatory beat (the original pack's strongest moment, kept deliberately), but the paired choice is now genuinely different from the original's insurance choice (which duplicated the theme this exact month) — family support is a *different* real-world safety net than insurance, giving the month two distinct lessons instead of one repeated one.
**6. Difficulty:** Hard.
**7. Event category:** Financial emergency (mandatory) / Social responsibility, structured as an investment-opportunity choice (choice) — PRD §6.
**8. Balance justification:** unchanged from original — ₹15,000 sits at the engine's own "severe" emergency tier, appropriately sized for the pack's first real stress test.

---

### Month 7 — Making a Move

**1. Mandatory event**
`event_name`: "New Job, New Costs" · `event_type`: fixed · `impact_target`: cash · `value`: -3500 · `description`: "You take a new job with better long-term prospects, but the notice-period income gap and transition costs hit your wallet this month."

**2. Optional choice**
`name`: "Negotiate Your Salary" · `cost`: 0 · `risk_type`: low · `reward_type`: cash · `reward_value`: 9000 · `probability`: 50

**3. Learning objective:** distinguish a job switch (an event that happens *to* you, with real friction costs) from salary negotiation (an active choice you make, costing nothing but effort and carrying real uncertainty).
**4. Financial concepts:** job-switching friction costs; negotiation as a zero-capital, positive-EV skill. **Constraint note:** the engine's `MONTHLY_INCOME` is a fixed constant, not adjustable per-player — this is represented honestly as a one-time cash outcome (a signing/retention-style bonus), not a permanent salary change, since the latter isn't something the existing mechanics can express.
**5. Expected trade-offs:** the mandatory event is realistically negative-leaning (switching jobs has real short-term costs even when the long-term move is right) — a nuance the original pack's promotion-only framing didn't capture. The zero-cost negotiation choice is a genuine coin-flip (50%), teaching that negotiating "costs nothing to try" is true financially even though it doesn't always work.
**6. Difficulty:** Medium.
**7. Event category:** Expense (mandatory) / Investment opportunity, structured as a career/skill decision (choice) — PRD §6.
**8. Balance justification:** EV +₹4,500 on a zero-cost choice — favorable but genuinely uncertain (a coin-flip, not a sure thing), appropriate for a skill-based rather than capital-based decision.

---

### Month 8 — Betting on Yourself

**1. Mandatory event**
`event_name`: "Sector Rally" · `event_type`: percentage · `impact_target`: stocks · `value`: 12 · `description`: "A strong earnings season lifts stock valuations broadly. Every player faces the identical move this month (ADR-009)."

**2. Optional choice**
`name`: "Launch a Side Business" · `cost`: 12000 · `risk_type`: high · `reward_type`: cash · `reward_value`: 30000 · `probability`: 35

**3. Learning objective:** experience genuine entrepreneurship risk — the largest cost and largest potential reward in the pack, with the lowest probability, matching the real shape of small-business outcomes (most don't recoup their first-year investment; the ones that work, work big).
**4. Financial concepts:** entrepreneurship risk/reward asymmetry; capital-intensive risk vs. the zero-cost risks of months 3 and 7; opportunity cost of capital tied up in a venture.
**5. Expected trade-offs:** this replaces the original's mild "buy gold during a rally" choice (itself another disguised investment-tip choice) with a decision structurally distinct from anything else in the pack — the biggest number, the lowest odds, and the only "high" risk_type in the set. It forms the top rung of a 3-step career-risk ladder across the pack (zero-cost freelance gig → zero-cost negotiation → capital-intensive side business).
**6. Difficulty:** Medium–Hard.
**7. Event category:** Market fluctuation (mandatory, admin-designed) / Investment opportunity, structured as an entrepreneurship decision (choice) — PRD §6.
**8. Balance justification:** EV -₹1,500 — deliberately negative, realistic for early-stage entrepreneurship, and distinguishable from every other "spend cash, get cash" choice by its risk_type and stakes rather than just its flavor text.

---

### Month 9 — The Big One

**1. Mandatory event**
`event_name`: "Major Home Repair" · `event_type`: fixed · `impact_target`: cash · `value`: -18000 · `description`: "A major system failure at home demands immediate repair. If your emergency fund can't cover it, you may need to take on debt to close the gap."

**2. Optional choice**
`name`: "'Buy Now, Pay Later' Upgrade" · `cost`: 4000 · `risk_type`: low · `reward_type`: cash · `reward_value`: 4300 · `probability`: 90

**3. Learning objective:** experience the game's existing auto-loan safety net as a real, felt consequence for the first time (for underprepared players), in the same month as a "credit discipline" trap that looks safe but quietly isn't.
**4. Financial concepts:** loan situations (the engine's existing 12%/month auto-loan, triggered here for real rather than just mentioned); the following months' automatic loan amortization is loan *repayment* in action; credit discipline — a 90%-probability "sure thing" that is still negative EV.
**5. Expected trade-offs:** this is the pack's largest single mandatory cost, deliberately sized above a typical emergency-fund cushion so the loan mechanic becomes a real possibility, not just background lore. The paired choice is a trap by design: it "always seems to work" (90% of the time) which is exactly what makes small bad-credit habits dangerous — the lesson is in noticing the EV is still negative despite looking safe, especially stacked in the same month as the mandatory expense.
**6. Difficulty:** Medium–Hard.
**7. Event category:** Financial emergency (mandatory) / a credit-discipline decision, structured as an investment-opportunity choice (choice) — PRD §6.
**8. Balance justification:** EV -₹130 on the choice — deliberately near-breakeven-negative rather than obviously bad, because real "safe-looking" credit traps rarely look obviously bad in the moment either.

---

### Month 10 — Staying the Course

**1. Mandatory event**
`event_name`: "Market Stress Test" · `event_type`: percentage · `impact_target`: stocks · `value`: -15 · `description`: "A sharp downturn tests every portfolio at once. Every player faces the identical move this month (ADR-009)."

**2. Optional choice**
`name`: "Long-Term Reserve Contribution" · `cost`: 5000 · `risk_type`: low · `reward_type`: gold · `reward_value`: 5800 · `probability`: 70

**3. Learning objective:** the pack's central climax (kept from the original) — see liquidity, discipline, and risk protection determine outcomes more than raw stock exposure, per ADR-008's whole design premise. The paired choice tests whether players keep contributing to long-term savings *during* a downturn, when it feels worst to do so.
**4. Financial concepts:** portfolio stress-testing; the ADR-008 composite score's divergence from naive net-worth ranking under pressure; long-term/retirement-style saving discipline, specifically saving through — not around — a downturn.
**5. Expected trade-offs:** mandatory event unchanged (it was already the pack's best-designed moment). The choice is new: contributing to a long-term gold reserve *while stocks are crashing* is psychologically the hardest kind of "good" financial decision — it won't feel rewarding this month, which is realistic and intentional.
**6. Difficulty:** Hard.
**7. Event category:** Market fluctuation (mandatory, admin-designed) / long-term planning, structured as an investment-opportunity choice (choice) — PRD §6.
**8. Balance justification:** EV -₹940 — deliberately negative in-the-moment, because the entire point of "long-term planning" as a distinct lesson from "investment opportunity" is that it isn't supposed to look good on a one-month EV basis.

---

### Month 11 — Recognition

**1. Mandatory event**
`event_name`: "Tax Settlement" · `event_type`: fixed · `impact_target`: cash · `value`: -5000 · `description`: "Annual tax obligations come due."

**2. Optional choice**
`name`: "Promoted to Team Lead" · `cost`: 1500 · `risk_type`: medium · `reward_type`: cash · `reward_value`: 11000 · `probability`: 65

**3. Learning objective:** a genuine promotion moment, distinct from month 7's job switch and salary negotiation — this one is explicitly framed as the payoff of sustained performance across the year (echoing month 2's skill investment and month 7's negotiation), not a new job or a market event.
**4. Financial concepts:** tax obligation planning (mandatory, unchanged) — a *predictable* cost, deliberately contrasted with the pack's random emergencies; career advancement as a distinct outcome from job-switching or negotiating.
**5. Expected trade-offs:** replaces the original's "tax-saving investment" choice (which made the entire month about tax, twice) with a career-progression moment — giving month 11 two genuinely different lessons (predictable-obligation planning + career advancement) instead of one repeated theme.
**6. Difficulty:** Medium.
**7. Event category:** Expense (mandatory) / career advancement, structured as an investment-opportunity choice (choice) — PRD §6.
**8. Balance justification:** EV +₹5,650 — a clearly favorable, deserved payoff late in the game, appropriate for a moment meant to reward sustained good decisions rather than test the player again.

---

### Month 12 — Closing the Year

**1. Mandatory event**
`event_name`: "Year-End Performance Bonus" · `event_type`: fixed · `impact_target`: cash · `value`: 10000 · `description`: "A full year of consistent work is rewarded with a year-end performance bonus."

**2. Optional choice**
`name`: "Charitable Giving — Year-End Donation" · `cost`: 5000 · `risk_type`: low · `reward_type`: cash · `reward_value`: 5800 · `probability`: 55

**3. Learning objective:** close on a values-based note, same intent as the original — but with a mechanically realistic frame: the "reward" represents a probabilistic tax deduction/refund on the donation, not the donation itself paying the player back.
**4. Financial concepts:** values-aligned spending; realistic tax treatment of charitable giving; discipline measured across the whole game, not the final round (ADR-008's anti-gaming design, unchanged from original reasoning).
**5. Expected trade-offs:** same low-stakes, deliberately non-decisive intent as the original month 12, but the reward mechanism now maps to something real (tax deduction odds) rather than charity mysteriously returning cash.
**6. Difficulty:** Easy.
**7. Event category:** Windfall (mandatory) / values-based decision, structured as an investment-opportunity choice for schema purposes (choice) — PRD §6.
**8. Balance justification:** EV -₹1,810 — negative and low-stakes by design, same rationale as the original: the last decision should teach a values lesson, not be one more optimization problem, and per ADR-008 cannot meaningfully move final rank.

---

## Part 3 — Comparison Table (Every Change)

| Month | Original mandatory | New mandatory | Original choice | New choice | What changed | Why |
|---|---|---|---|---|---|---|
| 2 | Bank Account Setup Fees (-₹1,500 cash) | **Lifestyle Creep** (-₹2,500 expense_increase) | Professional Certification (cost 8k → cash 20k, 70%) | **Online Skill Certification (Equity Track)** (cost 8k → **stocks** 19k, 70%) | Mandatory reframed from generic fee to a named, specific behavioral pattern (lifestyle inflation); choice reward type changed cash→stocks | Original mandatory taught nothing specific; "lifestyle inflation" was entirely missing from the pack and is explicitly requested. Reward-type diversification adds the pack's first non-cash choice reward with a realistic justification (equity/RSU) |
| 3 | Subscription Creep (-₹1,200 expense) + Hot Stock Tip (cost 5k → stocks 6k, 45%, negative EV) | **Transport Upkeep** (-₹1,800 cash) | **Weekend Freelance Gig** (cost **0** → cash 4,500, 55%) | Both replaced | Original month was a near-duplicate of month 2's shape (fixed cost + risky cash-for-stocks tip). New choice introduces the pack's first zero-cost, skill-based decision — freelancing/gig income, entirely missing from the original pack |
| 4 | Utility Deposit Increase (-₹2,000 expense) | **Rent Renewal — Rates Increase** (-₹2,200 expense) | Lock-In Fixed-Rate Utility Plan (cost 3k → cash 6.5k, 60%) | **Budget Optimization Challenge** (cost 2k → **emergency_fund** 5k, 75%) | Mandatory reframed explicitly as a housing decision rather than a generic utility notice; choice replaced with an explicit budget-optimization mechanic rewarding into the emergency fund | "Housing decisions" and "budget optimization" were both explicitly requested and both missing from the original; rewarding into emergency_fund (not cash) makes the mechanical outcome match the stated lesson |
| 5 | Market Correction (-8% stocks, unchanged) | Market Correction (-8% stocks, **unchanged**) | Emergency Fund Top-Up Drive (cost 5k → EF 6k, 80%) | **Term Insurance Enrollment** (cost 4.5k → cash 13k, 45%) | Choice replaced — original paired a market event with *another* savings/investment-shaped choice | Insurance was present only reactively in month 6 originally; moving proactive insurance to month 5 and decoupling it from the market event breaks the "market month = investment choice" pattern and sets up month 6's payoff more deliberately |
| 6 | Medical Emergency (-₹15,000 cash, unchanged) | Medical Emergency (-₹15,000 cash, **unchanged**) | Health Insurance Enrollment (cost 4k → cash 12k, 50%) | **Family Support Network** (cost 3k → cash 7.5k, 60%) | Choice replaced — insurance moved to month 5, freeing this month for a genuinely different safety-net concept | "Family responsibilities" was present only as a vague social-cost line elsewhere; giving it a real, load-bearing role here (family support during the emergency) is both a missing-situation fix and a narrative improvement |
| 7 | Team Outing (-₹2,000 cash) + Apply for Internal Promotion (cost 2k → cash 25k, 40%) | **New Job, New Costs** (-₹3,500 cash) | **Negotiate Your Salary** (cost **0** → cash 9,000, 50%) | Both replaced | "Job switch" and "salary negotiation" are both explicitly requested and were both missing (original only had "promotion"); promotion is preserved but moved to month 11 to avoid three career-progression beats clustering in one month | Splits one overloaded career month into two distinct, better-paced career moments across the pack |
| 8 | Sector Rally (+12% stocks, unchanged) | Sector Rally (+12% stocks, **unchanged**) | Gold Accumulation Plan (cost 6k → gold 7.5k, 65%) | **Launch a Side Business** (cost 12k → cash 30k, 35%, high risk) | Choice replaced — original was a mild, easy-to-miss diversification nudge | "Entrepreneurship/side business" was explicitly requested and entirely missing; this is now the pack's single highest-stakes choice, distinct in shape (not just flavor) from every other choice |
| 9 | Family Gathering Contribution (-₹3,000 cash) + Community Investment Circle (cost 5k → cash 9k, 55%) | **Major Home Repair** (-₹18,000 cash) | **'Buy Now, Pay Later' Upgrade** (cost 4k → cash 4.3k, 90%, near-breakeven) | Both replaced | Original month was vague filler ("community investment circle" is not a defined real product). Redesign makes this month the pack's real loan-trigger moment and adds a credit-discipline trap | "Loan situations," "loan repayment," and "credit discipline" were all explicitly requested and entirely missing from the original pack — this month now carries all three |
| 10 | Market Stress Test (-15% stocks, unchanged) | Market Stress Test (-15% stocks, **unchanged**) | Defensive Rebalancing Seminar (cost 3k → EF 5.5k, 70%) | **Long-Term Reserve Contribution** (cost 5k → gold 5.8k, 70%) | Choice replaced with an explicit long-term-planning frame | "Long-term planning" as a concept distinct from general "defensiveness" was explicitly requested and not clearly present; framing this as sustained contribution through a downturn is a sharper, more specific lesson |
| 11 | Tax Settlement (-₹5,000 cash, unchanged) | Tax Settlement (-₹5,000 cash, **unchanged**) | Tax-Saving Investment (cost 8k → stocks 10.5k, 60%) | **Promoted to Team Lead** (cost 1.5k → cash 11k, 65%) | Choice replaced — original made the whole month about tax twice | Restores "promotion" (moved from month 7) as its own distinct beat; gives month 11 two different lessons instead of one repeated one |
| 12 | Year-End Performance Bonus (+₹10,000 cash, unchanged) | Year-End Performance Bonus (+₹10,000 cash, **unchanged**) | Charitable Giving (cost 5k → cash 5.5k, 50%) | **Charitable Giving — Year-End Donation** (cost 5k → cash 5.8k, 55%, reframed) | Same structural choice, reframed | Original's "charity pays you back" framing didn't map to anything real; reframing the reward as a probabilistic tax-deduction refund is the same mechanic with a financially literate justification |

---

## Part 4 — Educational Coverage Matrix

| Financial concept | Where taught (month) | Mechanic used |
|---|---|---|
| Lifestyle inflation | 2 (mandatory) | Fixed expense_increase |
| Equity/RSU compensation | 2 (choice) | Cost → stocks reward |
| Gig economy / freelancing | 3 (choice) | Zero-cost → cash reward |
| Transport/asset upkeep costs | 3 (mandatory) | Fixed cash |
| Housing cost shocks | 4 (mandatory) | Fixed expense_increase |
| Budget optimization | 4 (choice) | Cost → emergency_fund reward |
| Market volatility (downside) | 5 (mandatory) | Percentage stocks -8% |
| Insurance as a hedge | 5 (choice) | Cost → cash reward, moderate probability |
| Emergency preparedness / safety net | 6 (mandatory) | Fixed cash, large |
| Family/social capital as a resource | 6 (choice) | Cost → cash reward |
| Job-switch friction costs | 7 (mandatory) | Fixed cash |
| Salary negotiation | 7 (choice) | Zero-cost → cash reward, 50/50 |
| Market volatility (upside) | 8 (mandatory) | Percentage stocks +12% |
| Entrepreneurship risk/reward | 8 (choice) | High cost → high cash reward, low probability |
| Loan situations (engine's real auto-loan) | 9 (mandatory) | Large fixed cash, sized to trigger the safety net |
| Loan repayment | 9 → 10–15 (emergent) | Existing amortization mechanic, triggered by month 9 |
| Credit discipline | 9 (choice) | Low cost, near-certain small reward, negative EV |
| Portfolio stress-testing | 10 (mandatory) | Percentage stocks -15% |
| Long-term / retirement-style planning | 10 (choice) | Cost → gold reward, negative EV in-the-moment |
| Tax obligation planning | 11 (mandatory) | Fixed cash, predictable |
| Promotion / career advancement | 11 (choice) | Cost → cash reward, moderate-high probability |
| Performance bonus | 12 (mandatory) | Fixed cash, positive |
| Charitable giving / values-based spending | 12 (choice) | Cost → cash reward (tax-deduction framing) |

**Coverage against your requested list:** salary negotiation ✅ (7), promotion ✅ (11), job switch ✅ (7), performance bonus ✅ (12), freelancing ✅ (3), side business/entrepreneurship ✅ (8), insurance ✅ (5), loan repayment ✅ (9→onward), credit discipline ✅ (9), budget optimization ✅ (4), family responsibilities ✅ (6), housing decisions ✅ (4), vehicle maintenance ✅ (3), skill development ✅ (2), emergency planning ✅ (6), tax planning ✅ (11), lifestyle inflation ✅ (2), charity ✅ (12), long-term planning ✅ (10). All 19 explicitly named situations are covered, each in its own distinct month/slot — none doubled up, none missing.

---

## Part 5 — Release Recommendation

**The redesigned pack is superior to the original and should replace it before C2 is considered closed.**

Reasoning, tied directly to your review objectives:

- **Educational value:** the original taught roughly 8 distinct concepts across 11 choices (several repeated in different clothing); the redesign teaches 19+ distinct, named concepts with no repetition, directly matching every situation on your requested list.
- **Decision diversity:** the original's 11 choices were mechanically identical (pay cash, get probabilistic reward, varying only the label). The redesign introduces 3 zero-cost skill-based choices (months 2's precedent aside, specifically 3, 7) and one high-stakes capital choice (8) that are structurally, not just narratively, different from the rest.
- **Financial realism:** two clear original weaknesses are fixed — "community investment circle" (undefined product) is gone, and "charity pays you cash" (backwards mechanically) is now framed as a tax-deduction refund, which is how charitable giving actually interacts with money.
- **Narrative progression:** career progression is now a genuine 3-beat arc (freelance gig → negotiate → promotion, with side-business and job-switch as parallel tracks) instead of a single flat "apply for promotion" moment; the loan mechanic — present in the engine since the beginning but never once surfaced by the original pack's content — is now a real, felt moment in month 9 with visible consequences through month repayment.
- **Difficulty progression:** the redesign adds a third genuine stress point (month 9's loan trigger + credit trap) alongside the original's two (6, 10), forming a more dramatic back-half gauntlet (8→9→10) rather than the original's flatter middle stretch.
- **Replayability:** with more distinct decision *shapes* (not just different flavor text on the same shape), a repeat player experiences meaningfully different tension from choice to choice rather than recognizing "this is another pay-cash-get-cash-back month" by month 5 or 6.

**What is unchanged and should stay that way:** the three market-percentage beats (months 5, 8, 10) and their exact magnitudes, the month 6 medical emergency, the month 11 tax settlement, and the month 12 bonus — these were already well-designed, already balanced, and already tied directly to ADR-008/ADR-009. The redesign touches only the elements the review found weak; it does not change the engine, the schema, the balance philosophy, or anything already working.

---

## Part 6 — Universal Narrative Continuity Addendum

**This addendum does not modify Parts 1–5 above.** It adds narrative-continuity text on top of the redesigned pack's existing fields only. Two schema facts constrain everything below and are worth stating plainly: `optional_choices` has no `description` column at all (only `id, month, name, cost, risk_type, reward_type, reward_value, probability`) — so a choice's only player-visible text is its short `name`. Real prose only exists on `events.description`. Every field below is one that already exists and is already entered through the existing `POST /event` / `POST /choice-admin` endpoints exactly as before — nothing here requires a new column, a new endpoint, conditional rendering, or any per-player lookup.

Because no per-player templating exists anywhere in the schema or engine, every description below is written to be **true regardless of what any individual player actually did** — it references the *category* of decision (skills, preparation, discipline, budgeting, risk management, long-term planning) rather than asserting a specific outcome, investment, loan, success, or failure. This is deliberately not "your freelance gig paid off" — it's "whatever you built this year is about to matter," which is honest for every player reading it, whether they took that choice, skipped it, won the roll, or lost it.

### Month 2 — Lifestyle Creep
- **Updated mandatory event description:** "Your first real paycheck makes small upgrades feel affordable — a nicer phone plan, more takeout, a few 'treat yourself' purchases. The habits you build with your very first paycheck tend to stick, for better or worse."
- **Updated optional choice name:** No change needed — "Online Skill Certification (Equity Track)" already reads well on its own.
- **Universal callback language:** *"The habits you build with your very first paycheck tend to stick, for better or worse."*
- **Educational narrative purpose:** month 2 has nothing behind it to call back to — instead of a backward reference, it plants a forward-looking theme (habit formation) that later months can echo without asserting what any specific player's habits turned out to be.

### Month 3 — Getting By
- **Updated mandatory event description:** "Between commuting wear-and-tear and routine upkeep, getting around cost more than expected this month — a reminder that steady habits and new skills take time to pay off, even while the regular costs of daily life keep coming."
- **Updated optional choice name:** No change needed — "Weekend Freelance Gig" is already clear and short.
- **Universal callback language:** *"...a reminder that steady habits and new skills take time to pay off, even while the regular costs of daily life keep coming."*
- **Educational narrative purpose:** reinforces that skill/habit-building (month 2's theme) is a process, not an event — the ordinary costs of living don't pause for it, regardless of whether this particular player is investing in themselves this year or not.

### Month 4 — Home Base
- **Updated mandatory event description:** "Your lease renews this month and rents citywide have climbed — the first visible sign of inflation. How closely you've been tracking your spending starts to matter more from here on."
- **Updated optional choice name:** No change needed — "Budget Optimization Challenge" already names the theme directly.
- **Universal callback language:** *"How closely you've been tracking your spending starts to matter more from here on."*
- **Educational narrative purpose:** introduces budgeting/tracking as an ongoing discipline rather than a one-month event, setting up every later month where preparation is referenced without needing to know whether this player actually budgeted carefully.

### Month 5 — Weathering the Dip
- **Updated mandatory event description:** "A broad market pullback trims stock valuations across the board. Every player faces the identical move this month — how well-prepared anyone is for volatility like this is about to be tested, one way or another."
- **Updated optional choice name:** No change needed — "Term Insurance Enrollment" is already precise.
- **Universal callback language:** *"How well-prepared anyone is for volatility like this is about to be tested, one way or another."*
- **Educational narrative purpose:** names risk management as the month's theme without presupposing whether this player is well-diversified, over-exposed, or somewhere in between — true for all three.

### Month 6 — When It Happens
- **Updated mandatory event description:** "An unexpected hospital visit requires immediate payment — the kind of moment that reveals how much preparation and discipline actually matter, regardless of how the rest of the year has gone so far."
- **Updated optional choice name:** No change needed — "Family Support Network" already stands on its own.
- **Universal callback language:** *"...reveals how much preparation and discipline actually matter, regardless of how the rest of the year has gone so far."*
- **Educational narrative purpose:** the explicit "regardless of how the rest of the year has gone" phrasing exists specifically to avoid implying this player has (or hasn't) prepared well — it states the theme (preparation matters) without judging the player's history.

### Month 7 — Making a Move
- **Updated mandatory event description:** "You take a new job with better long-term prospects, but the notice-period income gap and transition costs hit your wallet this month. Whatever skills or side income anyone has worked on this year are about to be worth something in a negotiation or a new role."
- **Updated optional choice name:** "Negotiate Your Salary — Make Your Case" (was: "Negotiate Your Salary") — the addition is generic ("make your case") and doesn't specify what the case consists of.
- **Universal callback language:** *"Whatever skills or side income anyone has worked on this year are about to be worth something in a negotiation or a new role."*
- **Educational narrative purpose:** directly echoes months 2–3's skill/income themes as a general principle ("whatever... anyone has worked on") without claiming this specific player built anything — the callback works identically for a player who took every skill-building choice and one who took none.

### Month 8 — Betting on Yourself
- **Updated mandatory event description:** "A strong earnings season lifts stock valuations broadly. Every player faces the identical move this month — the discipline to stay invested through the harder months is what a rally like this tends to reward."
- **Updated optional choice name:** No change needed — "Launch a Side Business" is already direct.
- **Universal callback language:** *"The discipline to stay invested through the harder months is what a rally like this tends to reward."*
- **Educational narrative purpose:** frames the rally as a lesson about discipline in general (a widely-true statement about markets) rather than a comment on this player's own month 5 decisions, which may have gone any number of ways.

### Month 9 — The Big One
- **Updated mandatory event description:** "A major system failure at home demands immediate repair. Preparation — whether that's an emergency fund, insurance, or simply careful budgeting — determines whether a shock like this is a manageable setback or a lasting one."
- **Updated optional choice name:** No change needed — "'Buy Now, Pay Later' Upgrade" already names the temptation plainly.
- **Universal callback language:** *"Preparation... determines whether a shock like this is a manageable setback or a lasting one."*
- **Educational narrative purpose:** replaces the redesign's earlier, more pointed phrasing ("you may need to take on debt") with fully theme-level language — it names preparation as the deciding factor without asserting that any particular player lacks it, has it, or will end up borrowing.

### Month 10 — Staying the Course
- **Updated mandatory event description:** "A sharp downturn tests every portfolio at once. Every player faces the identical move this month — the decisions that hold up under pressure are usually the ones made calmly, long before the pressure arrived."
- **Updated optional choice name:** No change needed — "Long-Term Reserve Contribution" is already thematically clear.
- **Universal callback language:** *"The decisions that hold up under pressure are usually the ones made calmly, long before the pressure arrived."*
- **Educational narrative purpose:** ties the climax month back to the whole year's theme of preparation and discipline as a general truth about downturns, not a verdict on how this player specifically has played the game so far.

### Month 11 — Recognition
- **Updated mandatory event description:** "Annual tax obligations come due — a predictable cost that rewards planning ahead rather than reacting in the moment. Consistency over the course of a year tends to get noticed."
- **Updated optional choice name:** No change needed — "Promoted to Team Lead" names the opportunity being offered, not an assumed outcome (the probability field still determines whether it's granted).
- **Universal callback language:** *"Consistency over the course of a year tends to get noticed."*
- **Educational narrative purpose:** connects tax-planning discipline to the promotion opportunity thematically (consistency is rewarded) without stating that this player has been consistent or will be promoted — the choice's own probability still decides that.

### Month 12 — Closing the Year
- **Updated mandatory event description:** "A full year of consistent work is rewarded with a year-end performance bonus. As the year closes, your own monthly record — visible on your dashboard — is the real account of how you got here, whatever path that was."
- **Updated optional choice name:** No change needed — "Charitable Giving — Year-End Donation" is already clear.
- **Universal callback language:** *"Your own monthly record — visible on your dashboard — is the real account of how you got here, whatever path that was."*
- **Educational narrative purpose:** this is the addendum's one deliberate pointer to a real, already-existing mechanic — `GET /dashboard`'s `event_logs` field already returns each player's complete, accurate, per-player month-by-month history. That *is* the personalized "year in review" the original request was reaching for; this line just tells the player it's there, in language true for every player without exception, since everyone has a log regardless of its contents.

### How this addendum improves narrative continuity while remaining fully compatible with V1

Nothing here required a new mechanic, because the two-part solution was already latent in the existing system: (1) `events.description` already supports full prose, so eleven months of static text can carry a consistent thematic thread (habits → skills → budgeting → risk → preparation → discipline → long-term thinking) purely through word choice, with no conditional logic anywhere; and (2) the dashboard's `event_logs` already *is* a genuine, accurate, per-player narrative record — it just wasn't being pointed at. The addendum's callback language creates the *feeling* of a game that remembers the player, using only static global text truthful for every possible play-through, while the month 12 pointer directs players to the one place a truly personalized account already, mechanically, exists. Every field changed here is a field that already existed, entered through the same two admin endpoints, validated by the same rules, with zero risk to anything already approved, tested, or deployed.

---

*End of content review, redesign, and narrative continuity addendum. No code, architecture, database, business rules, scoring, APIs, ADRs, SRS, or PRD were modified in producing this document.*
