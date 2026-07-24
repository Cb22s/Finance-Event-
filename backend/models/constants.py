# =============================================================================
# GAME CONSTANTS — Single source of truth for all game parameters
# =============================================================================

# Monthly income every player receives
MONTHLY_INCOME = 100000

# Initial allocation budget (Month 1)
INITIAL_BUDGET = 100000

# Total game duration
TOTAL_MONTHS = 12

# ──── LIFESTYLE COSTS ────
LIFESTYLE_COSTS = {
    "city": {
        "rent": 44000,
        "food": 24000,
        "transport": 10000,
        "utilities": 10000,
        "total": 88000
    },
    "outer": {
        "rent": 28000,
        "food": 22000,
        "transport": 22000,
        "utilities": 10000,
        "total": 82000
    }
}
# Surplus after expenses: city Rs12,000/mo, outer Rs18,000/mo on a Rs1,00,000 salary.
# REBALANCE (2026-07-21): was city 40,000 / outer 25,000 total, leaving a Rs60-75k
# risk-free surplus every single month. With nothing able to lose money at that scale,
# every player finished rich and the leaderboard bunched at the top. Expenses now
# consume ~7/8 of income, so allocation decisions actually bind.
#
# SECOND PASS: an earlier attempt at 78k/72k (Rs22-28k surplus) still failed the
# balance sim — accumulated salary dominated every investment decision, the spread
# between the best and worst strategy was only 1.16x, and simply HOARDING CASH beat
# investing. A game that rewards passivity teaches the opposite of what this event
# is for. Surplus is now small enough that returns on capital, not payroll, decide
# the leaderboard.

# ──── ASSET GROWTH RATES (per month) ────
STOCK_BASE_GROWTH = 0.012       # 1.2% monthly base (~15%/yr) before volatility
GOLD_BASE_GROWTH = 0.006        # 0.6% monthly base (~7.5%/yr), stable
EMERGENCY_FUND_GROWTH = 0.005   # 0.5% monthly (~6%/yr savings interest)
# REBALANCE (2026-07-21): previously 8% / 4% / 2% PER MONTH, i.e. ~150%/yr on
# stocks. Compounded over 12 rounds that turned any stock allocation into a
# guaranteed win and made every other decision in the game irrelevant.

# ──── STOCK VOLATILITY RANGE ────
STOCK_VOLATILITY_MIN = -0.09    # Worst auto month: -7.8% net of base growth
STOCK_VOLATILITY_MAX = 0.09     # Best auto month: +10.2% net of base growth
# Symmetric so the volatility draw itself has zero expected value; all drift
# comes from STOCK_BASE_GROWTH. Was -0.15/+0.20, a +2.5%/mo free lunch on top
# of an already absurd 8% base.

# ──── LOAN PARAMETERS ────
# REBALANCE (2026-07-21): rate was 0.12 = 12% PER MONTH (~289%/yr), which is not a
# loan, it is a death sentence. Split into two rates so that borrowing on purpose is
# a real strategic option while being forced into debt still hurts.
LOAN_INTEREST_RATE = 0.012      # 1.2%/mo (~15%/yr) — player-initiated loans
AUTO_LOAN_INTEREST_RATE = 0.025 # 2.5%/mo (~34%/yr) — punitive; forced on cash crisis
LOAN_EMI_FRACTION = 0.10        # (legacy) flat-EMI fraction — kept for reference
LOAN_TERM_MONTHS = 6            # Default term; loans amortize to zero over this many months
LOAN_TERM_OPTIONS = [3, 6, 12]  # Terms a player may choose when borrowing
LOAN_MIN_AMOUNT = 10000
# Total outstanding debt is capped at this multiple of monthly income. Without a cap a
# player could borrow unbounded amounts, dump it all into stocks and leverage-farm the
# leaderboard — the exact failure ADR-008 was written to prevent.
MAX_TOTAL_DEBT_MULTIPLE = 3.0   # Rs3,00,000 ceiling at Rs1,00,000 income
# EMI affordability gate: total EMIs may not exceed this share of monthly income.
MAX_EMI_TO_INCOME = 0.40

# ──── BIKE PARAMETERS ────
BIKE_DOWN_PAYMENT = 10000
BIKE_EMI = 5000
BIKE_LOCK_IN_MONTHS = 3
BIKE_TRANSPORT_DISCOUNT = 0.50  # 50% discount on transport

# ──── SELL PENALTY ────
SELL_PENALTY_RATE = 0.10        # 10% penalty on selling assets

# ──── INFLATION ────
INFLATION_RATE_PER_MONTH = 0.005  # 0.5% monthly inflation on expenses
INFLATION_START_MONTH = 4          # Inflation kicks in from month 4

# ──── TRUST SCORE PARAMETERS ────
TRUST_HELP_AMOUNTS = {
    "none": 0,
    "medium": 2000,
    "high": 5000
}
TRUST_SCORE_GAIN = {
    "none": 0,
    "medium": 1,
    "high": 3
}
TRUST_IGNORE_PENALTY = -1  # Penalty for ignoring social events repeatedly

# ──── EVENT PROBABILITY WEIGHTS ────
# Used by the dynamic event engine
EVENT_BASE_PROBABILITIES = {
    "financial_emergency": 0.25,
    "investment_opportunity": 0.30,
    "social_responsibility": 0.20,
    "market_fluctuation": 0.40,
    "windfall": 0.10,
    "expense_spike": 0.20
}

# ──── RISK LEVEL THRESHOLDS ────
RISK_LEVEL_THRESHOLDS = {
    "conservative": 0.20,   # < 20% in stocks
    "moderate": 0.50,       # 20-50% in stocks
    "aggressive": 1.0       # > 50% in stocks
}

# ──── FINANCIAL HEALTH SCORE WEIGHTS (ADR-008, ratified 2026-07-11) ────
# Composite leaderboard score. Formula is PUBLIC to players (ADR-000: player trust).
# Replaces net-worth-only ranking, which rewarded maximum-leverage gambling.
SCORE_WEIGHTS = {
    "net_worth": 0.40,        # Wealth built
    "liquidity": 0.15,        # Emergency fund adequacy (months of expenses)
    "debt_control": 0.15,     # Debt relative to assets
    "risk_protection": 0.15,  # Inverse of portfolio risk score
    "discipline": 0.15        # Consistency across rounds (no cash crises)
}

# Net worth component: normalized against total resources received so far
# (initial budget + salary months). Capped so extreme leverage can't dominate.
NW_NORMALIZATION_CAP = 1.25

# Liquidity component: emergency fund covering this many months of expenses = full marks
LIQUIDITY_TARGET_MONTHS = 6

# Monthly discipline grades (averaged across the game)
DISCIPLINE_CLEAN_MONTH = 100      # Met all obligations from cash flow
DISCIPLINE_EF_RESCUE = 40         # Emergency fund had to cover a cash deficit
DISCIPLINE_AUTO_LOAN = 0          # Cash crisis forced an auto-loan

# ──── MARRIAGE & COURTSHIP PARAMETERS (ADR-002) ────
MARRIAGE_MONTH = 6
WEDDING_COST = 88000
SPOUSE_BASE_EXPENSE = 9000

ARCHETYPES = {
    "saver": {
        "name": "The Saver",
        "income": 10000,
        "expense_mod": -9000,
        "stocks": 0,
        "gold": 8000,
        "ef": 22000,
        "loan": 0,
        "description": "Strong expense discipline, small emergency buffer. Low income; limited upside."
    },
    "earner": {
        "name": "The Earner",
        "income": 36000,
        "expense_mod": 12000,
        "stocks": 0,
        "gold": 0,
        "ef": 0,
        "loan": 0,
        "description": "High second income, but higher lifestyle expense and event exposure."
    },
    "investor": {
        "name": "The Investor",
        "income": 9000,
        "expense_mod": -1000,
        "stocks": 44000,
        "gold": 20000,
        "ef": 24000,
        "loan": 0,
        "description": "Brings an existing portfolio of stocks, gold, and cash. Volatile but high potential."
    },
    "anchor": {
        "name": "The Anchor",
        "income": 14000,
        "expense_mod": -2000,
        "stocks": 8000,
        "gold": 0,
        "ef": 45000,
        "loan": 0,
        "description": "Stable income and a well-funded emergency fund. Predictable and solid."
    }
}



# ──── MARKET SCENARIO REGIMES (2026-07-21) ────
# Stocks and gold are no longer drawn independently. Each month resolves to ONE
# scenario that moves both together with a stated cause, because that correlation IS
# the lesson: in a geopolitical shock capital flees equities into gold, so a
# diversified player survives a month that wipes out an all-in-stocks player.
#
# Each regime: (stock_pct_range, gold_pct_range, weight, name, reason template)
MARKET_REGIMES = {
    "war": {
        "name": "Geopolitical Conflict",
        "reason": "War has broken out. Investors are fleeing equities for safe havens, "
                  "and gold is being bid up hard.",
        "stock": (-0.18, -0.08),
        "gold": (0.06, 0.14),
        "weight": 10
    },
    "crash": {
        "name": "Market Crash",
        "reason": "A banking failure has triggered a broad sell-off. Equities are down "
                  "sharply; gold is catching the flight to safety.",
        "stock": (-0.25, -0.12),
        "gold": (0.04, 0.10),
        "weight": 8
    },
    "rate_hike": {
        "name": "Central Bank Rate Hike",
        "reason": "The RBI has raised rates to fight inflation. Borrowing costs are up, "
                  "equities are under pressure, and gold is less attractive than yield.",
        "stock": (-0.09, -0.03),
        "gold": (-0.05, -0.01),
        "weight": 12
    },
    "inflation_spike": {
        "name": "Inflation Spike",
        "reason": "Fuel and food prices have surged. Equities are flat to soft while "
                  "gold rallies as an inflation hedge.",
        "stock": (-0.03, 0.02),
        "gold": (0.04, 0.08),
        "weight": 12
    },
    "steady": {
        "name": "Steady Growth",
        "reason": "No major shocks. Corporate earnings are in line and markets are "
                  "grinding quietly higher.",
        "stock": (0.01, 0.04),
        "gold": (0.00, 0.02),
        "weight": 25
    },
    "boom": {
        "name": "Bull Run",
        "reason": "Strong GDP numbers and heavy foreign inflows. Equities are running; "
                  "money is rotating out of gold into risk.",
        "stock": (0.06, 0.12),
        "gold": (-0.03, 0.01),
        "weight": 15
    },
    "recovery": {
        "name": "Post-Crisis Recovery",
        "reason": "Confidence is returning after the shock. Equities are rebounding and "
                  "the safe-haven premium on gold is unwinding.",
        "stock": (0.04, 0.09),
        "gold": (-0.04, 0.00),
        "weight": 12
    },
    "correction": {
        "name": "Technical Correction",
        "reason": "Markets got ahead of fundamentals and are giving some back. An "
                  "ordinary pullback, not a crisis.",
        "stock": (-0.07, -0.02),
        "gold": (0.00, 0.03),
        "weight": 15
    }
}

# Regime that follows a shock is biased toward recovery, so the market has memory
# instead of being a fresh coin flip each month.
POST_SHOCK_REGIMES = ["recovery", "steady", "correction"]
SHOCK_REGIMES = ["war", "crash"]


# ──── INSURANCE (replaces Social Investment / trust, 2026-07-21) ────
# Trust score was removed from the player UI: it cost real money, fed almost
# nothing into the ADR-008 leaderboard score, and taught no financial lesson.
# Insurance replaces it because it is in the PRD, it is a genuine risk-management
# decision, and it gives the risk_protection score component a lever the player
# can actually pull.
#
# The trade is deliberately uncomfortable: premiums are a GUARANTEED small loss
# every month against an UNCERTAIN large loss. A player who buys cover and is
# never hit has "wasted" money — and that is exactly the lesson.
INSURANCE_PLANS = {
    "none": {
        "name": "No Cover",
        "premium": 0,
        "emergency_coverage": 0.0,
        "description": "No premium. You absorb the full cost of any emergency."
    },
    "basic": {
        "name": "Basic Health Cover",
        "premium": 2500,
        "emergency_coverage": 0.50,
        "description": "Rs2,500/month. Covers 50% of any medical or emergency event."
    },
    "comprehensive": {
        "name": "Comprehensive Health + Life",
        "premium": 6000,
        "emergency_coverage": 0.80,
        "description": "Rs6,000/month. Covers 80% of any medical or emergency event."
    }
}

# Which event categories insurance pays out against. Market losses are NOT
# insurable — a player cannot buy protection from their own portfolio choices.
INSURABLE_CATEGORIES = {"emergency", "medical"}
