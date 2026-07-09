// =============================================================================
// ADMIN LOGIN — email/password, then verify the account is a real admin.
// A successful Supabase login is NOT enough: we call the backend /admin/me with
// the session token, and the backend checks the server-only public.admins table.
// Non-admins are signed out immediately so a student session can't reach here.
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
  const client = window.supabase;
  if (!client) { alert('Supabase not initialised. Check js/config.js.'); return; }

  const form      = document.getElementById('adminForm');
  const emailEl   = document.getElementById('email');
  const passEl    = document.getElementById('password');
  const errorBox  = document.getElementById('loginError');
  const loader    = document.getElementById('loader');
  const submitBtn = document.getElementById('submitBtn');

  const showError = (m) => { errorBox.textContent = m; errorBox.classList.remove('d-none'); };
  const clearError = () => errorBox.classList.add('d-none');
  const busy = (on) => { loader.style.display = on ? 'block' : 'none'; submitBtn.disabled = on; };

  // If already signed in AND already an admin, skip straight to the panel.
  verifyAdmin().then((ok) => { if (ok) window.location.href = '/admin.html'; });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();
    busy(true);
    try {
      const { error } = await client.auth.signInWithPassword({
        email: (emailEl.value || '').trim(),
        password: passEl.value || ''
      });
      if (error) throw error;

      const ok = await verifyAdmin();
      if (ok) {
        window.location.href = '/admin.html';
      } else {
        await client.auth.signOut();          // don't leave a non-admin session around
        busy(false);
        showError('This account is not an admin.');
      }
    } catch (err) {
      busy(false);
      showError(err.message || 'Login failed.');
    }
  });
});

// Returns true only if there's a session AND the backend confirms admin rights.
async function verifyAdmin() {
  try {
    const { data: { session } } = await window.supabase.auth.getSession();
    if (!session) return false;
    const res = await fetch(`${API_BASE_URL}/admin/me`, {
      headers: { 'Authorization': 'Bearer ' + session.access_token }
    });
    return res.ok;
  } catch (e) {
    console.error('[AdminLogin] verify failed:', e.message);
    return false;
  }
}
