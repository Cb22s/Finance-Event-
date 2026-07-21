"""
12-month balance simulation (2026-07-21 rebalance verification).

Runs several archetypal player strategies through the real engine and reports
final net worth + Financial Health Score, to check that:
  1. Profit is no longer automatic.
  2. Strategies are separated by a meaningful spread.
  3. No single strategy dominates in every market regime.
Run: python3 tools/balance_sim.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.monthly_processor import process_month_for_player
from engine.market_engine import resolve_market_scenario
from models.constants import TOTAL_MONTHS


STRATEGIES = {
    "All-in stocks":      {"stocks": 1.00, "gold": 0.00, "ef": 0.00, "cash": 0.00},
    "All-in gold":        {"stocks": 0.00, "gold": 1.00, "ef": 0.00, "cash": 0.00},
    "Balanced 40/30/30":  {"stocks": 0.40, "gold": 0.30, "ef": 0.30, "cash": 0.00},
    "Conservative EF":    {"stocks": 0.10, "gold": 0.10, "ef": 0.80, "cash": 0.00},
    "Hoards cash":        {"stocks": 0.00, "gold": 0.00, "ef": 0.00, "cash": 1.00},
    # Borrows the full Rs3,00,000 debt ceiling in month 2 and puts it in stocks.
    # This is the strategy the debt cap exists to bound; it must be able to WIN big
    # and LOSE big, otherwise the loan feature is decorative.
    "Leveraged stocks":   {"stocks": 1.00, "gold": 0.00, "ef": 0.00, "cash": 0.00,
                           "borrow": 300000},
}

# A minimal shock pack, standing in for the months 2-12 content the admin must author.
# Without events NOTHING can destroy a passive player, which is why the unshocked
# spread below is so narrow.
SAMPLE_EVENTS = {
    4:  {"event_name": "Medical Emergency", "event_type": "fixed", "impact_target": "cash",
         "value": -120000, "description": "Hospitalisation not covered by insurance."},
    7:  {"event_name": "Job Loss (1 month)", "event_type": "fixed", "impact_target": "cash",
         "value": -100000, "description": "Laid off; no salary this month."},
    10: {"event_name": "Major Home Repair", "event_type": "fixed", "impact_target": "cash",
         "value": -85000, "description": "Roof collapse after monsoon damage."},
}


def run(strategy_name, split, auto_market=True, lifestyle="city", with_events=False):
    player = {
        "user_id": "00000000-0000-0000-0000-00000000000a",
        "month": 1, "cash": 22000, "stocks": 40000, "gold": 20000,
        "emergency_fund": 18000, "loans": 0, "lifestyle_type": lifestyle,
        "bike_status": False, "bike_lock_in_months": 0, "trust_score": 0,
        "risk_level": 50, "discipline_score": 100, "spouse_archetype": None
    }
    crises = 0
    loans = []
    borrow = split.get("borrow", 0)
    if borrow:
        from engine.monthly_processor import _amortized_emi
        from models.constants import LOAN_INTEREST_RATE
        emi = _amortized_emi(borrow, LOAN_INTEREST_RATE, 12)
        loans = [{"id": 1, "principal": borrow, "current_amount": borrow,
                  "interest_rate": LOAN_INTEREST_RATE, "term_months": 12, "emi": emi}]
        player["stocks"] += borrow   # borrowed cash goes straight into the market

    for m in range(2, TOTAL_MONTHS + 1):
        scenario = resolve_market_scenario(m, None, auto_market)
        events = []
        if with_events and m in SAMPLE_EVENTS:
            events = [SAMPLE_EVENTS[m]]
        res = process_month_for_player(
            player=player, month=m, admin_events=events, active_loans=loans,
            pending_sales=[], auto_events=False, auto_market=auto_market,
            market_scenario=scenario
        )
        loans = [{**l, "current_amount": u["current_amount"]}
                 for l in loans for u in res["loan_updates"] if u["id"] == l["id"]
                 and u["status"] == "active"]
        st = res["updated_state"]
        if "CRITICAL" in " ".join(res["event_log"]):
            crises += 1
        # Apply the strategy's monthly allocation of leftover cash
        avail = st["cash"]
        st["stocks"] += avail * split["stocks"]
        st["gold"] += avail * split["gold"]
        st["emergency_fund"] += avail * split["ef"]
        st["cash"] = avail * split["cash"]
        player = st
    return player, crises


def main():
    for auto, evts in ((True, False), (True, True)):
        label = ("AUTO MARKET ON + SHOCK EVENTS" if evts
                 else "AUTO MARKET ON, NO EVENTS (current live config)")
        print(f"\n{'='*68}\n{label}\n{'='*68}")
        print(f"{'Strategy':<22}{'Net worth':>14}{'Score':>9}{'Crises':>8}")
        rows = []
        for name, split in STRATEGIES.items():
            final, crises = run(name, split, auto_market=auto, with_events=evts)
            rows.append((name, final["net_worth"], final["financial_health_score"], crises))
            print(f"{name:<22}{final['net_worth']:>14,.0f}"
                  f"{final['financial_health_score']:>9.1f}{crises:>8}")
        nws = [r[1] for r in rows]
        best, worst = max(nws), min(nws)
        print(f"\n  Spread: Rs{worst:,.0f} -> Rs{best:,.0f}  "
              f"(best is {best/max(worst,1):.2f}x worst)")

    print(f"\n{'='*68}\n12-MONTH MARKET PATH (auto)\n{'='*68}")
    for m in range(1, TOTAL_MONTHS + 1):
        s = resolve_market_scenario(m, None, True)
        print(f"  M{m:2d}  {s['name']:<24} stocks {s['stock_pct']*100:+6.1f}%   "
              f"gold {s['gold_pct']*100:+6.1f}%")


if __name__ == "__main__":
    main()
