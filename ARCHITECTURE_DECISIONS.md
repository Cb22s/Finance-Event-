# Money Master — Architecture Decision Record

Status: Approved by product owner on 2026-07-11.
These decisions are permanent unless explicitly superseded by a new approved ADR entry.

## Mandatory Engineering Workflow (product-owner mandate, 2026-07-12)

Every change follows, with each step a separate approval gate:

```
Architecture Decision → Ratification → Database Design → UI Design
  → Implementation Plan → Development → Verification
```

Before development begins, five artifacts require approval: database migration plan,
file impact analysis, dependency graph, rollback strategy, test strategy.
Unratified ADRs and ADRs with open product decisions must not be implemented.
Incomplete or truncated source files halt work immediately pending the missing source.

*(The ADR-008/009 fairness fixes implemented 2026-07-11 were retroactively approved
2026-07-12 with their five artifacts; the gates bind strictly from that date forward.)*

**Change classification (ADR-013) determines which gates apply to a given change.
The full workflow above is the Level 4–5 path.**

---

## ADR-000: Core Product Principles

**Status:** Permanent.

Money Master is an AI-powered financial life simulation platform. The primary goal is financial education through realistic life decisions.

Architecture decisions must prioritize:

1. Educational value
2. Realism
3. Fair competition
4. Deterministic financial calculations
5. Explainable AI
6. Long-term extensibility
7. Separation of concerns
8. Player trust

Whenever two principles conflict:

- Financial correctness > AI creativity
- Business Rules > AI reasoning
- Architecture > Feature convenience
- Educational value > Entertainment
- Determinism > Randomness

*Interpretation note (architect):* "Determinism > Randomness" does not prohibit random life events — it requires that any randomness be controlled: seeded, auditable, and identical (or expected-value-equivalent) across players in ranked play. Uncontrolled per-player randomness that affects ranking violates this principle and Principle 3 (fair competition).

---

## ADR-001: Household Entity (Version 1 Architectural Foundation)

**Status:** Approved for Version 1.
**Type:** Pure architecture. No gameplay, UI, or player-facing changes in Version 1.

The Household is the primary financial entity of the simulation. Every player is created as a Household containing exactly one member. All financial data references `household_id` rather than `user_id`/`player_id`.

**Current state (pre-decision):** `player_state`, `player_loans`, `player_sales`, `player_relative_score`, `player_relative_actions`, and `player_month_log` are keyed to `user_id`. Database design for this ADR must produce a migration plan from user-keyed to household-keyed records.

### Architectural Principle 1 — Household First

The Household is the primary financial entity. Every player is created as a Household of exactly one member. Marriage never creates a new household; it adds a member to the existing one. All financial systems are household-centric from the beginning — there is no player-keyed financial path.

### Architectural Principle 2 — Household Independence

The Household does not depend on marriage and must never be documented or implemented as a marriage feature. It is the permanent financial unit of the simulation. Future systems that integrate into it: marriage, children, dependents, elder care, joint taxation, shared insurance, household investments, household businesses, household assets, household liabilities.

### Architectural Principle 3 — Financial Ownership

Every financial record explicitly defines its owner. Ownership types: Individual, Household, Business, Organization (future). The system must not assume every transaction belongs to the household. Examples: personal salary → Individual; house rent → Household; business revenue → Business entity.

*Implementation note (flagged for database design step, not yet decided):* polymorphic ownership (`owner_type` + `owner_id`) cannot be enforced with native Postgres foreign keys. The database design must choose between (a) an `owners` supertype table that Individual/Household/Business rows extend, or (b) mutually exclusive nullable FK columns with a CHECK constraint. Option (a) is recommended for extensibility; decide at database design, not during implementation.

### Architectural Principle 4 — AI Isolation

The Household Entity contains no AI logic. It stores only factual financial data. AI personality, memory, conversation history, negotiation context, and behavioral state live in independent services that *reference* the Household. AI models can evolve without touching the financial architecture.

### Architectural Principle 5 — Version Stability

The Household architecture exists in Version 1 but is invisible to the player. No gameplay, UI complexity, or player decisions are introduced because of it. Its sole V1 purpose is a stable foundation for future features.

---

## ADR-002: Marriage & Life Partner System (Future Version)

**Status:** Approved for a future version. Not in Version 1. Gameplay design summary only; full spec at pickup time.

Accepted form (from architectural review, 2026-07-11):

- Spouse options are a fixed set of EV-balanced archetypes; every player faces the identical choice set (fairness in ranked play).
- Traits are discoverable, not hidden: limited conversation actions with deterministic reveal rules. No hidden-trait luck.
- Remaining single is a fully viable, never-penalized strategy.
- Marriage adds a member to the player's existing household (per ADR-001, Principle 1).
- Divorce, children, and in-laws are excluded; each requires its own future proposal.

---

## ADR-003: Hybrid Conversational AI Pipeline (Preferred Long-Term Design)

**Status:** Approved as the permanent AI interaction architecture. Supersedes menu-driven negotiation.

Canonical pipeline (amended 2026-07-11 to make Validation and Confirmation explicit stages):

```
Player (natural language)
  → Intent Extraction
  → Validation          (closed schema check; invalid → clarification, never guessed)
  → Confirmation        (player explicitly approves the interpreted intent)
  → Structured Proposal (the confirmed, validated intent — sole input to rules)
  → Business Rules Engine
  → Simulation Engine
  → AI Conversation Engine
  → Player
```

The AI never determines financial outcomes. It may only: interpret structured intent, communicate naturally, express personality, and maintain memory. Business Rules remain deterministic: identical structured inputs must produce functionally equivalent outcomes.

Hardening constraints (part of this decision):

1. **Closed intent schema.** Intent Extraction outputs only from a fixed enum of proposal types with typed parameters. Non-validating output is rejected and triggers clarification — never guessed.
2. **Confirmation gate.** The extracted structured proposal is shown to the player for explicit confirmation before the Business Rules Engine executes. No unconfirmed proposal reaches the rules engine.
3. **Full audit log.** Raw player text, extracted intent, player confirmation, and rules-engine inputs/outputs are persisted for every conversational decision. Explainability derives from this trail, not from the LLM.

---

## ADR-004: Simulation Engine

**Status:** Approved.

The Simulation Engine is responsible for generating every life event. Examples: career progression, promotion, job loss, inflation, interest rate changes, medical emergencies, business opportunities, family events, economic recession, tax policy.

The Simulation Engine never directly modifies financial records. Event flow:

```
Simulation Engine
  → Generates Event
  → Business Rules evaluate impact
  → Database updated
  → AI explains event
  → Player responds
```

*Architect notes (recorded with this ADR):*

1. **Event sources.** Admin-authored, round-released events (the current V1 mechanism in `event_engine.py`) are one source *within* the Simulation Engine, not a competing system. Procedurally generated events are a future second source behind the same interface. Both emit the same structured Event object.
2. **Determinism constraint (per ADR-000).** Event generation must be reproducible: a given (game seed, round, household state) always yields the same event. In ranked play, events affecting ranking must be identical across players or expected-value-equivalent. No unseeded per-player randomness.
3. **Closing the loop.** "Player responds" feeds back through the ADR-003 pipeline: natural language → intent extraction → confirmed structured proposal → Business Rules. The Simulation Engine never consumes raw player text.
4. **Ordering is binding.** Database update precedes AI explanation. The AI narrates committed facts; it never announces outcomes the rules engine has not yet produced.

---

## ADR-005: Financial Ownership

**Status:** Approved (ratified 2026-07-11). Chosen option: (a) `owners` supertype table.
**Scope note:** Promotes ADR-001 Principle 3 to a standalone cross-cutting decision; ADR-001 P3 becomes a reference to this ADR.

Every financial record explicitly declares its owner. Owner types: **Individual**, **Household**, **Business**, **Organization** (future). No system may assume household ownership by default. Personal salary → Individual. Rent → Household. Business revenue → Business.

Rules: ownership is assigned at record creation and immutable thereafter (transfers create new records, preserving history per the no-overwrite rule). Aggregations (net worth, scoring) roll Individual and Business records up to the owning household explicitly — the rollup is a computation, never a storage default.

**Open decision (yours):** FK enforcement strategy — (a) `owners` supertype table extended by individuals/households/businesses (recommended: real FK integrity, extensible to Organization), or (b) mutually exclusive nullable FK columns + CHECK constraint (simpler, but every new owner type is a migration).

---

## ADR-006: Event Engine — Definition & Impact Format

**Status:** Approved (ratified 2026-07-11). Chosen options: flat field-op-value DSL for V1; event chaining deferred.
**Boundary (ratified):** ADR-004 owns generation architecture; this ADR owns what an event *is*; ADR-011 owns how admins release them.

An Event is data, not code. Structure: identity (id, name, description, version), targeting (all households / filtered by state), timing (round, duration), **impact rules** (declarative list of operations: `{target_field, operation, value|percentage, floor, cap}` — e.g., `{stocks, multiply, 0.70}` = 30% crash), and optional **response choices** (structured decision options presented to the player, each mapped to its own impact rules).

Impact rules are validated against a closed operation vocabulary at authoring time — an admin cannot type arbitrary code. Events are versioned; a released event's definition is immutable (fixes require a new version, per audit rules). Executed impacts always flow through the Business Rules Engine (ADR-004 flow), never applied directly.

**Open decisions (yours):** (1) DSL depth — flat field-op-value rules (recommended for V1) vs. conditional rules ("if household has insurance, halve the impact") which are more realistic but harder to validate; (2) event chaining (event A schedules event B) — recommend deferring.

---

## ADR-007: Business Rules Engine

**Status:** Approved (ratified 2026-07-11).

The Business Rules Engine is the **only** component permitted to mutate financial records. Simulation proposes, AI narrates, players propose — rules execute.

Properties: every rule is a pure deterministic function `(current state, structured input) → transaction list`; no I/O, no randomness, no LLM calls inside rules; identical inputs yield identical transactions (ADR-000). All tunable parameters live in one versioned constants module (the existing `constants.py` pattern, elevated to a rule). Every evaluation is logged with inputs, rule version, and resulting transactions. Financial mutations are transactions appended to history — never in-place overwrites. Month/round processing is idempotent: reprocessing the same round cannot double-apply.

**Open decision (yours):** none of substance — this codifies your stated rules. Flag anything you'd loosen.

---

## ADR-008: Scoring

**Status:** Approved (ratified 2026-07-11). Chosen options: draft weights accepted (40/15/15/15/15); formula fully public. **Contains the largest open product decision in this set.**

**Current-state conflict:** the live leaderboard ranks by `net_worth` alone (`game_service.get_leaderboard`), while the product spec promises scoring on net worth, liquidity, investment growth, debt control, risk protection, and discipline. Net-worth-only ranking rewards maximum-leverage gambling — the opposite of the educational goal.

Proposal — a composite **Financial Health Score**, computed by the Business Rules Engine, formula public to players (player trust, ADR-000):

| Component | Draft weight | Measures |
|---|---|---|
| Net worth | 40% | Wealth built |
| Liquidity | 15% | Emergency fund adequacy (months of expenses covered) |
| Debt control | 15% | EMI-to-income ratio, no defaults |
| Risk protection | 15% | Insurance coverage, diversification (existing risk_score inverted) |
| Discipline | 15% | Consistency across rounds: no missed obligations, no panic sells |

Anti-gaming: components are computed as averages across rounds, not final-round snapshots — final-round window dressing (dump everything into cash, buy insurance in month 12) moves the score marginally, not decisively.

**Open decisions (yours):** (1) the weights — this decides who wins your event; (2) whether the full formula is public or only the components (recommend fully public).

---

## ADR-009: Economic Engine

**Status:** Approved (ratified 2026-07-11). Chosen options: global path ratified; scenario selection = both (admin-designed or seeded random). **Contains a fairness fix to existing code.**

**Current-state conflict:** `market_engine.py` seeds volatility per `(user_id, month)` — reproducible, but two players with identical portfolios earn different returns in the same month. That is per-player luck on a ranked leaderboard, violating ADR-000 (fair competition, determinism) even though it is technically seeded.

Proposal: one **global economic path per game** — a single seeded sequence per `(game_id, month)` producing that month's stock return, gold return, inflation rate, and interest rate, applied identically to every household. Markets are shared reality; skill is how you position against them. Personal events (medical emergency, job loss) may remain per-household only where expected-value-equivalent across players or delivered identically via admin release (ADR-011).

Admin capability: choose or preview the economic scenario before the game (e.g., "recession mid-game") rather than accepting a random path — supports designed learning arcs.

**Open decisions (yours):** (1) ratify the global-path fix (strongly recommended — this is a bug against your own principles); (2) scenario selection: admin-designed paths vs. seeded random vs. both.

---

## ADR-010: AI Memory

**Status:** Approved (ratified 2026-07-11). Chosen option: whole-game retention.

Two distinct things are both called "memory"; this ADR separates them permanently:

1. **Deterministic history** — facts in the database: past decisions, transactions, event outcomes, revealed NPC traits. May feed Business Rules inputs (e.g., the spouse agreement function's "previous decisions"). Owned by the financial architecture.
2. **Conversational memory** — an independent AI service (per ADR-001 P4) storing per-`(household, npc)` structured summaries: commitments made, tone history, topics discussed. Feeds **only** the AI Conversation Engine for continuity and personality. **Never** an input to Business Rules — otherwise LLM summarization errors would corrupt financial outcomes.

Conversational memory entries are structured extracts (not raw transcripts), timestamped, append-only, and inspectable by admins for dispute resolution. Raw transcripts are retained separately for audit (ADR-003 log) but are not the reasoning substrate.

**Open decision (yours):** retention — keep conversational memory for the whole game (recommended for a 12-round event; trivial volume) vs. windowed.

---

## ADR-011: Admin Event Release

**Status:** Approved (ratified 2026-07-11). Chosen options: manual admin lock; read-only pending-impact preview.
**Boundary (ratified):** operational control of event delivery; definitions are ADR-006, generation is ADR-004.

Event lifecycle states: `draft → scheduled → released → locked → processed → archived`. Admin releases a round's events to **all households simultaneously** — no staggered visibility (fairness). Release opens the decision window; lock closes it; processing runs Business Rules for all households in one pass; results publish together with updated scores.

Binding rules: a released event is immutable (corrections = compensating new event, never edits); locked decisions cannot be amended by players or admins; every admin action is audit-logged with actor and timestamp; processing a round is idempotent (ADR-007).

**Open decisions (yours):** (1) lock mechanism — manual admin lock (recommended for a live college event; the emcee controls pacing) vs. timed auto-lock vs. both; (2) whether admins can preview each household's pending impact before processing (recommend yes, read-only).

---

## ADR-012: Versioning Strategy

**Status:** Approved (ratified 2026-07-11). Chosen option: V1 ships the ADR-008 composite score.

Three things version independently:

1. **Product versions.** V1 = current 12-month event game + Household foundation (ADR-001) + fairness fixes (ADR-008/009 if ratified). Features enter a version only through a ratified ADR. V1 scope freezes on your declaration; after freeze, new ideas go to V2 backlog by default.
2. **Rules & constants.** Every balance change (growth rates, loan interest, score weights) increments a rules version recorded on every transaction and score it produced. A finished game is permanently auditable against the exact rules it ran under. **No mid-game rules changes** — a game runs start-to-finish on one rules version.
3. **Content.** Event definitions (ADR-006) and future spouse archetypes (ADR-002) carry their own versions; released content is immutable.

**Open decisions (yours):** (1) declare the V1 scope freeze; (2) whether V1 ships the ADR-008 composite score or keeps net-worth ranking one final event before switching (I recommend shipping the fix — every event run on net-worth-only ranking teaches the wrong lesson).

---

## ADR-013: Change Classification

**Status:** Approved (ratified 2026-07-12, with four architect amendments).

Every change is classified before work begins. Required workflow depends on **risk level, not code size**.

| Level | Scope | Examples | Required gates |
|---|---|---|---|
| **1 — Cosmetic** | Presentation only | UI text, colors, CSS, icons, fonts, spacing, tooltips | Change description + rollback plan |
| **2 — Functional** | New capability, no financial mutation | New screen, read-only report/dashboard, read-only API endpoint, non-financial validation | Impact analysis, UI review, implementation plan, rollback plan |
| **3 — Business Logic** | Financial computation & game mechanics | Loan/salary/investment calculations, event processing, scoring, monthly processing | ADR, database review, implementation plan, test plan, rollback plan |
| **4 — Architecture** | Structural / cross-cutting | Household entity, Business Rules Engine, AI pipeline, ownership model, event engine, **auth/RLS/permissions** | Full ADR, database design, architecture review, migration strategy, implementation plan, verification plan |
| **5 — Product Vision** | New product capability | Marriage, multiplayer, AI coach, business ownership, retirement | Feature evaluation, PRD update, ADR if required, architecture review, database review, UI review, implementation planning, development, verification |

**Binding rules (amendments ratified with this ADR):**

1. **Discriminator rule (overrides example lists).** Anything that mutates financial records, affects ranking, or touches the Business Rules Engine is Level 3 minimum, regardless of size. A "new API endpoint" that writes financial state is Level 3, not Level 2; validation on a financial mutation path is Level 3.
2. **Highest level wins.** A change spanning multiple levels is classified at the highest level it touches. Genuine doubt escalates one level up, never down.
3. **Security is Level 4.** Authentication, RLS policies, and permission changes are always Level 4.
4. **Deploy timing.** Level 3+ changes deploy only between games (per ADR-012). Levels 1–2 may deploy anytime.
5. **ADR creation gate (added 2026-07-12).** A new ADR may be created only if the change (a) alters core architecture, (b) modifies an existing approved ADR, or (c) introduces a completely new subsystem. Everything else is documented through its ADR-013 level artifacts — Level 3 changes reference the existing ADR they implement rather than spawning new ones.
