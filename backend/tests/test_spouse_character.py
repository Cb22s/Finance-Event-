import unittest

from models.constants import ARCHETYPES, CHARACTER_PROFILES, NEGOTIATION_FLOOR_RATIO
from services.spouse_character_service import (
    evaluate_spouse_character, calculate_trait_alignment,
    validate_argument_features, DEFAULT_ARGUMENT_FEATURES,
)
from services import ai_service
from services import negotiation_service as ns


class TestSpouseCharacterService(unittest.TestCase):

    def test_character_trait_alignment(self):
        # Saver values FINANCIAL and FAMILY
        t_saver_fin = calculate_trait_alignment("saver", "FINANCIAL", 0.8)
        t_saver_sta = calculate_trait_alignment("saver", "STATUS", 0.8)
        self.assertGreater(t_saver_fin, t_saver_sta)

        # Earner values STATUS
        t_earner_sta = calculate_trait_alignment("earner", "STATUS", 0.8)
        t_earner_pru = calculate_trait_alignment("earner", "FINANCIAL", 0.8)
        self.assertGreater(t_earner_sta, t_earner_pru)

        # Investor values FINANCIAL and FUTURE
        t_inv_fin = calculate_trait_alignment("investor", "FINANCIAL", 0.8)
        t_inv_sta = calculate_trait_alignment("investor", "STATUS", 0.8)
        self.assertGreater(t_inv_fin, t_inv_sta)

        # Anchor values FAMILY and FINANCIAL
        t_anc_fam = calculate_trait_alignment("anchor", "FAMILY", 0.8)
        t_anc_sta = calculate_trait_alignment("anchor", "STATUS", 0.8)
        self.assertGreater(t_anc_fam, t_anc_sta)

    def test_flx_compromise_responsiveness(self):
        # Investor FLX = 65, Earner FLX = 40
        features = {"primary_category": "FINANCIAL", "argument_quality": 0.8}
        eval_inv = evaluate_spouse_character("investor", features, 60, 2)
        eval_ear = evaluate_spouse_character("earner", features, 60, 2)
        self.assertGreater(eval_inv["delta_floor"], eval_ear["delta_floor"])

    def test_floor_hard_cap_enforced(self):
        # Even quality = 1.0 cannot breach archetype floor
        features = {"primary_category": "FINANCIAL", "argument_quality": 1.0}
        for aid in ARCHETYPES:
            eval_res = evaluate_spouse_character(aid, features, 100, 2)
            hard_floor = NEGOTIATION_FLOOR_RATIO[aid]
            self.assertGreaterEqual(eval_res["effective_floor_ratio"], hard_floor)

    def test_weak_argument_has_minimal_floor_reduction(self):
        weak_features = {"primary_category": "FINANCIAL", "argument_quality": 0.1, "is_aggressive_or_dismissive": True}
        eval_res = evaluate_spouse_character("saver", weak_features, 60, 2)
        self.assertLessEqual(eval_res["delta_floor"], 0.03)

    def test_repeated_argument_diminishing_returns(self):
        features = {"primary_category": "FINANCIAL", "argument_quality": 0.8}
        first_turn = evaluate_spouse_character("saver", features, 60, 2, previous_category=None)
        second_turn = evaluate_spouse_character("saver", features, 60, 2, previous_category="FINANCIAL")
        self.assertGreater(first_turn["trait_alignment"], second_turn["trait_alignment"])

    def test_ai_schema_validation_rejects_monetary_fields(self):
        malformed = {
            "accept_offer": True,
            "new_price": 3000,
            "primary_category": "FINANCIAL",
            "argument_quality": 0.9
        }
        validated = validate_argument_features(malformed)
        self.assertNotIn("accept_offer", validated)
        self.assertNotIn("new_price", validated)
        self.assertEqual(validated["argument_quality"], DEFAULT_ARGUMENT_FEATURES["argument_quality"])

    def test_ai_fallback_handling(self):
        # Passing invalid inputs returns safe default features
        fallback = ai_service.extract_argument_features("", {"ask": 5000, "title": "test"})
        self.assertEqual(fallback["ai_source"], "fallback")
        self.assertIn("primary_category", fallback)

    def test_determinism(self):
        features = {"primary_category": "FAMILY", "argument_quality": 0.75}
        res1 = evaluate_spouse_character("anchor", features, 60, 2)
        res2 = evaluate_spouse_character("anchor", features, 60, 2)
        self.assertEqual(res1, res2)

    def test_negotiation_evaluate_with_character_context(self):
        proposal = {"ask": 10000, "archetype_id": "saver", "kind": "festival", "title": "Festival"}
        features = {"primary_category": "FINANCIAL", "argument_quality": 0.8}
        res = ns.evaluate(
            intent="COUNTER_OFFER",
            params={"amount": 7000},
            proposal=proposal,
            round_no=2,
            satisfaction=60,
            player_cash=50000,
            argument_features=features
        )
        self.assertIn("character_eval", res)
        self.assertIn("effective_floor_ratio", res["character_eval"])


if __name__ == "__main__":
    unittest.main()
