# =============================================================================
# DETERMINISM VERIFICATION SUITE — T1.1 (V1_IMPLEMENTATION_PLAN.md Milestone 1)
#
# Operationalizes SRS.md §8 ("determinism: same inputs twice -> identical
# outputs") and SRS.md §5 Invariant 1 ("all randomness is seeded... same
# inputs -> same outputs, always") as runnable, repeatable checks.
#
# Four categories, as scoped and approved:
#   1. Same Input -> Same Output
#   2. Full 12-month deterministic replay
#   3. Seed stability verification
#   4. Hidden randomness detection
#
# Zero new dependencies (stdlib `unittest` + `ast` only — requirements.txt is
# untouched). Pure read-only imports of engine/ only — no DB, no Flask app
# context, no environment variables required, because these modules have no
# I/O (SRS §2: "engine/ — pure game logic. No HTTP, no direct DB writes").
#
# Scope note: services/game_service.py (fair_roll, etc.) is intentionally
# NOT imported here. Unlike engine/, SRS §2 never claims game_service.py is
# DB-decoupled ("services/game_service — DB reads, leaderboard query,
# fair_roll..."), and in practice it isn't importable in isolation: it does
# `from supabase_client import supabase` at module load, which eagerly
# constructs a live Supabase client and fails without real network access.
# fair_roll's seed formula (documented, hashlib-based) is exercised
# separately in TestSeedStability by independently re-deriving that formula
# — but the actual production fair_roll function itself is out of this
# suite's reach without either a live network path or a production-code
# change to make the import lazy, and no production code is modified here.
#
# This file is purely additive. No production code was modified to write it.
# =============================================================================

import ast
import copy
import hashlib
import os
import random
import sys
import unittest

# Make `engine.*` importable regardless of the directory this is invoked
# from (mirrors how routes/services already import it).
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from engine import market_engine, event_engine, monthly_processor, scoring  # noqa: E402


# =============================================================================
# Shared fixtures
# =============================================================================

def make_player(**overrides) -> dict:
    """A representative player_state-shaped dict. Override fields as needed."""
    base = {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "month": 2,
        "cash": 20000.0,
        "stocks": 30000.0,
        "gold": 15000.0,
        "emergency_fund": 10000.0,
        "loans": 0.0,
        "pending_cash_next_month": 0.0,
        "lifestyle_type": "city",
        "bike_status": False,
        "bike_lock_in_months": 0,
        "net_worth": 75000.0,
        "trust_score": 0.0,
        "risk_level": 50,
        "discipline_score": 100.0,
        "financial_health_score": 0.0,
        "status": "active",
    }
    base.update(overrides)
    return base


PROFILES = {
    "balanced": make_player(),
    "aggressive_low_liquidity": make_player(
        user_id="22222222-2222-2222-2222-222222222222",
        cash=5000.0, stocks=70000.0, gold=5000.0, emergency_fund=2000.0,
    ),
    "conservative_bike_owner": make_player(
        user_id="33333333-3333-3333-3333-333333333333",
        cash=15000.0, stocks=10000.0, gold=10000.0, emergency_fund=40000.0,
        lifestyle_type="outer", bike_status=True, bike_lock_in_months=3,
    ),
}

# A small synthetic admin-events fixture — test data only, unrelated to the
# approved content pack (which is content design, not test fixtures).
SYNTHETIC_ADMIN_EVENTS = {
    5: [{"event_name": "Test Market Note", "event_type": "fixed",
         "impact_target": "cash", "value": -1000, "description": "fixture"}],
    9: [{"event_name": "Test Major Cost", "event_type": "fixed",
         "impact_target": "cash", "value": -5000, "description": "fixture"}],
}


def run_month_twice(player, month, admin_events=None, active_loans=None, pending_sales=None):
    """Call process_month_for_player twice on independently deep-copied
    inputs and return both results for comparison."""
    r1 = monthly_processor.process_month_for_player(
        player=copy.deepcopy(player), month=month,
        admin_events=copy.deepcopy(admin_events),
        active_loans=copy.deepcopy(active_loans),
        pending_sales=copy.deepcopy(pending_sales),
    )
    r2 = monthly_processor.process_month_for_player(
        player=copy.deepcopy(player), month=month,
        admin_events=copy.deepcopy(admin_events),
        active_loans=copy.deepcopy(active_loans),
        pending_sales=copy.deepcopy(pending_sales),
    )
    return r1, r2


def apply_month_result(active_loans, result):
    """Mirror what admin_routes.next_month does to loan state between
    months, for the multi-month replay harness."""
    active_loans = copy.deepcopy(active_loans)
    by_id = {loan["id"]: loan for loan in active_loans}
    for update in result["loan_updates"]:
        if update["id"] in by_id:
            by_id[update["id"]]["current_amount"] = update["current_amount"]
            by_id[update["id"]]["status"] = update["status"]
    next_id = (max(by_id.keys()) + 1) if by_id else 1
    for new_loan in result["new_loans"]:
        loan_row = dict(new_loan)
        loan_row["id"] = next_id
        next_id += 1
        by_id[loan_row["id"]] = loan_row
    return [loan for loan in by_id.values() if loan["status"] == "active"]


def replay_full_game(player, admin_events_by_month=None):
    """Sequentially process months 2..12 for one player, threading state
    exactly as the real engine loop does. Returns the list of per-month
    updated_state snapshots (the full trajectory)."""
    admin_events_by_month = admin_events_by_month or {}
    state = copy.deepcopy(player)
    active_loans = []
    trajectory = []
    for month in range(2, 13):
        result = monthly_processor.process_month_for_player(
            player=copy.deepcopy(state),
            month=month,
            admin_events=copy.deepcopy(admin_events_by_month.get(month)),
            active_loans=copy.deepcopy(active_loans),
            pending_sales=[],
        )
        state = result["updated_state"]
        active_loans = apply_month_result(active_loans, result)
        trajectory.append(copy.deepcopy(result))
    return trajectory


# =============================================================================
# 1. SAME INPUT -> SAME OUTPUT
# =============================================================================

class TestSameInputSameOutput(unittest.TestCase):
    """Direct, single-call determinism: identical inputs must produce
    byte-identical (structurally equal) outputs, for every engine function
    that touches state, across every representative profile and month."""

    def test_process_month_for_player_all_profiles_all_months(self):
        for profile_name, profile in PROFILES.items():
            for month in range(2, 13):
                with self.subTest(profile=profile_name, month=month):
                    r1, r2 = run_month_twice(profile, month)
                    self.assertEqual(r1["updated_state"], r2["updated_state"])
                    self.assertEqual(r1["event_log"], r2["event_log"])
                    self.assertEqual(r1["loan_updates"], r2["loan_updates"])
                    self.assertEqual(r1["new_loans"], r2["new_loans"])
                    self.assertEqual(r1["events_triggered"], r2["events_triggered"])
                    self.assertEqual(r1["starting_cash"], r2["starting_cash"])
                    self.assertEqual(r1["ending_cash"], r2["ending_cash"])
                    self.assertEqual(r1["net_worth"], r2["net_worth"])

    def test_process_month_with_admin_events_and_active_loans(self):
        profile = PROFILES["aggressive_low_liquidity"]
        loans = [{"id": 1, "user_id": profile["user_id"], "principal": 10000.0,
                  "current_amount": 9000.0, "interest_rate": 0.12,
                  "month_taken": 4, "status": "active"}]
        sales = [{"asset_type": "gold", "cash_to_receive": 2000.0,
                  "month_to_credit": 5}]
        for month, events in SYNTHETIC_ADMIN_EVENTS.items():
            with self.subTest(month=month):
                r1, r2 = run_month_twice(profile, month, admin_events=events,
                                          active_loans=loans, pending_sales=sales)
                self.assertEqual(r1["updated_state"], r2["updated_state"])
                self.assertEqual(r1["event_log"], r2["event_log"])

    def test_calculate_investment_growth_deterministic(self):
        for profile in PROFILES.values():
            for month in range(2, 13):
                g1 = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                g2 = market_engine.calculate_investment_growth(copy.deepcopy(profile), month)
                self.assertEqual(g1, g2)

    def test_generate_events_for_player_deterministic(self):
        for profile in PROFILES.values():
            for month in range(2, 13):
                admin_events = SYNTHETIC_ADMIN_EVENTS.get(month)
                e1 = event_engine.generate_events_for_player(copy.deepcopy(profile), month, admin_events)
                e2 = event_engine.generate_events_for_player(copy.deepcopy(profile), month, admin_events)
                self.assertEqual(e1, e2)

    def test_apply_event_to_state_is_pure(self):
        """Control case: apply_event_to_state has no randomness at all —
        confirms the baseline (non-RNG-touching code) is trivially
        deterministic, which is the expected floor for everything else."""
        event = {"name": "Test", "description": "test", "value": -1000,
                 "impact_target": "cash", "type": "fixed", "trust_change": -1}
        r1 = event_engine.apply_event_to_state(event, 10000, 5000, 3000, 2000, 5)
        r2 = event_engine.apply_event_to_state(event, 10000, 5000, 3000, 2000, 5)
        self.assertEqual(r1, r2)

    def test_scoring_functions_are_pure(self):
        """scoring.py has zero randomness by construction (SRS §2) —
        confirms that holds, and that it isn't accidentally broken later."""
        for _ in range(5):
            r1 = scoring.calculate_financial_health_score(
                net_worth=80000, month=6, emergency_fund=10000,
                monthly_expense=40000, loans=5000, total_assets=95000,
                risk_score=45, discipline_avg=88.5
            )
            r2 = scoring.calculate_financial_health_score(
                net_worth=80000, month=6, emergency_fund=10000,
                monthly_expense=40000, loans=5000, total_assets=95000,
                risk_score=45, discipline_avg=88.5
            )
            self.assertEqual(r1, r2)

    # Note: game_service.fair_roll is not exercised here — see the scope
    # note at the top of this file. Its documented seed formula is verified
    # independently in TestSeedStability.


# =============================================================================
# 2. FULL 12-MONTH DETERMINISTIC REPLAY
# =============================================================================

class TestFull12MonthReplay(unittest.TestCase):
    """Runs an entire months-2..12 game twice, per profile, threading state
    (including loans created mid-game) exactly as the real /next-month loop
    does. Catches order-dependent or accumulation divergence that isolated
    single-month checks (category 1) could miss."""

    def test_full_replay_matches_across_two_independent_runs(self):
        for profile_name, profile in PROFILES.items():
            with self.subTest(profile=profile_name):
                trajectory_1 = replay_full_game(profile, SYNTHETIC_ADMIN_EVENTS)
                trajectory_2 = replay_full_game(profile, SYNTHETIC_ADMIN_EVENTS)
                self.assertEqual(len(trajectory_1), 11)  # months 2..12
                for month_index, (m1, m2) in enumerate(zip(trajectory_1, trajectory_2), start=2):
                    with self.subTest(month=month_index):
                        self.assertEqual(m1["updated_state"], m2["updated_state"])
                        self.assertEqual(m1["event_log"], m2["event_log"])
                        self.assertEqual(m1["net_worth"], m2["net_worth"])

    def test_full_replay_final_month_score_matches(self):
        """Specifically checks the value the leaderboard ranks by — if
        anything upstream in the 11-month chain diverged, this is where it
        would surface as a wrong final score."""
        for profile_name, profile in PROFILES.items():
            with self.subTest(profile=profile_name):
                traj_1 = replay_full_game(profile, SYNTHETIC_ADMIN_EVENTS)
                traj_2 = replay_full_game(profile, SYNTHETIC_ADMIN_EVENTS)
                final_score_1 = traj_1[-1]["updated_state"]["financial_health_score"]
                final_score_2 = traj_2[-1]["updated_state"]["financial_health_score"]
                self.assertEqual(final_score_1, final_score_2)


# =============================================================================
# 3. SEED STABILITY VERIFICATION
# =============================================================================

class TestSeedStability(unittest.TestCase):
    """Independently re-derives the seed formula documented in each engine
    module's own comments/docstrings and confirms the engine's actual
    internal seeding matches that formula exactly — not just "consistent
    with itself," but consistent with the *documented contract*. This is a
    regression guard: a future accidental change to the seed string format
    (typo, reordering, salt change) would be caught here even though it
    might still look self-consistent under category 1's tests."""

    def test_market_engine_global_seed_matches_documented_formula(self):
        for month in range(2, 13):
            with self.subTest(month=month):
                expected_seed = int(
                    hashlib.sha256(f"GLOBAL:{month}:market".encode()).hexdigest(), 16
                )
                expected_rng = random.Random(expected_seed)
                actual_rng = market_engine._seeded_rng(month)
                expected_draws = [expected_rng.random() for _ in range(20)]
                actual_draws = [actual_rng.random() for _ in range(20)]
                self.assertEqual(expected_draws, actual_draws)

    def test_event_engine_per_player_seed_matches_documented_formula(self):
        test_cases = [
            ("user-a", 3, "events"), ("user-b", 7, "events"),
            ("GLOBAL", 5, "market_events"), ("user-c", 12, "events"),
        ]
        for user_id, month, salt in test_cases:
            with self.subTest(user_id=user_id, month=month, salt=salt):
                seed_str = f"{user_id}:{month}:{salt}"
                expected_seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
                expected_rng = random.Random(expected_seed)
                actual_rng = event_engine._seeded_random(user_id, month, salt)
                expected_draws = [expected_rng.random() for _ in range(20)]
                actual_draws = [actual_rng.random() for _ in range(20)]
                self.assertEqual(expected_draws, actual_draws)

    def test_market_seed_is_month_only_not_per_player(self):
        """ADR-009: the global market path must be identical across every
        player in a given month — i.e. the seed must depend on month only."""
        rng_a = market_engine._seeded_rng(6)
        rng_b = market_engine._seeded_rng(6)
        self.assertEqual([rng_a.random() for _ in range(10)],
                          [rng_b.random() for _ in range(10)])

    def test_market_seed_differs_across_months(self):
        """A degenerate seeding scheme (e.g. always seeding 0) would pass
        every 'same input -> same output' test while being deterministically
        wrong. Confirm distinct months actually produce distinct sequences."""
        draws_by_month = {}
        for month in range(2, 13):
            rng = market_engine._seeded_rng(month)
            draws_by_month[month] = tuple(rng.random() for _ in range(10))
        self.assertEqual(len(set(draws_by_month.values())), len(draws_by_month),
                          "two different months produced identical draw sequences")

    def test_fair_roll_formula_is_internally_consistent(self):
        """game_service.fair_roll itself isn't imported here (see the scope
        note at the top of this file), but its documented formula
        (hashlib.sha256(f"{user_id}:{month}:{choice_id}") -> digest % 100 + 1
        -> compare to probability) is deterministic and stateless by
        construction — reproducing it independently twice must always agree
        with itself, which is the property the real function inherits by
        using the exact same formula."""
        seed_str = "user-xyz:8:15"
        digest_1 = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
        digest_2 = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
        self.assertEqual(digest_1, digest_2)
        roll_1 = (digest_1 % 100) + 1
        roll_2 = (digest_2 % 100) + 1
        self.assertEqual(roll_1, roll_2)
        self.assertEqual(roll_1 <= 40, roll_2 <= 40)


# =============================================================================
# 4. HIDDEN RANDOMNESS DETECTION
# =============================================================================

# The only functions permitted to call the `random` module directly. Every
# other function that needs randomness must go through one of these two
# seeded wrappers (or hashlib-based determinism, as game_service.fair_roll
# uses, which needs no `random` import at all).
ALLOWED_RANDOM_CALLERS = {
    # _regime_rng is a second SEEDED wrapper (seed = sha256("GLOBAL:{month}:regime")),
    # kept separate from _seeded_rng so that changing a magnitude draw cannot reshuffle
    # which regime a month resolves to. Both are month-seeded and player-independent,
    # which is the property this test actually guards (ADR-009).
    "market_engine.py": {"_seeded_rng", "_regime_rng"},
    "event_engine.py": {"_seeded_random"},
}

SCANNED_FILES = [
    "engine/market_engine.py",
    "engine/event_engine.py",
    "engine/monthly_processor.py",
    "engine/scoring.py",
    "services/game_service.py",
]

# Any use of these anywhere in the scanned files is hidden non-determinism —
# none of these modules should ever need wall-clock time or random UUIDs for
# a rule that must reprocess identically given the same inputs (ADR-000).
FORBIDDEN_MODULES = {"time", "datetime", "uuid"}


def _find_calls_on_name(tree, target_name, allowed_functions):
    """Returns (lineno, attribute) for every `<target_name>.<attr>(...)` call
    found outside the given allowed enclosing function names."""
    violations = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.func_stack = []

        def visit_FunctionDef(self, node):
            self.func_stack.append(node.name)
            self.generic_visit(node)
            self.func_stack.pop()

        def visit_Call(self, node):
            func = node.func
            if (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == target_name):
                current_func = self.func_stack[-1] if self.func_stack else None
                if current_func not in allowed_functions:
                    violations.append((node.lineno, func.attr))
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


class TestHiddenRandomnessDetection(unittest.TestCase):
    """Static-analysis pass over the actual source files: proves no
    unseeded `random.*` call exists outside the two documented seeded
    wrapper functions, and that no wall-clock/UUID-based nondeterminism
    (time/datetime/uuid) exists anywhere in the deterministic engine layer.
    This directly operationalizes ADR-000 ('Determinism > Randomness ...
    any randomness must be seeded, auditable') as a checkable fact rather
    than a reviewed-by-eye claim."""

    def test_no_unseeded_random_calls_outside_approved_wrappers(self):
        for relative_path in SCANNED_FILES:
            full_path = os.path.join(BACKEND_ROOT, relative_path)
            with self.subTest(file=relative_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=full_path)
                filename = os.path.basename(relative_path)
                allowed = ALLOWED_RANDOM_CALLERS.get(filename, set())
                violations = _find_calls_on_name(tree, "random", allowed)
                self.assertEqual(
                    violations, [],
                    f"Unseeded random.* call(s) found in {relative_path} "
                    f"outside {allowed or '(no functions are allowed to call random directly here)'}: {violations}"
                )

    def test_no_wall_clock_or_uuid_nondeterminism(self):
        for relative_path in SCANNED_FILES:
            full_path = os.path.join(BACKEND_ROOT, relative_path)
            with self.subTest(file=relative_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=full_path)
                for forbidden in FORBIDDEN_MODULES:
                    violations = _find_calls_on_name(tree, forbidden, allowed_functions=set())
                    self.assertEqual(
                        violations, [],
                        f"Non-deterministic {forbidden}.* call(s) found in {relative_path}: {violations}"
                    )

    def test_only_expected_files_import_random(self):
        """A file gaining a new, unreviewed `import random` is itself a
        signal worth catching explicitly, independent of what it does with
        it (covered by the test above regardless, but this pins down the
        expected import surface as its own explicit fact)."""
        expected_importers = set(ALLOWED_RANDOM_CALLERS.keys())
        actual_importers = set()
        engine_dir = os.path.join(BACKEND_ROOT, "engine")
        for filename in os.listdir(engine_dir):
            if not filename.endswith(".py"):
                continue
            with open(os.path.join(engine_dir, filename), "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filename)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "random":
                            actual_importers.add(filename)
        self.assertEqual(actual_importers, expected_importers)

    def test_repeated_instantiation_of_same_seed_never_diverges(self):
        """Belt-and-suspenders behavioral check to accompany the static
        scan: instantiate each seeded helper many times in a loop (as would
        happen across many players/months in one /next-month call) and
        confirm no run ever diverges from the first."""
        baseline = [market_engine._seeded_rng(4).random() for _ in range(30)]
        for _ in range(20):
            repeat = [market_engine._seeded_rng(4).random() for _ in range(30)]
            self.assertEqual(baseline, repeat)

        baseline2 = [event_engine._seeded_random("user-repeat", 4, "events").random() for _ in range(30)]
        for _ in range(20):
            repeat2 = [event_engine._seeded_random("user-repeat", 4, "events").random() for _ in range(30)]
            self.assertEqual(baseline2, repeat2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
