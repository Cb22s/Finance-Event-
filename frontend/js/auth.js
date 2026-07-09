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

  // Toggle between login and signup
  if (toggleMode) {
    toggleMode.addEventListener('click', (e) => {
      e.preventDefault();
      clearError();
      if (mode === 'login') {
        mode = 'signup';
        nameField.style.display = 'block';
        submitLabel.textContent = 'Create account';
        toggleHint.textContent = 'Already have an account?';
        toggleMode.textContent = 'Log in';
        passEl.setAttribute('autocomplete', 'new-password');
      } else {
        mode = 'login';
        nameField.style.display = 'none';
        submitLabel.textContent = 'Log in';
        toggleHint.textContent = 'New here?';
        toggleMode.textContent = 'Create an account';
        passEl.setAttribute('autocomplete', 'current-password');
      }
    });
  }

  // Submit
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearError();
      const email = (emailEl.value || '').trim();
      const password = passEl.value || '';
      if (!email || password.length < 6) {
        showError('Enter a valid email and a password of at least 6 characters.');
        return;
      }
      busy(true);
      try {
        if (mode === 'signup') {
          const { data, error } = await client.auth.signUp({
            email,
            password,
            options: { data: { name: (nameEl.value || '').trim() || email.split('@')[0] } }
          });
          if (error) throw error;
          // If email confirmation is OFF, a session is returned and the
          // onAuthStateChange listener redirects. If it's ON, tell the user.
          if (!data.session) {
            busy(false);
            showError('Account created. Check your email to confirm, then log in.');
            return;
          }
        } else {
          const { error } = await client.auth.signInWithPassword({ email, password });
          if (error) throw error;
          // onAuthStateChange handles redirect
        }
      } catch (err) {
        busy(false);
        showError(err.message || 'Authentication failed.');
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
