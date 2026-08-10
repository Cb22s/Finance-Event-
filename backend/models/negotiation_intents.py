# =============================================================================
# NEGOTIATION INTENT SCHEMA (ADR-003 constraint, ADR-014)
# =============================================================================
# CLOSED schema: a fixed enum with typed parameters. Anything that does not match
# is REJECTED, never guessed. A wrong guess here would move real money on a
# ranked leaderboard, so ambiguity must fail loudly and be handed back to the
# player for clarification.
#
# This module has NO network dependency. The offline parser below is good enough
# to run the entire negotiation without an LLM, which is what makes the event-day
# fallback real rather than theoretical.

import re

ACCEPT_PROPOSAL = "ACCEPT_PROPOSAL"
COUNTER_OFFER = "COUNTER_OFFER"
REQUEST_DELAY = "REQUEST_DELAY"
PROPOSE_ALTERNATIVE = "PROPOSE_ALTERNATIVE"
ASK_QUESTION = "ASK_QUESTION"
REFUSE = "REFUSE"

INTENTS = {
    ACCEPT_PROPOSAL: {},
    COUNTER_OFFER: {"amount": int},
    REQUEST_DELAY: {"months": int},
    PROPOSE_ALTERNATIVE: {"alternative_id": str},
    ASK_QUESTION: {"topic": str},
    REFUSE: {},
}

QUESTION_TOPICS = {"cost", "why", "alternatives", "timing", "affordability"}
ALTERNATIVES = {"cheaper_venue", "smaller_scale", "split_over_months", "family_help"}

DELAY_MIN_MONTHS = 1
DELAY_MAX_MONTHS = 3


class IntentError(ValueError):
    """Raised when text cannot be mapped to exactly one valid intent."""


def validate(intent: str, params: dict) -> dict:
    """
    Validate an intent+params pair against the closed schema.
    Returns cleaned params. Raises IntentError on anything unrecognised —
    we never silently coerce, because coercion here spends the player's money.
    """
    if intent not in INTENTS:
        raise IntentError(f"Unknown intent '{intent}'.")

    spec = INTENTS[intent]
    params = params or {}
    clean = {}

    for key, typ in spec.items():
        if key not in params or params[key] is None:
            raise IntentError(f"'{intent}' requires '{key}'.")
        try:
            clean[key] = typ(params[key])
        except (TypeError, ValueError):
            raise IntentError(f"'{key}' must be {typ.__name__}.")

    extra = set(params) - set(spec)
    if extra:
        raise IntentError(f"Unexpected parameter(s): {sorted(extra)}.")

    if intent == COUNTER_OFFER and clean["amount"] < 0:
        raise IntentError("A counter-offer cannot be negative.")
    if intent == REQUEST_DELAY and not (DELAY_MIN_MONTHS <= clean["months"] <= DELAY_MAX_MONTHS):
        raise IntentError(f"Delay must be {DELAY_MIN_MONTHS}-{DELAY_MAX_MONTHS} months.")
    if intent == PROPOSE_ALTERNATIVE and clean["alternative_id"] not in ALTERNATIVES:
        raise IntentError(f"Unknown alternative. Choose from {sorted(ALTERNATIVES)}.")
    if intent == ASK_QUESTION and clean["topic"] not in QUESTION_TOPICS:
        raise IntentError(f"Unknown topic. Choose from {sorted(QUESTION_TOPICS)}.")

    return clean


# ──────────────────────────────────────────────────────────────────────────────
# OFFLINE PARSER — the event-day fallback
# ──────────────────────────────────────────────────────────────────────────────
_MONEY = re.compile(r'(?:rs\.?|inr|₹)?\s*(\d[\d,]*)\s*(k|thousand|lakh|l)?\b', re.I)
_ACCEPT = re.compile(r'\b(ok(ay)?|agree|accept|fine|yes|deal|go ahead|approved?|sure)\b', re.I)
_REFUSE = re.compile(r"\b(no|refuse|reject|can'?t afford|cannot afford|not possible|decline|drop it)\b", re.I)
_DELAY = re.compile(r'\b(later|next month|postpone|delay|wait|defer)\b', re.I)
_QUESTION = re.compile(r'\b(why|how much|what for|explain|can we afford)\b', re.I)


def _money_to_int(num: str, suffix: str | None) -> int:
    v = int(num.replace(",", ""))
    if suffix:
        s = suffix.lower()
        if s in ("k", "thousand"):
            v *= 1000
        elif s in ("lakh", "l"):
            v *= 100000
    return v


def parse_offline(text: str) -> tuple[str, dict]:
    """
    Best-effort intent extraction with no network. Deliberately conservative:
    when the text is ambiguous it raises rather than guessing, and the UI asks
    the player to rephrase or use a number.
    """
    if not text or not text.strip():
        raise IntentError("Say something to her first.")
    t = text.strip()

    money = _MONEY.search(t)
    has_accept = bool(_ACCEPT.search(t))
    has_refuse = bool(_REFUSE.search(t))
    has_delay = bool(_DELAY.search(t))

    if has_accept and has_refuse:
        raise IntentError("That reads as both yes and no — could you rephrase?")

    # A number present means a concrete counter-offer, which outranks softer cues.
    if money:
        amount = _money_to_int(money.group(1), money.group(2))
        if has_delay and amount <= DELAY_MAX_MONTHS:
            return REQUEST_DELAY, {"months": amount}
        return COUNTER_OFFER, {"amount": amount}

    if has_delay:
        return REQUEST_DELAY, {"months": 1}
    if has_refuse:
        return REFUSE, {}
    if has_accept:
        return ACCEPT_PROPOSAL, {}
    if _QUESTION.search(t):
        return ASK_QUESTION, {"topic": "why"}

    raise IntentError(
        "I could not tell what you meant. Try naming an amount "
        "(for example “I can do ₹15,000”), or say yes, no, or later."
    )
