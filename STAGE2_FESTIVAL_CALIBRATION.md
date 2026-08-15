# Stage 2 — Festival Initial-Budget Calibration (Sensitivity Analysis)

**Status:** ANALYSIS ONLY. No source/DB/UI/AI/negotiation change; nothing committed. All numbers computed from the exact Stage-2 formula and the real repository values (player income ₹100,000; spouse income 5k/16k/4k/7k; Stage-1B expense_mod −2,500/+4,500/−1,500/−500; floor ratios saver 0.50 / earner 0.70 / investor 0.60 / anchor 0.55; POSTURE_SCALE 30,000; satisfaction 60). Central values use jitter = 0.

**Headline finding (up front):** `base_k` and `importance` enter the formula **only as their product** (`Ask ∝ base_k × importance`). They are therefore one mathematical degree of freedom for the *size* of the ask and have **zero** effect on archetype *differentiation* — the inter-archetype spread is a constant **~27.7%** in every one of the 25 cells. This is not a bug (the formula is self-consistent); it is a redundancy the brief asked me to evaluate (Q3/Q4). I am reporting it, not changing anything.

---

## 1. Sensitivity Matrix (5 × 5, central asks in ₹, jitter = 0)

| base_k | imp | eff | Saver | Earner | Investor | Anchor | avg | min | max | spread | spr% |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 1.00 | 0.500 | 48,000 | 66,500 | 49,500 | 52,500 | 54,125 | 48,000 | 66,500 | 18,500 | 27.8% |
| 0.50 | 1.05 | 0.525 | 50,500 | 70,000 | 52,000 | 55,000 | 56,875 | 50,500 | 70,000 | 19,500 | 27.9% |
| 0.50 | 1.10 | 0.550 | 53,000 | 73,500 | 54,500 | 58,000 | 59,750 | 53,000 | 73,500 | 20,500 | 27.9% |
| 0.50 | 1.15 | 0.575 | 55,500 | 76,500 | 57,000 | 60,500 | 62,375 | 55,500 | 76,500 | 21,000 | 27.5% |
| 0.50 | 1.20 | 0.600 | 58,000 | 80,000 | 59,500 | 63,000 | 65,125 | 58,000 | 80,000 | 22,000 | 27.5% |
| 0.60 | 1.00 | 0.600 | 58,000 | 80,000 | 59,500 | 63,000 | 65,125 | 58,000 | 80,000 | 22,000 | 27.5% |
| 0.60 | 1.05 | 0.630 | 60,500 | 84,000 | 62,000 | 66,500 | 68,250 | 60,500 | 84,000 | 23,500 | 28.0% |
| 0.60 | 1.10 | 0.660 | 63,500 | 88,000 | 65,000 | 69,500 | 71,500 | 63,500 | 88,000 | 24,500 | 27.8% |
| 0.60 | 1.15 | 0.690 | 66,500 | 92,000 | 68,000 | 72,500 | 74,750 | 66,500 | 92,000 | 25,500 | 27.7% |
| 0.60 | 1.20 | 0.720 | 69,500 | 96,000 | 71,000 | 76,000 | 78,125 | 69,500 | 96,000 | 26,500 | 27.6% |
| 0.65 | 1.00 | 0.650 | 62,500 | 86,500 | 64,000 | 68,500 | 70,375 | 62,500 | 86,500 | 24,000 | 27.7% |
| 0.65 | 1.05 | 0.683 | 65,500 | 91,000 | 67,500 | 72,000 | 74,000 | 65,500 | 91,000 | 25,500 | 28.0% |
| **0.65** | **1.10** | **0.715** | **69,000** | **95,500** | **70,500** | **75,000** | **77,500** | **69,000** | **95,500** | **26,500** | **27.7%** |
| 0.65 | 1.15 | 0.747 | 72,000 | 99,500 | 74,000 | 78,500 | 81,000 | 72,000 | 99,500 | 27,500 | 27.6% |
| 0.65 | 1.20 | 0.780 | 75,000 | 104,000 | 77,000 | 82,000 | 84,500 | 75,000 | 104,000 | 29,000 | 27.9% |
| 0.70 | 1.00 | 0.700 | 67,500 | 93,500 | 69,000 | 73,500 | 75,875 | 67,500 | 93,500 | 26,000 | 27.8% |
| 0.70 | 1.05 | 0.735 | 70,500 | 98,000 | 72,500 | 77,500 | 79,625 | 70,500 | 98,000 | 27,500 | 28.1% |
| 0.70 | 1.10 | 0.770 | 74,000 | 102,500 | 76,000 | 81,000 | 83,375 | 74,000 | 102,500 | 28,500 | 27.8% |
| 0.70 | 1.15 | 0.805 | 77,500 | 107,500 | 79,500 | 84,500 | 87,250 | 77,500 | 107,500 | 30,000 | 27.9% |
| 0.70 | 1.20 | 0.840 | 81,000 | 112,000 | 83,000 | 88,500 | 91,125 | 81,000 | 112,000 | 31,000 | 27.7% |
| 0.75 | 1.00 | 0.750 | 72,000 | 100,000 | 74,000 | 79,000 | 81,250 | 72,000 | 100,000 | 28,000 | 28.0% |
| 0.75 | 1.05 | 0.788 | 76,000 | 105,000 | 78,000 | 83,000 | 85,500 | 76,000 | 105,000 | 29,000 | 27.6% |
| 0.75 | 1.10 | 0.825 | 79,500 | 110,000 | 81,500 | 87,000 | 89,500 | 79,500 | 110,000 | 30,500 | 27.7% |
| 0.75 | 1.15 | 0.862 | 83,000 | 115,000 | 85,000 | 90,500 | 93,375 | 83,000 | 115,000 | 32,000 | 27.8% |
| 0.75 | 1.20 | 0.900 | 86,500 | 120,000 | 89,000 | 94,500 | 97,500 | 86,500 | 120,000 | 33,500 | 27.9% |

Note the proof of redundancy: `(0.50, 1.20)` and `(0.60, 1.00)` — both eff = 0.600 — are **identical rows**. Guardrails (MIN ≈ 0.25×HHI ≈ 26k; SOFT_CAP ≈ 1.5×HHI ≈ 156–174k) never bind anywhere in the matrix — healthy (they're safety rails for future extreme `CharAdj`, dormant now).

## 2. Archetype-Level Results — base_k = 0.65, importance = 1.10

| Archetype | HHI | Expense Mod | Posture | Base | Initial Ask | Negotiation Floor |
|---|---:|---:|---:|---:|---:|---:|
| Saver | 105,000 | −2,500 | 0.917 | 68,250 | **69,000** | 45,500 |
| Earner | 116,000 | +4,500 | 1.150 | 75,400 | **95,500** | 76,000 |
| Investor | 104,000 | −1,500 | 0.950 | 67,600 | **70,500** | 51,500 |
| Anchor | 107,000 | −500 | 0.983 | 69,550 | **75,000** | 52,000 |

Jitter band (±2%): Saver 67.5–70k · Earner 93.5–97.5k · Investor 69–72k · Anchor 73.5–76.5k. Small, cosmetic, seeded.

## 3. Economic Interpretation

At 0.65/1.10 the asks are **0.66–0.82 × household income** (0.69–0.95 × the player's ₹100k monthly salary). Against a game where a disciplined player ends ~₹130k net worth over 12 months, a one-time festival of ₹69k–95.5k is a **financially meaningful decision** — big enough to matter, not big enough to end a run, and negotiable. The **Earner** asks the most (₹95.5k — her income + lifestyle) and the **Saver** the least (₹69k — frugal); the household that has to fund the Earner's festival is also the one with the extra ₹16k/mo income, so the ask scales with the capacity to pay. The effective baseline **0.715** means: *before* the spouse's spend-lean, the festival is pitched at ~72% of a month's household income — a "significant family event," which is the intended feel.

## 4. Parameter Redundancy Analysis (Q3 & Q4)

**Q3 — Are `base_k` and `importance` duplicating the same scaling? Yes, mathematically.** `Ask = round500(base_k × HHI × Posture × importance)` — the two constants appear **only** as the product `base_k × importance`. The matrix confirms it empirically: equal products give identical asks, and spread% is invariant (~27.7%) because neither constant touches the differentiators (`HHI`, `Posture`). Today they are **one** degree of freedom for the number.

**Q4 — Keep both, or make one a different concept?** Keep both, but with a clear division of labour and calibrate the **product**, not each in isolation:
- `base_k` = the **global economy anchor** — festival size as a share of household income. Set once, rarely changed, lives with the economy constants.
- `importance` = the **per-event social/family weight** — varies *between* festivals (a minor festival vs. a wedding-season one) and is the seam the future **family/character model** will feed (family_festival_importance, status).

That semantic split is valid and future-useful even though the two are mathematically fused *right now* (there is currently one festival and `CharAdj = 1.0`). Recommendation: **retain both for clarity and future-proofing, document that only their product is economically active today, and tune via the effective baseline.** Collapsing them into a single constant now would just have to be re-split when multiple festivals / the character model arrive — no benefit.

## 5. Negotiation Quality (at 0.65/1.10)

| Archetype | Ask | Floor | Floor % of ask | Max cut | Feel |
|---|---:|---:|---:|---:|---|
| Saver | 69,000 | 45,500 | 65.9% | **34.1%** | easiest to trim (frugal) |
| Anchor | 75,000 | 52,000 | 69.3% | 30.7% | moderately movable |
| Investor | 70,500 | 51,500 | 73.0% | 27.0% | moderate |
| Earner | 95,500 | 76,000 | 79.6% | **20.4%** | firmest (defends her lifestyle) |

This is **good** negotiation design: floors sit at 66–80% of the ask, so the player can meaningfully reduce (20–34%) but can't trivialise it, and **archetype clearly changes difficulty** (Saver cuttable to −34%, Earner only −20%). The room (₹19k–23.5k) is a real decision at this economy. Importantly, negotiation quality is driven by the **floor ratios** (locked) and the ask size — so it holds across the whole recommended range, not just this cell.

## 6. Recommended Range

Because only the **product** matters, I recommend an **effective-baseline** range and a way to split it:

- **Effective baseline (`base_k × importance`): 0.62 – 0.72.** Below ~0.60 the festival starts to feel trivial vs. a ₹100k salary; above ~0.75 the Earner ask crosses ₹100k (a full month's salary, one-time) and risks feeling punitive.
- Split as: **`base_k` 0.60 – 0.65** (global anchor) **×** **`importance` 1.00 – 1.10** (event weight). Provisional single festival: `base_k = 0.62`, `importance = 1.08` → eff ≈ 0.67.

## 7. Recommended Candidate

No cell is *mathematically* superior (they're a continuum of one product), so this is a **design-feel** call, not an optimisation. I recommend nudging **slightly below** the provisional to keep the Earner's top-end under a full month's salary:

- **base_k = 0.62, importance = 1.08 → effective ≈ 0.67.** Asks ≈ Saver 64k · Earner 88k · Investor 65k · Anchor 70k; Earner stays < ₹90k, all still meaningful, negotiation room unchanged (floor ratios are independent of scale).
- The provisional **0.65 / 1.10** is also perfectly defensible if you want the festival to bite a little harder (Earner 95.5k). Either is fine; the difference is tone, not correctness.

**Do not lock either yet** — the right effective baseline is best confirmed by one playtest, and `importance` will change meaning once the character/family model lands.

## 8. Risks

- **Economic:** at the high end (eff ≥ 0.80) the Earner ask exceeds ₹100k — a full month's salary as a one-time hit — which could feel punitive; keep eff ≤ ~0.72.
- **Balancing:** the festival is a **one-time** outflow at settlement (like WEDDING_COST), so it does **not** perturb the EV-balanced monthly economy — *provided* it is modelled as a one-time cost, not a recurring modifier. (Confirm at implementation.)
- **Player experience:** three of four archetypes cluster (Saver 69k / Investor 70.5k / Anchor 75k) because `expense_mod` is a weak differentiator and HHI barely varies at a ₹100k salary. Only the Earner stands apart. The festival will feel *samey* across three spouses until the character model adds status/tradition/frugality — a known, accepted limitation, not a calibration failure.
- **Parameter interaction:** the `base_k × importance` fusion means a future author who bumps `importance` for a "bigger" festival is really just scaling `base_k` — document this so no one double-scales by accident.
- **Future character-model risk:** once `CharAdj ≠ 1.0` and `importance` blends with family traits, the *effective* multiplier could drift past the guardrails; the SOFT_CAP (1.5×HHI) is the backstop — keep it.

## 9. Stage 2 Decision

# B. CALIBRATION PASS — PARAMETERS PROVISIONAL

The model is economically sensible: asks are meaningful (0.66–0.82× HHI), guardrails stay dormant, archetype ordering holds, and negotiation room is real and archetype-differentiated. But (1) `base_k` and `importance` are **one mathematical lever** today — calibrate their product, keep both only for semantic/future clarity — and (2) the exact effective baseline is a design-feel choice best confirmed by a single playtest and revisited when the character model gives `importance` real independent meaning. Recommended working point: **effective ≈ 0.67 (e.g. base_k 0.62 × importance 1.08)**, with the provisional 0.65 / 1.10 an acceptable alternative. Parameters stay **provisional**, not production-locked.

---

*No files changed. Awaiting your pick of the effective baseline (and whether to keep the two-knob split) before Stage 3 implementation.*
