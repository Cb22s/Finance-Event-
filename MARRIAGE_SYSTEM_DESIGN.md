# Marriage & Life Partner System — Design

**ADR-002, layered on the Household foundation (ADR-001)**

- **Status:** Proposed, future version. Approved in *form* on 2026-07-11; not scheduled, not ratified for build.
- **Change level:** L5 (Product Vision) — the highest gate. Full pipeline required before any code.
- **BLOCKED BY:** Household foundation (ADR-001). Marriage inserts a member into a household; households must exist first. See `HOUSEHOLD_MIGRATION_PLAN.md`.
- **Purpose of this doc:** the design artifact for your gate review — not an implementation spec. It exists so the L5 pipeline has something concrete to evaluate.

---

## 1. Approved form (locked 2026-07-11 — do not re-litigate here)

- **EV-balanced spouse archetypes.** A fixed set; every player faces the *identical* choice set. Fairness in ranked play.
- **Deterministic trait reveal.** Hidden traits are surfaced by rules, never by RNG. No hidden-trait luck.
- **Single stays viable.** Choosing not to marry is a legitimate competitive strategy, not a handicap.
- **Explicitly deferred (separate proposals):** divorce, children, in-laws.

Everything below is *how* to realize that form. Where I add something new, it's flagged as an open decision, not a fait accompli.

---

## 2. How marriage sits on the household

Marriage is a **membership event**, not a new entity:

```
INSERT household_members (household_id = <player's household>,
                          user_id      = <spouse NPC pseudo-user or null>,
                          member_role  = 'spouse',
                          joined_month = <current month>)
```

The spouse contributes into the *existing* household (ADR-001 Principle 1). Concretely a spouse brings:
- **Income** — owned Individual (the spouse), rolled up to the household for scoring.
- **Assets / liabilities** — the archetype's starting portfolio and any debts, tagged with the spouse's ownership.
- **A trait profile** — modifiers on household expenses, risk exposure, and event probabilities.

**Design question (yours):** is the spouse a real `users` row, or an NPC represented purely by a `household_members` row with a null `user_id`? *Recommend NPC / null user_id* — the spouse never logs in, and a null-user member keeps auth/RLS simple. This needs the `household_members.user_id` to be nullable, which is a one-line amendment to the ADR-001 schema — cheaper to decide now than to migrate later.

---

## 3. Spouse archetypes (EV-balanced)

A fixed, versioned, immutable content set (ADR-012). Illustrative starting set of four, each a transparent trade-off with **no strictly-dominant option**:

| Archetype | Brings | Cost / risk |
|---|---|---|
| **The Saver** | Strong expense discipline (household expense −X%), small emergency buffer | Low income; limited upside |
| **The Earner** | High second income | Higher lifestyle expense (lifestyle creep modifier); higher event exposure |
| **The Investor** | An existing portfolio (stocks/gold) | Inherits market volatility; can drag in a crash |
| **The Anchor** | Stable income + a funded emergency fund | Low ceiling; minimal growth contribution |

Each archetype is a **declarative stat block** (income, expense modifier, asset contribution, liability, risk tolerance, trait tags) — data, not code, consistent with ADR-006's "an event is data" philosophy.

**The hard constraint: EV-balance.** "Same choice set for all players" only produces fairness if the archetypes are genuinely expected-value-equivalent *and* EV-equivalent to staying single. If one archetype is quietly best, ranking is decided by who guessed right at the altar — luck, not skill, which violates ADR-000. Therefore:

- EV-balance must be **proven by seeded simulation** across representative strategies before ratification (a fairness gate, same standard as ADR-009's global market path).
- "Viable single" is a *measurable* bar: the EV of not marrying must fall inside the same tolerance band as the archetypes. This may require giving singles a compensating advantage (e.g., lower fixed household cost) — **open decision (yours):** is EV-balance alone enough, or does single get an explicit offset?

---

## 4. Deterministic trait reveal (no luck)

Traits are hidden at proposal and revealed by a **fixed reveal map**, not RNG:

- Each "conversation action" the player spends (a turn / a resource) deterministically reveals a specific trait. Same actions → same reveals for every player. Auditable, reproducible (ADR-000).
- This rides the **canonical hybrid pipeline** you mandated: `Player NL → Intent Extraction → Validation → Confirmation → Structured Proposal → Business Rules → Simulation → AI Conversation → Player`. The **rules** decide what is revealed and what marriage does financially; the **AI only narrates** it. The AI never determines a financial or reveal outcome — closed intent schema, confirmation gate, full audit log.
- Reveal state is **deterministic history** in the DB (ADR-010). The AI's chatty memory of the courtship lives in the separate conversational-memory service and is *never* an input to the rules engine.

---

## 5. Financial & scoring impact

- **Household aggregates:** income = Σ member incomes; expenses = base + spouse modifier; emergency fund / investments become household-owned roll-ups (ADR-005 rollup rule — a computation, never a storage default).
- **Scoring (ADR-008) recomputes on household aggregates.** This is the subtle part: `net_worth_component` normalizes against *expected resources* (`INITIAL_BUDGET + salary·months`). A two-income household has ~double the resources, so the normalization denominator must include spouse income or married players' net-worth component is unfairly inflated/deflated versus singles. **The scoring normalization must be re-derived for households** — flag as an ADR-008 amendment, not a silent tweak.
- **Liquidity / discipline / risk components** operate on household totals; definitions carry over but must be re-tolerance-checked in the EV simulation.

---

## 6. Data-model additions (on top of ADR-001)

- `spouse_archetypes` — content table (id, name, stat block JSON, version). Immutable per released version (ADR-012).
- `household_members` gains: `archetype_id`, `revealed_traits jsonb`, nullable `user_id` (see §2).
- `marriage_events` / courtship log — deterministic facts (proposal, confirmation, reveals) in the DB; conversational tone/memory in the separate AI service (ADR-010 split).

No change to the seven financial tables beyond what ADR-001 already establishes — marriage reuses `household_id`.

---

## 7. Event integration (ADR-004 / ADR-006)

New **household-scoped** events, authored in the same declarative impact-rule DSL, all held to the same fairness/EV-equivalence rule as existing events: spouse job loss, spouse medical emergency, dual-income promotion, joint big-purchase decision. Admin-released household events follow ADR-011's simultaneous-release lifecycle.

---

## 8. What must happen before a single line of marriage code

This is an L5 feature; the gate is deliberately heavy. In order:

1. **Ship ADR-001** (Household foundation) — the blocker. Nothing here works without it.
2. **Ratify ADR-002 form** and the schema amendments in §2/§6.
3. **EV-balance simulation** proving archetypes + "viable single" sit inside one tolerance band. Fairness gate — hard requirement.
4. **ADR-008 scoring amendment** for household aggregates (re-derived normalization).
5. **UI design** — proposal, conversation/reveal, marriage confirmation, household dashboard.
6. **Full L5 artifacts** — PRD update, DB review, implementation plan, rollback, verification plan.

---

## 9. Open decisions (yours)

1. **Spouse identity** — NPC with null `user_id` (recommended) vs. real user row.
2. **Single viability** — is EV-balance sufficient, or does staying single get an explicit compensating offset?
3. **Spouse income** — guaranteed fixed, or itself an EV trade (higher income ↔ higher volatility)?
4. **Archetype count** — 4 (illustrated) or more? More archetypes = more balancing surface to prove fair.
5. **Divorce** — currently deferred. *Recommend keep deferred* until the base marriage loop is proven.
6. **Timing** — does marriage become available in a fixed game window (e.g., months 4–8) or any time? Affects EV math.

None of these need answering today. The only thing on the critical path right now is ADR-001 (`HOUSEHOLD_MIGRATION_PLAN.md`, §8 decision #1).
