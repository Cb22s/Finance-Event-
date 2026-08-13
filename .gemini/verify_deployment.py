import requests
import json
from supabase import create_client

SUPABASE_URL = "https://ujoqdsesfctxmzmlxewu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVqb3Fkc2VzZmN0eG16bWx4ZXd1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzYwMTgwMiwiZXhwIjoyMDk5MTc3ODAyfQ.9zXvonC6BSfAMAzNeQxLfro6yPDiRkM1w-8aWyD-_EE"

def run_tests():
    results = {}
    
    # 1. Backend Health
    try:
        r = requests.get("http://localhost:5000/health", timeout=5)
        results["Backend Health (/health)"] = "PASS" if r.status_code == 200 and r.json().get("status") == "ok" else f"FAIL ({r.status_code})"
    except Exception as e:
        results["Backend Health (/health)"] = f"FAIL ({e})"

    # 2. Supabase DB Connectivity & RPC Verification
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.table("game_control").select("*").limit(1).execute()
        results["Database Connectivity (game_control)"] = "PASS" if res.data is not None else "FAIL"
        
        # Test RPC player_apply_atomic for non-existent player (action_key=None -> checks player_state FOR UPDATE -> PLAYER_NOT_FOUND)
        dummy_uid = "00000000-0000-0000-0000-000000000000"
        try:
            supabase.rpc("player_apply_atomic", {
                "p_user_id": dummy_uid,
                "p_month": 1,
                "p_action_key": None,
                "p_require_cash": None,
                "p_deltas": {},
                "p_sets": {},
                "p_clamp_satisfaction": False,
                "p_recompute_networth": False,
                "p_loan_inserts": [],
                "p_loan_updates": []
            }).execute()
            results["RPC player_apply_atomic (PLAYER_NOT_FOUND error handling)"] = "FAIL (No exception raised)"
        except Exception as rpc_e:
            err_msg = str(rpc_e)
            if "PLAYER_NOT_FOUND" in err_msg:
                results["RPC player_apply_atomic (PLAYER_NOT_FOUND error handling)"] = "PASS"
            else:
                results["RPC player_apply_atomic (PLAYER_NOT_FOUND error handling)"] = f"FAIL ({err_msg})"

    except Exception as e:
        results["Database Connectivity"] = f"FAIL ({e})"

    # 3. Frontend Local Server Check (HTML pages loading)
    pages = [
        ("index.html", "Landing/Login Page"),
        ("dashboard.html", "Player Dashboard"),
        ("admin-login.html", "Admin Login Page"),
        ("admin.html", "Admin Dashboard"),
        ("leaderboard.html", "Leaderboard Page"),
        ("allocation.html", "Allocation Page"),
        ("case-study.html", "Case Study Page")
    ]
    for filename, title in pages:
        try:
            r = requests.get(f"http://localhost:5500/{filename}", timeout=5)
            results[f"Frontend Page: {title}"] = "PASS" if r.status_code == 200 else f"FAIL ({r.status_code})"
        except Exception as e:
            results[f"Frontend Page: {title}"] = f"FAIL ({e})"

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_tests()
