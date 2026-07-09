# =============================================================================
# AUTH SERVICE — Handles user authentication via Supabase
# =============================================================================

import os
import hmac
from functools import wraps

from flask import request, jsonify

from supabase_client import supabase


def is_admin_user(uid: str) -> bool:
    """True only if this user id is listed in the server-only public.admins table.
    Clients can't read/write that table (RLS with no policies); only this backend
    can, using the service_role key."""
    if not uid:
        return False
    try:
        res = supabase.table('admins').select('user_id').eq('user_id', uid).limit(1).execute()
        return bool(res.data)
    except Exception as e:
        print(f"[Auth] admin check failed: {e}")
        return False


def admin_required(fn):
    """Decorator: allow only a signed-in Supabase user who is in public.admins.
    The client must send the user's Supabase session token as
    'Authorization: Bearer <access_token>'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = get_user_id(request)
        if not uid or not is_admin_user(uid):
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
