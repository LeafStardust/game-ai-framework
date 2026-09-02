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
BondValue
= bond_strength(points)
× realization
× optional calibration weight
```

```text
RelationshipValue
= coefficient × min(BondValueA, BondValueB)
```

```text
MotifValue
= completion × estimated_payoff
```

```text
BuildValue(state)
= Σ BondValue
+ Σ RelationshipValue
+ Σ MotifValue
```

```text
StrategyDelta(candidate)
= BuildValue(projected_state_after_candidate)
- BuildValue(current_state)
- transition_cost
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

Validated green.

- 46 canonical Bonds.
- Renames: `burnt → hand_leveling`, `gold_economy → gold_cards`, `vampire → enhancement_consumption`.

## Phase B — Mechanical descriptors — COMPLETE

Validated green.

- `games/balatro/mechanics.py` is the canonical public mechanics surface.
- All production Bond evaluators use mechanics and/or direct public state rather than local name-driven strategy tables.
- Reachable rank geometry audited, including suit ladder `3 / 6 / 10 / 14 / 19`.

## Phase C — Mechanics → Bond contributions — COMPLETE

Validated green across all 46 Bonds.

- `games/balatro/bonds/contributions.py` owns keyed contribution normalization.
- Every emitted production contribution has `source_id` and `mechanic` diagnostics.
- Same source counts at most once within a Bond, but may support multiple Bonds.
- Current/projected evaluation is stateless and symmetric.

## Phase D — Bond strategic value — COMPLETE

Validated green.

- `games/balatro/bonds/strategic_value.py` owns canonical per-Bond value.
- Nonlinear strength uses exponent `1.35`.
- Realization factors: `DORMANT 0.0`, `PARTIAL 0.35`, `ACTIVE 0.75`, `MATURE 1.0`.
- Locked Bonds have zero value.
- Ranks are diagnostics only.
- Optional calibration weights default to `1.0`.

## Phase E — Sparse relationships and exceptional motifs — COMPLETE

Validated green after fixing the Phase E circular import.

Canonical sparse positive relationships:
- Held Cards + Steel
- Held Cards + Held Retrigger
- Steel + Held Retrigger
- Card Destruction + Deck Thinning

Canonical conflicts:
- Discard + No Discard
- Face Cards + No Face Cards
- Enhancement Consumption + Enhanced Cards

Unlisted pairs are neutral.

Canonical motif layer initially contains one exceptional package only:

```text
Baron + Mime + at least two Steel Kings
```

No prescriptions or named-strategy authority exist in canonical motif output. Legacy `motifs.py` remains cleanup-only until its final consumers migrate.

## Phase F — Canonical `BuildValue(state)` — COMPLETE

Validated green.

- `games/balatro/bonds/build_value.py` is the single canonical whole-build value evaluator.
- It exposes Bond, relationship, motif subtotals and full diagnostics.
- Exact composition is `BuildValue = bond_total + relationship_total + motif_total`.
- BuildValue does not project candidates or choose actions.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE

Validated green after fixing missing projected Bonds to count as fully removed realized structure.

- `games/balatro/bonds/strategy_delta.py` compares canonical current/projected BuildValue.
- `strategy_delta_from_states(current_state, projected_state)` is the canonical state-comparison boundary.
- `strategy_delta(candidate, state, projector=...)` delegates candidate simulation to the caller-owned domain projector.
- Default transition inertia is `5%` of removed realized Bond value.
- Relationship/motif losses are not charged twice as transition inertia.
- Deepening structure gives positive delta; removal adds small inertia; materially stronger alternatives can still win.
- No strategy identity, commitment state, pivot FSM, or prescription fields exist in `StrategyDelta`.

## Phase H — Integrate canonical strategic decision owners — ACTIVE

First active vertical slice: Joker acquisition/replacement.

- `games/balatro/joker_policy.py` previously contained a parallel `_bond_transition_bonus()` that re-evaluated Bond ranks, composition coherence, legacy motifs, pinned strategies, `StrategyPlan` progress, conflicts, and pivot state.
- That parallel authority is being replaced by exactly one caller-projected canonical `StrategyDelta` term at the existing D2 Joker utility boundary.
- D2's native `JokerBuildTransitionPlanner` continues to own literal mechanical/build projection.
- Joker transaction economics, affordability, slot handling, early-run safety, and existing admission rules remain authoritative and unchanged by the strategic layer.
- Initial integration weight is deliberately conservative and remains a Phase L tuning parameter rather than architecture.

After Joker integration is green, continue through persistent build domains:

1. booster/pack choices;
2. Tarot/Spectral use and persistent deck transformations;
3. Planet/hand development;
4. remaining persistent construction choices.

For each domain:
- use the domain's existing legal/mechanical projector;
- add one `StrategyDelta` term at the final value boundary;
- remove the obsolete Bond-specific/strategy-plan scoring path it replaces;
- do not wire individual Bond IDs into the decision owner.

## Phase I — Verify tactical exploitation

Verify canonical tactical owners exploit constructed engines, especially:

- Burnt first-discard hand leveling;
- card destruction/deck thinning;
- held cards/Steel/held retrigger.

## Phase J — Deterministic end-to-end proofs

Minimum representative paths:

1. Hand Leveling / Discard / Hand Development
2. Card Destruction / Deck Thinning
3. Held Cards / Steel / Held Retrigger

Prove compatible candidates gain strategic value, destructive replacement loses dependent value, materially stronger alternatives can still win, and tactical owners exploit resulting mechanics.

## Phase K — Migration cleanup gate

Repository-wide audit must confirm no production dependency on rejected commitment/prescription authority, no duplicate Bond/build evaluator, no obsolete compatibility wrapper after its final consumer, and no stale tests/docs enforcing rejected architecture.

## Phase L — Targeted live validation and tuning

Only after deterministic proofs and cleanup are green:

- Red Deck / White Stake local runs;
- inspect coherent build emergence, bait rejection, preservation, justified pivots;
- tune contribution weights, curve, realization, relationships, motif payoff, transition cost, and integration weight.

## Phase M — Broader competence

After Bond-guided Red/White competence is demonstrated, address broader gameplay failures, consistency, stakes, and decks.

# Exact next action

**Validate the first Phase H Joker StrategyDelta integration slice.**

1. Prove Joker add/replacement uses caller-owned public state projection and canonical `StrategyDelta`.
2. Prove native D2 build gain and economics remain separate inputs rather than being replaced by strategic value.
3. Prove the old composition/pinned-strategy/StrategyPlan imports are absent from the Joker policy.
4. If green, continue immediately to the canonical pack/booster decision owner and repeat the same migration pattern.

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

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent exploit that engine to win?**
