import json
from supabase import create_client

SUPABASE_URL = "https://ujoqdsesfctxmzmlxewu.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVqb3Fkc2VzZmN0eG16bWx4ZXd1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzYwMTgwMiwiZXhwIjoyMDk5MTc3ODAyfQ.9zXvonC6BSfAMAzNeQxLfro6yPDiRkM1w-8aWyD-_EE"

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
