# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests and live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest command must use `-q`.
- Preserve exact mechanics, legality, boss rules, affordability, survival, and hidden-information boundaries.
- Prefer canonical ownership over wrappers/rescue layers.
- Cleanup is part of migration completion.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical architecture:

```text
PUBLIC GAME STATE
→ MECHANICAL DESCRIPTORS
→ WEIGHTED BOND CONTRIBUTIONS
→ BOND DEVELOPMENT + REALIZATION
→ SPARSE RELATIONSHIPS + EXCEPTIONAL MOTIFS
→ BuildValue(state)
→ PROJECTED STATE AFTER CANDIDATE
→ StrategyDelta(candidate)
→ EXISTING CANONICAL DECISION OWNER
```

Bonds provide strategic value/guidance only. Tactical/gameplay owners remain authoritative for mechanics and hard constraints.

## Canonical formulas

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

```text
BondValue = bond_strength(points) × realization × optional calibration weight
RelationshipValue = coefficient × min(BondValueA, BondValueB)
MotifValue = completion × estimated_payoff
BuildValue(state) = Σ BondValue + Σ RelationshipValue + Σ MotifValue
StrategyDelta(candidate) = BuildValue(projected) - BuildValue(current) - transition_cost
```

Transition cost is small inertia against near-equal thrashing, not a strategy state machine.

# Explicitly obsolete architecture

Do not rebuild or preserve as production authority:

- giant persistent strategy controller/state machine;
- named strategy identity as primary action authority;
- FORMING/PINNED/etc. as required action states;
- mandatory persistent `StrategyPlan` propagation;
- `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, `commit_*`, or pivot-prescription plumbing as the foundation;
- manual 46-Bond wiring into every decision owner;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- motif explosion;
- duplicate Bond/build evaluators.

# Migration contract

```text
new canonical path implemented
→ production consumer migrated
→ deterministic tests prove replacement
→ dependency search confirms old path unnecessary
→ obsolete code/tests/docs deleted
```

Required end state:

```text
ONE mechanics → Bonds → BuildValue → StrategyDelta path
ONE set of production integrations
NO parallel legacy Bond planner/controller path
NO dead prescription plumbing
NO obsolete compatibility wrappers/tests/docs
```

# CURRENT DEVELOPMENT PATH

## Phase A — Freeze Bond vocabulary — COMPLETE

Validated green. 46 canonical Bonds; canonical renames are `burnt → hand_leveling`, `gold_economy → gold_cards`, and `vampire → enhancement_consumption`.

## Phase B — Mechanical descriptors — COMPLETE

Validated green. `games/balatro/mechanics.py` is the canonical public mechanics surface and production Bond evaluators use mechanics/direct public state rather than local strategy-name tables.

## Phase C — Mechanics → Bond contributions — COMPLETE

Validated green across all 46 Bonds. `games/balatro/bonds/contributions.py` owns keyed contribution normalization; the same source counts at most once within a Bond but may support multiple Bonds.

## Phase D — Bond strategic value — COMPLETE

Validated green. `games/balatro/bonds/strategic_value.py` owns nonlinear per-Bond value with exponent `1.35`, realization factors `0 / 0.35 / 0.75 / 1.0`, ranks as diagnostics only, and optional calibration weights.

## Phase E — Sparse relationships and exceptional motifs — COMPLETE

Validated green.

Positive relationships:
- Held Cards + Steel
- Held Cards + Held Retrigger
- Steel + Held Retrigger
- Card Destruction + Deck Thinning

Conflicts:
- Discard + No Discard
- Face Cards + No Face Cards
- Enhancement Consumption + Enhanced Cards

Unlisted pairs are neutral. Canonical exceptional motif scope currently contains only Baron + Mime + at least two Steel Kings.

## Phase F — Canonical `BuildValue(state)` — COMPLETE

Validated green. `games/balatro/bonds/build_value.py` is the single whole-build evaluator and exposes Bond, relationship, motif, and total diagnostics without choosing actions.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE

Validated green after correcting disappeared projected Bonds to count as fully removed realized structure.

- `strategy_delta_from_states(current_state, projected_state)` is the canonical state-comparison boundary.
- `strategy_delta(candidate, state, projector=...)` delegates candidate simulation to the caller-owned domain projector.
- Default transition inertia is `5%` of removed realized Bond value.
- Relationship/motif losses are not charged twice as inertia.
- No strategy identity, commitment state, pivot FSM, or prescription fields exist in `StrategyDelta`.

## Phase H — Integrate canonical strategic decision owners — ACTIVE

### H1 — Joker acquisition/replacement — COMPLETE

Validated green.

- The old Joker transition bonus based on Bond ranks, composition coherence, pinned strategy, `StrategyPlan`, legacy motifs, and pivot state has been removed from the production Joker policy.
- The installed post-transaction D2 authority now combines:

```text
post-transaction native mechanical gain
+ 0.10 × canonical StrategyDelta
+ existing transaction economics
```

- Affordability, slot handling, early-run safety, and mechanically negative replacement rejection remain authoritative.

### H2 — Booster/pack persistent choices — COMPLETE

Validated green.

- The historical StrategyPlan/Bond-goal pack bonus has been replaced by projected canonical StrategyDelta for exact persistent PLAYING_CARD and PLANET pack outcomes.
- Playing-card projection appends the materialized card to persistent deck state.
- Planet projection increments the relevant public hand level.
- Base pack legality, literal value, stochastic expectation, and Skip remain authoritative.
- `_goal_ids` / `_playing_card_matches` remain temporarily as inert compatibility helpers only; production pack scoring does not call them. Remove at Phase K once final import users are migrated.

### H3 — Tarot/Spectral persistent deck transformations — COMPLETE

Validated green.

- `ContextualConsumableTargetEvaluator` remains the canonical owner for deterministic target legality and literal/contextual target quality.
- `games/balatro/consumable_strategy_delta_policy.py` reuses the real deterministic consumable `can_use/use` implementation on a deep-copied public state.
- Exact transformed hand cards are synchronized into authoritative `owned_deck` by public `live_id` when live observation uses separate card objects.
- Hanged Man uses the existing shared permanent playing-card destruction semantics rather than duplicating them.
- Only already-positive deterministic target evaluations receive the conservative `0.10 × StrategyDelta` adjustment.
- Stochastic/generation/economy-only/Joker-targeted/unsupported consumables remain outside this projection path and fail closed.
- No individual Bond IDs or StrategyPlan goals are wired into the target owner.
- Focused deterministic target/consumable regressions are green.

### H4 — Planet / hand-development owners — ACTIVE

Current continuation checkpoint:

- Two distinct production owners have been identified:
  1. shop acquisition through `ConsumableAcquisitionPolicy`;
  2. held-Planet use timing.
- The Planet path has been wired toward canonical projected `StrategyDelta` at both owners; **the migration boundary and regression proof still need to be finished/verified before H4 can be marked complete.**
- Shop acquisition keeps its existing B4 consumable/mechanical value and adds a separate conservative strategic term:

```text
existing B4 Planet value
+ 0.10 × canonical StrategyDelta
+ existing transaction/economy logic
```

- Do not collapse mechanical hand-level value, transaction economics, and coherent-build value into one opaque score.
- Held-Planet timing already has tactical authority for clear probability, pace recovery, final-hand urgency, slot pressure, duplication, and Planet scalers. StrategyDelta may provide diagnostics/ranking context there, but **must not flip the canonical HOLD/USE timing decision.**
- The shop path still has/previously had a legacy Bond-rank relevance veto. Remove that veto rather than retaining it as parallel strategic authority once canonical StrategyDelta is proven.
- The legacy Planet relevance wrapper is installed globally through `games/balatro/__init__.py`; remove its production import/install when the migrated shop owner no longer depends on it.
- Preserve legality, affordability, survival, scoring pace, boss logic, and tactical Planet-use timing as higher authority than strategic guidance.

H4 completion gate:
1. verify the shop owner projects the exact real Planet hand-level result and consumes canonical `StrategyDelta`;
2. verify the held-use owner exposes/uses strategic value only without overriding HOLD/USE tactical authority;
3. remove the legacy Bond-rank Planet relevance veto from production scoring;
4. remove its global wrapper import/install from `games/balatro/__init__.py` once no required production user remains;
5. add deterministic regressions proving exact projection, strategic adjustment, and authority separation;
6. fix the lingering Held Cards policy label `candidly_superior_composition → clearly_superior_composition` if it has not already been committed;
7. run focused local validation and mark H4 COMPLETE only after green.

After H4 is green, inspect the remaining persistent construction/development consumers and migrate the narrowest next owner using the same shared `StrategyDelta` path. Do not add Bond-specific controllers.

## Phase I — Verify tactical exploitation

Verify canonical tactical owners exploit constructed engines, especially Burnt first-discard hand leveling, card destruction/deck thinning, and held cards/Steel/held retrigger.

## Phase J — Deterministic end-to-end proofs

Minimum representative paths:
1. Hand Leveling / Discard / Hand Development
2. Card Destruction / Deck Thinning
3. Held Cards / Steel / Held Retrigger

Prove compatible candidates gain strategic value, destructive replacement loses dependent value, materially stronger alternatives can still win, and tactical owners exploit resulting mechanics.

## Phase K — Migration cleanup gate

Repository-wide audit must confirm no production dependency on rejected commitment/prescription authority, no duplicate Bond/build evaluator, no obsolete compatibility wrapper after its final consumer, and no stale tests/docs enforcing rejected architecture.

## Phase L — Targeted live validation and tuning

Only after deterministic proofs and cleanup are green: run Red Deck / White Stake locally, inspect coherent build emergence/bait rejection/preservation/justified pivots, then tune contribution weights, curve, realization, relationships, motif payoff, transition cost, and integration weights.

## Phase M — Broader competence

After Bond-guided Red/White competence is demonstrated, address broader gameplay failures, consistency, stakes, and decks.

# Exact next action

**Finish the Phase H4 Planet / hand-development migration boundary and deterministic proof.**

1. Fresh-fetch the two Planet owners plus `games/balatro/__init__.py` and verify the current branch state before editing.
2. Finish/verify exact Planet projected-state integration at shop acquisition and held-use owners.
3. Remove the obsolete Bond-rank Planet relevance veto and its global production installation once dependency search proves it unnecessary.
4. Add focused deterministic tests proving exact hand-level projection and that StrategyDelta cannot override tactical HOLD/USE authority.
5. Fix the Held Cards `candidly → clearly` policy-label typo if still present.
6. Ask the user to run the focused local H4 regression command.
7. On green, mark H4 COMPLETE and continue immediately to the next remaining persistent construction/development owner.

# Progress criterion

```text
mechanical semantics
→ canonical Bond contributions
→ Bond/relationship/motif value
→ BuildValue
→ StrategyDelta
→ canonical decision-owner integration
→ legacy-path removal
→ tactical exploitation
→ deterministic E2E proof
→ cleanup gate
→ live validation/tuning
```

Controlling question:

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent actually exploit that engine to win?**
