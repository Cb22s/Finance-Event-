// ⬇️ FILL THESE FROM YOUR FRESH SUPABASE PROJECT
//    Supabase Dashboard → Project Settings → API
//    - Project URL      → SUPABASE_URL
//    - anon public key   → SUPABASE_ANON_KEY   (safe to expose in the browser)
//    Do NOT put the service_role key here — that belongs only in backend/.env
const SUPABASE_URL = "https://YOUR-NEW-PROJECT-REF.supabase.co";

const SUPABASE_ANON_KEY = "PASTE-YOUR-NEW-ANON-PUBLIC-KEY-HERE";

// Auto-detect: use the local Flask backend when opened via localhost,
// otherwise the deployed Render backend. No manual switching needed.
const _isLocal = ["localhost", "127.0.0.1"].includes(location.hostname);
const API_BASE_URL = _isLocal
  ? "http://localhost:5000"
  : "https://financial-pecc.onrender.com";

window.supabase = window.supabase.createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY
);

// Backward compatibility for existing code using 'db'
window.db = window.supabase;
