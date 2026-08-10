"""
ADR-014 test strategy, implemented in full.

The load-bearing tests are determinism, cross-player fairness and
no-LLM-dependency: together they prove the leaderboard measures financial
judgment rather than English fluency or network luck.
"""
import unittest

from models.constants import (
    NEGOTIATION_MAX_ROUNDS, NEGOTIATION_MIN_ROUND_TO_ACCEPT,
    SATISFACTION_EXPENSE_SWING, negotiation_min_ratio, satisfaction_expense_drift,
)
from models.negotiation_intents import (
    parse_offline, validate, IntentError,
    ACCEPT_PROPOSAL, COUNTER_OFFER, REQUEST_DELAY, REFUSE,
)
from services import negotiation_service as ns
from services import ai_service


class TestIntentSchema(unittest.TestCase):
    """Invalid or ambiguous input must be REJECTED, never guessed (ADR-003)."""

    def test_rejects_gibberish(self):
        with self.assertRaises(IntentError):
            parse_offline("asdfghjkl")

    def test_rejects_contradiction(self):
        with self.assertRaises(IntentError):
            parse_offline("yes but no")

    def test_rejects_empty(self):
        with self.assertRaises(IntentError):
            parse_offline("   ")

    def test_rejects_unknown_intent(self):
        with self.assertRaises(IntentError):
            validate("BRIBE_HER", {})

    def test_rejects_missing_param(self):
        with self.assertRaises(IntentError):
            validate(COUNTER_OFFER, {})

    def test_rejects_extra_param(self):
        with self.assertRaises(IntentError):
            validate(ACCEPT_PROPOSAL, {"amount": 5000})

    def test_rejects_negative_offer(self):
        with self.assertRaises(IntentError):
            validate(COUNTER_OFFER, {"amount": -1})

    def test_rejects_out_of_range_delay(self):
        with self.assertRaises(IntentError):
            validate(REQUEST_DELAY, {"months": 99})

    def test_parses_indian_money_formats(self):
        for text, expected in [("15,000", 15000), ("Rs 18k", 18000),
                               ("₹12000", 12000), ("2 lakh", 200000)]:
            intent, params = parse_offline(text)
            self.assertEqual(intent, COUNTER_OFFER)
            self.assertEqual(params["amount"], expected, msg=text)


class TestNoInstantAccept(unittest.TestCase):
    """The 'cannot convince immediately' requirement (ADR-014 §2.2)."""

    def setUp(self):
        self.p = ns.generate_proposal("u1", 7, "earner")

    def test_round_one_never_accepts_even_at_full_ask(self):
        r = ns.evaluate(COUNTER_OFFER, {"amount": self.p["ask"] - 1},
                        self.p, 1, 100, 10 ** 7)
        self.assertFalse(r["resolved"])
        self.assertEqual(r["outcome"], "continue")

    def test_round_two_can_accept(self):
        r = ns.evaluate(COUNTER_OFFER, {"amount": self.p["ask"] - 1},
                        self.p, NEGOTIATION_MIN_ROUND_TO_ACCEPT, 100, 10 ** 7)
        self.assertTrue(r["resolved"])

    def test_exact_full_ask_accepted_any_round(self):
        # Paying her full price is agreement, not negotiation.
        r = ns.evaluate(COUNTER_OFFER, {"amount": self.p["ask"]}, self.p, 1, 60, 10 ** 7)
        self.assertEqual(r["outcome"], "accepted_full")

    def test_runs_out_of_rounds(self):
        r = ns.evaluate(COUNTER_OFFER, {"amount": 1}, self.p,
                        NEGOTIATION_MAX_ROUNDS, 50, 10 ** 7)
        self.assertTrue(r["resolved"])
        self.assertEqual(r["outcome"], "auto_resolved")
        self.assertLess(r["satisfaction_delta"], 0)


class TestThresholdMonotonic(unittest.TestCase):
    def test_higher_satisfaction_never_raises_the_bar(self):
        for arch in ("saver", "earner", "investor", "anchor"):
            prev = None
            for sat in range(0, 101, 5):
                r = negotiation_min_ratio(arch, sat)
                if prev is not None:
                    self.assertLessEqual(r, prev + 1e-9,
                        f"{arch}: ratio rose from {prev} to {r} at satisfaction {sat}")
                prev = r

    def test_ratio_stays_in_unit_range(self):
        for arch in ("saver", "earner", "investor", "anchor"):
            for sat in (0, 50, 100):
                self.assertTrue(0 < negotiation_min_ratio(arch, sat) <= 1.0)


class TestDeterminism(unittest.TestCase):
    def test_proposal_is_stable_across_calls(self):
        a = ns.generate_proposal("user-x", 8, "investor")
        for _ in range(100):
            b = ns.generate_proposal("user-x", 8, "investor")
            self.assertEqual(a, b)

    def test_evaluation_is_stable(self):
        p = ns.generate_proposal("user-x", 8, "investor")
        first = ns.evaluate(COUNTER_OFFER, {"amount": 20000}, p, 2, 60, 10 ** 7)
        for _ in range(100):
            self.assertEqual(ns.evaluate(COUNTER_OFFER, {"amount": 20000},
                                         p, 2, 60, 10 ** 7), first)

    def test_different_months_differ(self):
        asks = {ns.generate_proposal("user-x", m, "earner")["ask"] for m in range(7, 13)}
        self.assertGreater(len(asks), 1, "every month produced the identical ask")


class TestCrossPlayerFairness(unittest.TestCase):
    """ADR-000: same situation + same offer => same outcome, for everyone."""

    def test_same_offer_same_outcome(self):
        pa = ns.generate_proposal("alice", 7, "anchor")
        pb = ns.generate_proposal("bob", 7, "anchor")
        # Asks may differ per player, but the RULE applied is identical.
        for p in (pa, pb):
            r = ns.evaluate(COUNTER_OFFER, {"amount": p["ask"]}, p, 2, 60, 10 ** 7)
            self.assertEqual(r["outcome"], "accepted_full")

    def test_identical_inputs_identical_result(self):
        p = ns.generate_proposal("alice", 7, "saver")
        ra = ns.evaluate(COUNTER_OFFER, {"amount": 9000}, p, 2, 70, 10 ** 7)
        rb = ns.evaluate(COUNTER_OFFER, {"amount": 9000}, p, 2, 70, 10 ** 7)
        self.assertEqual(ra, rb)

    def test_phrasing_cannot_change_outcome(self):
        """Two ways of saying the same number must resolve identically."""
        p = ns.generate_proposal("alice", 7, "saver")
        a = parse_offline("I can do 15,000")
        b = parse_offline("lets say Rs 15k")
        self.assertEqual(a[1]["amount"], b[1]["amount"])
        self.assertEqual(
            ns.evaluate(a[0], a[1], p, 2, 60, 10 ** 7),
            ns.evaluate(b[0], b[1], p, 2, 60, 10 ** 7),
        )


class TestNoLLMDependency(unittest.TestCase):
    """The whole feature must work with the network unplugged."""

    def test_rules_engine_imports_no_network_client(self):
        import inspect
        src = inspect.getsource(ns)
        for banned in ("urllib", "requests", "http", "socket", "ai_service"):
            self.assertNotIn(banned, src,
                f"negotiation_service must not reference {banned}")

    def test_extract_intent_works_without_key(self):
        p = ns.generate_proposal("u", 7, "earner")
        out = ai_service.extract_intent("I can manage 20k", p)
        self.assertEqual(out["intent"], COUNTER_OFFER)
        self.assertEqual(out["params"]["amount"], 20000)

    def test_narrate_always_returns_a_line(self):
        p = ns.generate_proposal("u", 7, "earner")
        for outcome in ("continue", "accepted_full", "accepted_counter",
                        "refused", "delayed", "auto_resolved", "invalid"):
            v = ai_service.narrate(outcome, "because", p, "The Earner", 60)
            self.assertTrue(v["line"].strip())


class TestSatisfactionBounds(unittest.TestCase):
    def test_expense_drift_is_bounded(self):
        for sat in range(-50, 151):
            d = satisfaction_expense_drift(sat)
            self.assertLessEqual(abs(d), SATISFACTION_EXPENSE_SWING + 1e-9)

    def test_drift_direction(self):
        self.assertGreater(satisfaction_expense_drift(0), 0)    # unhappy costs more
        self.assertAlmostEqual(satisfaction_expense_drift(50), 0)
        self.assertLess(satisfaction_expense_drift(100), 0)     # happy costs less

    def test_clamped(self):
        self.assertEqual(ns.clamp_satisfaction(-40), 0)
        self.assertEqual(ns.clamp_satisfaction(9999), 100)


class TestProposalEffects(unittest.TestCase):
    """Her proposals are not all bad deals — that is the educational point."""

    def test_lifestyle_returns_nothing(self):
        p = ns.generate_proposal("u", 7, "earner")
        e = ns.evaluate(ACCEPT_PROPOSAL, {}, p, 2, 60, 10 ** 7)["effects"]
        self.assertEqual(set(e), {"cash"})
        self.assertLess(e["cash"], 0)

    def test_investment_converts_to_stocks(self):
        p = ns.generate_proposal("u", 7, "investor")
        e = ns.evaluate(ACCEPT_PROPOSAL, {}, p, 2, 60, 10 ** 7)["effects"]
        self.assertAlmostEqual(e["stocks"], -e["cash"])

    def test_protection_converts_to_emergency_fund(self):
        p = ns.generate_proposal("u", 7, "anchor")
        e = ns.evaluate(ACCEPT_PROPOSAL, {}, p, 2, 60, 10 ** 7)["effects"]
        self.assertAlmostEqual(e["emergency_fund"], -e["cash"])

    def test_saving_reduces_recurring_expense(self):
        p = ns.generate_proposal("u", 7, "saver")
        e = ns.evaluate(ACCEPT_PROPOSAL, {}, p, 2, 60, 10 ** 7)["effects"]
        self.assertLess(e["household_expense_modifier"], 0)

    def test_cannot_agree_beyond_cash(self):
        p = ns.generate_proposal("u", 7, "earner")
        r = ns.evaluate(ACCEPT_PROPOSAL, {}, p, 2, 60, 100)
        self.assertEqual(r["outcome"], "invalid")
        self.assertFalse(r["resolved"])


if __name__ == "__main__":
    unittest.main()
