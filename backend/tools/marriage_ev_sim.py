"""
MARRIAGE EV-BALANCE SIMULATOR  (ADR-002 fairness gate)

Purpose: prove the spouse archetypes -- and the choice to STAY SINGLE -- sit
inside one expected-value tolerance band. If they don't, the leaderboard is
decided by who guessed right at the altar (luck), which violates ADR-000.

This is a BALANCE TOOL, not game code. It touches no production logic.
Run:  python3 backend/tools/marriage_ev_sim.py
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.constants import (
    MONTHLY_INCOME, LIFESTYLE_COSTS, TOTAL_MONTHS,
    STOCK_BASE_GROWTH, GOLD_BASE_GROWTH, EMERGENCY_FUND_GROWTH,
    INFLATION_RATE_PER_MONTH, INFLATION_START_MONTH,
)

MARRIAGE_MONTH = 6          # admin opens the marriage round here (mid-game)
WEDDING_COST   = 88000      # one-off cost of marrying (makes SINGLE viable)
SPOUSE_BASE_EXPENSE = 9000  # every spouse adds household cost per month

# ── ARCHETYPE STAT BLOCKS (declarative data, ADR-006 style) ──
# income      : spouse monthly income
# expense_mod : monthly change to household expenses (+ = costs more)
# stocks/gold/ef/loan : one-off contribution at marriage
ARCHETYPES = {
    # Each archetype mixes market-exposed and market-independent value so none
    # is a one-way bet on whether the admin authors a bull or flat market.
    "The Saver":    {"income": 10000, "expense_mod": -9000, "stocks":     0, "gold":  8000, "ef": 22000, "loan":     0},
    "The Earner":   {"income": 36000, "expense_mod": 12000, "stocks":     0, "gold":     0, "ef":     0, "loan":     0},
    "The Investor": {"income":  9000, "expense_mod": -1000, "stocks": 44000, "gold": 20000, "ef": 24000, "loan":     0},
    "The Anchor":   {"income": 14000, "expense_mod": -2000, "stocks":  8000, "gold":     0, "ef": 45000, "loan":     0},
}

# ── REPRESENTATIVE PLAYER STRATEGIES (how they deploy surplus each month) ──
# fractions of monthly surplus directed to stocks / gold / emergency fund / cash
STRATEGIES = {
    "aggressive":   {"stocks": 0.80, "gold": 0.10, "ef": 0.10},
    "balanced":     {"stocks": 0.45, "gold": 0.25, "ef": 0.30},
    "conservative": {"stocks": 0.15, "gold": 0.25, "ef": 0.60},
    "hoarder":      {"stocks": 0.00, "gold": 0.00, "ef": 0.20},   # rest stays cash
}


def expense_for(month, lifestyle="city"):
    base = LIFESTYLE_COSTS[lifestyle]["total"]
    if month < INFLATION_START_MONTH:
        return base
    n = month - INFLATION_START_MONTH + 1
    return base * ((1 + INFLATION_RATE_PER_MONTH) ** n)


def simulate(archetype_name, strategy_name, market_on: bool, lifestyle="city"):
    """Run months 1..12 and return final net worth."""
    cash = 0.0; stocks = 0.0; gold = 0.0; ef = 0.0; loans = 0.0
    arc = ARCHETYPES.get(archetype_name)
    mix = STRATEGIES[strategy_name]

    for month in range(1, TOTAL_MONTHS + 1):
        # marriage lands at MARRIAGE_MONTH
        if arc and month == MARRIAGE_MONTH:
            cash -= WEDDING_COST
            stocks += arc["stocks"]; gold += arc["gold"]; ef += arc["ef"]
            loans += arc["loan"]

        income = MONTHLY_INCOME
        expense = expense_for(month, lifestyle)
        if arc and month >= MARRIAGE_MONTH:
            income += arc["income"]
            expense += SPOUSE_BASE_EXPENSE + arc["expense_mod"]

        cash += income - expense

        # deploy surplus per strategy (only positive cash is deployed)
        if cash > 0:
            to_stocks = cash * mix["stocks"]; to_gold = cash * mix["gold"]; to_ef = cash * mix["ef"]
            stocks += to_stocks; gold += to_gold; ef += to_ef
            cash -= (to_stocks + to_gold + to_ef)

        # growth
        if market_on:
            stocks *= (1 + STOCK_BASE_GROWTH)
            gold *= (1 + GOLD_BASE_GROWTH)
        ef *= (1 + EMERGENCY_FUND_GROWTH)

        # spouse-contributed loan amortises simply over remaining months
        if loans > 0:
            pay = min(loans, 8000)
            loans -= pay; cash -= pay

    return cash + stocks + gold + ef - loans


def run(market_on: bool):
    label = "MARKET ON (auto growth)" if market_on else "MARKET OFF (admin-authored only)"
    print("\n" + "=" * 78)
    print(f"  {label}   |  marriage month {MARRIAGE_MONTH}, wedding Rs{WEDDING_COST:,}")
    print("=" * 78)
    options = ["(stay single)"] + list(ARCHETYPES.keys())
    strat_names = list(STRATEGIES.keys())

    table = {}
    for opt in options:
        arc = None if opt == "(stay single)" else opt
        table[opt] = {s_: simulate(arc, s_, market_on) for s_ in strat_names}

    means = {o: sum(v.values()) / len(v) for o, v in table.items()}
    baseline = means["(stay single)"]
    best, worst = max(means.values()), min(means.values())
    spread = (best - worst) / abs(best) * 100 if best else 0

    hdr = f"{'OPTION':<16}" + "".join(f"{s_[:9]:>12}" for s_ in strat_names) + f"{'MEAN':>13}{'vs SINGLE':>12}"
    print(hdr); print("-" * 78)
    for opt, v in sorted(means.items(), key=lambda kv: -kv[1]):
        row = f"{opt:<16}" + "".join(f"{table[opt][s_]/1000:>11.0f}k" for s_ in strat_names)
        d = (v - baseline) / abs(baseline) * 100 if baseline else 0
        print(row + f"{v/1000:>12.0f}k{d:>11.1f}%")
    print("-" * 78)

    # GATE 1: overall spread
    g1 = spread <= 8
    # GATE 2: single viability - single must sit within 4% of the archetype mean
    arch_mean = sum(means[o] for o in ARCHETYPES) / len(ARCHETYPES)
    single_gap = (arch_mean - baseline) / abs(baseline) * 100
    g2 = abs(single_gap) <= 4
    # GATE 3: no archetype wins under EVERY strategy (no strict dominance)
    dominant = None
    for opt in ARCHETYPES:
        tops_all = all(table[opt][s_] >= max(table[o2][s_] for o2 in options) for s_ in strat_names)
        if not tops_all:
            continue
        rivals = [means[o] for o in ARCHETYPES if o != opt]
        lead = (means[opt] - max(rivals)) / abs(max(rivals)) * 100
        if lead > 2.0:            # material lead => genuine dominance
            dominant = f"{opt} (+{lead:.1f}%)"
    g3 = dominant is None

    print(f"GATE 1 spread best-vs-worst : {spread:5.1f}%  (<=8%)   {'PASS' if g1 else 'FAIL'}")
    print(f"GATE 2 single-vs-archetypes : {single_gap:+5.1f}%  (+/-4%)  {'PASS' if g2 else 'FAIL'}")
    print(f"GATE 3 strict dominance     : {dominant or 'none':<9}          {'PASS' if g3 else 'FAIL'}")
    print("VERDICT:", "PASS - fair choice set" if (g1 and g2 and g3) else "FAIL - needs tuning")
    return g1 and g2 and g3


if __name__ == "__main__":
    s1 = run(market_on=True)
    s2 = run(market_on=False)
    print("\nNOTE: with market OFF, archetype value depends entirely on the market")
    print("events YOU author. Re-run this after the months 2-12 content pack exists.")
