// ============================================================================
// MIRA — anime guide character 
// ============================================================================
// Hand-drawn SVG (no external image: nothing to load, scales to any screen,
// works offline on event-day wifi). She has 5 expressions driven by real game
// state, blinks and bobs on idle, and speaks only when the situation CHANGES —
// never on the 5-second dashboard poll, so she guides instead of nagging.
// Click her to replay the current tip.

(function () {
    let _lastKey = null;
    let _hideTimer = null;
    let _lastMessage = null;

    // ── Character artwork ────────────────────────────────────────────────────
    // Groups are id'd so expressions can swap eyes/mouth/brows without redraw.
    const CHARACTER_SVG = `
    <svg viewBox="0 0 120 130" width="100%" height="100%" aria-hidden="true">
      <defs>
        <linearGradient id="miraHair" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#7dd3fc"/>
          <stop offset="55%" stop-color="#38bdf8"/>
          <stop offset="100%" stop-color="#0ea5e9"/>
        </linearGradient>
        <linearGradient id="miraCoat" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3b82f6"/>
          <stop offset="100%" stop-color="#1d4ed8"/>
        </linearGradient>
      </defs>

      <g id="miraAll">
        <!-- back hair -->
        <path d="M18 60 C14 26 34 8 60 8 C86 8 106 26 102 60 C101 76 98 88 94 96
                 C92 78 96 60 92 48 C74 56 46 56 28 48 C24 60 28 78 26 96
                 C22 88 19 76 18 60 Z" fill="url(#miraHair)"/>

        <!-- shoulders / blazer -->
        <path d="M32 128 C34 108 44 100 60 100 C76 100 86 108 88 128 Z" fill="url(#miraCoat)"/>
        <path d="M52 101 L60 114 L68 101 L60 98 Z" fill="#f8fafc"/>
        <path d="M58 108 L62 108 L61 118 L59 118 Z" fill="#f59e0b"/>

        <!-- neck -->
        <path d="M52 88 h16 v12 c0 4 -16 4 -16 0 Z" fill="#f6d9c4"/>

        <!-- face -->
        <ellipse cx="60" cy="60" rx="30" ry="32" fill="#fde8d7"/>

        <!-- ears -->
        <ellipse cx="30" cy="62" rx="5" ry="7" fill="#fde8d7"/>
        <ellipse cx="90" cy="62" rx="5" ry="7" fill="#fde8d7"/>

        <!-- fringe / bangs -->
        <path d="M30 46 C30 22 46 12 60 12 C74 12 90 22 90 46
                 C86 36 78 30 70 34 C64 24 52 26 48 36 C42 32 34 38 30 46 Z"
              fill="url(#miraHair)"/>
        <path d="M60 12 C70 14 78 22 80 34 C74 26 66 22 60 22 Z" fill="#bae6fd" opacity="0.55"/>

        <!-- side locks -->
        <path d="M28 44 C24 60 26 78 30 92 C34 80 32 60 34 48 Z" fill="url(#miraHair)"/>
        <path d="M92 44 C96 60 94 78 90 92 C86 80 88 60 86 48 Z" fill="url(#miraHair)"/>

        <!-- brows -->
        <g id="miraBrows">
          <path id="browL" d="M40 46 q7 -4 14 -1" stroke="#0284c7" stroke-width="2.6" fill="none" stroke-linecap="round"/>
          <path id="browR" d="M66 45 q7 -3 14 1" stroke="#0284c7" stroke-width="2.6" fill="none" stroke-linecap="round"/>
        </g>

        <!-- eyes -->
        <g id="miraEyes">
          <ellipse cx="47" cy="60" rx="8" ry="9.5" fill="#ffffff"/>
          <ellipse cx="73" cy="60" rx="8" ry="9.5" fill="#ffffff"/>
          <ellipse id="irisL" cx="47" cy="60.5" rx="5.6" ry="7" fill="#0369a1"/>
          <ellipse id="irisR" cx="73" cy="60.5" rx="5.6" ry="7" fill="#0369a1"/>
          <circle cx="45" cy="57.5" r="2.3" fill="#ffffff"/>
          <circle cx="71" cy="57.5" r="2.3" fill="#ffffff"/>
          <circle cx="49" cy="63.5" r="1.1" fill="#ffffff" opacity="0.75"/>
          <circle cx="75" cy="63.5" r="1.1" fill="#ffffff" opacity="0.75"/>
        </g>

        <!-- blush -->
        <g id="miraBlush" opacity="0.5">
          <ellipse cx="38" cy="71" rx="6" ry="3.2" fill="#fb7185"/>
          <ellipse cx="82" cy="71" rx="6" ry="3.2" fill="#fb7185"/>
        </g>

        <!-- mouth -->
        <path id="miraMouth" d="M54 77 q6 6 12 0" stroke="#be5a4a" stroke-width="2.4"
              fill="none" stroke-linecap="round"/>

        <!-- floating coin she holds up -->
        <g id="miraCoin">
          <circle cx="100" cy="96" r="10" fill="#fbbf24" stroke="#d97706" stroke-width="2"/>
          <text x="100" y="101" text-anchor="middle" font-size="12" font-weight="700" fill="#92400e">₹</text>
        </g>
      </g>
    </svg>`;

    // Expression = mouth shape + brow angle + optional eye squash/blush.
    const EXPRESSIONS = {
        happy:   { mouth: 'M54 77 q6 6 12 0',  browL: 'M40 46 q7 -4 14 -1', browR: 'M66 45 q7 -3 14 1',  blush: 0.5,  squash: 1 },
        excited: { mouth: 'M52 75 q8 11 16 0', browL: 'M40 43 q7 -5 14 -2', browR: 'M66 41 q7 -4 14 2',  blush: 0.85, squash: 1.1 },
        alert:   { mouth: 'M55 78 q5 4 10 0',  browL: 'M40 43 q7 -3 14 0',  browR: 'M66 43 q7 -2 14 0',  blush: 0.4,  squash: 1.15 },
        worried: { mouth: 'M54 80 q6 -5 12 0', browL: 'M40 44 q7 3 14 -2',  browR: 'M66 42 q7 -3 14 3',  blush: 0.3,  squash: 0.95 },
        sleepy:  { mouth: 'M56 78 q4 3 8 0',   browL: 'M40 47 q7 -2 14 0',  browR: 'M66 47 q7 0 14 0',   blush: 0.35, squash: 0.35 }
    };

    function setExpression(name) {
        // If the 3D VRM model loaded, it owns the face and the SVG is hidden.
        if (window.MiraCore && window.MiraCore.on3D) {
            window.MiraCore.on3D(name);
            return;
        }
        const e = EXPRESSIONS[name] || EXPRESSIONS.happy;
        const q = (id) => document.getElementById(id);
        if (!q('miraMouth')) return;
        q('miraMouth').setAttribute('d', e.mouth);
        q('browL').setAttribute('d', e.browL);
        q('browR').setAttribute('d', e.browR);
        q('miraBlush').setAttribute('opacity', e.blush);
        const eyes = q('miraEyes');
        eyes.style.transformOrigin = '60px 60px';
        eyes.style.transform = `scaleY(${e.squash})`;
    }

    function ensureDom() {
        if (document.getElementById('mascot')) return;
        const el = document.createElement('div');
        el.id = 'mascot';
        el.innerHTML =
            '<div id="mascotBubble" role="status" aria-live="polite"></div>' +
            '<div id="mascotBody" title="Mira — your money guide" role="button" tabindex="0" ' +
            'aria-label="Mira, your guide. Activate to repeat the current tip.">' +
            CHARACTER_SVG + '</div>';
        document.body.appendChild(el);
        const body = document.getElementById('mascotBody');
        const replay = () => { if (_lastMessage) show(_lastMessage, true); };
        body.addEventListener('click', replay);
        body.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); replay(); }
        });
        startBlinking();
    }

    // Natural irregular blinking — a fixed CSS interval reads robotic.
    function startBlinking() {
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        (function loop() {
            const wait = 2200 + Math.random() * 3800;
            setTimeout(() => {
                const eyes = document.getElementById('miraEyes');
                if (eyes && !eyes.dataset.busy) {
                    const prev = eyes.style.transform;
                    eyes.style.transition = 'transform 90ms';
                    eyes.style.transform = 'scaleY(0.1)';
                    setTimeout(() => { eyes.style.transform = prev || 'scaleY(1)'; }, 110);
                }
                loop();
            }, wait);
        })();
    }

    function show(msg, force) {
        ensureDom();
        const bubble = document.getElementById('mascotBubble');
        bubble.innerHTML = msg;
        bubble.classList.add('show');
        clearTimeout(_hideTimer);
        _hideTimer = setTimeout(() => bubble.classList.remove('show'), force ? 6000 : 10000);
    }

    // First match wins — ordered by urgency.
    function pick(data) {
        const p = data.player || {};
        const alloc = data.allocation || {};
        const market = data.market || {};
        const loans = (data.loan_info && data.loan_info.outstanding) || 0;
        const ins = (data.insurance && data.insurance.current) || 'none';
        const m = p.month || 1;
        const rs = (v) => '₹' + Math.round(v).toLocaleString('en-IN');

        if (p.net_worth < 0)
            return ['neg' + m, 'worried',
                'Your net worth has gone <strong>negative</strong>. Clear debt before the interest compounds. 😰'];

        if (alloc.required && !alloc.done)
            return ['alloc' + m, 'alert',
                `You have <strong>${rs(alloc.available_cash)}</strong> sitting idle! Open the <strong>Invest</strong> tab and put it to work. 📈`];

        if (data.courtship && m === data.courtship.marriage_month && data.game && data.game.marriage_round_active && !p.spouse_archetype)
            return ['wed' + m, 'excited',
                "It's the <strong>marriage round</strong>! 💍 Use your free dates to reveal traits first — decide with your head, not just your heart. 😄"];

        if (market.stock_pct <= -0.10)
            return ['crash' + m, 'worried',
                `<strong>${market.name}</strong> just hit the market. 📉 Don't panic-sell — holding through March 2020 was the winning move. 🧘`];

        if (market.stock_pct >= 0.08)
            return ['boom' + m, 'excited',
                `<strong>${market.name}</strong> — markets are flying! 🚀 Booms always end. Rebalance while it's still green. 😎`];

        if (loans > 150000)
            return ['debt' + m, 'worried',
                `Your debt is <strong>${rs(loans)}</strong>. ⚠️ Every EMI eats a future month — prepay from the Invest tab.`];

        if (ins === 'none' && m >= 3)
            return ['ins' + m, 'alert',
                'Still no insurance? 🛡️ One hospital bill can undo months of good decisions. See <strong>Loans &amp; Cover</strong>.'];

        if (p.status === 'waiting')
            return ['wait' + m, 'sleepy',
                'Turn locked — waiting for the organizer to open the next month. 😴 Take a breather.'];

        return ['idle' + m, 'happy',
            `Month ${m} of 12. 🪙 Wealth is built in the boring months — check your split, then lock in. ✅`];
    }

    window.mascotUpdate = function (data) {
        try {
            ensureDom();
            const [key, mood, msg] = pick(data);
            _lastMessage = msg;
            setExpression(mood);
            if (key !== _lastKey) { _lastKey = key; show(msg); }
        } catch (e) { /* the guide must never break the dashboard */ }
    };
})();
