"""
MARRIAGE BALANCE TUNER (2026-07-24)

The V2 rebalance cut the player's monthly surplus from ~Rs60,000 to ~Rs12,000.
The spouse stat blocks were never re-tuned, so a spouse earning Rs10-36k/mo went
from a marginal boost to a 1.8-2.25x multiplier on everything the player does.
marriage_ev_sim.py now FAILS gates 1 and 2: marrying beats staying single by
+10.2%, which makes the marriage round a no-brainer instead of a decision.

This searches for stat blocks that pass the gates in BOTH market regimes while
keeping each archetype's identity (saver = frugal, earner = income, investor =
market-exposed, anchor = safe reserves).

Run: python3 tools/marriage_tuner.py
"""
import sys, os, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tools.marriage_ev_sim as sim


def gates(market_on):
    options = ["(stay single)"] + list(sim.ARCHETYPES.keys())
    strats = list(sim.STRATEGIES.keys())
    table = {o: {s: sim.simulate(None if o == "(stay single)" else o, s, market_on)
                 for s in strats} for o in options}
    means = {o: sum(v.values()) / len(v) for o, v in table.items()}
    base = means["(stay single)"]
    best, worst = max(means.values()), min(means.values())
    spread = (best - worst) / abs(best) * 100
    arch_mean = sum(means[o] for o in sim.ARCHETYPES) / len(sim.ARCHETYPES)
    gap = (arch_mean - base) / abs(base) * 100
    dom = 0.0
    for opt in sim.ARCHETYPES:
        if all(table[opt][s] >= max(table[o2][s] for o2 in options) for s in strats):
            rivals = [means[o] for o in sim.ARCHETYPES if o != opt]
            dom = max(dom, (means[opt] - max(rivals)) / abs(max(rivals)) * 100)
    return spread, gap, dom, means


def score():
    """Total gate violation across both regimes. 0 = passes everything."""
    tot = 0.0
    for mk in (True, False):
        spread, gap, dom, _ = gates(mk)
        tot += max(0, spread - 8) ** 2
        tot += max(0, abs(gap) - 4) ** 2
        tot += max(0, dom - 2) ** 2
    return tot


# Identity-preserving templates: (income, expense_mod, stocks, gold, ef)
# expressed as shape; the tuner scales income and dowry independently.
SHAPES = {
    "The Saver":    dict(income=0.30, expense_mod=-0.90, stocks=0.00, gold=0.35, ef=0.65),
    "The Earner":   dict(income=1.00, expense_mod=+1.20, stocks=0.00, gold=0.00, ef=0.15),
    "The Investor": dict(income=0.25, expense_mod=-0.10, stocks=1.00, gold=0.45, ef=0.10),
    "The Anchor":   dict(income=0.45, expense_mod=-0.20, stocks=0.15, gold=0.00, ef=1.00),
}


def build(inc_base, exp_base, dowry_base):
    out = {}
    for name, sh in SHAPES.items():
        out[name] = {
            "income": round(sh["income"] * inc_base / 500) * 500,
            "expense_mod": round(sh["expense_mod"] * exp_base / 500) * 500,
            "stocks": round(sh["stocks"] * dowry_base / 1000) * 1000,
            "gold": round(sh["gold"] * dowry_base / 1000) * 1000,
            "ef": round(sh["ef"] * dowry_base / 1000) * 1000,
            "loan": 0,
        }
    return out


best = None
for inc in range(4000, 20001, 1000):            # Earner's income = inc
    for exp in range(2000, 12001, 1000):        # expense modifier magnitude
        for dowry in range(0, 60001, 5000):     # asset dowry magnitude
            for wed in range(20000, 140001, 5000):
                sim.ARCHETYPES = build(inc, exp, dowry)
                sim.WEDDING_COST = wed
                s = score()
                if best is None or s < best[0]:
                    best = (s, inc, exp, dowry, wed)
                if s == 0:
                    break
        if best and best[0] == 0:
            break
    if best and best[0] == 0:
        break

s, inc, exp, dowry, wed = best
sim.ARCHETYPES = build(inc, exp, dowry)
sim.WEDDING_COST = wed
print(f"BEST  violation={s:.3f}  income_base={inc:,}  expense_base={exp:,}  "
      f"dowry_base={dowry:,}  WEDDING_COST={wed:,}\n")
for name, a in sim.ARCHETYPES.items():
    print(f"  {name:<14} income {a['income']:>7,}  exp_mod {a['expense_mod']:>+7,}  "
          f"stocks {a['stocks']:>6,}  gold {a['gold']:>6,}  ef {a['ef']:>6,}")
print()
for mk in (True, False):
    spread, gap, dom, means = gates(mk)
    tag = "MARKET ON " if mk else "MARKET OFF"
    print(f"{tag}  spread {spread:5.1f}% (<=8) {'PASS' if spread<=8 else 'FAIL'}   "
          f"single-gap {gap:+5.1f}% (+/-4) {'PASS' if abs(gap)<=4 else 'FAIL'}   "
          f"dominance {dom:4.1f}% (<=2) {'PASS' if dom<=2 else 'FAIL'}")
    for o, v in sorted(means.items(), key=lambda kv: -kv[1]):
        print(f"      {o:<16}{v/1000:>8.0f}k")
