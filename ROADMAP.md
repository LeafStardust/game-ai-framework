# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests and live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest command must use `-q`.
- Preserve exact Balatro mechanics, legality, boss rules, affordability, and hidden-information boundaries.
- Prefer canonical ownership over late wrappers/rescue layers.
- Numerical tuning must not compensate for missing mechanics or semantics.
- Cleanup is part of migration completion; do not leave parallel legacy Bond systems behind.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

The Bond system supplies strategic guidance so coherent engines emerge from public game state and candidate changes. It is a guideline, not an action-command system.

# Final Bond architecture

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

## Mechanical descriptors

Components expose mechanics, not Bond names. One mechanic/source may support several Bonds.

Examples:

```text
Mime        → retrigger_held_cards
Steel card  → held scoring / enhanced-card state
Burnt Joker → discard_hand_leveling
Trading Card / Sixth Sense → card_destruction
```

## Bond value

```text
BondValue
= bond_strength(points)
× realization
× optional calibration weight
```

Canonical initial curve:

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

Ranks are diagnostics only.

## Relationships

Relationships are sparse and mechanically justified.

```text
RelationshipValue
= coefficient × min(BondValueA, BondValueB)
```

Unlisted pairs are neutral.

## Motifs

Motifs exist only for exact genuinely super-additive packages that Bond values and pair relationships cannot adequately express.

Canonical initial example:

```text
Baron + Mime + suitable Steel Kings
```

```text
MotifValue = completion × estimated_payoff
```

Do not create motifs for ordinary archetypes or use motifs to issue tactical prescriptions.

## Whole-build strategic value

```text
BuildValue(state)
= Σ BondValue
+ Σ RelationshipValue
+ Σ MotifValue
```

Current strategy is emergent from the resulting build value, not a separately authoritative named strategy.

## Projected candidate value

```text
StrategyDelta(candidate)
= BuildValue(projected_state_after_candidate)
- BuildValue(current_state)
- transition_cost
```

Transition cost is small inertia against near-equal thrashing, not a pivot state machine.

Canonical decision owners combine strategic delta with immediate mechanics, economy, survival, and boss correctness. Hard legality/affordability/survival constraints remain authoritative.

# Explicitly obsolete architecture

Do not rebuild or preserve as production authority:

- giant persistent strategy controller/state machine;
- strategy identity as primary decision authority;
- FORMING/PINNED/etc. as required action states;
- mandatory persistent `StrategyPlan` propagation;
- `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, `commit_*`, or pivot-prescription plumbing as the foundation;
- manual Bond-by-Bond wiring into each decision owner;
- one execution policy tree per Bond;
- generic pivot FSM/pivot resistance;
- motif explosion;
- duplicate composition/evaluation paths.

Valid mechanics trapped in legacy modules may be migrated before those modules are deleted.

# Migration and cleanup contract

For each capability:

```text
new canonical path implemented
→ production consumer migrated
→ deterministic tests prove replacement
→ dependency search confirms old path is unnecessary
→ obsolete code/tests/docs deleted
```

Required final state:

```text
ONE mechanics → Bonds → BuildValue → StrategyDelta path
ONE set of production integrations
NO parallel legacy Bond planner/controller path
NO dead prescription plumbing
NO obsolete compatibility wrappers/tests/docs
```

Before completion classify remaining old-system references as `RETAIN`, `MIGRATE`, or `DELETE`. No `MIGRATE` or `DELETE` items may remain at the cleanup gate.

# CURRENT DEVELOPMENT PATH

## Phase A — Audit and freeze Bond vocabulary — COMPLETE

Validated green.

- Frozen catalogue: **46 Bonds**.
- Canonical renames: `burnt → hand_leveling`, `gold_economy → gold_cards`, `vampire → enhancement_consumption`.
- Canonical IDs, registration, rank progression, semantic coverage, and renamed-axis realization are aligned.

## Phase B — Complete semantic mechanical descriptors — COMPLETE

Validated green.

- `games/balatro/mechanics.py` is the canonical public component-mechanics surface.
- All 46 production Bond evaluators use mechanics and/or direct public state rather than local component-name strategy tables.
- Direct deck/rank/suit/enhancement/seal/hand-level/history/economy state remains canonical evidence.
- Runtime mechanics plus centralized snapshot compatibility cover retained components.
- Arbitrary-name descriptor tests prove semantic ownership.
- Reachable rank geometry is audited, including shared suit ladder `3 / 6 / 10 / 14 / 19`.

## Phase C — Canonical mechanics → Bond contributions — COMPLETE

Validated green across the full 46-Bond ledger migration.

- `games/balatro/bonds/contributions.py` owns keyed contribution normalization.
- Every emitted production contribution has stable `source_id` and `mechanic` diagnostics.
- Same underlying source counts at most once inside one Bond.
- The same source may still support several Bonds.
- Evaluation is stateless and symmetric for current/projected state.
- Hand patterns, ranks/consumables, engines/economy, residual axes, Hand Leveling, Gold Cards, Enhancement Consumption, Held Cards, and No Face Cards are ledger-backed.
- Catalogue-wide contract tests prove keyed diagnostics and rank reachability.

## Phase D — Bond strategic value — COMPLETE

Validated green on the canonical strategic-value slice.

- `games/balatro/bonds/strategic_value.py` owns Bond strategic value.
- `bond_strength(points) = points ** 1.35` supplies nonlinear increasing marginal development value.
- Existing categorical realization is converted once to numeric factors:
  - `DORMANT = 0.0`
  - `PARTIAL = 0.35`
  - `ACTIVE = 0.75`
  - `MATURE = 1.0`
- Locked Bonds always have zero strategic value.
- Optional non-negative calibration weights default to `1.0`.
- `BondStrategicValue` exposes points, nonlinear strength, realization/factor, calibration weight, final value, rank diagnostics, and underlying development.
- Rank does not directly modify value.
- `evaluate_bond_values(state)` composes the canonical evaluate/realize/value path.
- Tests prove monotonic strength, increasing marginal gain, monotonic realization value, rank non-authority, locked-zero behavior, calibration, and explainability.

Do not live-tune exponent/factors until deterministic integration is complete.

## Phase E — Sparse relationships and exceptional motifs — ACTIVE

Current implementation pending local validation:

- `games/balatro/bonds/relationships.py` preserves the compatibility relationship-kind API while adding canonical numeric relationship definitions and `RelationshipValue` diagnostics.
- Canonical formula is exactly `coefficient × min(BondValueA, BondValueB)`.
- Current sparse positive relationships:
  - Held Cards + Steel
  - Held Cards + Held Retrigger
  - Steel + Held Retrigger
  - Card Destruction + Deck Thinning
- Current sparse conflicts:
  - Discard + No Discard
  - Face Cards + No Face Cards
  - Enhancement Consumption + Enhanced Cards
- Unlisted pairs are neutral and are not materialized by value evaluation.
- Coefficients are conservative placeholders for later live tuning, not substitutes for missing semantics.
- `games/balatro/bonds/motif_value.py` is the new canonical motif-value layer.
- It initially contains **one** exceptional motif only: Baron + Mime + at least two Steel Kings.
- Motif requirements are mechanical/state evidence, not component display-name strategy commands.
- One isolated package component has zero motif completion/value; two requirements establish potential; the exact complete package receives full completion.
- Motif output contains requirements, completion, estimated payoff, value, and relevant Bonds only—no prescriptions or strategy-state authority.
- The old `motifs.py` remains legacy-only until dependency cleanup; it is not the canonical value path.

Phase E completion gate:

1. relationship sign/formula/sparsity tests green;
2. exceptional motif completion/value tests green;
3. no generic hand-leveling↔discard/no-discard relationship is introduced;
4. no ordinary archetype motif proliferation;
5. then mark Phase E complete and begin canonical BuildValue.

## Phase F — Canonical `BuildValue(state)`

Create one authoritative evaluator:

```text
BuildValue
= Bond values
+ relationship values
+ motif values
```

Expose diagnostics. Do not choose actions here.

## Phase G — Projected-state `StrategyDelta(candidate)`

Implement:

```text
current = BuildValue(state)
projected = BuildValue(state_after_candidate)
delta = projected - current - transition_cost
```

Removing/replacing components must remove dependent strategic value. Pivots emerge from resulting whole-build value, not named-strategy switching rules.

## Phase H — Integrate canonical strategic decision owners

Wire the same `StrategyDelta` into persistent build decisions:

- Joker acquisition/replacement/sale;
- booster choices;
- Tarot/Spectral use;
- destruction/transformation/enhancement;
- Planet/hand development;
- other persistent construction choices.

Delete obsolete strategic paths as their consumers migrate.

## Phase I — Verify tactical exploitation

Verify canonical tactical owners exploit constructed engines, including:

- Burnt first-discard hand leveling;
- destruction/deck thinning;
- held cards/Steel/held retrigger.

Fix tactical mechanics only in their canonical owners when concrete failures are demonstrated.

## Phase J — Deterministic end-to-end proofs

Minimum paths:

1. Hand Leveling / Discard / Hand Development
2. Card Destruction / Deck Thinning
3. Held Cards / Steel / Held Retrigger

Prove compatible candidates gain value, destructive replacements lose dependent value, materially better alternatives can still win, and tactical owners exploit resulting mechanics.

## Phase K — Bond migration cleanup gate

Repository-wide audit must confirm:

- no production consumer uses rejected commitment/prescription authority;
- no duplicate Bond/build evaluator remains active;
- no obsolete compatibility wrapper survives its final consumer;
- no stale tests/docs enforce rejected planner/controller behavior;
- useful mechanics are intentionally migrated or retained.

## Phase L — Targeted live validation and tuning

Only after deterministic proofs and cleanup are green:

- run Red Deck / White Stake locally;
- inspect coherent build emergence, bait rejection, preservation, and justified pivots;
- tune contribution weights, curve, realization, relationships, motif payoff, transition cost, and strategic integration weight.

## Phase M — Broader competence

After Bond-guided Red/White is demonstrated:

- address gameplay failures exposed by live runs;
- improve semantic/meta coverage as needed;
- measure win consistency;
- only then expand stake/deck scope.

# Exact next action

**Validate the first Phase E relationship/motif value slice, then continue automatically.**

After green:

1. mark Phase E complete if sparse relationship and exceptional-motif contracts remain satisfied;
2. immediately implement Phase F canonical `BuildValue(state)` from Bond + relationship + motif values;
3. keep BuildValue purely diagnostic/value-producing with no action authority;
4. begin projected-state `StrategyDelta` only after BuildValue is locally green.

# Progress criterion

Each cycle should advance one concrete artifact:

```text
mechanical semantic coverage
canonical Bond contribution evaluation
Bond/relationship/motif value
BuildValue
projected StrategyDelta
canonical consumer integration
legacy-path removal
tactical exploitation
end-to-end strategic proof
repository-wide cleanup gate
live win-rate evidence / calibrated constants
```

Controlling question:

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent exploit that engine to win?**
