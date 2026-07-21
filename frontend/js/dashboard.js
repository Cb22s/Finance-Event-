// ============================================================================
// DASHBOARD — Main game interface with correct API endpoints
// ============================================================================

let currentUser = null;
let currentMonth = 1;

// ── Auth Helper ──
async function getAuthHeaders() {
    const { data: { session } } = await window.supabase.auth.getSession();
    if (!session) {
        window.location.href = '/';
        return {};
    }
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
    };
}

// ── Toast Notification ──
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.id = 'toastContainer';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-glass toast-${type}`;
    const icons = {
        error: 'fa-circle-xmark',
        success: 'fa-circle-check',
        info: 'fa-circle-info'
    };
    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Format Currency (Indian) ──
function formatINR(val) {
    return `₹${Math.floor(val).toLocaleString('en-IN')}`;
}

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
    const waitForSession = async () => {
        let retries = 5;
        while (retries--) {
            const { data: { session } } = await window.supabase.auth.getSession();
            if (session) return session;
            await new Promise(res => setTimeout(res, 500));
        }
        alert("Please login first.");
        window.location.href = '/';
        return null;
    };

    const session = await waitForSession();
    if (!session) return;

    currentUser = session.user;

    window.supabase.auth.onAuthStateChange((event, session) => {
        if (!session) window.location.href = '/';
        else currentUser = session.user;
    });

    document.getElementById('userName').innerText =
        currentUser.user_metadata?.name || currentUser.email;

    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await window.supabase.auth.signOut();
        window.location.href = '/';
    });

    const staySingleBtn = document.getElementById('staySingleBtn');
    if (staySingleBtn) {
        staySingleBtn.addEventListener('click', async () => {
            if (!confirm("Choose to stay single? This choice is final for this game.")) return;
            try {
                const h = await getAuthHeaders();
                const res = await fetch(`${API_BASE_URL}/courtship/marry`, {
                    method: 'POST',
                    headers: h,
                    body: JSON.stringify({ choice: 'single' })
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(data.message, 'success');
                    await loadDashboard();
                } else {
                    showToast(data.error, 'error');
                }
            } catch (err) {
                showToast('Failed to stay single', 'error');
            }
        });
    }

    document.getElementById('endTurnBtn').addEventListener('click', async () => {
        if (!confirm("Lock your turn for this month? You won't be able to make more decisions until the admin advances.")) return;

        try {
            const h = await getAuthHeaders();
            const res = await fetch(`${API_BASE_URL}/lock-turn`, {
                method: 'POST',
                headers: h
            });
            const data = await res.json();
            if (res.ok) showToast(data.message, 'success');
            else showToast(data.error, 'error');
            await loadDashboard();
        } catch (err) {
            console.error(err);
            showToast('Failed to lock turn', 'error');
        }
    });

    await loadDashboard();
    setInterval(loadDashboard, 5000);
});

// ══════════════════════════════════════════════
// LOAD DASHBOARD DATA
// ══════════════════════════════════════════════
async function loadDashboard() {
    try {
        const h = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/dashboard`, { headers: h });

        if (res.status === 404) {
            window.location.href = 'allocation.html';
            return;
        }

        const data = await res.json();
        if (data.error) {
            if (data.error.includes('No player state')) {
                window.location.href = 'allocation.html';
            }
            return;
        }

        const p = data.player;
        const g = data.game;

        // Game ended → leaderboard
        if (g && g.game_status === 'ended') {
            window.location.href = 'leaderboard.html';
            return;
        }

        // ── Update UI ──
        document.getElementById('monthBadge').innerText = `Month ${p.month}`;
        currentMonth = p.month;

        // Net Worth
        const nwEl = document.getElementById('netWorthVal');
        nwEl.innerText = formatINR(p.net_worth);
        if (p.net_worth < 0) nwEl.classList.add('negative');
        else nwEl.classList.remove('negative');

        // Stats
        document.getElementById('cashVal').innerText = formatINR(p.cash);
        document.getElementById('stocksVal').innerText = formatINR(p.stocks);
        document.getElementById('goldVal').innerText = formatINR(p.gold);
        document.getElementById('emergencyVal').innerText = formatINR(p.emergency_fund);
        document.getElementById('loanVal').innerText = formatINR(p.loans);
        document.getElementById('pendingVal').innerText = formatINR(p.pending_cash_next_month || 0);
        document.getElementById('lifestyleVal').innerText = p.lifestyle_type === 'city' ? 'City' : 'Outer';
        document.getElementById('bikeVal').innerText = p.bike_status
            ? (p.bike_lock_in_months > 0 ? `Locked (${p.bike_lock_in_months}m)` : 'Free')
            : 'None';
        
        const relVal = document.getElementById('relationshipVal');
        if (relVal) {
            if (p.spouse_archetype) {
                if (p.spouse_archetype === 'single') {
                    relVal.innerText = 'Single';
                } else {
                    const names = {
                        saver: 'Saver',
                        earner: 'Earner',
                        investor: 'Investor',
                        anchor: 'Anchor'
                    };
                    relVal.innerText = names[p.spouse_archetype] || p.spouse_archetype;
                }
            } else {
                relVal.innerText = 'Unmarried';
            }
        }

        // Risk & Trust
        const riskLevel = p.risk_level || 50;
        const riskLabel = riskLevel > 70 ? 'High' : riskLevel > 40 ? 'Medium' : 'Low';
        const riskColor = riskLevel > 70 ? 'var(--accent-rose)' : riskLevel > 40 ? 'var(--accent-amber)' : 'var(--accent-emerald)';
        document.getElementById('riskVal').innerHTML = `<span style="color:${riskColor}">${riskLabel} (${riskLevel})</span>`;
        document.getElementById('trustVal').innerText = p.trust_score || 0;

        // ── Courtship & Marriage UI Render ──
        const courtshipSec = document.getElementById('courtshipSection');
        const courtship = data.courtship;
        if (courtshipSec && courtship) {
            if (p.month === 6 && g.marriage_round_active && !p.spouse_archetype) {
                courtshipSec.style.display = 'block';
                const datesUsed = courtship.dates_used || 0;
                document.getElementById('datesUsedVal').innerText = datesUsed;
                
                const extraNotice = document.getElementById('extraDateNotice');
                if (datesUsed >= 3) {
                    extraNotice.style.display = 'inline';
                } else {
                    extraNotice.style.display = 'none';
                }
                
                const grid = document.getElementById('candidatesGrid');
                grid.innerHTML = courtship.spouse_options.map(opt => {
                    const isIncomeRevealed = courtship.reveals.some(r => r.archetype_id === opt.id && r.trait_key === 'income');
                    const isExpenseRevealed = courtship.reveals.some(r => r.archetype_id === opt.id && r.trait_key === 'expense_mod');
                    const isAssetsRevealed = courtship.reveals.some(r => r.archetype_id === opt.id && r.trait_key === 'assets');
                    
                    return `
                        <div class="choice-card" style="display:flex; flex-direction:column; justify-content:space-between; padding:1.25rem;">
                            <div>
                                <div style="font-weight:700; font-size:1.05rem; color:var(--accent-rose); margin-bottom:0.25rem;">
                                    <i class="fa-solid fa-heart" style="margin-right:0.4rem;"></i>${opt.name}
                                </div>
                                <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.75rem; min-height:48px; line-height:1.4;">
                                    ${opt.description}
                                </p>
                                
                                <div style="font-size:0.8rem; border-top:1px solid rgba(255,255,255,0.05); padding-top:0.6rem; margin-bottom:0.75rem; display:flex; flex-direction:column; gap:0.4rem;">
                                    <div style="display:flex; justify-content:space-between;">
                                        <span style="color:var(--text-muted);">Spouse Income:</span>
                                        <span id="income-${opt.id}" style="font-weight:600; color:var(--text-secondary);">${isIncomeRevealed ? _formatRevealedTrait(opt.id, 'income') : '?'}</span>
                                    </div>
                                    <div style="display:flex; justify-content:space-between;">
                                        <span style="color:var(--text-muted);">Spouse Expenses:</span>
                                        <span id="expense-${opt.id}" style="font-weight:600; color:var(--text-secondary);">${isExpenseRevealed ? _formatRevealedTrait(opt.id, 'expense_mod') : '?'}</span>
                                    </div>
                                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                        <span style="color:var(--text-muted); white-space:nowrap; margin-right:0.5rem;">Spouse Assets:</span>
                                        <span id="assets-${opt.id}" style="font-weight:600; text-align:right; color:var(--text-secondary); max-width:180px; word-break:break-word;">${isAssetsRevealed ? _formatRevealedTrait(opt.id, 'assets') : '?'}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div style="display:flex; flex-direction:column; gap:0.4rem;">
                                <div style="display:flex; gap:0.4rem;">
                                    <button class="btn-ghost" style="flex:1; font-size:0.72rem; padding:0.4rem 0.2rem; border-color:rgba(244,63,94,0.3); color:var(--accent-rose);"
                                            onclick="revealTrait('${opt.id}', 'income')" ${isIncomeRevealed ? 'disabled' : ''}>
                                        Reveal Income
                                    </button>
                                    <button class="btn-ghost" style="flex:1; font-size:0.72rem; padding:0.4rem 0.2rem; border-color:rgba(244,63,94,0.3); color:var(--accent-rose);"
                                            onclick="revealTrait('${opt.id}', 'expense_mod')" ${isExpenseRevealed ? 'disabled' : ''}>
                                        Reveal Expense
                                    </button>
                                </div>
                                <button class="btn-ghost" style="font-size:0.72rem; padding:0.4rem; border-color:rgba(244,63,94,0.3); color:var(--accent-rose);"
                                        onclick="revealTrait('${opt.id}', 'assets')" ${isAssetsRevealed ? 'disabled' : ''}>
                                    Reveal Portfolio
                                </button>
                                <button class="btn-glow" style="font-size:0.8rem; padding:0.5rem; background:var(--gradient-rose); border:none; color:white; font-weight:700; cursor:pointer;"
                                        onclick="proposeMarriage('${opt.id}')">
                                    Propose (₹88,000)
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                courtshipSec.style.display = 'none';
            }
        }

        // ── Optional Choices ──
        const optsCon = document.getElementById('optionalChoicesContainer');
        if (optsCon && data.choices) {
            if (data.choices.length === 0) {
                optsCon.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">No opportunities this month.</p>';
            } else {
                optsCon.innerHTML = data.choices.map(c => `
                    <div class="choice-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span style="font-weight: 600; font-size: 0.9rem;">${c.name}</span>
                            <span style="font-size: 0.75rem; color: var(--accent-amber); font-weight: 600;">Cost: ${formatINR(c.cost)}</span>
                        </div>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                            ${c.risk_type} • ${c.probability}% chance → ${formatINR(c.reward_value)} ${c.reward_type}
                        </p>
                        <button class="btn-ghost" style="width: 100%; font-size: 0.8rem; padding: 0.4rem; border-color: rgba(245,158,11,0.3); color: var(--accent-amber);"
                                onclick="buyOptionalChoice(${c.id})">
                            <i class="fa-solid fa-dice"></i> Take Chance
                        </button>
                    </div>
                `).join('');
            }
        }

        // ── Event Logs ──
        const logContainer = document.getElementById('eventLogContainer');
        if (data.event_logs && data.event_logs.length > 0) {
            logContainer.innerHTML = data.event_logs.reverse().map(log => {
                const entries = (log.summary || '').split(' | ');
                const monthLabel = `<div style="font-weight:700; color:var(--accent-primary); margin-bottom:0.5rem; font-size:0.85rem;">Month ${log.month}</div>`;
                const items = entries.map(entry => {
                    let cls = 'info';
                    if (entry.includes('⚠') || entry.includes('CRITICAL') || entry.includes('📉')) cls = 'negative';
                    else if (entry.includes('💰') || entry.includes('📈') || entry.includes('✅') || entry.includes('SUCCESS')) cls = 'positive';
                    else if (entry.includes('⚡') || entry.includes('!')) cls = 'warning';
                    return `<div class="event-log-item ${cls}">${entry}</div>`;
                }).join('');
                return monthLabel + items;
            }).join('<hr style="border-color: rgba(255,255,255,0.05); margin: 1rem 0;">');
        }

        // ── Trust Scores from Supabase ──
        try {
            const { data: scores } = await window.supabase.from('player_relative_score')
                .select('*')
                .eq('user_id', currentUser.id);

            if (scores) {
                scores.forEach(s => {
                    if (s.relative_type === 'poor') document.getElementById('trustPoor').innerText = s.trust_score;
                    if (s.relative_type === 'rich') document.getElementById('trustRich').innerText = s.trust_score;
                });
            }
        } catch (e) { /* non-critical */ }

        // ── UI Lock State ──
        const actionButtons = document.querySelectorAll('.sell-btn, .choice-card button, #relativeContainer button');
        const endTurnBtn = document.getElementById('endTurnBtn');
        const statusBanner = document.getElementById('statusBanner');

        if (p.status === 'waiting') {
            actionButtons.forEach(btn => btn.disabled = true);
            endTurnBtn.style.display = 'none';
            statusBanner.style.display = 'flex';
        } else {
            actionButtons.forEach(btn => btn.disabled = false);
            endTurnBtn.style.display = 'inline-block';
            statusBanner.style.display = 'none';
        }

    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

// ══════════════════════════════════════════════
// PLAYER ACTIONS — Using correct API endpoints
// ══════════════════════════════════════════════

// ── Sell Asset → POST /sell ──
window.sellAsset = async function(asset) {
    const amountStr = prompt(`How much ${asset} do you want to sell?\n(10% penalty applies, cash credited next month)`);
    if (!amountStr) return;

    const amount = parseInt(amountStr);
    if (isNaN(amount) || amount <= 0) {
        showToast('Enter a valid positive amount', 'error');
        return;
    }

    try {
        const h = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/sell`, {
            method: 'POST',
            headers: h,
            body: JSON.stringify({ asset, amount })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message, 'success');
        } else {
            showToast(data.error, 'error');
        }
        await loadDashboard();
    } catch (err) {
        showToast('Failed to sell asset', 'error');
    }
};

// ── Handle Relative → POST /handle-relative ──
window.handleRelative = async function(relative_type, action) {
    if (action === 'none') {
        try {
            const h = await getAuthHeaders();
            const res = await fetch(`${API_BASE_URL}/handle-relative`, {
                method: 'POST',
                headers: h,
                body: JSON.stringify({ relative_type, action: 'none' })
            });
            const data = await res.json();
            showToast(data.message, 'info');
        } catch (err) {
            showToast('Action failed', 'error');
        }
        return;
    }

    const cost = action === 'medium' ? '₹2,000' : '₹5,000';
    if (!confirm(`Help ${relative_type} relative for ${cost}?`)) return;

    try {
        const h = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/handle-relative`, {
            method: 'POST',
            headers: h,
            body: JSON.stringify({ relative_type, action })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message, 'success');
        } else {
            showToast(data.error, 'error');
        }
        await loadDashboard();
    } catch (err) {
        showToast('Action failed', 'error');
    }
};

// ── Buy Optional Choice → POST /buy-choice ──
window.buyOptionalChoice = async function(id) {
    if (!confirm('Take this chance? Cost will be deducted immediately.')) return;

    try {
        const h = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/buy-choice`, {
            method: 'POST',
            headers: h,
            body: JSON.stringify({ choice_id: id })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message, data.success ? 'success' : 'info');
        } else {
            showToast(data.error, 'error');
        }
        await loadDashboard();
    } catch (err) {
        showToast('Action failed', 'error');
    }
};

// ── Reveal Trait → POST /courtship/reveal ──
window.revealTrait = async function(archetype_id, trait_key) {
    const datesUsed = parseInt(document.getElementById('datesUsedVal').innerText || '0');
    if (datesUsed >= 3) {
        if (!confirm("You have used all 3 free dates. Going on an extra date to reveal this trait costs ₹5,000. Proceed?")) return;
    }
    try {
        const h = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/courtship/reveal`, {
            method: 'POST',
            headers: h,
            body: JSON.stringify({ archetype_id, trait_key })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message, 'success');
            await loadDashboard();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Failed to reveal candidate trait', 'error');
    }
};

// ── Propose Marriage → POST /courtship/marry ──
window.proposeMarriage = async function(archetype_id) {
    if (!confirm("Are you sure you want to propose? Wedding costs ₹88,000 and this choice is final.")) return;
    try {
        const h = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/courtship/marry`, {
            method: 'POST',
            headers: h,
            body: JSON.stringify({ choice: archetype_id })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message, 'success');
            await loadDashboard();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Failed to propose marriage', 'error');
    }
};

// ── Format Revealed Trait ──
function _formatRevealedTrait(archetype_id, trait_key) {
    if (archetype_id === 'saver') {
        if (trait_key === 'income') return '+₹10,000/mo';
        if (trait_key === 'expense_mod') return '₹0/mo (net)';
        if (trait_key === 'assets') return 'Gold ₹8K, EF ₹22K';
    } else if (archetype_id === 'earner') {
        if (trait_key === 'income') return '+₹36,000/mo';
        if (trait_key === 'expense_mod') return '₹21,000/mo (net)';
        if (trait_key === 'assets') return 'Brings no assets/liabilities';
    } else if (archetype_id === 'investor') {
        if (trait_key === 'income') return '+₹9,000/mo';
        if (trait_key === 'expense_mod') return '₹8,000/mo (net)';
        if (trait_key === 'assets') return 'Stocks ₹44K, Gold ₹20K, EF ₹24K';
    } else if (archetype_id === 'anchor') {
        if (trait_key === 'income') return '+₹14,000/mo';
        if (trait_key === 'expense_mod') return '₹7,000/mo (net)';
        if (trait_key === 'assets') return 'Stocks ₹8K, EF ₹45K';
    }
    return '?';
}
