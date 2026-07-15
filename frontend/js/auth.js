// =============================================================================
// AUTH — Email + password (Supabase Auth)
// Replaces the old Google OAuth flow. The backend validates whatever Supabase
// JWT it receives, so no backend change is needed for this switch.
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
  const client = window.supabase;
  if (!client) {
    alert('System error: Supabase not initialised. Check js/config.js.');
    return;
  }

  const form        = document.getElementById('authForm');
  const emailEl     = document.getElementById('email');
  const passEl      = document.getElementById('password');
  const nameField   = document.getElementById('nameField');
  const nameEl      = document.getElementById('fullName');
  const errorBox    = document.getElementById('loginError');
  const loader      = document.getElementById('loader');
  const submitBtn   = document.getElementById('submitBtn');
  const submitLabel = document.getElementById('submitLabel');
  const toggleMode  = document.getElementById('toggleMode');
  const toggleHint  = document.getElementById('toggleHint');

  let mode = 'login'; // 'login' | 'signup'

  function showError(msg) {
    if (!errorBox) { alert(msg); return; }
    errorBox.textContent = msg;
    errorBox.classList.remove('d-none');
  }
  function clearError() { errorBox && errorBox.classList.add('d-none'); }
  function busy(on) {
    if (loader) loader.style.display = on ? 'block' : 'none';
    if (submitBtn) submitBtn.disabled = on;
  }

  // Redirect if already signed in
  checkSessionAndRedirect();

  // React to auth changes (covers refresh-token restore, sign-out, etc.)
  client.auth.onAuthStateChange((event, session) => {
    if (session && (event === 'SIGNED_IN' || event === 'USER_UPDATED')) {
      window.location.href = '/case-study.html';
    } else if (event === 'SIGNED_OUT') {
      window.location.href = '/';
    }
  });

  // Login only — accounts are pre-created by the admin in Supabase.
  // Public signup is disabled in Supabase, so there is no "create account" path.

  // Submit
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearError();
      // Players log in with a plain username. Admin-created accounts use an
      // internal email of <username>@event.local, so map it here. A full email
      // typed by the operator is honoured as-is.
      let email = (emailEl.value || '').trim().toLowerCase();
      if (email && !email.includes('@')) email = email + '@event.local';
      const password = passEl.value || '';
      if (!email || password.length < 6) {
        showError('Enter your username and a password of at least 6 characters.');
        return;
      }
      busy(true);
      try {
        const { error } = await client.auth.signInWithPassword({ email, password });
        if (error) throw error;
        // onAuthStateChange handles the redirect on success
      } catch (err) {
        busy(false);
        showError(err.message || 'Invalid email or password.');
      }
    });
  }
});

// Shared: redirect to the app if a session already exists
async function checkSessionAndRedirect() {
  try {
    const { data: { session } } = await window.supabase.auth.getSession();
    if (session) window.location.href = '/case-study.html';
  } catch (e) {
    console.error('[Auth] Session check failed:', e.message);
  }
}

// Global sign-out helper other pages can call
window.logout = async function () {
  await window.supabase.auth.signOut();
  window.location.href = '/';
};
