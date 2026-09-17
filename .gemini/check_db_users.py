import json
import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY before running this script.")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("--- USERS TABLE ---")
res_users = supabase.table("users").select("*").execute()
print(json.dumps(res_users.data, indent=2))

print("--- ADMINS TABLE ---")
res_admins = supabase.table("admins").select("*").execute()
print(json.dumps(res_admins.data, indent=2))

print("--- PLAYER STATE TABLE ---")
res_ps = supabase.table("player_state").select("user_id, month, cash, net_worth, status").execute()
print(json.dumps(res_ps.data, indent=2))
