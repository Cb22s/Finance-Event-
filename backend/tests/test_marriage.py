import unittest
from engine.scoring import calculate_financial_health_score, net_worth_component
from engine.monthly_processor import process_month_for_player
from models.constants import (
    ARCHETYPES, SPOUSE_BASE_EXPENSE, MONTHLY_INCOME, LIFESTYLE_COSTS
)
from engine.market_engine import calculate_inflation_adjustment

class TestMarriageSystem(unittest.TestCase):
    def test_net_worth_normalization_with_spouse_income(self):
        # Without spouse income
        nw_score_single = net_worth_component(net_worth=100000, month=6, spouse_income=0.0)
        
        # With spouse income (e.g. Earner: 36000)
        nw_score_married = net_worth_component(net_worth=100000, month=6, spouse_income=36000)
        
        # Since expected resources is higher for married players, they should get a lower score for the SAME net worth
        self.assertTrue(nw_score_married < nw_score_single)

    def test_monthly_processor_adds_spouse_income_and_expenses(self):
        player = {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "month": 6,
            "cash": 10000,
            "stocks": 0,
            "gold": 0,
            "emergency_fund": 0,
            "loans": 0,
            "lifestyle_type": "city",
            "bike_status": False,
            "spouse_archetype": "saver" # Saver has income 10000, expense_mod -9000
        }
        
        result = process_month_for_player(
            player=player,
            month=7,
            admin_events=[],
            active_loans=[],
            pending_sales=[],
            auto_events=False,
            auto_market=False
        )
        
        # Derived from constants rather than hardcoded, so a future rebalance of
        # LIFESTYLE_COSTS updates the expectation instead of silently failing.
        # (This assertion previously hardcoded 79193.98 against a city expense of
        # 40,000; the 2026-07-21 rebalance raised it to 78,000 and broke the test.)
        expense = calculate_inflation_adjustment(LIFESTYLE_COSTS['city']['total'], 7)
        spouse_expense = SPOUSE_BASE_EXPENSE + ARCHETYPES['saver']['expense_mod']
        spouse_income = ARCHETYPES['saver']['income']
        expected = round(10000 + MONTHLY_INCOME + spouse_income - expense - spouse_expense, 2)
        self.assertAlmostEqual(result["ending_cash"], expected, places=2)
        self.assertEqual(result["updated_state"]["spouse_archetype"], "saver")

if __name__ == "__main__":
    unittest.main()
