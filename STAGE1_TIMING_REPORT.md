# Stage 1 — Marriage Timing (Month 6 → 4): Implementation Report

**Status:** Code changes applied to the working tree only. **No commit, no push, no migration, no DB/UI-beyond-scope, no deploy.** The mandatory EV fairness gate **FAILED**, so per instruction I stopped, did **not** retune archetypes, and am reporting for approval.

---

## Files Changed

| File | What changed | Class |
|---|---|---|
| `backend/models/constants.py` | `MARRIAGE_MONTH = 6` → `4` | A |
| `backend/routes/player_routes.py` | 6 marriage-specific literal `6`s → `MARRIAGE_MONTH` (lock_turn guard, courtship_reveal gate, courtship_marry gate, marriage score `month=`, both marriage month-log entries) | A |
| `frontend/js/dashboard.js` | courtship UI gate `p.month === 6` → `p.month === courtship.marriage_month` (self-syncs to backend) | A |
| `frontend/js/mascot.js` | marriage hint `m === 6` → `m === data.courtship.marriage_month` | A |
| `frontend/dashboard.html` | marriage panel text/comment "Month 6" → "Month 4" | D |
| `frontend/admin.html` | marriage-round help text "Month 6" → "Month 4" | D |

*(Working tree also shows `backend/utils.py` and `frontend/js/case-study.js` as modified — those are **pre-existing** uncommitted changes from before this session; I did **not** touch them in Stage 1.)*

No hardcoded `4` in the frontend — both gates read the backend-provided `courtship.marriage_month`, so they track `MARRIAGE_MONTH` automatically.

---

## Marriage Timing Changes

- Marriage eligibility (reveal, marry, lock-turn guard) now fires at **`MARRIAGE_MONTH` (=4)**.
- Marriage scoring and both month-log entries now record **Month 4**.
- Frontend courtship panel and mascot hint now appear when `player.month === courtship.marriage_month` (=4).
- `negotiation_service`, `monthly_processor`, `scoring` formulas, `event_engine`, archetype economics, `WEDDING_COST`, satisfaction — **untouched**.

---

## Tests

`python -m unittest discover -s tests` → **69 passed / 0 failed / 0 skipped.** Compile clean (`py_compile`). The timing change is code-correct and breaks nothing in the suite.

---

## EV Simulation — BEFORE vs AFTER

Run: `backend/tools/marriage_ev_sim.py`, before (month 6) and after (month 4).

**Market ON**

| Gate | Month 6 | Month 4 | Result |
|---|---:|---:|---|
| Spread (≤8%) | 4.0% | **13.9%** | ❌ FAIL |
| Single viability (±4%) | +1.7% | +0.2% | ✅ PASS |
| Strict dominance | none | **The Earner +7.3%** | ❌ FAIL |

**Market OFF**

| Gate | Month 6 | Month 4 | Result |
|---|---:|---:|---|
| Spread (≤8%) | 5.5% | **16.5%** | ❌ FAIL |
| Single viability (±4%) | +1.6% | −0.0% | ✅ PASS |
| Strict dominance | none | **The Earner +7.0%** | ❌ FAIL |

**Verdict: FAIL — needs tuning** (both markets). Independently reproduced; the Month-6 baseline (4.0% / 5.5%) still reproduces exactly before the change.

### Why the earlier marriage timing caused it (root cause, not a bug)
Marriage now lands **2 months earlier**, so every spouse contributes income for **9 months (m4–12)** instead of **7 (m6–12)**. That extra window rewards **recurring income** far more than a **one-time asset injection**:
- **The Earner** (income ₹16,000/mo, almost no brought assets) gains ~2 × ₹16,000 = **~₹32,000** of extra spouse income → it pulls clear of the field and becomes **strictly dominant (+7.0–7.3%)**.
- **The Investor** (low income ₹4,000, asset-heavy) barely benefits from the extra 2 months → it sags to the bottom.
- The gap between the income-heavy top and the asset-heavy bottom widens → **spread blows out to 13.9% / 16.5%**, well past the 8% gate.

The four archetypes were EV-certified **for marriage at Month 6**. Their income/asset mix is only balanced against a 7-month contribution window; at a 9-month window the balance tips toward income. This is exactly the non-mechanical dependency flagged as the Stage-1 gate in the dependency audit.

---

## Regression Checks (code-verified; HTTP/live paths marked)

| # | Check | Result |
|---|---|---|
| 1 | Marriage offer appears in Month 4 | ✅ code (backend gates + frontend gate now use month 4 / `courtship.marriage_month`) — *HTTP not run* |
| 2 | Courtship/reveal available Month 4 | ✅ code (`!= MARRIAGE_MONTH`) |
| 3 | Marriage completes Month 4 | ✅ code |
| 4 | Marriage NOT available Month 6 | ✅ code (gate now rejects `month != 4`, so month 6 is rejected) |
| 5 | Marriage scoring uses Month 4 | ✅ code (`month=MARRIAGE_MONTH`) |
| 6 | Marriage month logs record Month 4 | ✅ code (both inserts `MARRIAGE_MONTH`) |
| 7 | Lock-turn guard uses Month 4 | ✅ code (`== MARRIAGE_MONTH`) |
| 8 | Dashboard displays Month 4 messaging | ✅ text updated |
| 9 | Mascot hint uses configured marriage month | ✅ `data.courtship.marriage_month` |
| 10 | Monthly spouse processing still correct | ✅ tests (monthly_processor untouched; `test_monthly_processor_adds_spouse_income` green) |
| 11 | Negotiation engine unchanged | ✅ `negotiation_service.py` not in diff |
| 12 | Unrelated Month-6/9 event logic unchanged | ✅ `event_engine.py` not in diff; `month>=6` / `month>=9` still present |

*No authenticated production marriage test was run (game is post-event at month 12; no safe test account exercised).*

---

## Unrelated Logic Confirmed Untouched
`negotiation_service.py`, AI service/prompts, spouse character model, archetype economics (`ARCHETYPES`, income/assets/expense_mod/loan, floor ratios), `WEDDING_COST`, spouse income/assets, satisfaction model, `monthly_processor`, scoring **formulas**, `event_engine` Month-6/Month-9 rules, database schema, Supabase data, migrations. None modified.

---

## Final Decision

# STAGE 1 BLOCKED — EV/BALANCE ISSUE

The **code** change is complete and correct (69/69 tests, compile clean, timing verified, engine/economics untouched). But moving marriage to Month 4 **breaks two of the three fairness gates** — spread (13.9% / 16.5% vs ≤8%) and strict dominance (The Earner +7.0–7.3%) — because the extra 2-month spouse-income window favours the income-heavy archetype. As instructed, I did **not** retune `ARCHETYPES` / income / assets / expense_mod / loan / floor ratios.

**State:** changes are staged in the working tree only — uncommitted, unpushed, not deployed, DB untouched. **Do not deploy Month-4 as-is; it is economically unfair.**

**Decision needed from you (options):**
1. **Approve a re-tune** of the four archetype stat blocks to restore EV-balance at a 9-month window (e.g., trim The Earner's income and/or lift the asset-heavy archetypes), then re-run the sim to green. — *I will not start this without your explicit go-ahead.*
2. **Adjust a timing lever instead of the archetypes** — e.g., keep the wedding/asset injection but scale spouse income by remaining months, or set an income ramp — a design change, needs its own approval.
3. **Revert Stage 1** back to Month 6 and reconsider the concept timeline.

Say which, and I'll proceed. Until then, nothing is committed or deployed.
