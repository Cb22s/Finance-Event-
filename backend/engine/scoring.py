# =============================================================================
# SCORING ENGINE (ADR-008)
# Composite Financial Health Score — the leaderboard ranking metric.
#
# Pure deterministic functions (ADR-007): no I/O, no randomness, no LLM.
# Identical inputs always produce identical scores.
# The formula is PUBLIC to players (ADR-000: player trust).
# =============================================================================

from models.constants import (
    SCORE_WEIGHTS, NW_NORMALIZATION_CAP, LIQUIDITY_TARGET_MONTHS,
    MONTHLY_INCOME, INITIAL_BUDGET
)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def net_worth_component(net_worth: float, month: int) -> float:
    """
    Net worth normalized against total resources received so far
    (initial budget + salaries). Capped at NW_NORMALIZATION_CAP so extreme
    leverage cannot dominate the score. 0-100.
    """
    expected_resources = INITIAL_BUDGET + MONTHLY_INCOME * max(month - 1, 0)
    if expected_resources <= 0:
        return 0.0
    ratio = max(net_worth, 0) / expected_resources
    return _clamp(ratio / NW_NORMALIZATION_CAP * 100)


def liquidity_component(emergency_fund: float, monthly_expense: float) -> float:
    """Months of expenses the emergency fund covers, vs. the target. 0-100."""
    if monthly_expense <= 0:
        return 100.0
    months_covered = emergency_fund / monthly_expense
    return _clamp(months_covered / LIQUIDITY_TARGET_MONTHS * 100)


def debt_control_component(loans: float, total_assets: float) -> float:
    """100 with no debt; falls as debt approaches/exceeds total assets. 0-100."""
    if loans <= 0:
        return 100.0
    if total_assets <= 0:
        return 0.0
    return _clamp((1 - loans / total_assets) * 100)


def risk_protection_component(risk_score: int) -> float:
    """Inverse of the 0-100 portfolio risk score."""
    return _clamp(100 - risk_score)


def calculate_financial_health_score(net_worth: float, month: int,
                                     emergency_fund: float, monthly_expense: float,
                                     loans: float, total_assets: float,
                                     risk_score: int, discipline_avg: float) -> dict:
    """
    Composite Financial Health Score per ADR-008.
    Returns the composite and every component so the breakdown can be
    shown to players (public formula).
    """
    components = {
        "net_worth": round(net_worth_component(net_worth, month), 1),
        "liquidity": round(liquidity_component(emergency_fund, monthly_expense), 1),
        "debt_control": round(debt_control_component(loans, total_assets), 1),
        "risk_protection": round(risk_protection_component(risk_score), 1),
        "discipline": round(_clamp(discipline_avg), 1),
    }
    composite = sum(components[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS)
    return {"score": round(composite, 2), "components": components}


def update_discipline_average(previous_avg: float, month: int, month_grade: float) -> float:
    """
    Running average of monthly discipline grades over months 1..month.
    Month 1 (allocation month) counts as clean; previous_avg starts at 100.
    Deterministic and order-independent given the same grade sequence.
    """
    m = max(month, 1)
    return round((previous_avg * (m - 1) + month_grade) / m, 2)
