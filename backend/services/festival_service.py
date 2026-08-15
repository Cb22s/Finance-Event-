# =============================================================================
# FESTIVAL BUDGET GENERATOR (Stage 2 formula + Phase 3A character adjustment)
# =============================================================================
# Produces the Month-6 festival's INITIAL ask as a proposal dict in exactly the
# shape negotiation_service.evaluate() already consumes. This module decides
# the OPENING number only; every rupee of the negotiation itself is decided by
# the unchanged rules engine (floors, rounds, counteroffers, satisfaction).
#
# Phase 3A contract:
#   Economic Archetype + Character Traits + Festival Context
#         -> character-adjusted initial festival budget
#         -> EXISTING negotiation engine (untouched)
#
# Deterministic, no LLM, no network, no randomness: the same player with the
# same spouse always gets the same ask, so a page refresh cannot reroll it —
# the same idempotency rule as generate_proposal.
# FLX deliberately does not appear here: it drives negotiation in Phase 3B.

from models.constants import (
    MONTHLY_INCOME, LIFESTYLE_COSTS, SPOUSE_BASE_EXPENSE, ARCHETYPES,
    CHARACTER_PROFILES, FESTIVAL_EVENT,
    POSTURE_SCALE, POSTURE_MIN, POSTURE_MAX,
    CHAR_ADJ_MIN, CHAR_ADJ_MAX,
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _round500(value: float) -> int:
    return int(round(value / 500.0) * 500)


def char_adjustment(archetype_id: str) -> float:
    """
    Stage-3 approved CharAdj. Status and family pressure raise the ask;
    prudence lowers it. Clamped so character never overwhelms economics.

        CharAdj = clamp(1 + 0.15*(STA-50)/50 + 0.15*(FAM-50)/50
                          - 0.08*(PRU-50)/50, 0.85, 1.25)
    """
    traits = CHARACTER_PROFILES.get(archetype_id)
    if not traits:
        return 1.0  # unknown spouse: character-neutral, Stage-2 behaviour
    raw = (1.0
           + 0.15 * (traits["STA"] - 50) / 50.0
           + 0.15 * (traits["FAM"] - 50) / 50.0
           - 0.08 * (traits["PRU"] - 50) / 50.0)
    return _clamp(raw, CHAR_ADJ_MIN, CHAR_ADJ_MAX)


def compute_festival_ask(archetype_id: str) -> int:
    """
    Stage-2B approved Model C formula (Monthly Household Net Surplus Anchor)
    with the Phase-3A character multiplier:

        HHI              = player income + spouse income
        Mandatory Living = city base living cost + spouse base expense + expense_mod
        Monthly Surplus  = max(1000, HHI - Mandatory Living)
        Posture          = clamp(1 + expense_mod / 30000, 0.85, 1.20)
        Base Capacity    = Monthly Surplus * base_k * posture * importance
        Ask              = round500(Base Capacity * CharAdj)

    Deterministic, grounded in discretionary cash flow capacity.
    """
    arch = ARCHETYPES[archetype_id]
    hhi = MONTHLY_INCOME + arch["income"]
    mandatory_living = (LIFESTYLE_COSTS["city"]["total"]
                        + SPOUSE_BASE_EXPENSE
                        + arch["expense_mod"])
    surplus_mo = max(1000.0, hhi - mandatory_living)
    posture = _clamp(1.0 + arch["expense_mod"] / float(POSTURE_SCALE),
                     POSTURE_MIN, POSTURE_MAX)
    raw = (surplus_mo * FESTIVAL_EVENT["base_k"] * posture
           * FESTIVAL_EVENT["importance"] * char_adjustment(archetype_id))
    return _round500(raw)


def generate_festival_budget(user_id: str, month: int, archetype_id: str) -> dict:
    """
    Build the festival proposal. Signature mirrors generate_proposal (user_id
    is the seed slot — unused today because the ask is fully deterministic,
    kept so a future seeded jitter needs no interface change).

    Returns the exact dict shape evaluate()/the UI already consume. kind
    'festival' carries no financial return in _effects — pure consumption,
    like 'lifestyle', which is the point of it.
    """
    if archetype_id not in ARCHETYPES:
        return None
    return {
        "archetype_id": archetype_id,
        "kind": FESTIVAL_EVENT["kind"],
        "title": FESTIVAL_EVENT["title"],
        "description": FESTIVAL_EVENT["description"],
        "ev_note": FESTIVAL_EVENT["ev_note"],
        "ask": compute_festival_ask(archetype_id),
        "month": month,
    }
