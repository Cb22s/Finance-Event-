# Money Master — RC4 Production-Hardening Session Notes

**Date:** 2026-07-15 · **Role:** Lead/Security/QA/Release Engineer (Claude) · **Authority:** continuous hardening pass authorized by product owner; architecture/PRD/ADRs/SRS/scoring/gameplay frozen. Inputs: `RC3_PRODUCTION_AUDIT.md`, `QA_REPORT_V1.md`, `RC1_REPORT.md`, `RC2_READINESS_PLAN.md`.

This session implemented the High findings and the low-risk Medium/documentation findings from the RC3 audit, ran full verification, and re-audited. Deploy remains manual and between-games (ADR-012).

---

## 1. What was implemented

| ID | Sev | Type | Change |
|---|---|---|---|
| **F-01** (QA-014) | High | Backend code | `market_engine.calculate_investment_growth`: both `rng.uniform` draws hoisted **unconditionally**, fixed order (stock vol → gold fluct); `> 0` guards now gate only application. Restores ADR-009 / SRS §5 Inv.2 fairness. |
| **F-02** | High | Deploy docs | `DEPLOY_FRESH.md §2` now lists the **four** canonical fresh-install files in order (adds `admin_setup.sql`, `idempotency_migration.sql`), preventing the silent break of buy-choice/relative-help. README updated to match. |
| **F-03** | Medium | Backend code | `game_service.mark_action` no longer swallows all exceptions — only a unique-violation returns `False` ("already claimed"); every other error re-raises so misconfig is loud. New helper `_is_unique_violation`. |
| **F-04** | Medium | SQL/docs | `supabase_migration.sql` given a bold **SUPERSEDED — DO NOT RUN** header (it re-opens public `player_state` reads and reverts the scoring RPC). README's instruction to run it removed. |
| **F-05** | Medium | Hygiene | Stray `frontend/backend/` neutralized: service-key field stripped, files replaced with deprecation warnings, dir added to `.gitignore`. **Manual follow-up:** `git rm -r "frontend/backend"`. |
| **F-06** | Medium | Deploy docs | `DEPLOY_FRESH.md` §3/§4a/§6 rewritten to match the shipped **login-only** flow (admin-created accounts; email/password admin at `/admin-login.html`). |
| **F-07** | Low | Docs | `ADMIN_TOKEN`/`X-Admin-Token` purged from `DEPLOY_FRESH.md`, `backend/.env.example`, `V1_IMPLEMENTATION_PLAN.md §7.2`. |
| **QA-013** | Medium | Ops docs | New `RUNBOOK.md` — admin recovery procedures (backend down, wrong event, early advance, per-player fix, Start-Game misclick, full rollback). |

**Documented only (per rules — Low/cosmetic/conditional):** F-08 (dead `utils.py`), F-09 (cash read-modify-write race, single-user narrow window), F-10 (`case_study` seed vs constants; dead `relative_events`), QA-006/008/009/010/011.

**Deliberately deferred:** **QA-012** (per-player sequential queries in `/next-month`). Conditional Medium (only matters >~100 players) on the financial hot path; cannot be integration-tested against a live DB in this environment. Shipping unverified would violate "low-risk / don't weaken verification." Pre-specified batch-fetch fix (SRS §9 / Plan T2.1) stays ready for a future between-games change once headcount is confirmed.

---

## 2. Files modified

**Code:** `backend/engine/market_engine.py`, `backend/services/game_service.py`.
**SQL:** `supabase_migration.sql` (SUPERSEDED header only — no logic change).
**Docs:** `DEPLOY_FRESH.md`, `README.md`, `backend/.env.example`, `V1_IMPLEMENTATION_PLAN.md`, `QA_REPORT_V1.md` (addendum), `.gitignore`.
**New:** `RUNBOOK.md`, `RC4_HARDENING_NOTES.md`. `frontend/backend/.env` + `requirements.txt` overwritten with deprecation warnings.

**No new migration files created** — all fixes are code or documentation; no schema change against a running project. F-01/F-03 are backend-code changes that deploy with the backend, between games.

---

## 3. Verification results

- **Full unit/determinism/fairness suite:** `python -m unittest` → **30 / 30 PASS** (was 29/30; the failing `test_zero_holding_players_do_not_break_fairness_for_others` now passes).
- **Fairness (F-01):** zero-stock and stock-holding players with identical gold now receive an **identical** gold rate (2.371%); a 5-portfolio diverse sweep yields exactly **one** distinct gold rate. ADR-009 satisfied.
- **Determinism:** same-month repeat byte-identical; stock rate distinct across all 11 months (non-degenerate). Both-asset holders unchanged from pre-fix (same seed/draw order).
- **Security:** all `player_*` RLS policies are SELECT-own-only; both `SECURITY DEFINER` RPCs revoked from PUBLIC/anon/authenticated and granted only `service_role`; frontend performs zero direct DB writes. No public write policy in canonical schema.
- **Migration:** all 13 backend-referenced tables are created by the four canonical fresh-install files; superseded file quarantined.
- **Deployment:** `DEPLOY_FRESH.md` order/keys/auth now match reality.

---

## 4. Scorecard (Δ vs RC3)

| Dimension | RC3 | RC4 | Note |
|---|---|---|---|
| Production Readiness | 60 | **72** | Code/security/deploy-integrity closed; content pack + dry run + deploy-of-fixes still open |
| Security | 75 | **85** | Stale-migration landmine + frontend footgun neutralized; RLS/RPC verified |
| Financial Correctness | 80 | **88** | F-01 fairness restored; F-09 minor race documented |
| Fairness | 70 | **95** | F-01 fixed and verified 30/30 |
| Performance | 60 | **60** | Unchanged; QA-012 deferred with rationale |
| Maintainability | 70 | **76** | Loud-failure gate, doc drift corrected, migration quarantined |

---

## 5. GO / NO-GO

- **Code / Security / Deploy-integrity: GO.** Zero open Critical, zero open code-level High; suite green; deploy docs correct.
- **Live event: NO-GO** — unchanged from RC1/RC2, blocked by operational items outside this session's code scope: author the months 2–12 content pack; commit + deploy the (now-larger) approved backend set and run the live smoke test; perform a full 12-month dry run; confirm headcount (and decide QA-012). `RUNBOOK.md` now exists, removing that blocker.

*End of RC4 notes. Fixes are in the working tree, verified by the suite; deployment is manual, between games.*
