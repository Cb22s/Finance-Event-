# =============================================================================
# DEPRECATED — this module is dead code and intentionally left empty.
# =============================================================================
# It previously held duplicate copies of fair_roll, an in-memory rate-limit,
# auth/DB helpers, and a STALE validate_rpc_payload whose required-field set was
# out of date (missing the ADR-008 discipline_score / financial_health_score
# fields). Nothing imports it (verified). The live implementations are:
#
#   - fair_roll, mark_action/action_done, validate_rpc_payload, DB helpers
#         -> backend/services/game_service.py
#   - get_user_id / admin_required
#         -> backend/services/auth_service.py
#
# Do NOT re-add helpers here. Importing from this module is unsupported; use the
# services modules above. Kept as an empty stub only because file deletion was
# not available in the hardening environment — safe to `git rm backend/utils.py`.
# See QA_REPORT_V1.md F-08.
