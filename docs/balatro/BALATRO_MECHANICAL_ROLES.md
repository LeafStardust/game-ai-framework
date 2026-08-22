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

Role enrichment is centralized in `games/balatro/bonds/mechanical_roles.py`. Unknown/future contributors remain valid and simply carry empty role metadata until classified.

## Initial role vocabulary

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

This vocabulary may expand when Realization exposes a genuinely distinct mechanic. Do not create one role per Joker.

## High-impact mappings implemented first

The initial registry covers the contributors needed for the first Realization/motif work, including Baron, Mime, Blackboard, Shoot the Moon, Raised Fist, Steel infrastructure, Steel Joker, Erosion, Trading Card, Sixth Sense, Square Joker, Spare Trousers, Stuntman, Superposition, Ancient Joker, Cloud 9, 8 Ball, Vampire, Midas Mask, Driver's License, and Mime-copying Blueprint/Brainstorm contributions.

## Realization use

Realization should consume enriched developments rather than infer behavior from raw Joker names whenever possible.

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

This is how the system preserves the Currency Wars-style Bond model while still understanding that different components inside the same Bond have different kits.
