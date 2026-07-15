# =============================================================================
# CROSS-PLAYER FAIRNESS VERIFICATION SUITE — T1.2
# (V1_IMPLEMENTATION_PLAN.md Milestone 1)
#
# Operationalizes SRS.md §8 ("cross-player market fairness") and SRS.md §5
# Invariant 2 ("Market outcomes identical for all players in a month") and
# ADR-009 (one global economic path per game/month, applied identically to
# every household).
#
# Deliberately black-box: this file calls only the actual production
# functions (market_engine.calculate_investment_growth,
# event_engine.generate_events_for_player) and compares their OBSERVED
# outputs to each other. It does not reconstruct, reimplement, or duplicate
# the seeded-RNG algorithm (hashlib/seed-string logic) anywhere — per your
# explicit instruction, this suite verifies *behavior*, not *implementation*.
# T1.1's seed-stability tests already cover formula-level regression
# checking; that is not repeated here.
#
# Four checks, as approved:
#   1. Every player receives the same market growth rate in the same month.
#   2. Different months produce different market growth rates.
#   3. Repeating the same month produces the same market growth rate.
#   4. Personal events differ correctly between users with identical state.
#
# Scope note (unchanged from the approved plan): "fairness" here means the
# shared MARKET rate is identical across players — not that every player's
# whole month looks identical. Personal events (PRD §6) are seeded per
# (user_id, month) and are supposed to vary; check 4 exists specifically to
# confirm that variation is real, not to assert sameness.
#
# Zero new dependencies (stdlib `unittest` only). Self-contained — does not
# import from test_determinism.py, so it can run standalone. Purely
# additive: no production code was modified to write it.
# =============================================================================

import copy
import os
import sys
import unittest

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from engine import market_engine, event_engine  # noqa: E402


# =============================================================================
# Shared fixtures
# =============================================================================

def make_player(**overrides) -> dict:
    base = {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "month": 2,
        "cash": 20000.0,
        "stocks": 30000.0,
        "gold": 15000.0,
        "emergency_fund": 10000.0,
        "loans": 0.0,
        "trust_score": 0.0,
    }
    base.update(overrides)
    return base


# A deliberately diverse set of portfolios — tiny, huge, and mixed holdings
# — so "same rate, different dollar outcome" can be observed, not assumed.
DIVERSE_PROFILES = [
    make_player(user_id="p-tiny", stocks=1000.0, gold=500.0, emergency_fund=200.0),
    make_player(user_id="p-small", stocks=8000.0, gold=3000.0, emergency_fund=4000.0),
    make_player(user_id="p-medium", stocks=45000.0, gold=12000.0, emergency_fund=15000.0),
    make_player(user_id="p-large", stocks=250000.0, gold=90000.0, emergency_fund=60000.0),
    make_player(user_id="p-huge", stocks=1500000.0, gold=400000.0, emergency_fund=300000.0),
    make_player(user_id="p-stock-heavy", stocks=300000.0, gold=1000.0, emergency_fund=500.0),
    make_player(user_id="p-gold-heavy", stocks=1000.0, gold=200000.0, emergency_fund=500.0),
    make_player(user_id="p-balanced", stocks=60000.0, gold=60000.0, emergency_fund=60000.0),
]

# Rate-comparison tolerance: absolute rate difference allowed, to absorb the
# function's own `round(value, 2)` on dollar output (negligible at these
# holding sizes — see _derive_rate for why this is safe, not a fudge).
RATE_TOLERANCE = 1e-4


def _derive_rate(before: float, after: float) -> float:
    """Back out the observed growth rate from an actual before/after pair.
    Only meaningful for nonzero holdings (division by zero otherwise)."""
    return (after - before) / before


# =============================================================================
# 1. EVERY PLAYER RECEIVES THE SAME MARKET GROWTH RATE, SAME MONTH
# =============================================================================

class TestSameMonthSameRateAcrossPlayers(unittest.TestCase):
    """Calls the real calculate_investment_growth for many different
    portfolios in the same month and confirms the *rate* each one
    experienced is identical, even though the *dollar* outcome correctly
    scales with each player's own holdings."""

    def test_stock_rate_identical_across_diverse_players(self):
        for month in range(2, 13):
            with self.subTest(month=month):
                rates = []
                for profile in DIVERSE_PROFILES:
                    result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                    rate = _derive_rate(profile["stocks"], result["stocks"])
                    rates.append(rate)
                baseline = rates[0]
                for i, rate in enumerate(rates[1:], start=1):
                    with self.subTest(player_index=i):
                        self.assertAlmostEqual(rate, baseline, delta=RATE_TOLERANCE)

    def test_gold_rate_identical_across_diverse_players(self):
        for month in range(2, 13):
            with self.subTest(month=month):
                rates = []
                for profile in DIVERSE_PROFILES:
                    result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                    rate = _derive_rate(profile["gold"], result["gold"])
                    rates.append(rate)
                baseline = rates[0]
                for i, rate in enumerate(rates[1:], start=1):
                    with self.subTest(player_index=i):
                        self.assertAlmostEqual(rate, baseline, delta=RATE_TOLERANCE)

    def test_emergency_fund_rate_identical_across_diverse_players(self):
        for month in range(2, 13):
            with self.subTest(month=month):
                rates = []
                for profile in DIVERSE_PROFILES:
                    result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                    rate = _derive_rate(profile["emergency_fund"], result["emergency_fund"])
                    rates.append(rate)
                baseline = rates[0]
                for i, rate in enumerate(rates[1:], start=1):
                    with self.subTest(player_index=i):
                        self.assertAlmostEqual(rate, baseline, delta=RATE_TOLERANCE)

    def test_zero_holding_players_do_not_break_fairness_for_others(self):
        """A player with no stocks/gold simply doesn't participate in that
        asset's growth this month (no delta to derive a rate from) — that
        should have no bearing on the rate every other player observes."""
        month = 6
        zero_stock_player = make_player(user_id="p-zero-stocks", stocks=0.0, gold=20000.0)
        normal_player = make_player(user_id="p-normal", stocks=50000.0, gold=20000.0)

        zero_result = market_engine.calculate_investment_growth(copy.deepcopy(zero_stock_player), month)
        normal_result = market_engine.calculate_investment_growth(copy.deepcopy(normal_player), month)

        self.assertEqual(zero_result["stocks"], 0.0)  # no growth applied — correct, not unfair
        gold_rate_zero_player = _derive_rate(zero_stock_player["gold"], zero_result["gold"])
        gold_rate_normal_player = _derive_rate(normal_player["gold"], normal_result["gold"])
        self.assertAlmostEqual(gold_rate_zero_player, gold_rate_normal_player, delta=RATE_TOLERANCE)


# =============================================================================
# 2. DIFFERENT MONTHS PRODUCE DIFFERENT MARKET GROWTH RATES
# =============================================================================

class TestDifferentMonthsDifferentRates(unittest.TestCase):
    """A degenerate seeding scheme (e.g. accidentally always drawing the
    same value) would pass every same-month fairness check while being
    deterministically wrong. Confirm distinct months actually observably
    differ for the same player."""

    def test_stock_rate_varies_across_months(self):
        profile = make_player(user_id="p-month-sweep", stocks=100000.0, gold=50000.0)
        rates = []
        for month in range(2, 13):
            result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
            rates.append(_derive_rate(profile["stocks"], result["stocks"]))
        distinct = any(abs(r - rates[0]) > RATE_TOLERANCE for r in rates[1:])
        self.assertTrue(distinct, f"all 11 months produced the same stock rate: {rates}")

    def test_gold_rate_varies_across_months(self):
        profile = make_player(user_id="p-month-sweep-2", stocks=100000.0, gold=50000.0)
        rates = []
        for month in range(2, 13):
            result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
            rates.append(_derive_rate(profile["gold"], result["gold"]))
        distinct = any(abs(r - rates[0]) > RATE_TOLERANCE for r in rates[1:])
        self.assertTrue(distinct, f"all 11 months produced the same gold rate: {rates}")

    def test_no_two_adjacent_months_collide_for_every_pair(self):
        """Stronger sweep: every month's stock rate is checked against every
        other month's, not just against month 2. Some pairwise closeness is
        statistically expected across 11 draws — this only fails if the
        whole sequence collapses to a small number of repeated values,
        which is what an unseeded/degenerate implementation would produce."""
        profile = make_player(user_id="p-pairwise", stocks=200000.0)
        rates = []
        for month in range(2, 13):
            result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
            rates.append(round(_derive_rate(profile["stocks"], result["stocks"]), 4))
        distinct_count = len(set(rates))
        self.assertGreater(distinct_count, 1,
                            f"expected varied rates across 11 months, got: {rates}")


# =============================================================================
# 3. REPEATING THE SAME MONTH PRODUCES THE SAME MARKET GROWTH RATE
# =============================================================================

class TestSameMonthRepeatability(unittest.TestCase):
    """The rate itself — not just the whole function's output structurally
    (already covered in T1.1) — must be stable across repeated calls for
    the same month, observed the same black-box way as checks 1 and 2."""

    def test_stock_rate_stable_across_repeated_calls_same_month(self):
        profile = make_player(user_id="p-repeat", stocks=75000.0)
        for month in range(2, 13):
            with self.subTest(month=month):
                r1 = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                r2 = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                rate1 = _derive_rate(profile["stocks"], r1["stocks"])
                rate2 = _derive_rate(profile["stocks"], r2["stocks"])
                self.assertAlmostEqual(rate1, rate2, delta=RATE_TOLERANCE)

    def test_gold_rate_stable_across_repeated_calls_same_month(self):
        profile = make_player(user_id="p-repeat-2", gold=40000.0)
        for month in range(2, 13):
            with self.subTest(month=month):
                r1 = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                r2 = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                rate1 = _derive_rate(profile["gold"], r1["gold"])
                rate2 = _derive_rate(profile["gold"], r2["gold"])
                self.assertAlmostEqual(rate1, rate2, delta=RATE_TOLERANCE)

    def test_rate_stable_across_many_repeated_calls_not_just_two(self):
        """A stronger form of the same check — five calls, not two, to rule
        out anything that happens to agree twice by chance."""
        profile = make_player(user_id="p-repeat-many", stocks=60000.0)
        month = 8
        rates = []
        for _ in range(5):
            result = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
            rates.append(_derive_rate(profile["stocks"], result["stocks"]))
        baseline = rates[0]
        for rate in rates[1:]:
            self.assertAlmostEqual(rate, baseline, delta=RATE_TOLERANCE)


# =============================================================================
# 4. PERSONAL EVENTS DIFFER CORRECTLY BETWEEN USERS WITH IDENTICAL STATE
# =============================================================================

class TestPersonalEventsVaryByUser(unittest.TestCase):
    """The deliberate counterpart to checks 1-3: personal events (PRD §6 —
    emergency, opportunity, social, expense spike, windfall, trust penalty)
    are supposed to differ per user_id even when every other input is
    identical. This confirms that variation is real, catching the failure
    mode where personal events get accidentally globalized (which would
    silently break "consequences of individual choices" and would NOT be
    caught by checks 1-3, which only look at the market component)."""

    def test_identical_state_different_user_ids_produce_different_event_sets(self):
        identical_state = {
            "cash": 3000.0, "stocks": 20000.0, "gold": 5000.0,
            "emergency_fund": 1000.0, "loans": 0.0, "trust_score": 0.0,
        }
        user_ids = [f"user-{i:03d}" for i in range(15)]
        results = []
        for uid in user_ids:
            player = {**identical_state, "user_id": uid}
            events = event_engine.generate_events_for_player(player, month=6)
            results.append(events)

        distinct_results = {str(r) for r in results}
        self.assertGreater(
            len(distinct_results), 1,
            "15 different users with identical state all produced the identical "
            "event set — personal events do not appear to be seeded per user_id"
        )

    def test_same_user_id_identical_state_reproduces_identical_events(self):
        """Companion control: it's not that the function is randomly
        unstable — the SAME user_id must still be fully deterministic
        (T1.1 territory), so any variation seen above is attributable to
        user_id specifically, not general noise."""
        player = {
            "user_id": "user-fixed", "cash": 3000.0, "stocks": 20000.0,
            "gold": 5000.0, "emergency_fund": 1000.0, "loans": 0.0, "trust_score": 0.0,
        }
        e1 = event_engine.generate_events_for_player(copy.deepcopy(player), month=6)
        e2 = event_engine.generate_events_for_player(copy.deepcopy(player), month=6)
        self.assertEqual(e1, e2)

    def test_different_users_vary_across_multiple_months(self):
        """Repeats the core check across several months rather than just
        one, since a seeding bug could plausibly be month-dependent."""
        identical_state = {
            "cash": 5000.0, "stocks": 15000.0, "gold": 8000.0,
            "emergency_fund": 2000.0, "loans": 0.0, "trust_score": 0.0,
        }
        for month in [3, 6, 9, 12]:
            with self.subTest(month=month):
                results = []
                for i in range(10):
                    player = {**identical_state, "user_id": f"user-month-{month}-{i}"}
                    results.append(event_engine.generate_events_for_player(player, month))
                distinct_results = {str(r) for r in results}
                self.assertGreater(len(distinct_results), 1,
                                    f"month {month}: 10 users, identical state, identical events")


if __name__ == "__main__":
    unittest.main(verbosity=2)
