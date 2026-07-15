// ============================================================================
// ADMIN PANEL — Game control, event management, leaderboard
// ============================================================================

// Escape user-controlled strings before inserting into innerHTML. Player names
// (public.users.name) are editable by the logged-in student via RLS, so they
// must be treated as untrusted when rendered. Prevents stored XSS in the admin
// standings. Security hardening only — legitimate names render identically.
function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (c) => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast-glass toast-${type}`;
    const icons = { error: 'fa-circle-xmark', success: 'fa-circle-check', info: 'fa-circle-info' };
    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function showSystemLog(msg, type = 'success') {
    const el = document.getElementById('systemLog');
    const text = document.getElementById('systemLogText');
    el.className = `alert-glass alert-${type} mb-section animate-slide-down`;
    text.innerText = msg;
    el.style.display = 'flex';
    setTimeout(() => { el.style.display = 'none'; }, 6000);
}

function formatINR(val) {
    return `₹${Math.floor(val || 0).toLocaleString('en-IN')}`;
}

// ============================================================================
// ADMIN AUTH — every privileged call carries the admin's Supabase session token.
// The backend checks the server-only public.admins table. No session, or a
// session that isn't an admin, bounces the user to the admin login page.
// ============================================================================
function goToAdminLogin() {
    window.location.href = '/admin-login.html';
}

// Drop-in replacement for fetch() on protected admin endpoints.
// On a 401, silently refreshes the session and retries ONCE before bouncing
// to login — an expired access token mid-event never kicks the admin out.
async function adminFetch(url, options = {}, _retried = false) {
    const { data: { session } } = await window.supabase.auth.getSession();
    if (!session) { goToAdminLogin(); throw new Error('Not signed in'); }
    const headers = Object.assign({}, options.headers || {}, {
        'Authorization': 'Bearer ' + session.access_token
    });
    const res = await fetch(url, Object.assign({}, options, { headers }));
    if (res.status === 401) {
        if (!_retried) {
            const { data, error } = await window.supabase.auth.refreshSession();
            if (!error && data?.session) return adminFetch(url, options, true);
        }
        if (typeof showToast === 'function') showToast('Not authorized as admin. Redirecting to login…', 'error');
        setTimeout(goToAdminLogin, 1200);
    }
    return res;
}

document.addEventListener('DOMContentLoaded', () => {
    let currentServerMonth = 1;

    // ── Page gate: must be a signed-in admin (adminFetch redirects otherwise) ──
    adminFetch(`${API_BASE_URL}/admin/me`).catch(() => {});

    // ── Logout ──
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', async () => {
        await window.supabase.auth.signOut();
        goToAdminLogin();
    });

    // ── Players: load + render editable table ──
    async function loadPlayers() {
        const box = document.getElementById('playersContainer');
        try {
            const res = await adminFetch(`${API_BASE_URL}/admin/players`);
            if (!res || !res.ok) return;
            const data = await res.json();
            const players = data.players || [];
            box.innerHTML = players.length
                ? renderPlayersTable(players)
                : '<p style="color:var(--text-muted); font-size:0.85rem; padding:1rem;">No players have joined yet.</p>';
        } catch (e) {
            box.innerHTML = '<p style="color:var(--accent-rose); font-size:0.85rem; padding:1rem;">Failed to load players.</p>';
        }
    }
    window._reloadPlayers = loadPlayers;   // let the global save/reset refresh the list
    document.getElementById('refreshPlayersBtn').addEventListener('click', loadPlayers);
    loadPlayers();

    // ── Poll game status ──
    async function tickStatus() {
        try {
            const res = await fetch(`${API_BASE_URL}/game-status`);
            if (res.ok) {
                const data = await res.json();
                const badge = data.game_status === 'active'
                    ? `<span style="color: var(--accent-emerald);">● ACTIVE</span>`
                    : data.game_status === 'ended'
                        ? `<span style="color: var(--accent-rose);">■ ENDED</span>`
                        : `<span style="color: var(--accent-amber);">◌ WAITING</span>`;
                document.getElementById('gameStatusLabel').innerHTML =
                    `${badge} — Month ${data.current_month} of 12`;
                currentServerMonth = data.current_month;
            }
        } catch (e) { console.error('Status poll failed', e); }
    }

    setInterval(tickStatus, 3000);
    tickStatus();

    // ── Start Game ──
    document.getElementById('startBtn').addEventListener('click', async () => {
        if (!confirm('Start/restart the game? This will WIPE all player data!')) return;
        try {
            const res = await adminFetch(`${API_BASE_URL}/start-game`, { method: 'POST' });
            const data = await res.json();
            showSystemLog(data.message || data.error, res.ok ? 'success' : 'danger');
            showToast(res.ok ? 'Game started!' : 'Failed', res.ok ? 'success' : 'error');
            tickStatus();
            await loadLeaderboard();
        } catch (e) {
            showToast('Error starting game', 'error');
        }
    });

    // ── Next Month ──
    document.getElementById('nextBtn').addEventListener('click', async () => {
        const btn = document.getElementById('nextBtn');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner-glass" style="width:16px;height:16px;border-width:2px;margin:0 auto;"></div>';

        try {
            const res = await adminFetch(`${API_BASE_URL}/next-month`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ expected_month: currentServerMonth })
            });
            const data = await res.json();

            if (res.ok) {
                showSystemLog(data.message, 'success');
                showToast(`Month processed! ${data.events_triggered || 0} events triggered.`, 'success');

                // Show event details
                if (data.event_details && data.event_details.length > 0) {
                    const box = document.getElementById('eventResults');
                    box.innerHTML = `<strong style="color: var(--accent-primary);">📊 Events this round:</strong>\n` +
                        data.event_details.map(e =>
                            `  [${e.category || 'event'}] ${e.event} (value: ${e.value})`
                        ).join('\n');
                    box.style.display = 'block';
                }
            } else {
                showSystemLog(data.error || 'Failed to advance month', 'danger');
                showToast(data.error || 'Month processing failed', 'error');
            }

            tickStatus();
            await loadLeaderboard();
        } catch (e) {
            showToast('Network error during month processing', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-forward-step"></i> Next Month';
        }
    });

    // ── End Game ──
    document.getElementById('endBtn').addEventListener('click', async () => {
        if (!confirm('End the game now? This will show the final leaderboard to all players.')) return;
        try {
            const res = await adminFetch(`${API_BASE_URL}/end-game`, { method: 'POST' });
            const data = await res.json();
            showSystemLog(data.message, res.ok ? 'success' : 'danger');
            tickStatus();
        } catch (e) {
            showToast('Error ending game', 'error');
        }
    });

    // ── Load Events List ──
    async function loadEvents() {
        try {
            const { data, error } = await window.supabase.from('events').select('*').order('month');
            const list = document.getElementById('eventList');
            if (!data || data.length === 0) {
                list.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">No events added yet.</p>';
                return;
            }
            list.innerHTML = data.map(ev => `
                <div class="event-chip">
                    <span style="color: var(--text-secondary);">
                        <strong style="color: var(--text-primary);">M${ev.month}</strong>
                        ${ev.event_name}
                        <span style="color: var(--text-muted);">(${ev.event_type} / ${ev.impact_target}: ${ev.value})</span>
                    </span>
                    <button onclick="delEvent(${ev.id})" style="background: none; border: none; color: var(--accent-rose); cursor: pointer; font-size: 0.75rem; padding: 0.2rem 0.4rem;">
                        <i class="fa-solid fa-times"></i>
                    </button>
                </div>
            `).join('');
        } catch (e) { console.error('Events load failed', e); }
    }

    // ── Load Leaderboard ──
    async function loadLeaderboard() {
        const tbody = document.getElementById('leaderboardTbody');
        try {
            const res = await fetch(`${API_BASE_URL}/leaderboard`);
            const data = await res.json();

            if (!data || data.length === 0) {
                tbody.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">No players yet.</p>';
                return;
            }

            const trophies = ['🏆', '🥈', '🥉'];
            tbody.innerHTML = data.map((row, idx) => {
                const name = escapeHtml(row.users?.name || 'Anonymous');
                const trophy = idx < 3 ? trophies[idx] + ' ' : '';
                return `
                    <div class="lb-row">
                        <span style="color: var(--text-muted); font-family: var(--font-mono); font-size:0.85rem;">${idx + 1}</span>
                        <span style="font-weight: 600;">${trophy}${name}</span>
                        <span style="color: var(--accent-emerald); font-family: var(--font-mono); font-size: 0.9rem;">${formatINR(row.net_worth)}</span>
                    </div>
                `;
            }).join('');
        } catch (e) {
            tbody.innerHTML = '<p style="color: var(--accent-rose); font-size: 0.85rem; padding: 1rem;">Error loading standings.</p>';
        }
    }

    // ── Event Form Submit ──
    document.getElementById('eventForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            month: parseInt(document.getElementById('evMonth').value),
            event_name: document.getElementById('evName').value,
            event_type: document.getElementById('evType').value,
            impact_target: document.getElementById('evImpact').value,
            value: parseFloat(document.getElementById('evValue').value),
            description: document.getElementById('evDesc').value
        };

        const res = await adminFetch(`${API_BASE_URL}/event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast(`Event added for Month ${payload.month}`, 'success');
            e.target.reset();
            await loadEvents();
        } else {
            showToast('Failed to add event', 'error');
        }
    });

    // ── Choice Form Submit ──
    document.getElementById('choiceForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            month: parseInt(document.getElementById('optMonth').value),
            name: document.getElementById('optName').value,
            cost: parseFloat(document.getElementById('optCost').value),
            risk_type: document.getElementById('optRisk').value,
            reward_type: document.getElementById('optRewardType').value,
            probability: parseInt(document.getElementById('optProb').value),
            reward_value: parseFloat(document.getElementById('optVal').value)
        };

        const res = await adminFetch(`${API_BASE_URL}/choice-admin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast(`Choice "${payload.name}" added for Month ${payload.month}`, 'success');
            e.target.reset();
        } else {
            showToast('Failed to add choice', 'error');
        }
    });

    document.getElementById('refreshLeaderboardBtn').addEventListener('click', loadLeaderboard);

    // Init
    loadEvents();
    loadLeaderboard();
});

// ── Delete Event (global) ──
window.delEvent = async function(id) {
    const res = await adminFetch(`${API_BASE_URL}/event/${id}`, { method: 'DELETE' });
    if (res.ok) {
        // Reload events list
        const { data } = await window.supabase.from('events').select('*').order('month');
        const list = document.getElementById('eventList');
        document.getElementById('eventList').innerHTML = '';
        // Trigger refresh without page reload
        const event = new Event('submit');
        document.getElementById('eventList').dispatchEvent(event);
        window.location.reload();
    }
};

// ============================================================================
// PLAYERS — editable table + save/reset (all via the admin-gated backend)
// ============================================================================
function renderPlayersTable(players) {
    const num = (v) => (v == null ? 0 : v);
    const field = (key, uid, val) =>
        `<input class="input-glass" style="padding:0.3rem 0.4rem; font-size:0.8rem; width:92px;" type="number" id="${key}_${uid}" value="${num(val)}">`;

    const row = (p) => {
        const uid = p.user_id;
        const name = (p.users && p.users.name) || 'Player';
        const email = (p.users && p.users.email) || '';
        const safeName = name.replace(/'/g, '');
        return `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:0.5rem; min-width:150px;">
                <div style="font-weight:600; font-size:0.85rem;">${name}</div>
                <div style="color:var(--text-muted); font-size:0.72rem;">${email}</div>
            </td>
            <td style="padding:0.5rem; text-align:center; font-size:0.8rem;">M${num(p.month)}</td>
            <td style="padding:0.4rem;">${field('cash', uid, p.cash)}</td>
            <td style="padding:0.4rem;">${field('stocks', uid, p.stocks)}</td>
            <td style="padding:0.4rem;">${field('gold', uid, p.gold)}</td>
            <td style="padding:0.4rem;">${field('emergency_fund', uid, p.emergency_fund)}</td>
            <td style="padding:0.4rem;">${field('loans', uid, p.loans)}</td>
            <td style="padding:0.4rem;">
                <select class="input-glass" style="padding:0.3rem 0.4rem; font-size:0.8rem;" id="status_${uid}">
                    <option value="active" ${p.status === 'active' ? 'selected' : ''}>active</option>
                    <option value="waiting" ${p.status === 'waiting' ? 'selected' : ''}>waiting</option>
                </select>
            </td>
            <td style="padding:0.5rem; text-align:right; color:var(--accent-emerald); font-family:var(--font-mono); font-size:0.82rem;">${formatINR(p.net_worth)}</td>
            <td style="padding:0.4rem; white-space:nowrap;">
                <button class="btn-glow" style="padding:0.3rem 0.6rem; font-size:0.75rem; border:none; cursor:pointer;" onclick="savePlayer('${uid}')">Save</button>
                <button class="btn-glow-danger" style="padding:0.3rem 0.6rem; font-size:0.75rem; border:none; cursor:pointer;" onclick="resetPlayer('${uid}','${safeName}')">Reset</button>
            </td>
        </tr>`;
    };

    return `
    <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
        <thead>
            <tr style="color:var(--text-muted); font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em;">
                <th style="text-align:left; padding:0.5rem;">Player</th>
                <th style="padding:0.5rem;">Month</th>
                <th style="padding:0.5rem;">Cash</th>
                <th style="padding:0.5rem;">Stocks</th>
                <th style="padding:0.5rem;">Gold</th>
                <th style="padding:0.5rem;">Emerg.</th>
                <th style="padding:0.5rem;">Loans</th>
                <th style="padding:0.5rem;">Status</th>
                <th style="padding:0.5rem; text-align:right;">Net Worth</th>
                <th style="padding:0.5rem;">Actions</th>
            </tr>
        </thead>
        <tbody>${players.map(row).join('')}</tbody>
    </table>`;
}

window.savePlayer = async function (uid) {
    const val = (k) => { const el = document.getElementById(`${k}_${uid}`); return el ? el.value : undefined; };
    const statusEl = document.getElementById(`status_${uid}`);
    const payload = {
        user_id: uid,
        cash: val('cash'), stocks: val('stocks'), gold: val('gold'),
        emergency_fund: val('emergency_fund'), loans: val('loans'),
        status: statusEl ? statusEl.value : undefined
    };
    const res = await adminFetch(`${API_BASE_URL}/admin/update-player`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) { showToast('Player updated', 'success'); if (window._reloadPlayers) window._reloadPlayers(); }
    else showToast(data.error || 'Update failed', 'error');
};

window.resetPlayer = async function (uid, name) {
    if (!confirm(`Reset ${name || 'this player'}? This wipes their game data and lets them allocate again.`)) return;
    const res = await adminFetch(`${API_BASE_URL}/admin/reset-player`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: uid })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) { showToast('Player reset', 'success'); if (window._reloadPlayers) window._reloadPlayers(); }
    else showToast(data.error || 'Reset failed', 'error');
};


// Create a player login (username + password). Backend makes the auth user via
// the service_role admin API; the player then logs in from the landing page.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('createPlayerForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = (document.getElementById('cpUsername').value || '').trim().toLowerCase();
        const password = document.getElementById('cpPassword').value || '';
        const name = (document.getElementById('cpName').value || '').trim();
        if (!username || password.length < 6) {
            showToast('Enter a username and a password of at least 6 characters.', 'error');
            return;
        }
        const btn = form.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        try {
            const res = await adminFetch(`${API_BASE_URL}/admin/create-player`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, name })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                showToast(data.message || 'Player created', 'success');
                form.reset();
                if (window._reloadPlayers) window._reloadPlayers();
                if (window._reloadRoster) window._reloadRoster();
            } else {
                showToast(data.error || 'Create failed', 'error');
            }
        } catch (err) {
            showToast(err.message || 'Create failed', 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    });
});

// Player roster - every provisioned login and whether they have started playing.
document.addEventListener('DOMContentLoaded', () => {
    const box = document.getElementById('rosterContainer');
    if (!box) return;
    async function loadRoster() {
        try {
            const res = await adminFetch(`${API_BASE_URL}/admin/roster`);
            if (!res || !res.ok) return;
            const data = await res.json();
            const roster = data.roster || [];
            if (!roster.length) {
                box.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; padding:1rem;">No players created yet. Use Create Player above.</p>';
                return;
            }
            const rows = roster.map(p => {
                const badge = p.played
                    ? '<span style="color:var(--accent-emerald);">&#9679; Playing</span>'
                    : '<span style="color:var(--accent-amber);">&#9676; Waiting</span>';
                return `<tr>
                    <td style="padding:0.5rem; font-weight:600;">${escapeHtml(p.username)}</td>
                    <td style="padding:0.5rem;">${escapeHtml(p.name)}</td>
                    <td style="padding:0.5rem;">${badge}</td>
                </tr>`;
            }).join('');
            box.innerHTML = `<table style="width:100%; border-collapse:collapse; font-size:0.82rem;">
                <thead><tr style="color:var(--text-muted); font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em;">
                    <th style="text-align:left; padding:0.5rem;">Username</th>
                    <th style="text-align:left; padding:0.5rem;">Name</th>
                    <th style="text-align:left; padding:0.5rem;">Status</th>
                </tr></thead><tbody>${rows}</tbody></table>`;
        } catch (e) {
            box.innerHTML = '<p style="color:var(--accent-rose); font-size:0.85rem; padding:1rem;">Failed to load roster.</p>';
        }
    }
    window._reloadRoster = loadRoster;
    const btn = document.getElementById('refreshRosterBtn');
    if (btn) btn.addEventListener('click', loadRoster);
    loadRoster();
});


// Game Controls - toggle the automatic layer (auto events / auto market).
// Both OFF = full manual admin control (the default). Reads current state from
// /game-status and writes changes to /admin/settings.
document.addEventListener('DOMContentLoaded', () => {
    const evEl = document.getElementById('toggleAutoEvents');
    const mkEl = document.getElementById('toggleAutoMarket');
    const hint = document.getElementById('settingsHint');
    if (!evEl || !mkEl) return;

    function renderHint() {
        if (!hint) return;
        const manual = !evEl.checked && !mkEl.checked;
        hint.innerText = manual
            ? 'Full manual control: only the events YOU add fire, and markets move only when you set them.'
            : `Automatic: random events ${evEl.checked ? 'ON' : 'off'}, market ${mkEl.checked ? 'ON' : 'off'}.`;
    }
    async function loadSettings() {
        try {
            const res = await fetch(`${API_BASE_URL}/game-status`);
            if (!res.ok) return;
            const g = await res.json();
            evEl.checked = !!g.auto_events;
            mkEl.checked = !!g.auto_market;
            renderHint();
        } catch (e) { /* ignore */ }
    }
    async function save(field, value) {
        try {
            const res = await adminFetch(`${API_BASE_URL}/admin/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [field]: value })
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok) { showToast('Setting saved', 'success'); renderHint(); }
            else { showToast(data.error || 'Save failed', 'error'); loadSettings(); }
        } catch (err) { showToast('Save failed', 'error'); loadSettings(); }
    }
    evEl.addEventListener('change', () => save('auto_events', evEl.checked));
    mkEl.addEventListener('change', () => save('auto_market', mkEl.checked));
    loadSettings();
});
