# Balatro Mechanical Contributor Roles

Canonical contract for the layer between Bond contribution and Bond Realization.

## Purpose

Bond membership answers **what strategic axis a component develops**. Mechanical roles answer **how that component actually works**. These are separate on purpose.

Example:

```text
Baron
  Bond: Held Cards
  Role: HELD_RANK_PAYOFF
  Target: KINGS
  Condition: CARD_HELD_IN_HAND

Mime
  Bond: Held Retrigger
  Role: HELD_RETRIGGER
  Target: HELD_CARD_EFFECTS

Blackboard
  Bond: Held Cards
  Role: HELD_STATE_PAYOFF
  Target: HELD_BLACK_SUITS
  Condition: ALL_REMAINING_HELD_CARDS_SPADES_OR_CLUBS
```

Baron and Blackboard may both develop Held Cards without being mechanically interchangeable. Mime develops Held Retrigger and may compose with either only when its retrigger mechanic actually applies.

## Closed-world Joker knowledge policy

Balatro's Joker catalogue is a finite game ruleset. The agent is therefore expected to encode each Joker's actual stable mechanic explicitly and accurately rather than pretending Joker behavior is unknown or must be rediscovered generically.

The abstraction boundary is:

```text
explicit Joker mechanic knowledge
        ↓
roles / targets / conditions / behavior descriptors
        ↓
Bond development + realization
        ↓
strategy composition
        ↓
generic decision logic
```

It is acceptable and desirable for Joker definitions, behavior analyzers, realization rules, and unique execution mechanics to identify a Joker explicitly when that is the clearest representation of the real game rule. Examples include DNA's first-hand single-card copy, Green Joker's discard penalty, Card Sharp's repeated-hand requirement, and Walkie-Talkie's rank-specific payoff.

What should normally **not** be hard-coded is the combinatorial strategy table. The agent should not require one bespoke rule for every useful Joker pair/triple when exact component mechanics can compose correctly through shared semantics. Important known combinations still require explicit regression tests, and an explicit interaction/motif rule is preferred when generic semantics cannot faithfully represent the real Balatro interaction.

Correctness against Balatro mechanics takes priority over abstraction purity.

## Architecture

```text
component/state
  -> weighted Bond contribution
  -> mechanical role / target / condition metadata
  -> Bond rank
  -> Realization checks whether the relevant mechanics can function
  -> motifs detect compatible role combinations
  -> composer selects a power plan
```

The role layer is **quota-neutral**. Enriching a `BondContribution` or `BondDevelopment` must never change contribution totals, rank, target, unlock state, or existing realization state.

## Data model

`BondContribution` now supports optional:

```text
roles      tuple[MechanicalRole, ...]
targets    tuple[str, ...]
conditions tuple[str, ...]
```

Existing two-argument construction remains valid:

```python
BondContribution("Baron", 6.0)
```

Role enrichment is centralized in `games/balatro/bonds/mechanical_roles.py`. Unknown/unclassified contributors remain valid and carry empty role metadata until classified, but strategically relevant production Jokers should not remain unknown merely to preserve genericity.

## Role vocabulary

```text
HELD_RANK_PAYOFF
HELD_STATE_PAYOFF
HELD_RETRIGGER
HELD_CARD_XMULT
PLAYED_RETRIGGER
HAND_PAYOFF
HAND_LEVEL_ENGINE
RANK_PAYOFF
SUIT_PAYOFF
DENSITY_INFRASTRUCTURE
DECK_THIN_PAYOFF
DECK_THIN_ENGINE
DECK_GROWTH_ENGINE
ECONOMY_PAYOFF
ECONOMY_ENGINE
CONSUMABLE_ENGINE
ENHANCEMENT_PAYOFF
ENHANCEMENT_FEED
SCALER
COPY_ENGINE
SUPPORT
```

This vocabulary may expand when Realization exposes a genuinely distinct mechanic. Roles should describe reusable mechanics rather than merely duplicate Joker names; however, a Joker-specific role/condition is valid when the game mechanic is genuinely unique and cannot be represented faithfully by the existing vocabulary.

## Coverage rule

Mechanical coverage should converge toward the complete strategically relevant Joker catalogue, not stop at an initial high-impact subset. Each Joker should have enough explicit knowledge for the runtime to answer, where applicable:

- what it produces;
- what it requires;
- what it scales with;
- what it amplifies/retriggers/copies/transforms;
- what persistent state it accumulates;
- what actions damage or reset it;
- what actions are required to exploit it;
- which Bond(s), motif(s), or tactical layer it belongs to.

Coverage does not imply Bond quota. A Joker can be fully modeled while remaining tactical/support-only.

## Realization use

Realization should consume enriched developments and exact modeled Joker mechanics rather than repeatedly reconstructing behavior from fragile display-name heuristics.

Examples:

```text
HELD_RANK_PAYOFF(KINGS)
  -> realization depends on useful Kings being retainable in hand

HELD_RETRIGGER
  -> realization depends on a held-card effect worth retriggering

HELD_STATE_PAYOFF(HELD_BLACK_SUITS)
  -> realization depends on the remaining held hand satisfying the black-suit condition

ENHANCEMENT_PAYOFF + CONSUMES_ENHANCEMENTS
  -> Vampire realization depends on renewable/available enhancement feed

ENHANCEMENT_PAYOFF + PRESERVE_ENHANCEMENTS
  -> Driver's License realization depends on maintained enhanced-card density
```

This is how the system preserves the Currency Wars-style Bond model while exploiting the fact that Balatro itself is a closed, known ruleset.
