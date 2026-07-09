# =============================================================================
# AUTH SERVICE — Handles user authentication via Supabase
# =============================================================================

import os
import hmac
from functools import wraps

from flask import request, jsonify

from supabase_client import supabase


def _admin_token_valid(request) -> bool:
    """Return True only if a correct admin token is present."""
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        print("[Auth] ADMIN_TOKEN is not configured — refusing all admin access.")
        return False
    provided = request.headers.get("X-Admin-Token", "")
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)


def admin_required(fn):
    """Decorator that blocks a route unless a valid admin token is supplied."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _admin_token_valid(request):
            return jsonify({"error": "Admin authorization required."}), 401
        return fn(*args, **kwargs)
    return wrapper


def get_user_id(request) -> str | None:
    """Extract user_id from Bearer token via Supabase Auth."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    try:
        user_res = supabase.auth.get_user(token)
        return user_res.user.id
    except Exception as e:
        print(f"[Auth] Token validation failed: {e}")
        return None


def require_auth(request):
    """Returns user_id or raises a tuple (error_response, status_code)."""
    uid = get_user_id(request)
    if not uid:
        return None
    return uid
