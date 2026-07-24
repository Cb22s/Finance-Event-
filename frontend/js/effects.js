// ============================================================================
// EFFECTS — real-time visual feedback layer
// ============================================================================
// Pure presentation. Knows nothing about game rules; other scripts call these
// helpers. Respects prefers-reduced-motion (the CSS disables the animations and
// the counter falls back to setting the final value instantly).
// ============================================================================

const REDUCED_MOTION = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Remembers the last numeric value shown in each element so we can animate the
// delta between polls instead of snapping.
const _lastValues = {};

function _formatINRnum(v) {
    return '₹' + Math.round(v).toLocaleString('en-IN');
}

// Animate an element's number from its previous value to `to`, flashing
// green/red and floating a +/- delta chip. Used for cash, stocks, net worth etc.
function animateValue(elId, to) {
    const el = document.getElementById(elId);
    if (!el) return;
    const from = _lastValues[elId];
    _lastValues[elId] = to;

    // First render, or reduced motion → just set it.
    if (from === undefined || REDUCED_MOTION || from === to) {
        el.textContent = _formatINRnum(to);
        return;
    }

    const delta = to - from;
    _floatDelta(el, delta);
    el.classList.remove('value-up', 'value-down');
    void el.offsetWidth; // restart animation
    el.classList.add(delta >= 0 ? 'value-up' : 'value-down');

    el.classList.add('ticking');
    const start = performance.now();
    const dur = 650;
    function frame(now) {
        const t = Math.min(1, (now - start) / dur);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = _formatINRnum(from + delta * eased);
        if (t < 1) requestAnimationFrame(frame);
        else el.textContent = _formatINRnum(to);
    }
    requestAnimationFrame(frame);
}

function _floatDelta(el, delta) {
    if (Math.abs(delta) < 1) return;
    const host = el.closest('.stat-card, .net-worth-card, .glass-card') || el.parentElement;
    if (!host) return;
    if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
    const chip = document.createElement('span');
    chip.className = 'delta-chip ' + (delta >= 0 ? 'up' : 'down');
    chip.textContent = (delta >= 0 ? '+' : '-') + _formatINRnum(Math.abs(delta)).slice(1);
    host.appendChild(chip);
    setTimeout(() => chip.remove(), 1500);
}

// Shake a card — for a bad shock (emergency, market crash).
function shake(elId) {
    const el = document.getElementById(elId);
    if (!el || REDUCED_MOTION) return;
    el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake');
}

// Glow a card — for a good outcome.
function celebrate(elId) {
    const el = document.getElementById(elId);
    if (!el || REDUCED_MOTION) return;
    el.classList.remove('celebrate'); void el.offsetWidth; el.classList.add('celebrate');
}

// Confetti burst — for a big win / finishing the game well.
function confetti(count) {
    if (REDUCED_MOTION) return;
    const colors = ['#6366f1', '#10b981', '#f59e0b', '#f43f5e', '#06b6d4', '#a855f7'];
    const n = count || 80;
    for (let i = 0; i < n; i++) {
        const p = document.createElement('div');
        p.className = 'confetti-piece';
        p.style.left = Math.random() * 100 + 'vw';
        p.style.background = colors[i % colors.length];
        p.style.animationDuration = (2 + Math.random() * 1.8) + 's';
        p.style.animationDelay = (Math.random() * 0.4) + 's';
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 4200);
    }
}

// Reveal animation for the event / news card.
function revealEvent(elId) {
    const el = document.getElementById(elId);
    if (!el || REDUCED_MOTION) return;
    el.classList.remove('event-reveal'); void el.offsetWidth; el.classList.add('event-reveal');
}

// Expose globally so dashboard.js (loaded separately) can call these.
window.fx = { animateValue, shake, celebrate, confetti, revealEvent };
