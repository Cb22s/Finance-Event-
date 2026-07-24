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
    // The dashboard polls every 5s. Without this guard the poll re-rendered the
    // allocation and loan inputs mid-keystroke and wiped whatever the player had
    // typed — the single most infuriating bug in the old UI.
    setInterval(() => {
        if (isEditing()) return;
        loadDashboard();
    }, 5000);
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

        // Game ended → celebrate, then leaderboard
        if (g && g.game_status === 'ended') {
            if (window.fx && !sessionStorage.getItem('mm_finale')) {
                sessionStorage.setItem('mm_finale', '1');
                fx.confetti(120);
                setTimeout(() => { window.location.href = 'leaderboard.html'; }, 2200);
            } else {
                window.location.href = 'leaderboard.html';
            }
            return;
        }

        // ── Update UI ──
        document.getElementById('monthBadge').innerText = `Month ${p.month}`;
        currentMonth = p.month;

        // Net Worth — animated counter with green/red flash and delta chip
        const nwEl = document.getElementById('netWorthVal');
        if (window.fx) fx.animateValue('netWorthVal', p.net_worth);
        else nwEl.innerText = formatINR(p.net_worth);
        if (p.net_worth < 0) nwEl.classList.add('negative');
        else nwEl.classList.remove('negative');

        // Stats — animated
        if (window.fx) {
            fx.animateValue('cashVal', p.cash);
            fx.animateValue('stocksVal', p.stocks);
            fx.animateValue('goldVal', p.gold);
            fx.animateValue('emergencyVal', p.emergency_fund);
            fx.animateValue('loanVal', p.loans);
        } else {
            document.getElementById('cashVal').innerText = formatINR(p.cash);
            document.getElementById('stocksVal').innerText = formatINR(p.stocks);
            document.getElementById('goldVal').innerText = formatINR(p.gold);
            document.getElementById('emergencyVal').innerText = formatINR(p.emergency_fund);
            document.getElementById('loanVal').innerText = formatINR(p.loans);
        }
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

        // ── V2 renders: market news, monthly allocation, loans ──
        renderMarketNews(data.market, p.month);
        renderAllocation(data.allocation, data.loan_info);
        renderLoans(data.loan_info);
        renderActionBanner(data.allocation, p);
        renderInsurance(data.insurance);

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
                const riskColor = { low: 'var(--accent-emerald)', medium: 'var(--accent-amber)', high: 'var(--accent-rose)' };
                const riskEmoji = { low: '🟢', medium: '🟡', high: '🔴' };
                optsCon.innerHTML = data.choices.map(c => {
                    const rc = riskColor[c.risk_type] || 'var(--accent-amber)';
                    return `
                    <div class="choice-card" style="border-left: 3px solid ${rc};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span style="font-weight: 600; font-size: 0.9rem;">${c.name}</span>
                            <span style="font-size: 0.75rem; color: ${rc}; font-weight: 600;">${c.cost > 0 ? 'Cost: ' + formatINR(c.cost) : 'Free'}</span>
                        </div>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                            ${riskEmoji[c.risk_type] || ''} ${c.risk_type} risk • ${c.probability}% chance → <strong style="color:${rc};">${formatINR(c.reward_value)}</strong> ${c.reward_type}
                        </p>
                        <button class="btn-ghost" style="width: 100%; font-size: 0.8rem; padding: 0.4rem; border-color: ${rc}; color: ${rc};"
                                onclick="buyOptionalChoice(${c.id})">
                            <i class="fa-solid fa-dice"></i> Take Chance
                        </button>
                    </div>`;
                }).join('');
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
        // Trust / relative scores were removed with the Social Investment panel.
        // The trustPoor / trustRich elements no longer exist, so this fetch-and-write
        // has been deleted rather than left to throw on every dashboard poll.


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
            // A win pays off — celebrate. A loss — nothing, the sting is enough.
            if (window.fx && data.success) fx.confetti(60);
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


// ============================================================================
// V2 UI — market news, monthly allocation, loans
// ============================================================================

// 'allocKeep' is gone: the server now derives kept cash as the residual, so there
// is nothing for the player to balance and nothing to get wrong.
const ALLOC_IDS = ['allocStocks', 'allocGold', 'allocEf', 'allocPrepay'];

// The exact server-side value, held as a NUMBER. Never re-read from the rendered
// string: formatINR uses Math.floor while the backend rounds, so 8117.51 displayed
// as "8,117" and re-parsed as 8117 was 0.51 away from the server's 8118 and failed
// the "allocate exactly" check with no way for the player to satisfy it.
let allocAvailableRaw = 0;
let _lastSeenMonth = null;
const LOAN_IDS = ['loanAmount', 'loanTerm'];

// True while the player has focus in any input they are mid-way through filling.
// Used to suspend the 5s dashboard poll so a re-render cannot destroy their entry.
function isEditing() {
    const el = document.activeElement;
    if (!el) return false;
    return ALLOC_IDS.includes(el.id) || LOAN_IDS.includes(el.id);
}

function pctText(v) {
    const pct = (v * 100).toFixed(1);
    return `${v >= 0 ? '+' : ''}${pct}%`;
}

function pctColor(v) {
    if (v > 0.0005) return 'var(--accent-emerald)';
    if (v < -0.0005) return 'var(--accent-rose)';
    return 'var(--text-secondary)';
}

// ── MARKET NEWS ──────────────────────────────────────────────────────────────
function renderMarketNews(market, month) {
    const sec = document.getElementById('marketNews');
    if (!sec) return;
    if (!market || market.source === 'flat') {
        sec.style.display = 'none';
        return;
    }
    sec.style.display = 'block';
    document.getElementById('marketName').innerText = market.name || 'Market Update';
    document.getElementById('marketMonth').innerText = `Month ${month}`;
    document.getElementById('marketReason').innerText = market.reason || '';

    // Fire dramatic feedback ONLY when the month actually advances, so the 5s
    // poll doesn't re-trigger the animation every tick.
    if (window.fx && _lastSeenMonth !== null && month !== _lastSeenMonth) {
        fx.revealEvent('marketNews');
        if (market.stock_pct <= -0.10) fx.shake('marketNews');       // crash / war
        else if (market.stock_pct >= 0.08) fx.celebrate('marketNews'); // strong bull
    }
    _lastSeenMonth = month;

    const sEl = document.getElementById('marketStockPct');
    const gEl = document.getElementById('marketGoldPct');
    sEl.innerText = pctText(market.stock_pct);
    sEl.style.color = pctColor(market.stock_pct);
    gEl.innerText = pctText(market.gold_pct);
    gEl.style.color = pctColor(market.gold_pct);
}

// ── ACTION BANNER ────────────────────────────────────────────────────────────
function renderActionBanner(alloc, player) {
    const banner = document.getElementById('actionBanner');
    if (!banner) return;
    if (alloc && alloc.required && !alloc.done) {
        banner.style.display = 'block';
        document.getElementById('actionBannerTitle').innerText = 'Allocation required';
        document.getElementById('actionBannerText').innerText =
            `You have ${formatINR(alloc.available_cash)} sitting idle. Decide where it goes before ending Month ${player.month}.`;
        document.getElementById('actionBannerBtn').onclick = () => {
            document.getElementById('allocSection').scrollIntoView({ behavior: 'smooth', block: 'center' });
        };
    } else {
        banner.style.display = 'none';
    }
}

// ── MONTHLY ALLOCATION ───────────────────────────────────────────────────────
function renderAllocation(alloc, loanInfo) {
    const sec = document.getElementById('allocSection');
    if (!sec || !alloc) return;

    if (!alloc.required || alloc.done) {
        sec.style.display = 'none';
        return;
    }
    sec.style.display = 'block';

    allocAvailableRaw = Number(alloc.available_cash) || 0;
    document.getElementById('allocAvailable').innerText = formatINR(allocAvailableRaw);

    // Cap the repay field at what is actually owed.
    const outstanding = (loanInfo && loanInfo.outstanding) || 0;
    const prepayWrap = document.getElementById('allocPrepayWrap');
    const prepayInput = document.getElementById('allocPrepay');
    if (outstanding <= 0) {
        prepayWrap.style.display = 'none';
        prepayInput.value = 0;
    } else {
        prepayWrap.style.display = 'block';
        prepayInput.max = outstanding;
        document.getElementById('allocPrepayMax').innerText = `(owed ${formatINR(outstanding)})`;
    }

    recalcAllocation();
}

function allocTotal() {
    return ALLOC_IDS.reduce((sum, id) => {
        const el = document.getElementById(id);
        return sum + (el ? (parseFloat(el.value) || 0) : 0);
    }, 0);
}

function recalcAllocation() {
    const msg = document.getElementById('allocRemaining');
    const btn = document.getElementById('allocSubmit');
    if (!msg || !btn) return;

    const invested = allocTotal();
    const remainder = allocAvailableRaw - invested;

    // Only ONE way to fail now: trying to invest more than you have.
    if (remainder < -1) {
        msg.innerHTML = `<span style="color: var(--accent-rose);">Over by ${formatINR(Math.abs(remainder))}</span>`;
        btn.disabled = true;
    } else {
        msg.innerHTML = `<span style="color: var(--text-muted);">Remaining stays as cash: <strong style="color: var(--accent-emerald);">${formatINR(Math.max(0, remainder))}</strong></span>`;
        btn.disabled = false;
    }
}

// ── LOANS ────────────────────────────────────────────────────────────────────
function renderLoans(info) {
    const sec = document.getElementById('loanSection');
    if (!sec || !info) return;
    sec.style.display = 'block';

    const list = document.getElementById('loanList');
    if (!info.active || info.active.length === 0) {
        list.innerHTML = '<div style="font-size:0.85rem; color: var(--text-muted);">No active loans.</div>';
    } else {
        list.innerHTML = info.active.map(l => {
            const isAuto = l.loan_type === 'auto';
            return `<div class="choice-card" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                <div>
                    <div style="font-weight:600; font-size:0.9rem;">
                        ${isAuto ? '⚠️ Emergency Auto-Loan' : '🏦 Personal Loan'}
                        <span style="font-size:0.75rem; color:var(--text-muted); font-weight:400;">taken Month ${l.month_taken}</span>
                    </div>
                    <div style="font-size:0.75rem; color: var(--text-muted);">
                        ${(parseFloat(l.interest_rate) * 100).toFixed(1)}%/month · ${l.term_months || 6}-month term
                        ${isAuto ? ' · penalty rate' : ''}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-weight:700; color: var(--accent-rose);">${formatINR(l.current_amount)}</div>
                    <div style="font-size:0.75rem; color: var(--text-muted);">EMI ${formatINR(l.emi || 0)}</div>
                </div>
            </div>`;
        }).join('');
    }

    document.getElementById('loanSubtitle').innerText =
        `You can borrow up to ${formatINR(info.borrowing_headroom)} more at ` +
        `${(info.interest_rate * 100).toFixed(1)}%/month. Total EMI ${formatINR(info.monthly_emi)} of ${formatINR(info.emi_cap)} allowed.`;

    const form = document.getElementById('loanForm');
    const quote = document.getElementById('loanQuote');
    if (!info.can_borrow_this_month) {
        form.style.display = 'none';
        quote.innerText = 'You have already taken a loan this month.';
    } else if (info.borrowing_headroom <= 0) {
        form.style.display = 'none';
        quote.innerText = 'You have reached your debt ceiling. Repay before borrowing again.';
    } else {
        form.style.display = 'grid';
    }
}

async function refreshLoanQuote() {
    const amount = parseFloat(document.getElementById('loanAmount').value) || 0;
    const term = parseInt(document.getElementById('loanTerm').value, 10);
    const quote = document.getElementById('loanQuote');
    if (amount <= 0) { quote.innerText = ''; return; }
    try {
        const res = await fetch(`${API_BASE_URL}/loan/quote`, {
            method: 'POST',
            headers: await getAuthHeaders(),
            body: JSON.stringify({ amount, term_months: term })
        });
        const d = await res.json();
        if (!res.ok) { quote.innerText = d.error || ''; return; }
        quote.innerHTML = `EMI <strong>${formatINR(d.emi)}</strong>/month for ${d.term_months} months · ` +
            `total repayment <strong>${formatINR(d.total_repayment)}</strong> ` +
            `(interest ${formatINR(d.total_interest)})`;
    } catch (e) {
        quote.innerText = '';
    }
}

// ── Wiring ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    ALLOC_IDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', recalcAllocation);
    });

    const allocBtn = document.getElementById('allocSubmit');
    if (allocBtn) allocBtn.addEventListener('click', submitAllocation);

    LOAN_IDS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', refreshLoanQuote);
        if (el) el.addEventListener('change', refreshLoanQuote);
    });

    const loanBtn = document.getElementById('loanSubmit');
    if (loanBtn) loanBtn.addEventListener('click', submitLoan);
});

async function submitAllocation() {
    const btn = document.getElementById('allocSubmit');
    btn.disabled = true;
    const payload = {
        stocks: parseFloat(document.getElementById('allocStocks').value) || 0,
        gold: parseFloat(document.getElementById('allocGold').value) || 0,
        emergency_fund: parseFloat(document.getElementById('allocEf').value) || 0,
        loan_prepay: parseFloat(document.getElementById('allocPrepay').value) || 0
    };
    try {
        const res = await fetch(`${API_BASE_URL}/allocate-month`, {
            method: 'POST',
            headers: await getAuthHeaders(),
            body: JSON.stringify(payload)
        });
        const d = await res.json();
        if (res.ok) {
            showToast(d.message || 'Allocation confirmed', 'success');
            ALLOC_IDS.forEach(id => { document.getElementById(id).value = 0; });
            await loadDashboard();
        } else {
            showToast(d.error || 'Allocation failed', 'error');
            btn.disabled = false;
        }
    } catch (e) {
        showToast('Failed to connect to server', 'error');
        btn.disabled = false;
    }
}

async function submitLoan() {
    const btn = document.getElementById('loanSubmit');
    const amount = parseFloat(document.getElementById('loanAmount').value) || 0;
    const term = parseInt(document.getElementById('loanTerm').value, 10);
    btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE_URL}/loan`, {
            method: 'POST',
            headers: await getAuthHeaders(),
            body: JSON.stringify({ amount, term_months: term })
        });
        const d = await res.json();
        if (res.ok) {
            showToast(`${d.message} EMI ${formatINR(d.emi)}/month.`, 'success');
            await loadDashboard();
        } else {
            showToast(d.error || 'Loan request failed', 'error');
        }
    } catch (e) {
        showToast('Failed to connect to server', 'error');
    }
    btn.disabled = false;
}


// ── INSURANCE (replaces the removed Social Investment / trust mechanic) ──────
function renderInsurance(ins) {
    const wrap = document.getElementById('insuranceOptions');
    if (!wrap || !ins) return;

    wrap.innerHTML = ins.plans.map(p => {
        const selected = p.id === ins.current;
        return `<button class="choice-card" data-plan="${p.id}"
                    style="text-align:left; cursor:pointer; width:100%;
                           border:1px solid ${selected ? 'var(--accent-emerald)' : 'var(--border-glass)'};
                           background:${selected ? 'rgba(16,185,129,0.08)' : 'transparent'};">
            <div style="font-weight:600; font-size:0.9rem; display:flex; justify-content:space-between; gap:0.5rem;">
                <span>${p.name}</span>
                ${selected ? '<span style="color:var(--accent-emerald); font-size:0.75rem;">✓ Active</span>' : ''}
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.35rem;">${p.description}</div>
        </button>`;
    }).join('');

    wrap.querySelectorAll('button[data-plan]').forEach(b => {
        b.addEventListener('click', () => setInsurance(b.getAttribute('data-plan')));
    });
}

async function setInsurance(plan) {
    try {
        const res = await fetch(`${API_BASE_URL}/insurance`, {
            method: 'POST',
            headers: await getAuthHeaders(),
            body: JSON.stringify({ plan })
        });
        const d = await res.json();
        if (res.ok) {
            showToast(d.message, 'success');
            await loadDashboard();
        } else {
            showToast(d.error || 'Could not change cover', 'error');
        }
    } catch (e) {
        showToast('Failed to connect to server', 'error');
    }
}
