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

Reference shape:

```text
BondValue
= bond_strength(points)
× realization
× optional calibration weight
```

Initial development curve reference:

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

Ranks may remain diagnostic, but ranks must not directly issue actions.

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

The Joker/mechanic names Burnt Joker and Vampire remain valid mechanical concepts; only the strategic Bond IDs changed.

Phase A also established:

- canonical Bond IDs in `games/balatro/bonds/ids.py`;
- canonical evaluator/realizer registration for renamed axes;
- rank progression aligned to canonical IDs;
- reachable `gold_cards` R5 progression;
- semantic coverage aligned to canonical IDs;
- obsolete hard-unlock assumptions removed from migrated tests;
- Midas/Vampire face-feed realization corrected.

Do not reopen vocabulary design unless a concrete later failure proves a Bond invalid.

## Phase B — Complete semantic mechanical descriptors — ACTIVE

Audit the public mechanics required to evaluate all 46 retained Bonds.

Use/reuse the existing mechanical descriptor/profile layer where valid. Do **not** create a duplicate semantics system.

Prioritize:

- Jokers;
- enhancements, seals, editions where strategically relevant;
- Tarot/Spectral/Planet effects;
- deck composition properties;
- hand-level and persistent scaling state;
- other persistent mechanics that affect retained Bonds.

Requirements:

- descriptors express actual mechanics rather than Bond names or display-name heuristics where avoidable;
- each retained Bond has sufficient semantic evidence for current-state and projected-state evaluation;
- cross-mechanic enablers are represented explicitly;
- no numerical tuning yet beyond corrections required for semantic correctness;
- valid existing semantics should be retained/migrated rather than rewritten needlessly.

Deliverable: a deterministic semantic-coverage audit showing the cleaned Bond catalogue can be explained from public mechanical state without relying on the rejected strategy-plan architecture.

## Phase C — Implement canonical mechanics → Bond contributions

Implement one contribution path that:

- derives weighted Bond evidence from public mechanics;
- permits one mechanic to contribute to multiple Bonds;
- prevents double-counting of one underlying source;
- exposes per-source diagnostics;
- works identically for current and projected states.

## Phase D — Implement Bond strategic value

Implement:

- contribution totals;
- nonlinear development strength;
- realization factor;
- optional diagnostic ranks;
- explainable per-Bond strategic value.

Tests should emphasize monotonic/marginal behavior rather than arbitrary exact constants.

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

**Proceed with Phase B.**

1. Inspect the existing mechanical descriptor/profile layer and semantic registries.
2. Map each of the 46 canonical Bonds to the public mechanics/state features needed to evaluate it.
3. Identify missing, Joker-name-dependent, duplicate, or strategically opaque semantic channels.
4. Reuse/migrate valid existing descriptors.
5. Add only the missing canonical mechanical semantics.
6. Add/update focused semantic coverage tests.
7. When Phase B validation is green, mark Phase B COMPLETE and advance the roadmap to Phase C before writing contribution-scoring architecture.

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
