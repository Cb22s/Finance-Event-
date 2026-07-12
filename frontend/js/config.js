// ⬇️ FILL THESE FROM YOUR FRESH SUPABASE PROJECT
//    Supabase Dashboard → Project Settings → API
//    - Project URL      → SUPABASE_URL
//    - anon public key   → SUPABASE_ANON_KEY   (safe to expose in the browser)
//    Do NOT put the service_role key here — that belongs only in backend/.env
const SUPABASE_URL = "https://ujoqdsesfctxmzmlxewu.supabase.co";

const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVqb3Fkc2VzZmN0eG16bWx4ZXd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM2MDE4MDIsImV4cCI6MjA5OTE3NzgwMn0.QMSm9_jiV_Y-_H4PKWFeHLRgWISrEqELGdGiI_VZcJI";

// Auto-detect: use the local Flask backend when opened via localhost,
// otherwise the deployed Render backend. No manual switching needed.
const _isLocal = ["localhost", "127.0.0.1"].includes(location.hostname);
const API_BASE_URL = _isLocal
  ? "http://localhost:5000"
  : "https://finance-event.onrender.com";

// Session persistence: login survives browser restarts; access tokens
// auto-refresh in the background so users (and admins) are never silently
// logged out mid-event. Tokens still rotate hourly — a leaked token dies
// fast, but the session itself lives until explicit logout.
window.supabase = window.supabase.createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storage: window.localStorage
    }
  }
);

// Backward compatibility for existing code using 'db'
window.db = window.supabase;
