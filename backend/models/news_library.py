# =============================================================================
# REAL-WORLD NEWS LIBRARY
# =============================================================================
# A curated set of ACTUAL historical financial events, each with its real
# headline, real date, and the real (approximate, month-scaled) impact on Indian
# equities and gold.
#
# WHY A LIBRARY AND NOT A LIVE FEED:
#   1. Deterministic. Every player in every dry run sees the same market, so the
#      leaderboard stays comparable and ADR-009 holds.
#   2. No event-day risk. A live API that rate-limits or 500s at 10am during your
#      college event takes the whole game down. This works offline.
#   3. A live headline does not come with a percentage attached. Mapping
#      "RBI holds rates" to a number is guesswork; these numbers are what
#      actually happened.
#
# ACCURACY NOTE: figures are rounded to whole percents and scaled to a single
# month of play. Where an event unfolded over a quarter or a year, `real_note`
# states the true horizon so the case-study framing stays honest. These are
# teaching approximations, not investable data.
#
# TEACHING VALUE: note that gold does NOT always rise when equities fall.
# In the March 2020 liquidity crunch investors sold gold too, to cover margin
# calls. Events 'covid_crash_mar2020' and 'covid_gold_rally_2020' are deliberately
# sequenced to teach exactly that.

NEWS_EVENTS = {

    # ──────────────── GLOBAL CRISES ────────────────
    "gfc_crash_2008": {
        "headline": "Lehman Brothers collapses; global credit markets freeze",
        "date": "September 2008",
        "category": "crisis",
        "context": "The largest bankruptcy in US history triggered a worldwide "
                   "credit freeze. Foreign investors pulled capital out of Indian "
                   "equities at record pace.",
        "stock_pct": -0.24,
        "gold_pct": 0.05,
        "real_note": "The Sensex fell from 20,465 to 9,176 over calendar 2008, "
                     "roughly -55% for the year, while gold returned about +6% in "
                     "USD. Shown here scaled to one month.",
        "lesson": "In a genuine credit crisis, equities and gold decouple. The "
                  "player holding only stocks has no floor."
    },
    "covid_crash_mar2020": {
        "headline": "WHO declares COVID-19 a pandemic; India announces nationwide lockdown",
        "date": "March 2020",
        "category": "crisis",
        "context": "On 23 March 2020 the Sensex fell 13.15% in a single session, "
                   "its worst day ever. Gold fell too as investors sold "
                   "everything liquid to cover margin calls.",
        "stock_pct": -0.29,
        "gold_pct": -0.03,
        "real_note": "Sensex -28.6% over Jan-Mar 2020 (its sharpest quarterly "
                     "fall); the single worst day was -13.15% on 23 March.",
        "lesson": "Gold is a safe haven MOST of the time, not ALL of the time. "
                  "In a liquidity crunch everything sells off together."
    },
    "covid_gold_rally_2020": {
        "headline": "Central banks unleash record stimulus; gold hits all-time high",
        "date": "August 2020",
        "category": "recovery",
        "context": "Near-zero interest rates and massive fiscal stimulus drove "
                   "gold to a then-record high around $2,070/oz while equities "
                   "rebounded hard off the March lows.",
        "stock_pct": 0.09,
        "gold_pct": 0.11,
        "real_note": "Gold finished 2020 up roughly 25%, one of its strongest "
                     "years in decades, after gaining ~16% in the first half.",
        "lesson": "The recovery rewarded whoever did NOT panic-sell in March."
    },
    "dotcom_bust_2000": {
        "headline": "Dot-com bubble bursts; technology valuations collapse",
        "date": "March 2000",
        "category": "crisis",
        "context": "Internet companies with no earnings had been valued like "
                   "utilities with decades of cash flow. The correction was brutal "
                   "and concentrated in one sector.",
        "stock_pct": -0.20,
        "gold_pct": 0.02,
        "real_note": "The Nasdaq lost roughly 78% peak-to-trough over 2000-2002.",
        "lesson": "Concentration risk. A portfolio in one hot sector is not diversified."
    },

    # ──────────────── WAR & GEOPOLITICS ────────────────
    "russia_ukraine_2022": {
        "headline": "Russia invades Ukraine; oil crosses $130 and gold spikes",
        "date": "February 2022",
        "category": "war",
        "context": "War in a major commodity-exporting region sent energy and "
                   "food prices sharply higher. Capital rotated out of equities "
                   "and into gold as a safe haven.",
        "stock_pct": -0.08,
        "gold_pct": 0.09,
        "real_note": "Gold crossed $2,000/oz in the weeks after the invasion; "
                     "Brent crude briefly touched ~$139.",
        "lesson": "This is the textbook war trade: equities down, gold up. "
                  "A diversified player barely notices."
    },
    "gulf_war_1990": {
        "headline": "Iraq invades Kuwait; oil price doubles in three months",
        "date": "August 1990",
        "category": "war",
        "context": "An oil supply shock fed straight into inflation. India, a "
                   "large oil importer, faced a widening current account deficit.",
        "stock_pct": -0.11,
        "gold_pct": 0.07,
        "real_note": "Crude roughly doubled from ~$17 to ~$36/barrel between "
                     "August and October 1990.",
        "lesson": "Oil shocks hit importing countries twice: markets fall AND "
                  "the cost of living rises."
    },
    "kargil_1999": {
        "headline": "Kargil conflict begins along the Line of Control",
        "date": "May 1999",
        "category": "war",
        "context": "Regional conflict created short-term uncertainty, but the "
                   "market recovered quickly once the conflict stayed contained.",
        "stock_pct": -0.04,
        "gold_pct": 0.03,
        "real_note": "Indian equities recovered within months and ended 1999 "
                     "strongly.",
        "lesson": "Not every conflict is a crisis. Panic-selling on headlines "
                  "is itself a strategy, and usually a losing one."
    },

    # ──────────────── INDIA-SPECIFIC ────────────────
    "demonetisation_2016": {
        "headline": "Government withdraws Rs500 and Rs1,000 notes overnight",
        "date": "November 2016",
        "category": "policy",
        "context": "86% of currency in circulation was invalidated with four "
                   "hours' notice. Cash-dependent sectors seized up; gold demand "
                   "spiked as households sought to move out of cash.",
        "stock_pct": -0.06,
        "gold_pct": 0.04,
        "real_note": "Roughly 86% of the value of notes in circulation was "
                     "demonetised on 8 November 2016.",
        "lesson": "Holding everything in cash is not the safe option you think "
                  "it is. Policy can devalue cash overnight."
    },
    "harshad_mehta_1992": {
        "headline": "Securities scam exposed; Sensex collapses from record high",
        "date": "April 1992",
        "category": "crisis",
        "context": "A broker had been funnelling money from the interbank "
                   "securities market into equities. When it was exposed the "
                   "market fell for over a year.",
        "stock_pct": -0.19,
        "gold_pct": 0.04,
        "real_note": "The Sensex lost roughly 55% over the year following the "
                     "scam's exposure.",
        "lesson": "If a market is rising for reasons nobody can explain, that "
                  "IS the explanation."
    },
    "taper_tantrum_2013": {
        "headline": "US Fed signals taper; rupee crashes to record low of 68/USD",
        "date": "August 2013",
        "category": "policy",
        "context": "Foreign capital fled emerging markets on the hint of tighter "
                   "US policy. The rupee's fall pushed up import costs and gold "
                   "prices in rupee terms.",
        "stock_pct": -0.07,
        "gold_pct": 0.06,
        "real_note": "The rupee fell from ~55 to ~68 per USD between May and "
                     "August 2013.",
        "lesson": "Indian investors face currency risk on top of market risk. "
                  "Rupee gold can rise even when dollar gold does not."
    },
    "rbi_rate_hike_2022": {
        "headline": "RBI raises repo rate in surprise off-cycle move to fight inflation",
        "date": "May 2022",
        "category": "policy",
        "context": "Higher rates raise borrowing costs across the economy. "
                   "Equities de-rate and gold becomes less attractive against "
                   "newly competitive fixed-income yields.",
        "stock_pct": -0.05,
        "gold_pct": -0.03,
        "real_note": "The RBI raised the repo rate by 40bps to 4.40% on 4 May "
                     "2022, then repeatedly through the year.",
        "lesson": "Rate hikes hurt stocks AND gold at the same time. There is "
                  "no hiding place except cash and fixed deposits."
    },
    "gst_rollout_2017": {
        "headline": "GST rolled out nationwide; short-term disruption, long-term reform",
        "date": "July 2017",
        "category": "policy",
        "context": "A major tax overhaul caused temporary supply-chain "
                   "disruption, but markets looked through it to the efficiency "
                   "gains beyond.",
        "stock_pct": 0.03,
        "gold_pct": 0.00,
        "real_note": "Indian equities had a strong 2017 despite the transition.",
        "lesson": "Markets price the future, not the present."
    },
    "il_fs_default_2018": {
        "headline": "IL&FS defaults; credit crisis spreads through NBFC sector",
        "date": "September 2018",
        "category": "crisis",
        "context": "A large infrastructure lender defaulted, freezing credit for "
                   "non-bank finance companies and exposing how much borrowing "
                   "had been funding long assets with short money.",
        "stock_pct": -0.10,
        "gold_pct": 0.03,
        "real_note": "NBFC stocks fell 30-60% over the following months.",
        "lesson": "Debt kills when it comes due sooner than the asset pays off. "
                  "Watch your own EMI-to-income ratio."
    },

    # ──────────────── BOOMS & RECOVERIES ────────────────
    "post_covid_bull_2021": {
        "headline": "Vaccine rollout drives record retail participation in equities",
        "date": "2021",
        "category": "boom",
        "context": "Cheap money, reopening optimism and millions of new retail "
                   "demat accounts drove one of the strongest bull runs on record.",
        "stock_pct": 0.13,
        "gold_pct": -0.02,
        "real_note": "The Sensex gained roughly 22% over calendar 2021.",
        "lesson": "Money rotates OUT of gold when risk appetite returns."
    },
    "reform_rally_1991": {
        "headline": "India liberalises: licence raj dismantled, economy opens up",
        "date": "July 1991",
        "category": "boom",
        "context": "Balance-of-payments crisis forced sweeping reform. The market "
                   "re-rated violently as entire industries opened to competition "
                   "and foreign capital.",
        "stock_pct": 0.15,
        "gold_pct": -0.01,
        "real_note": "India pledged gold reserves to the Bank of England in 1991 "
                     "to avert default, months before the reforms.",
        "lesson": "The best returns often follow the worst crises. Whoever held "
                  "through 1991 was rewarded."
    },
    "china_stimulus_2009": {
        "headline": "Global stimulus packages spark sharpest recovery in decades",
        "date": "March 2009",
        "category": "recovery",
        "context": "Coordinated fiscal and monetary stimulus turned the post-GFC "
                   "market around faster than almost anyone expected.",
        "stock_pct": 0.17,
        "gold_pct": 0.02,
        "real_note": "The Sensex nearly doubled from its March 2009 low over the "
                     "following twelve months.",
        "lesson": "The recovery is invisible while it is happening. Selling at "
                  "the bottom locks in the loss permanently."
    },
    "y2k_it_boom_1999": {
        "headline": "Indian IT services boom on Y2K remediation demand",
        "date": "1999",
        "category": "boom",
        "context": "Global demand for software engineers to fix the millennium "
                   "bug put Indian IT on the world map and re-rated the sector.",
        "stock_pct": 0.11,
        "gold_pct": 0.00,
        "real_note": "Indian IT stocks were among the best global performers of "
                     "1999 before correcting sharply in 2000.",
        "lesson": "Sector booms are real, but they end. See dotcom_bust_2000."
    },

    # ──────────────── INFLATION & COMMODITIES ────────────────
    "inflation_spike_2022": {
        "headline": "Inflation hits multi-decade highs across major economies",
        "date": "June 2022",
        "category": "inflation",
        "context": "Supply-chain disruption plus energy shock pushed inflation to "
                   "levels not seen in forty years. Real returns on cash turned "
                   "sharply negative.",
        "stock_pct": -0.04,
        "gold_pct": 0.05,
        "real_note": "US CPI peaked around 9.1% in June 2022; Indian CPI ran "
                     "above the RBI's 6% tolerance band for months.",
        "lesson": "Inflation is a tax on cash. Money under the mattress lost "
                  "real value every month this year."
    },
    "oil_shock_1973": {
        "headline": "OPEC oil embargo quadruples crude prices",
        "date": "October 1973",
        "category": "inflation",
        "context": "The original energy crisis. Oil-importing economies faced "
                   "simultaneous recession and inflation, a combination previously "
                   "thought impossible.",
        "stock_pct": -0.13,
        "gold_pct": 0.12,
        "real_note": "Crude rose from ~$3 to ~$12/barrel; gold roughly doubled "
                     "over 1973-74.",
        "lesson": "Stagflation: the one environment where stocks and bonds both "
                  "lose and only hard assets hold up."
    },
    "gold_correction_2013": {
        "headline": "Gold posts worst annual loss in three decades",
        "date": "April 2013",
        "category": "correction",
        "context": "With the crisis fading and real yields rising, the safe-haven "
                   "premium unwound violently. Gold fell over 13% in two sessions.",
        "stock_pct": 0.04,
        "gold_pct": -0.14,
        "real_note": "Gold fell roughly 28% over calendar 2013, its worst year "
                     "since 1981.",
        "lesson": "Gold is NOT risk-free. An all-in-gold player can lose badly."
    },

    # ──────────────── ORDINARY MONTHS ────────────────
    "quiet_month": {
        "headline": "Markets drift; no major economic news",
        "date": "Any month",
        "category": "steady",
        "context": "Most months are not a crisis. Earnings come in near "
                   "expectations and prices grind quietly higher.",
        "stock_pct": 0.02,
        "gold_pct": 0.01,
        "real_note": "Historically, a small majority of months are mildly positive.",
        "lesson": "Wealth is built in boring months, not dramatic ones."
    },
    "earnings_beat": {
        "headline": "Corporate earnings beat estimates across sectors",
        "date": "Any quarter",
        "category": "steady",
        "context": "Broad-based earnings growth supports valuations without "
                   "speculative excess.",
        "stock_pct": 0.05,
        "gold_pct": 0.00,
        "real_note": "Earnings growth is the main long-run driver of equity returns.",
        "lesson": "Boring compounding beats dramatic timing."
    },
    "monsoon_failure": {
        "headline": "Deficient monsoon threatens rural demand and food inflation",
        "date": "July, drought year",
        "category": "inflation",
        "context": "A weak monsoon hits agricultural output, rural consumption "
                   "and food prices — a distinctly Indian macro risk.",
        "stock_pct": -0.05,
        "gold_pct": 0.03,
        "real_note": "Rural India is a large share of consumer demand; gold is "
                     "also a traditional rural savings vehicle.",
        "lesson": "Local risks matter as much as global headlines."
    },
    "budget_rally": {
        "headline": "Union Budget cuts capital gains tax, boosts infrastructure spend",
        "date": "February",
        "category": "policy",
        "context": "A market-friendly budget lifted sentiment, particularly in "
                   "infrastructure and capital-goods names.",
        "stock_pct": 0.07,
        "gold_pct": -0.01,
        "real_note": "Budget day is historically one of the most volatile "
                     "sessions of the Indian market year.",
        "lesson": "Policy is a market force. Read the budget."
    },
}


def get_event(key: str) -> dict | None:
    return NEWS_EVENTS.get(key)


def list_events() -> list:
    """All events as a list, each with its key folded in — for admin pickers."""
    return [{"key": k, **v} for k, v in NEWS_EVENTS.items()]


def events_by_category() -> dict:
    out = {}
    for k, v in NEWS_EVENTS.items():
        out.setdefault(v["category"], []).append({"key": k, **v})
    return out
