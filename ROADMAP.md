# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests and live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest command must use `-q`.
- Preserve exact Balatro mechanics, public-state legality, boss rules, affordability, and hidden-information boundaries.
- Prefer canonical ownership over late wrappers/rescue layers.
- Numerical tuning must not compensate for missing mechanics or semantics.
- Use scoped Conventional Commit messages.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

The current development target is the Bond system: give the agent a useful run-level strategic guideline so that it can recognize an emerging Balatro engine, deliberately strengthen it when worthwhile, preserve valuable synergy naturally, and pivot when a better resulting build exists.

# Bond-system vision

The source concept is **Honkai: Star Rail Currency Wars Bonds**.

The Balatro system does not need to copy Currency Wars literally. It must preserve the core feedback loop:

```text
RNG supplies components
→ components contribute to overlapping Bonds
→ Bonds become increasingly developed/valuable
→ compatible future components become more valuable
→ a coherent build direction emerges
→ the agent preferentially deepens that direction when justified
→ a materially better resulting build can still cause a pivot
```

The Bond system is a **guideline**, not a command system.

It should express:

> Given the current run, which strategic structures are becoming valuable, and how much does this candidate improve or damage them?

It must not blindly force a named build when survival, economy, boss requirements, immediate scoring, or a stronger alternative says otherwise.

# Final Bond architecture

This architecture is the current design to implement. Do not introduce another strategy-controller layer unless a concrete tested failure proves it necessary.

```text
PUBLIC GAME STATE
    ↓
MECHANICAL DESCRIPTORS
    ↓
BOND CONTRIBUTIONS
    ↓
BOND DEVELOPMENT + REALIZATION
    ↓
SPARSE BOND RELATIONSHIPS
    +
EXCEPTIONAL MOTIFS
    ↓
WHOLE-BUILD STRATEGIC VALUE
    ↓
PROJECTED STATE AFTER CANDIDATE
    ↓
STRATEGY DELTA
    ↓
EXISTING CANONICAL DECISION OWNER
```

## 1. Mechanical descriptors

Relevant Jokers, cards, enhancements, consumables, deck properties, hand-level effects, and other persistent public mechanics expose what they actually do.

Examples:

```text
Mime        → retrigger_held_cards
Steel card  → held_scoring, enhanced_card
Burnt Joker → discard_hand_leveling
Hanged Man  → card_destruction
```

Execution logic should reason from mechanics, not from Bond names.

## 2. Mechanics → weighted Bond contributions

A mechanic may contribute to one or more Bonds.

Example shape:

```text
retrigger_held_cards:
    Held Retrigger +3.0
    Held Cards     +1.0

held_scoring:
    Steel          +2.0
    Held Cards     +1.5

card_destruction:
    Card Destruction +2.0
    Deck Thinning    +1.5
```

Overlapping contribution is intentional. It is what lets a coherent build emerge from several mutually reinforcing pieces.

## 3. Bond development/value

Raw points are not the final strategic value.

Use a nonlinear development curve so that compatible follow-up pieces can become increasingly valuable as a Bond develops, while allowing later tuning from evidence.

Initial reference form:

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

The exact exponent is tuning data, not architecture.

Bond ranks may remain as diagnostics/UI if useful, but ranks themselves must not directly issue actions.

## 4. Realization

Each Bond has a realization factor in `[0.0, 1.0]` representing how much its theoretical support is actually usable in the current run.

Reference form:

```text
BondValue
= bond_strength(points)
× realization
× optional calibration weight
```

Development and realization are descriptive strategic evidence. They are not action-authority states.

## 5. Sparse Bond relationships

Only meaningful Bond pairs receive explicit synergy/conflict coefficients.

Examples:

```text
Held Cards + Steel            positive
Held Cards + Held Retrigger   positive
Steel + Held Retrigger        positive
Burnt + Discard               positive
Card Destruction + Deck Thin  positive
Discard + No Discard          negative
Face Cards + No Face Cards    negative
```

Reference form:

```text
RelationshipValue
= coefficient × min(BondValueA, BondValueB)
```

Do not build a dense all-pairs relationship matrix merely for completeness.

## 6. Motifs

Motifs exist only for combinations whose payoff is genuinely super-additive and cannot be represented adequately by ordinary Bond contributions plus sparse relationships.

Example: Baron + Mime + suitable held Steel Kings.

Do not turn every known Balatro archetype into a motif.

## 7. Whole-build strategic value

The central strategic evaluator is:

```text
BuildValue(state)
= Σ BondValue
+ Σ RelationshipValue
+ Σ MotifValue
```

The current strategy is therefore an emergent property of the current build, not a separately authoritative strategy identity.

## 8. Projected-state strategy delta

Every meaningful candidate should be evaluated against the resulting public state when practical:

```text
StrategyDelta(candidate)
= BuildValue(projected_state_after_candidate)
- BuildValue(current_state)
- transition_cost
```

This applies to relevant actions such as:
- buying/replacing/selling Jokers;
- pack selections;
- Tarot/Spectral choices and uses;
- deck destruction/transformation/enhancement;
- other persistent build-changing decisions.

A small transition cost may be used to prevent near-equal strategic thrashing:

```text
transition_cost
≈ small fraction of removed realized structure
```

This is inertia, not a persistent strategy state machine.

## 9. Decision integration

The Bond system does not replace Balatro decision logic.

Canonical decision owners combine strategic delta with their existing domain value:

```text
FinalCandidateValue
= immediate/mechanical value
+ economy value
+ survival value
+ future value
+ calibrated StrategyDelta
```

Hard constraints remain authoritative:
- legality;
- affordability;
- deterministic/material survival requirements;
- boss correctness;
- hidden-information boundaries.

The exact weighting is tuning work after the architecture is wired correctly.

## 10. Tactical execution remains mechanical

Bonds answer:

> What kind of build is valuable to develop?

Canonical gameplay policies answer:

> How do I execute these mechanics correctly right now?

Examples:
- Burnt/Discard strategic value does not itself choose the exact discard; D1 must understand Burnt's actual first-discard mechanic.
- Held/Steel/Retrigger strategic value does not itself choose exact played/held cards; D1 must evaluate the actual held-scoring/retrigger mechanics.

Do not create Bond-name-specific tactical command trees when generic mechanical semantics can express the behavior.

# Explicitly obsolete architecture

The following are **not** current development requirements and should not be rebuilt merely because older roadmap/code/docs mention them:

- a giant persistent run-level strategy controller;
- strategy identity as the primary decision authority;
- FORMING/PINNED/ESTABLISHED/DOMINANT as required action-authority states;
- mandatory persistent `StrategyPlan` command propagation across every decision owner;
- `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, etc. as the foundational strategic mechanism;
- manual wiring of every Bond into every decision owner;
- one execution policy tree per Bond;
- a large generic pivot state machine;
- arbitrary pivot resistance merely because a strategy was previously selected;
- motifs for ordinary synergies;
- another broad baseline competence audit before Bond work;
- another blind random live batch before the Bond architecture is implemented and deterministically checked.

Existing code implementing any of these concepts should be treated as reusable only where it still helps the new architecture. Do not preserve obsolete structure for its own sake.

# Migration and cleanup contract

The new Bond architecture is a **replacement**, not a second system that permanently coexists with the old one.

During migration, old code may remain temporarily only when it is still needed as a reference, compatibility bridge, or dependency of an unmigrated consumer. Every such temporary dependency must be removed once the replacement path is proven.

For each migrated Bond-system capability:

```text
new path implemented
→ production consumer migrated
→ deterministic tests prove replacement behavior
→ old dependency search confirms no required users remain
→ obsolete code/tests/docs are deleted in the same development phase
```

Cleanup is part of completion, not optional follow-up work.

Required cleanup includes, where obsolete under the final architecture:
- old strategy-controller/state-machine modules;
- commitment-authority plumbing;
- `StrategyPlan`/prescription command paths that no longer serve a valid diagnostic role;
- Bond-specific wrappers superseded by generic mechanics/`StrategyDelta` evaluation;
- duplicate composition/evaluation paths;
- stale compatibility shims after their last consumer migrates;
- tests that assert rejected architecture rather than intended behavior;
- stale docs/comments/imports/dead fields naming obsolete concepts.

Do **not** delete a legacy module merely because its name belongs to the old architecture; first determine whether it contains valid mechanics, semantic descriptors, relationships, motifs, diagnostics, or integration code worth migrating.

The required end state is:

```text
ONE canonical mechanics → Bonds → BuildValue → StrategyDelta path
ONE set of production integrations
NO parallel legacy Bond planner/controller path
NO dead strategy-prescription plumbing
NO obsolete Bond tests/docs kept for historical convenience
```

Before declaring the Bond migration complete, perform a repository-wide legacy cleanup audit and classify every remaining old-system reference as either:

```text
RETAIN — still valid under the final architecture
MIGRATE — useful logic still trapped in obsolete structure
DELETE — obsolete/dead
```

No `MIGRATE` or `DELETE` items may remain at Bond-system completion.

# CURRENT DEVELOPMENT PATH

Follow these steps in order unless a concrete blocking defect requires an incidental fix.

## Phase A — Audit and freeze the Bond vocabulary — ACTIVE

Audit **all currently listed Bonds** before building the new scoring system on top of them.

Do not discard the current list blindly and do not trust it blindly.

For every Bond classify it as exactly one of:

```text
KEEP
MERGE
RENAME
DEMOTE TO MECHANIC
REMOVE
```

A valid Bond should satisfy the following tests:

1. **Real strategic axis** — it represents something the run can meaningfully build around.
2. **Multi-component development** — multiple relevant components/state features can strengthen it; otherwise it may be only a mechanic.
3. **Future-choice effect** — developing it should make compatible future components/actions more strategically valuable.
4. **Distinctness** — it is not merely a duplicate measurement of another Bond.

Deliverables:
- cleaned/frozen Bond list;
- rationale for every merge/demotion/removal/rename;
- mapping from retained Bonds to the mechanics that can contribute to them.

Do not proceed with numerical tuning before this vocabulary is stable.

## Phase B — Complete semantic mechanical descriptors

Audit the public mechanics required to evaluate retained Bonds.

For relevant components, ensure descriptors can express the actual mechanics needed for strategic evaluation rather than display-name heuristics.

Prioritize:
- Jokers;
- enhancements/seals/editions where strategically relevant;
- Tarot/Spectral/Planet effects;
- deck composition properties;
- hand-level/persistent scaling state;
- other persistent mechanics that affect retained Bonds.

Do not require every possible Balatro mechanic before proceeding. Complete the semantics needed by the cleaned Bond set and candidate evaluation paths.

## Phase C — Implement mechanics → Bond contribution evaluation

Implement one canonical contribution path that:
- derives weighted Bond evidence from public state/mechanics;
- supports one mechanic contributing to multiple Bonds;
- avoids double-counting the same underlying source;
- exposes per-source diagnostics so incorrect scores can be explained.

The output must be usable for both current-state and projected-state evaluation.

## Phase D — Implement Bond value and realization

Implement:
- contribution totals;
- nonlinear development strength;
- realization;
- optional diagnostic ranks if retained;
- explainable per-Bond strategic value.

Tests should establish monotonic and intended marginal behavior rather than overfitting exact arbitrary constants.

## Phase E — Implement sparse relationships and exceptional motifs

Implement only justified relationships/conflicts and true motifs.

Requirements:
- relationship evaluation must operate on retained Bond semantics;
- unlisted Bond pairs remain neutral;
- motifs must be mechanically grounded and explainable;
- no generic rank collection or display-name matching.

## Phase F — Implement canonical `BuildValue(state)`

Create one authoritative whole-build strategic evaluator:

```text
BuildValue
= Bond values
+ relationship values
+ motif values
```

It must expose diagnostics showing which structures account for the result.

Do not make this function directly choose actions.

## Phase G — Implement projected-state `StrategyDelta(candidate)`

For each supported persistent build-changing candidate:

```text
current = BuildValue(state)
projected = BuildValue(state_after_candidate)
delta = projected - current - transition_cost
```

Requirements:
- candidate self-synergy must only appear if it exists in the resulting state;
- replacing/removing a component must correctly lose all dependent Bond/relationship/motif value;
- pivots should emerge from resulting whole-build value rather than named-strategy switching rules;
- transition cost must remain small and evidence-based.

## Phase H — Wire StrategyDelta into canonical strategic decision owners

Integrate the same strategic delta into the real owners that make persistent build decisions.

Audit and wire only relevant domains, including as applicable:
- Joker shop acquisition/replacement/sale;
- booster-pack choices;
- Tarot/Spectral selection/use;
- deck destruction/transformation/enhancement;
- Planet/hand-development choices;
- other persistent-state construction decisions.

Do not wire Bonds directly by name. Consumers should receive candidate strategic value derived from projected state.

As each consumer is migrated and proven, remove the obsolete path it replaces according to the **Migration and cleanup contract**. Do not accumulate parallel production paths until the end.

## Phase I — Verify tactical mechanics can exploit the developed build

Once the strategic layer can construct coherent engines, verify that canonical tactical owners can actually use the mechanics they construct.

This is not a second Bond architecture.

Examples:
- Burnt: first-discard hand-level development and later exploitation;
- thinning/destruction: correct removal targets and improved draw quality;
- Held/Steel/Retrigger: correct hold/play behavior and scoring exploitation.

Fix missing tactical mechanics in canonical owners when concrete failures are found.

## Phase J — Deterministic end-to-end proofs

Before broad live validation, prove several complete strategic paths using real production state/policies.

Minimum representative paths:

1. **Burnt / Discard / Hand Development**
2. **Card Destruction / Deck Thinning**
3. **Held Cards / Steel / Held Retrigger**

For each path prove:

```text
RNG/state supplies compatible pieces
→ Bonds develop
→ compatible candidate receives higher projected strategic value
→ agent deepens the engine when justified
→ destructive replacement loses appropriate strategic value
→ materially stronger alternative can still win
→ tactical owner can exploit the resulting mechanics
```

These are representative proofs of the generic architecture, not special pilot-specific controllers.

## Phase K — Bond migration cleanup gate

Before live validation, perform a repository-wide audit for old Bond architecture and remove all obsolete leftovers.

Required checks:
- no production consumer still depends on rejected commitment/prescription control paths;
- no duplicate Bond/build evaluators remain active;
- no obsolete compatibility wrapper remains after its final consumer was migrated;
- no stale tests enforce removed architecture;
- no stale docs/comments describe the rejected planner/controller model as current;
- all useful mechanics/semantic logic formerly embedded in legacy modules has been moved or intentionally retained in the canonical path.

The gate passes only when every remaining legacy-looking reference is explicitly justified as valid under the final architecture.

## Phase L — Targeted live validation and tuning

Only after the architecture is wired, deterministic proofs are green, and the cleanup gate passes:
- run targeted Red Deck / White Stake validation locally;
- inspect whether coherent builds actually emerge;
- inspect whether the agent rejects synergy bait when immediate/survival/economic value is insufficient;
- inspect whether established engines are preserved naturally;
- inspect whether justified pivots occur;
- tune contribution weights, nonlinear curve parameters, realization, relationship coefficients, motif payoff, transition cost, and strategic integration weight from observed failures.

Do not redesign the architecture merely because initial constants are poorly calibrated.

## Phase M — Broader competence work

After Bond-guided Red/White play is demonstrated:
- continue targeted gameplay fixes exposed by live runs;
- improve meta coverage/semantic completeness as needed;
- measure win consistency;
- only then consider broader stake/deck progression.

# Exact next action

**Start Phase A.**

1. Read the current Bond registry/definitions and all code that creates Bond evidence.
2. Enumerate the full current Bond list.
3. Audit every Bond against the four validity tests.
4. Produce the proposed cleaned Bond vocabulary with `KEEP / MERGE / RENAME / DEMOTE TO MECHANIC / REMOVE` decisions.
5. Inspect dependencies before deleting or renaming anything.
6. Update Bond definitions/tests/docs to the cleaned vocabulary.
7. Then proceed to Phase B semantic-descriptor coverage.

Do **not** return to the old three-pilot persistent-plan wiring task unless a concrete piece of that code is reusable under the architecture above.

# Progress criterion

A development cycle should move one of these concrete artifacts forward:

```text
clean Bond vocabulary
mechanical semantic coverage
correct Bond contribution evaluation
correct Bond/relationship/motif value
correct BuildValue
correct projected StrategyDelta
canonical consumer integration
legacy-path removal for migrated capability
mechanically correct tactical exploitation
end-to-end strategic proof
repository-wide Bond cleanup gate
live win-rate evidence / calibrated constants
```

The controlling question is now:

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent actually exploit that engine to win?**
