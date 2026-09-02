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

The Bond system supplies run-level strategic guidance so the agent can recognize emerging engines, deepen coherent builds, preserve valuable synergy naturally, and pivot when a materially better resulting build exists.

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

The Bond system is a **guideline**, not an action-command system.

## Mechanical descriptors

Game objects expose mechanics, not strategy labels.

Examples:

```text
Mime        → retrigger_held_cards
Steel card  → held_scoring, enhanced_card
Burnt Joker → discard_hand_leveling
Hanged Man  → card_destruction
```

A mechanic may contribute to multiple Bonds. Overlap is intentional.

## Bond value

Canonical shape:

```text
BondValue
= bond_strength(points)
× realization
× optional calibration weight
```

Initial development curve:

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

Ranks remain diagnostic and must not directly issue actions or alter strategic value.

## Relationships and motifs

Relationships are sparse and mechanically justified.

```text
RelationshipValue
= coefficient × min(BondValueA, BondValueB)
```

Motifs exist only for genuinely super-additive packages that ordinary Bond contributions and pair relationships cannot express adequately.

## Whole-build strategic value

```text
BuildValue(state)
= Σ BondValue
+ Σ RelationshipValue
+ Σ MotifValue
```

The strategy is therefore an emergent property of the current build, not a separately authoritative strategy identity.

## Projected candidate value

```text
StrategyDelta(candidate)
= BuildValue(projected_state_after_candidate)
- BuildValue(current_state)
- transition_cost
```

A small transition cost may prevent near-equal thrashing. It is inertia, not a strategy state machine.

Canonical decision owners combine strategic delta with their normal mechanical/economic/survival value. Legality, affordability, survival, boss correctness, and hidden-information rules remain authoritative.

## Tactical execution

Bonds answer:

> What kind of build is valuable to develop?

Gameplay policies answer:

> How do I execute those mechanics correctly right now?

Do not create Bond-name-specific tactical command trees when generic mechanical semantics can express the behavior.

# Explicitly obsolete architecture

Do not rebuild or preserve these as production authority:

- giant persistent strategy controller/state machine;
- strategy identity as primary decision authority;
- FORMING/PINNED/etc. as required action-authority states;
- mandatory persistent `StrategyPlan` propagation;
- prescription strings such as `seek_feature:*` / `seek_bond:*` as the foundational mechanism;
- manual Bond-by-Bond wiring into every decision owner;
- one execution policy tree per Bond;
- generic pivot FSM/pivot resistance;
- motifs for ordinary synergies;
- duplicate composition/evaluation paths.

Valid mechanics, descriptors, relationships, motifs, diagnostics, and integration code trapped inside legacy modules may be migrated before those modules are deleted.

# Migration and cleanup contract

For each migrated capability:

```text
new canonical path implemented
→ production consumer migrated
→ deterministic tests prove replacement
→ dependency search confirms old path is unnecessary
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

Before Bond migration is complete, classify remaining old-system references as:

```text
RETAIN — still valid under final architecture
MIGRATE — useful logic trapped in obsolete structure
DELETE — obsolete/dead
```

No `MIGRATE` or `DELETE` items may remain at completion.

# CURRENT DEVELOPMENT PATH

## Phase A — Audit and freeze Bond vocabulary — COMPLETE

Validated green on the focused Bond/realization/relationship suite.

Canonical frozen catalogue: **46 Bonds**.

Renamed strategic axes:

```text
burnt        → hand_leveling
gold_economy → gold_cards
vampire      → enhancement_consumption
```

Phase A established canonical Bond IDs, canonical registration for renamed axes, aligned rank progression and semantic coverage, reachable Gold progression, and corrected Midas/Vampire realization semantics.

Do not reopen vocabulary design unless a concrete later failure proves a Bond invalid.

## Phase B — Complete semantic mechanical descriptors — COMPLETE

Validated green on the focused mechanical-descriptor / semantic / Bond / realization / rank-progression suite.

Phase B established:

- `games/balatro/mechanics.py` as the canonical public component-mechanics query surface;
- native mechanics on modeled runtime components plus centralized snapshot compatibility;
- all 46 canonical evaluators driven by mechanics and/or direct public state rather than independent production name tables;
- explicit semantic coverage across hand patterns, ranks, suits, held/retrigger, enhancement, destruction/thinning, deck growth, economy, discard/no-discard, Tarot, Planet, and retained residual axes;
- intentional cross-axis mechanical overlap;
- reachable post-audit rank geometry, including the corrected shared suit ladder `3 / 6 / 10 / 14 / 19`.

## Phase C — Implement canonical mechanics → Bond contributions — COMPLETE

Validated green after the full 46-Bond contribution-ledger migration.

Phase C established:

- `games/balatro/bonds/contributions.py` as the canonical contribution/source ledger;
- stable `source_id` and `mechanic` diagnostics on emitted Bond evidence;
- same-source normalization at the Bond-development boundary to prevent accidental within-Bond double counting;
- intentional one-source-to-many-Bonds overlap remains valid because normalization is Bond-local;
- current/projected symmetry because contribution evaluation is stateless and derived only from supplied public state;
- all production evaluator families migrated onto keyed contribution helpers, including hand patterns, ranks/consumables, engines/economy, residual axes, Hand Leveling, Gold Cards, Enhancement Consumption, and No Face Cards;
- Ride the Bus, Raised Fist, and Blackboard expose native runtime mechanics;
- remaining string/snapshot compatibility is centralized rather than embedded in evaluators;
- a catalogue-wide contract test proves all emitted contributions across all 46 canonical Bonds carry stable `source_id` and `mechanic` diagnostics;
- rank reachability and semantic/mechanical suites remained green after migration.

Phase C deliverable is satisfied: there is one canonical mechanics/state → keyed weighted Bond-evidence path for the frozen catalogue.

## Phase D — Implement Bond strategic value — ACTIVE

Implement:

- contribution totals;
- nonlinear development strength;
- realization factor;
- optional calibration weight;
- diagnostic rank passthrough without rank-based value authority;
- explainable per-Bond strategic value.

Current Phase D slice pending local validation:

- `games/balatro/bonds/strategic_value.py` defines canonical `bond_strength(points) = points ** 1.35`;
- existing categorical realization (`DORMANT / PARTIAL / ACTIVE / MATURE`) is converted once to numeric factors `0.0 / 0.35 / 0.75 / 1.0` rather than creating a parallel realization system;
- locked Bonds are forced to zero strategic value;
- optional non-negative calibration weights are multiplicative and default to `1.0`;
- `BondStrategicValue` exposes points, nonlinear strength, categorical realization, numeric realization factor, calibration weight, final value, diagnostic rank, and underlying development;
- `evaluate_bond_values(state)` composes the existing canonical `evaluate_all_bonds(state)` pipeline with value evaluation;
- deterministic tests emphasize monotonic development, increasing marginal strength, monotonic realization, rank non-authority, locked zero value, calibration behavior, and explainable diagnostics.

Do not tune factors or exponent from live performance until the architecture is integrated and deterministic proofs are complete.

## Phase E — Relationships and motifs

Implement only justified sparse synergies/conflicts and genuinely super-additive motifs.

Unlisted Bond pairs remain neutral.

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

Removing/replacing components must remove all dependent strategic value. Pivots should emerge from resulting whole-build value, not named-strategy switching rules.

## Phase H — Integrate canonical strategic decision owners

Wire the same `StrategyDelta` into relevant persistent build decisions:

- Joker acquisition/replacement/sale;
- booster choices;
- Tarot/Spectral use;
- deck destruction/transformation/enhancement;
- Planet/hand development;
- other persistent construction choices.

Do not wire Bonds directly by name.

As each consumer migrates, delete the obsolete path it replaces.

## Phase I — Verify tactical exploitation

Verify canonical tactical owners can exploit builds the strategic layer constructs.

Representative mechanics:

- Burnt first-discard hand leveling;
- card destruction/deck thinning;
- held cards/Steel/held retrigger.

Fix missing tactical mechanics in canonical owners only when concrete failures are demonstrated.

## Phase J — Deterministic end-to-end proofs

Minimum representative paths:

1. Hand Leveling / Discard / Hand Development
2. Card Destruction / Deck Thinning
3. Held Cards / Steel / Held Retrigger

Prove:

```text
compatible state/components
→ Bonds develop
→ compatible candidate gains strategic value
→ engine deepens when justified
→ destructive replacement loses value
→ materially stronger alternative can still win
→ tactical owner exploits resulting mechanics
```

## Phase K — Bond migration cleanup gate

Repository-wide audit must confirm:

- no production consumer depends on rejected commitment/prescription control paths;
- no duplicate Bond/build evaluator remains active;
- no obsolete compatibility wrapper remains after its final consumer migrates;
- no stale tests/docs enforce the rejected architecture;
- useful mechanics formerly embedded in legacy modules have been migrated or explicitly retained.

## Phase L — Targeted live validation and tuning

Only after deterministic proofs and cleanup gate are green:

- run Red Deck / White Stake validation locally;
- inspect whether coherent builds emerge;
- inspect synergy bait rejection;
- inspect natural preservation of established engines;
- inspect justified pivots;
- tune contribution weights, nonlinear curve, realization, relationships, motif payoff, transition cost, and integration weight.

Do not redesign the architecture merely because initial constants need calibration.

## Phase M — Broader competence work

After Bond-guided Red/White play is demonstrated:

- address gameplay failures exposed by live runs;
- improve meta/semantic coverage as needed;
- measure win consistency;
- only then consider broader stake/deck progression.

# Exact next action

**Validate the first Phase D strategic-value slice, then continue automatically.**

After green:

1. audit value behavior against representative realized Bond states;
2. keep contribution/rank evaluation unchanged unless a concrete defect appears;
3. complete Phase D diagnostics/API coverage;
4. mark Phase D complete when the canonical value layer is proven catalogue-wide;
5. immediately begin Phase E sparse relationships and exceptional motifs.

# Progress criterion

A development cycle should advance one concrete artifact:

```text
mechanical semantic coverage
canonical Bond contribution evaluation
Bond/relationship/motif value
BuildValue
projected StrategyDelta
canonical consumer integration
legacy-path removal
mechanically correct tactical exploitation
end-to-end strategic proof
repository-wide cleanup gate
live win-rate evidence / calibrated constants
```

Controlling question:

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent exploit that engine to win?**
