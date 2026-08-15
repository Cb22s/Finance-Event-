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
    MARRIAGE_MONTH, WEDDING_COST, SPOUSE_BASE_EXPENSE,
    ARCHETYPES as _GAME_ARCHETYPES, FESTIVAL_EVENT,
)
from services.festival_service import compute_festival_ask

# ── PHASE 3A: Month-6 festival cost (character-adjusted initial ask) ──
# Modeled at the FULL initial ask — the worst case, a player who never
# negotiates. Negotiation can only reduce this (floor 50-70% of ask), so if
# the gates pass here they pass for every negotiated outcome as well.
FESTIVAL_ASKS = {a["name"]: compute_festival_ask(aid)
                 for aid, a in _GAME_ARCHETYPES.items()}

# All marriage numbers are now IMPORTED from models/constants.py above.
# They used to be duplicated here, which is precisely how the simulator came to
# certify a set of values the game no longer used (the V2 rebalance changed the
# economy; this file kept validating the old stat blocks). One source of truth.
ARCHETYPES = {a["name"]: {k: a[k] for k in ("income", "expense_mod", "stocks", "gold", "ef", "loan")}
              for a in _GAME_ARCHETYPES.values()}

# ── REPRESENTATIVE PLAYER STRATEGIES (how they deploy surplus each month) ──
# fractions of monthly surplus directed to stocks / gold / emergency fund / cash
STRATEGIES = {
    "aggressive":   {"stocks": 0.80, "gold": 0.10, "ef": 0.10},
    "balanced":     {"stocks": 0.45, "gold": 0.25, "ef": 0.30},
    "conservative": {"stocks": 0.15, "gold": 0.25, "ef": 0.60},
    "hoarder":      {"stocks": 0.00, "gold": 0.00, "ef": 0.20},   # rest stays cash
}


# DB events fetch (offline safe)
db_events = []
if os.environ.get("USE_SUPABASE_SIM") == "1":
    try:
        from supabase_client import supabase
        db_events = supabase.table("events").select("*").execute().data or []
        print(f"Loaded {len(db_events)} events from Supabase for the simulation.")
    except Exception as e:
        print(f"Warning: Could not fetch events from database ({e}). Running simulation with default behavior.")

events_by_month = {}
for ev in db_events:
    m = ev.get("month")
    if m not in events_by_month:
        events_by_month[m] = []
    events_by_month[m].append(ev)


def expense_for(month, lifestyle="city"):
    base = LIFESTYLE_COSTS[lifestyle]["total"]
    if month < INFLATION_START_MONTH:
        return base
    n = month - INFLATION_START_MONTH + 1
    return base * ((1 + INFLATION_RATE_PER_MONTH) ** n)


def simulate(archetype_name, strategy_name, market_on: bool, lifestyle="city", festival_asks=None):
    """Run months 1..12 and return final net worth."""
    if festival_asks is None:
        festival_asks = FESTIVAL_ASKS

    cash = 0.0; stocks = 0.0; gold = 0.0; ef = 0.0; loans = 0.0
    arc = ARCHETYPES.get(archetype_name)
    mix = STRATEGIES[strategy_name]

    for month in range(1, TOTAL_MONTHS + 1):
        # marriage lands at MARRIAGE_MONTH
        if arc and month == MARRIAGE_MONTH:
            cash -= WEDDING_COST
            stocks += arc["stocks"]; gold += arc["gold"]; ef += arc["ef"]
            loans += arc["loan"]

        # Phase 3A: the family festival lands two months after the wedding.
        if arc and month == FESTIVAL_EVENT["month"]:
            cash -= festival_asks.get(archetype_name, 0)

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

        # Apply database events for this month (mandatory global events)
        for ev in events_by_month.get(month, []):
            val = float(ev["value"])
            target = ev["impact_target"]
            etype = ev.get("event_type") or ev.get("type", "fixed")
            
            if etype == "percentage":
                if target == "stocks":
                    stocks += stocks * (val / 100)
                elif target == "gold":
                    gold += gold * (val / 100)
                elif target == "cash":
                    cash += cash * (val / 100)
            elif etype == "fixed":
                if target == "cash":
                    cash += val
                elif target == "stocks":
                    stocks += val
                elif target == "gold":
                    gold += val
                elif target == "expense_increase":
                    cash -= abs(val)

        # spouse-contributed loan amortises simply over remaining months
        if loans > 0:
            pay = min(loans, 8000)
            loans -= pay; cash -= pay

    return cash + stocks + gold + ef - loans


def run(market_on: bool, festival_asks=None, title_suffix=""):
    if festival_asks is None:
        festival_asks = FESTIVAL_ASKS

    label = "MARKET ON (auto growth)" if market_on else "MARKET OFF (admin-authored only)"
    if title_suffix:
        label += f" [{title_suffix}]"

    print("\n" + "=" * 78)
    print(f"  {label}   |  marriage month {MARRIAGE_MONTH}, wedding Rs{WEDDING_COST:,}, "
          f"festival month {FESTIVAL_EVENT['month']}")
    print("=" * 78)
    print("Festival Asks:", {k: f"Rs{v:,}" for k, v in festival_asks.items()})
    options = ["(stay single)"] + list(ARCHETYPES.keys())
    strat_names = list(STRATEGIES.keys())

    table = {}
    for opt in options:
        arc = None if opt == "(stay single)" else opt
        table[opt] = {s_: simulate(arc, s_, market_on, festival_asks=festival_asks) for s_ in strat_names}

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
    return {
        "spread": spread, "single_gap": single_gap, "dominant": dominant,
        "g1": g1, "g2": g2, "g3": g3, "verdict": (g1 and g2 and g3)
    }


if __name__ == "__main__":
    from models.constants import ARCHETYPES as GAME_ARCHETYPES, negotiation_min_ratio

    # Baseline asks with CharAdj = 1.0 (RUN A)
    def ask_no_char(aid):
        arch = GAME_ARCHETYPES[aid]
        hhi = MONTHLY_INCOME + arch["income"]
        mandatory_living = LIFESTYLE_COSTS["city"]["total"] + SPOUSE_BASE_EXPENSE + arch["expense_mod"]
        surplus_mo = max(1000.0, hhi - mandatory_living)
        posture = max(0.85, min(1.20, 1.0 + arch["expense_mod"] / 30000.0))
        return int(round((surplus_mo * FESTIVAL_EVENT["base_k"] * posture * FESTIVAL_EVENT["importance"] * 1.0) / 500.0) * 500)

    asks_run_a = {a["name"]: ask_no_char(aid) for aid, a in GAME_ARCHETYPES.items()}
    asks_run_b = {a["name"]: compute_festival_ask(aid) for aid, a in GAME_ARCHETYPES.items()}
    asks_negotiated = {a["name"]: int(round(compute_festival_ask(aid) * negotiation_min_ratio(aid, 60.0) / 500.0) * 500) for aid, a in GAME_ARCHETYPES.items()}

    print("\n" + "#" * 78)
    print("  RUN A: MODEL C + CharAdj = 1.0 (ISOLATED BASELINE)")
    print("#" * 78)
    run(market_on=True, festival_asks=asks_run_a, title_suffix="RUN A - Market ON")
    run(market_on=False, festival_asks=asks_run_a, title_suffix="RUN A - Market OFF")

    print("\n" + "#" * 78)
    print("  RUN B: MODEL C + APPROVED CHARACTER ADJUSTMENT (UNNEGOTIATED INITIAL ASKS)")
    print("#" * 78)
    run(market_on=True, festival_asks=asks_run_b, title_suffix="RUN B - Market ON")
    run(market_on=False, festival_asks=asks_run_b, title_suffix="RUN B - Market OFF")

    print("\n" + "#" * 78)
    print("  RUN B (NEGOTIATED): MODEL C + APPROVED CHARACTER ADJUSTMENT (NEGOTIATED OUTCOMES)")
    print("#" * 78)
    run(market_on=True, festival_asks=asks_negotiated, title_suffix="RUN B Negotiated - Market ON")
    run(market_on=False, festival_asks=asks_negotiated, title_suffix="RUN B Negotiated - Market OFF")

    print("\nNOTE: with market OFF, archetype value depends entirely on the market")
    print("events YOU author. Re-run this after the months 2-12 content pack exists.")

