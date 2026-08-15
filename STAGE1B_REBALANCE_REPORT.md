# Stage 1B — Archetype Rebalance for Month-4 Marriage

**Scope:** balancing only. Marriage stays Month 4. No negotiation/scoring/processor/event/AI/schema changes. Working tree only — not committed, not deployed, live DB untouched.

---

## 1. Current Month-4 Baseline (before rebalance)

| Market | Spread (≤8%) | Viability (±4%) | Dominance | Verdict |
|---|---:|---:|---|---|
| ON | 13.9% ❌ | +0.2% ✅ | The Earner +7.3% ❌ | FAIL |
| OFF | 16.5% ❌ | −0.0% ✅ | The Earner +7.0% ❌ | FAIL |

Archetype means (₹k), ON: Single 130.3 · Saver 126.5 · **Earner 141.5** · **Investor 121.9** · Anchor 131.9.

---

## 2. Root-Cause Sensitivity Analysis

Measured against the sim's own `simulate()` (marginal effect of each parameter on an archetype's mean net worth):

| Parameter bump | Δ mean, Market ON | Δ mean, Market OFF |
|---|---:|---:|
| income +₹1,000/mo | **+₹9.3k** | **+₹9.1k** |
| expense_mod −₹1,000 (=+₹1,000/mo net flow) | **+₹9.3k** | **+₹9.1k** |
| stocks +₹5,000 (one-time) | +₹5.6k | +₹5.0k |
| gold +₹5,000 (one-time) | +₹5.3k | +₹5.0k |
| ef +₹5,000 (one-time) | +₹5.2k | +₹5.2k |

**Conclusion:** net **monthly flow** (income − household expense) has ~**9.2× leverage** because it now compounds over **9 months** (m4–12); one-time brought assets are only ~1.0–1.1×. The imbalance is entirely **net-flow dispersion**:

| Archetype | income | +spouse_base+expense_mod | **net flow/mo** |
|---|---:|---:|---:|
| Earner | 16,000 | 9,000+3,500 | **+3,500** (highest) |
| Anchor | 7,000 | 9,000−500 | −1,500 |
| Saver | 5,000 | 9,000−2,500 | −1,500 |
| Investor | 4,000 | 9,000−500 | **−4,500** (lowest) |

Over 9 months the Earner→Investor flow gap (₹8,000/mo) opens a ~₹72k swing — that is the dominance and the blown spread. Brought assets (Investor's portfolio) can't close a gap that large. So the fix must **compress the two extreme net flows**, and to preserve identity it should touch **household expense, not income or assets**.

---

## 3. Candidate 1 — RECOMMENDED (passes)

Change **only the two extreme `expense_mod` values**. All incomes, all brought assets, loans, and floor ratios unchanged.

| Archetype | Parameter | Old | New | Reason |
|---|---|---:|---:|---|
| Earner | expense_mod | +3,500 | **+4,500** | net flow +3,500→+2,500/mo. Preserves "highest income by far, biggest lifestyle" — in fact *strengthens* it (earns most, spends most). Income 16,000 untouched. |
| Investor | expense_mod | −500 | **−1,500** | net flow −4,500→−3,500/mo. Lifts the 9-month drain that sank the portfolio archetype. Income 4,000 and the 35k+16k portfolio untouched — still "a market bet, not a salary." |

EV result (official `marriage_ev_sim.py`):

| Market | Spread | Viability | Dominance | Pass/Fail |
|---|---:|---:|---|---|
| ON | **4.3%** | **+0.1%** | none | ✅ PASS |
| OFF | **4.3%** | **−0.0%** | none | ✅ PASS |

Means (₹k) ON: Single 130.3 · Saver 126.5 · Earner 132.2 · Investor 131.2 · Anchor 131.9. OFF: Single 125.7 · Saver 122.7 · Earner 128.2 · Investor 123.6 · Anchor 128.2.

**Companion edit (required, transparent):** `marriage_migration.sql` seed rows for earner/investor updated to the same two values, because `test_archetype_source_consistency` (the D-01 guard) asserts the seed mirrors `constants.ARCHETYPES`. This is a **data-value mirror only** — no DDL, not applied to the DB, not run as a migration. (The live `spouse_archetypes` table still holds the old values; the engine reads `constants`, so gameplay uses the new ones. Re-syncing the live table is a deploy-time step, not done here.)

---

## 4. Candidate 2 — (tested, REJECTED)

Earner +3,500→+5,000, Investor −500→−2,000, Saver −2,500→−2,000. Over-corrected:

| Market | Spread | Viability | Dominance | Pass/Fail |
|---|---:|---:|---|---|
| ON | 10.3% | −0.7% | **The Investor +3.0%** | ❌ FAIL |
| OFF | 7.9% | −0.9% | none | ⚠ marginal |

Pushed the Investor into dominance and weakened the Saver too far. Discarded. **Candidate 3 not needed** — Candidate 1 already passes cleanly with a strictly smaller change.

---

## 5. Candidate 3
Not required (Candidate 1 passed).

---

## 6. Recommended Configuration
**Candidate 1.** It is the minimum defensible change: **two parameters, both `expense_mod`, ±₹1,000**, no income or asset touched. It restores all three gates in **both** markets with margin (4.3% spread vs 8% cap), and it fixes the cause (net-flow dispersion) at the exact two extremes rather than smearing changes across the set.

---

## 7. Economic Identity Check

| Archetype | Identity | Preserved? |
|---|---|---|
| **Saver** | conservative, savings-oriented, lean household | ✅ Untouched (income 5,000, expense_mod −2,500 — still the leanest household; gold 12k + ef 23k cushion) |
| **Earner** | income-oriented | ✅ Income 16,000 (unchanged — still highest by far); bigger lifestyle (expense_mod +4,500) *reinforces* "earns most, spends most" |
| **Investor** | asset/portfolio, market bet | ✅ Income 4,000 (unchanged — lowest, "not a salary"); portfolio 35k stocks + 16k gold (unchanged). Means show it: **strong Market-ON (131.2), weak Market-OFF (123.6)** — exactly "worth most if the market rises, least if it stalls." Slightly leaner household, still distinct from Saver (−1,500 vs −2,500) |
| **Anchor** | stable income + big emergency fund | ✅ Untouched (income 7,000, ef 35k) |

The four remain distinct in income (5k/16k/4k/7k), expense_mod (−2,500/+4,500/−1,500/−500), and asset profile. Not made equivalent.

---

## 8. Regression Tests
- `python -m unittest discover -s tests` → **69 passed / 0 failed / 0 skipped** (includes `test_archetype_source_consistency` — green because the seed mirror was updated).
- `marriage_ev_sim.py` → both markets PASS all three gates.
- Marriage timing still **Month 4** (`MARRIAGE_MONTH = 4`, unchanged).
- Changed files: `backend/models/constants.py`, `marriage_migration.sql` (mirror seed), plus the Stage-1 timing files. **Untouched:** `negotiation_service.py`, `scoring.py`, `monthly_processor.py`, `event_engine.py`, `WEDDING_COST`, floor ratios, DB, migrations-as-run, AI. (`backend/utils.py` and `frontend/js/case-study.js` appear in the diff but are pre-existing working-tree changes, not from this task.)

---

## 9. Final Decision

# BALANCED — READY FOR STAGE 2

Two `expense_mod` values changed (Earner +3,500→+4,500, Investor −500→−1,500); all three fairness gates pass in both markets with margin; archetype identities intact; 69/69 tests green. Nothing committed, pushed, deployed, or written to the production database.

**Deploy-time note (not now):** the live `spouse_archetypes` table still holds the pre-rebalance earner/investor values — it must be re-synced to `constants` (and the Month-4 timing shipped) whenever Stage 1/1B is deployed. Flagging so it isn't missed; not actioned here per your no-DB rule.
