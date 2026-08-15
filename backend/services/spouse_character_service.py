# =============================================================================
# SPOUSE CHARACTER SERVICE (Stage 3B)
# =============================================================================
# Deterministic evaluation module for spouse character traits (PRU, STA, FAM, FLX).
#
# ABSOLUTE AI RULE (ADR-003 / ADR-014):
# The LLM extracts argument features/categories ONLY. This service converts those
# features into deterministic negotiation parameters (effective floor ratio,
# trait alignment, counteroffer step-size bounds).
#
# THIS SERVICE NEVER TOUCHES AN LLM AND HAS ZERO NETWORK DEPENDENCIES.
# =============================================================================

from models.constants import (
    CHARACTER_PROFILES, NEGOTIATION_FLOOR_RATIO,
    SATISFACTION_MIN, SATISFACTION_MAX, NEGOTIATION_HARDNESS,
)

# ── ARGUMENT TAXONOMY ─────────────────────────────────────────────────────────
VALID_PRIMARY_CATEGORIES = {"FINANCIAL", "FAMILY", "STATUS", "FUTURE", "FAIRNESS"}

VALID_SUBCATEGORIES = {
    "FINANCIAL": {"financial_cashflow", "emergency_fund", "debt_obligations", "investment_goals"},
    "FAMILY": {"elder_respect", "tradition", "relative_hospitality"},
    "STATUS": {"social_reputation", "guest_experience", "quality_standards"},
    "FUTURE": {"upcoming_expenses", "financial_security", "long_term_planning"},
    "FAIRNESS": {"mutual_compromise", "shared_responsibility", "reasonableness"},
}

DEFAULT_ARGUMENT_FEATURES = {
    "primary_category": "FINANCIAL",
    "secondary_category": None,
    "argument_quality": 0.50,
    "appeals_to_values": ["prudence"],
    "contains_logical_reasoning": False,
    "is_aggressive_or_dismissive": False,
    "confidence_score": 0.0,
}


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def validate_argument_features(raw_data: dict) -> dict:
    """
    Validate and clamp LLM-extracted argument features.
    Strictly rejects any attempt to inject monetary decision fields.
    """
    if not isinstance(raw_data, dict):
        return dict(DEFAULT_ARGUMENT_FEATURES)

    # SAFETY GATE: Reject forbidden monetary fields if present
    forbidden_keys = {"accept_offer", "new_price", "agreed_amount", "decision", "discount", "floor"}
    if any(k in raw_data for k in forbidden_keys):
        # Discard invalid output and use clean defaults
        res = dict(DEFAULT_ARGUMENT_FEATURES)
        res["confidence_score"] = 0.0
        return res

    primary = str(raw_data.get("primary_category", "FINANCIAL")).upper()
    if primary not in VALID_PRIMARY_CATEGORIES:
        primary = "FINANCIAL"

    secondary = raw_data.get("secondary_category")
    if secondary:
        secondary = str(secondary).upper()
        if secondary not in VALID_PRIMARY_CATEGORIES or secondary == primary:
            secondary = None

    try:
        quality = float(raw_data.get("argument_quality", 0.50))
    except (ValueError, TypeError):
        quality = 0.50
    quality = _clamp(quality, 0.0, 1.0)

    try:
        confidence = float(raw_data.get("confidence_score", 0.50))
    except (ValueError, TypeError):
        confidence = 0.50
    confidence = _clamp(confidence, 0.0, 1.0)

    logical = bool(raw_data.get("contains_logical_reasoning", False))
    aggressive = bool(raw_data.get("is_aggressive_or_dismissive", False))
    appeals = list(raw_data.get("appeals_to_values") or [])

    return {
        "primary_category": primary,
        "secondary_category": secondary,
        "argument_quality": quality,
        "appeals_to_values": appeals,
        "contains_logical_reasoning": logical,
        "is_aggressive_or_dismissive": aggressive,
        "confidence_score": confidence,
    }


def calculate_trait_alignment(archetype_id: str, primary_category: str, quality: float,
                               is_aggressive: bool = False, is_repeated: bool = False) -> float:
    """
    Compute how strongly the player's argument aligns with the spouse's traits.
    Scale: 0.0 to 1.0.
    """
    traits = CHARACTER_PROFILES.get(archetype_id, {"PRU": 50, "STA": 50, "FAM": 50, "FLX": 50})
    pru = traits["PRU"] / 100.0
    sta = traits["STA"] / 100.0
    fam = traits["FAM"] / 100.0
    flx = traits["FLX"] / 100.0

    if primary_category == "FINANCIAL":
        weight = pru
    elif primary_category == "STATUS":
        weight = sta
    elif primary_category == "FAMILY":
        weight = fam
    elif primary_category == "FUTURE":
        weight = pru * 0.7 + fam * 0.3
    elif primary_category == "FAIRNESS":
        weight = fam * 0.5 + flx * 0.5
    else:
        weight = 0.5

    effective_quality = quality
    if is_aggressive:
        effective_quality *= 0.5
    if is_repeated:
        effective_quality *= 0.5  # Diminishing returns on repeated category

    return _clamp(weight * effective_quality, 0.0, 1.0)


def evaluate_spouse_character(archetype_id: str, argument_features: dict,
                              satisfaction: float, round_no: int,
                              previous_category: str = None) -> dict:
    """
    Deterministic Spouse Character Evaluation.

    Calculates:
      - trait_alignment (T_align): 0.0 .. 1.0
      - delta_floor: 0.0 .. 0.15
      - effective_floor_ratio: clamped at NEGOTIATION_FLOOR_RATIO[archetype_id]
      - reasoning_framing: character dialogue context string
    """
    features = validate_argument_features(argument_features)
    traits = CHARACTER_PROFILES.get(archetype_id, {"PRU": 50, "STA": 50, "FAM": 50, "FLX": 50})
    flx = traits["FLX"] / 100.0

    is_repeated = bool(previous_category and previous_category == features["primary_category"])
    t_align = calculate_trait_alignment(
        archetype_id, features["primary_category"], features["argument_quality"],
        is_aggressive=features["is_aggressive_or_dismissive"],
        is_repeated=is_repeated
    )

    # Delta floor: bounded discount on floor ratio based on T_align & FLX (max 0.15)
    delta_floor = _clamp(0.15 * t_align * flx, 0.0, 0.15)

    # Base min ratio from satisfaction (from constants.py negotiation_min_ratio logic)
    hard_floor = NEGOTIATION_FLOOR_RATIO.get(archetype_id, 0.60)
    sat = _clamp(satisfaction, SATISFACTION_MIN, SATISFACTION_MAX)
    unhappiness = 1.0 - (sat / 100.0)
    base_min_ratio = hard_floor + (1.0 - hard_floor) * unhappiness * NEGOTIATION_HARDNESS

    # ABSOLUTE HARD CAP: effective_floor_ratio can NEVER fall below hard_floor!
    effective_floor_ratio = max(hard_floor, base_min_ratio - delta_floor)

    # Dialogue framing helper based on archetype and evaluated alignment
    framing = _generate_character_framing(archetype_id, features["primary_category"], t_align)

    return {
        "archetype_id": archetype_id,
        "primary_category": features["primary_category"],
        "argument_quality": features["argument_quality"],
        "trait_alignment": round(t_align, 3),
        "delta_floor": round(delta_floor, 3),
        "base_min_ratio": round(base_min_ratio, 3),
        "effective_floor_ratio": round(effective_floor_ratio, 3),
        "hard_floor_ratio": hard_floor,
        "is_repeated": is_repeated,
        "framing": framing,
    }


def _generate_character_framing(archetype_id: str, category: str, t_align: float) -> str:
    """Generate narrative character framing for dialogue synthesis."""
    if archetype_id == "saver":
        if category in ("FINANCIAL", "FUTURE") and t_align >= 0.5:
            return "She respects your focus on household savings and emergency safety."
        if category == "FAMILY" and t_align >= 0.5:
            return "She appreciates honoring family tradition without wasteful spending."
        return "She remains cautious about spending beyond core household needs."

    if archetype_id == "earner":
        if category == "STATUS" and t_align >= 0.5:
            return "She appreciates maintaining our social image and quality standards."
        if t_align < 0.4:
            return "She feels a low budget compromises our standing with the family."
        return "She expects the event to reflect our professional and social standing."

    if archetype_id == "investor":
        if category in ("FINANCIAL", "FUTURE") and t_align >= 0.5:
            return "She strongly agrees with protecting liquidity and capital growth."
        return "She evaluates the budget logically against alternative capital uses."

    if archetype_id == "anchor":
        if category in ("FAMILY", "FINANCIAL") and t_align >= 0.5:
            return "She appreciates balancing family turnout with household stability."
        return "She seeks a dependable, stable compromise that keeps the peace."

    return "She considers your proposal within household budget limits."
