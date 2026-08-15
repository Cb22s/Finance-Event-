# =============================================================================
# AI SERVICE (ADR-003 / ADR-014)
# =============================================================================
# The ONLY module allowed to touch an LLM. It does exactly two jobs:
#   1. extract_intent()  — turn free text into a closed-schema intent
#   2. narrate()         — put her reply into words
#
# It NEVER decides a financial outcome. negotiation_service.py does that, from
# seeded rules, with no network access.
#
# EVENT-DAY CONTRACT: every function here returns something useful even with no
# API key, no network, or a timing-out provider. `ai_source` in the return value
# records which path ran ('llm' or 'template') so the audit log shows it.

import os
import json
import random
import urllib.request
import urllib.error

from models.negotiation_intents import (
    parse_offline, validate, IntentError, INTENTS,
    QUESTION_TOPICS, ALTERNATIVES,
)

LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "2.0"))
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

_SCHEMA_HINT = json.dumps({k: {p: t.__name__ for p, t in v.items()}
                           for k, v in INTENTS.items()})


def llm_available() -> bool:
    return bool(ANTHROPIC_KEY)


# ──────────────────────────────────────────────────────────────────────────────
# 1. INTENT EXTRACTION
# ──────────────────────────────────────────────────────────────────────────────
def extract_intent(text: str, proposal: dict) -> dict:
    """
    Free text -> {intent, params, ai_source}.

    The LLM is a CONVENIENCE, not a dependency: on any failure — no key, timeout,
    bad JSON, schema violation — this falls through to the offline parser. A
    result that fails validation is rejected outright rather than guessed at,
    because a wrong guess would spend the player's money (ADR-003).
    """
    if llm_available():
        try:
            raw = _anthropic_json(
                system=(
                    "You extract a single structured intent from a player's message in a "
                    "financial simulation game where they are negotiating a household expense "
                    "with their in-game spouse. Reply with ONLY a JSON object: "
                    '{"intent": <one of ' + ", ".join(INTENTS) + '>, "params": {...}}. '
                    f"Valid schema: {_SCHEMA_HINT}. "
                    f"ASK_QUESTION topics: {sorted(QUESTION_TOPICS)}. "
                    f"PROPOSE_ALTERNATIVE ids: {sorted(ALTERNATIVES)}. "
                    "Amounts are Indian rupees; convert 'k'/'lakh' to integers. "
                    "If the message is ambiguous, reply {\"intent\": null}."
                ),
                user=f"She asked for Rs{proposal['ask']:,} for: {proposal['title']}.\n"
                     f"Player said: {text}",
            )
            data = json.loads(raw)
            if data.get("intent"):
                params = validate(data["intent"], data.get("params") or {})
                return {"intent": data["intent"], "params": params, "ai_source": "llm"}
        except (IntentError, ValueError, KeyError, TypeError):
            pass          # fall through — never trust an unvalidated LLM result
        except Exception:
            pass          # network/provider failure is not the player's problem

    intent, params = parse_offline(text)          # raises IntentError -> handled by route
    return {"intent": intent, "params": validate(intent, params), "ai_source": "template"}


# ──────────────────────────────────────────────────────────────────────────────
# 1b. ARGUMENT FEATURE EXTRACTION (Stage 3B)
# ──────────────────────────────────────────────────────────────────────────────
def extract_argument_features(text: str, proposal: dict) -> dict:
    """
    Extract structured argument features from natural language text.

    Returns:
        {
          "primary_category": "FINANCIAL" | "FAMILY" | "STATUS" | "FUTURE" | "FAIRNESS",
          "secondary_category": str or None,
          "argument_quality": float (0.0 .. 1.0),
          "appeals_to_values": list[str],
          "contains_logical_reasoning": bool,
          "is_aggressive_or_dismissive": bool,
          "confidence_score": float (0.0 .. 1.0),
          "ai_source": "llm" | "fallback"
        }

    SAFETY GUARANTEE: NEVER extracts or returns monetary decision fields.
    Falls back gracefully to default neutral features on any network or parsing error.
    """
    from services.spouse_character_service import (
        validate_argument_features, DEFAULT_ARGUMENT_FEATURES, VALID_PRIMARY_CATEGORIES
    )

    if not text or len(text.strip()) < 3:
        res = validate_argument_features(DEFAULT_ARGUMENT_FEATURES)
        res["ai_source"] = "fallback"
        return res

    if llm_available():
        try:
            raw = _anthropic_json(
                system=(
                    "You analyze the reasoning in a player's natural-language message during a "
                    "financial negotiation with their in-game spouse. Extract structured features ONLY. "
                    "Do NOT decide monetary outcomes, prices, or decisions. Reply with ONLY a JSON object: "
                    "{\n"
                    f'  "primary_category": <one of {sorted(VALID_PRIMARY_CATEGORIES)}>,\n'
                    '  "secondary_category": <one of ' + str(sorted(VALID_PRIMARY_CATEGORIES)) + ' or null>,\n'
                    '  "argument_quality": <float 0.0 to 1.0 measuring logical depth>,\n'
                    '  "appeals_to_values": [<strings from "prudence", "family", "status", "future_security", "fairness">],\n'
                    '  "contains_logical_reasoning": <boolean>,\n'
                    '  "is_aggressive_or_dismissive": <boolean>,\n'
                    '  "confidence_score": <float 0.0 to 1.0>\n'
                    "}"
                ),
                user=f"Spouse proposal: Rs{proposal['ask']:,} for '{proposal['title']}'.\n"
                     f"Player said: '{text}'"
            )
            data = json.loads(raw)
            features = validate_argument_features(data)
            features["ai_source"] = "llm"
            return features
        except Exception:
            pass  # Fall through to deterministic fallback on any LLM/network error

    res = validate_argument_features(DEFAULT_ARGUMENT_FEATURES)
    res["ai_source"] = "fallback"
    return res


# ──────────────────────────────────────────────────────────────────────────────
# 2. NARRATION
# ──────────────────────────────────────────────────────────────────────────────
_FALLBACK_LINES = {
    "continue": [
        "I hear you, but that is not enough. Talk to me properly.",
        "You are not going to settle this in one sentence. What else can we do?",
        "I have thought about this a lot. Convince me.",
    ],
    "accepted_full": [
        "Thank you. Genuinely — that means a lot to me.",
        "You did not even argue. I appreciate that.",
    ],
    "accepted_counter": [
        "Fine. We will make it work at that.",
        "All right. Not what I wanted, but I can live with it.",
    ],
    "refused": [
        "So that is a no. I will remember this one.",
        "Right. I will drop it, then.",
    ],
    "delayed": [
        "Later, then. I will hold you to it.",
        "We keep saying later. Fine.",
    ],
    "auto_resolved": [
        "We were going in circles, so I went ahead and arranged it.",
        "I could not wait any longer. It is done.",
    ],
    "invalid": [
        "That does not make sense to me. Say it another way?",
    ],
}


def narrate(outcome: str, reason: str, proposal: dict, spouse_name: str,
            satisfaction: int, dialogue_rows: list = None) -> dict:
    """
    Her reply. Purely cosmetic — the outcome is already decided by the rules
    engine before this is called, and nothing here can change it.
    """
    # Admin-authored line bank wins when present.
    if dialogue_rows:
        matches = [d["line"] for d in dialogue_rows if d.get("outcome") == outcome]
        if matches:
            return {"line": random.choice(matches), "ai_source": "template"}

    if llm_available():
        try:
            line = _anthropic_text(
                system=(
                    f"You are {spouse_name}, a character in an Indian personal-finance "
                    "simulation game. You are speaking to your spouse about a household "
                    "expense. Reply in ONE or TWO short sentences, warm and human, never "
                    "cruel. Do NOT invent numbers or promise financial outcomes — the "
                    "result has already been decided. Never break character."
                ),
                user=(f"Topic: {proposal['title']} (you asked for Rs{proposal['ask']:,}).\n"
                      f"Outcome: {outcome}. Context: {reason}\n"
                      f"Your current happiness with them: {satisfaction}/100."),
            )
            if line:
                return {"line": line.strip(), "ai_source": "llm"}
        except Exception:
            pass

    pool = _FALLBACK_LINES.get(outcome) or _FALLBACK_LINES["continue"]
    return {"line": random.choice(pool), "ai_source": "template"}


# ──────────────────────────────────────────────────────────────────────────────
# Provider transport — stdlib only, hard timeout, no retries.
# A retry loop would multiply event-day latency; failing fast to templates is
# strictly better for the player.
# ──────────────────────────────────────────────────────────────────────────────
def _anthropic_call(system: str, user: str, max_tokens: int) -> str:
    payload = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SECONDS) as resp:
        body = json.loads(resp.read().decode())
    return "".join(b.get("text", "") for b in body.get("content", []))


def _anthropic_json(system: str, user: str) -> str:
    return _anthropic_call(system, user, 200)


def _anthropic_text(system: str, user: str) -> str:
    return _anthropic_call(system, user, 150)
