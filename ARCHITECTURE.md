# General Game AI Framework Architecture

## Overview

The General Game AI Framework is designed as a reusable architecture for building autonomous agents across different games.

The framework separates general AI capabilities from game-specific mechanics, state translation, strategy knowledge, and environment-specific policy configuration.

The core principle:

> The agent should know how to reason, while each game defines what can be reasoned about and which game-specific strategic knowledge is available.

---

# High-Level Architecture

```text
General Game AI Framework

        Agent Core

-----------------------------------------
|              |                        |
State        Decision              Learning
System       System                System
|              |                        |
-----------------------------------------

        Game Adapter / Policy Layer

----------------------------------------------------------
| Mechanics | State Translation | Strategy Knowledge     |
| Execution | Game Evaluation   | Environment Modifiers |
----------------------------------------------------------

        Specific Game Environment
```

The framework core remains game-independent. Game-specific strategy systems belong below that boundary.

---

# Component Responsibilities

## Framework Core

The framework core contains reusable abstractions shared by all games.

Responsibilities:

- define common interfaces;
- manage agent execution;
- store experiences;
- provide generic decision-making infrastructure;
- provide policy/search/evaluation plumbing without embedding one game's rules.

---

## State Representation

Represents the current condition of a game.

Examples:

- board position;
- player resources;
- available information;
- game history.

Each game provides its own state implementation.

---

## Action Representation

Represents possible decisions available to an agent.

Examples:

- playing a card;
- selecting a move;
- choosing an ability;
- taking an action.

---

## Game Environment

The environment connects the framework to the game.

Responsibilities:

- provide current state;
- provide available actions;
- execute actions;
- determine terminal conditions;
- provide rewards/results.

---

## Agent

The reusable agent architecture is responsible for selecting actions.

The generic agent does not embed one game's rules or strategy catalogue. It receives game-specific state, available actions, evaluation/policy services, and game-specific context through the adapter/policy layer.

---

## Decision Engine

The decision engine determines how an agent selects actions.

Possible implementations include:

- random selection;
- heuristic evaluation;
- search algorithms;
- reinforcement-learning policies;
- game-specific strategy-aware evaluation supplied below the framework boundary.

---

## Evaluation System

Evaluates states or actions.

Reusable evaluation infrastructure belongs in the framework. Game-specific evaluation rules and strategic knowledge belong in the game's implementation.

---

## Experience System

Stores interactions between agents and environments.

A single experience contains:

- previous state;
- selected action;
- reward;
- resulting state.

This enables future learning systems.

---

# Game-Specific Strategy Knowledge

Some games require persistent strategic knowledge beyond isolated action heuristics. That knowledge belongs to the **game implementation**, not the framework core.

A game may provide:

- universal strategy definitions for that game;
- component-to-strategy relationships;
- strategy conflicts;
- strategy evidence derived from current public state;
- environment/deck/difficulty modifiers;
- run-scoped strategy ranking and commitment state;
- strategy-aware candidate-value adjustments.

The generic framework may expose interfaces for these concepts later, but it must not depend on Balatro-specific strategy IDs, Jokers, poker hands, or consumables.

---

# Balatro Strategy Architecture

Balatro uses four distinct concepts that must not be conflated.

## 1. Universal Balatro strategy catalogue

The universal catalogue describes **game-wide build strategies** such as:

- poker-hand strategies;
- enhancement/mechanic strategies;
- specific synergy packages.

Each strategy owns exact named component relationships:

```text
Universal Strategy
    Gold components
    Silver components
    Bronze components
    Banned/conflict components
    support
    evidence rules
```

Individual Joker classes do **not** each store duplicated strategy-tier metadata.

At initialization, Balatro generates an inverse index:

```text
component -> [(strategy, relationship), ...]
```

for efficient shop and policy evaluation.

Unlisted component means **Neutral** for that strategy. Neutral is distinct from Bronze and from banned/conflict.

The documentation contract is split across:

- `BALATRO_STRATEGY_PLAYBOOKS.md` — architecture and behavioral rules;
- `BALATRO_STRATEGIES_POKER_HANDS.md` — poker-hand catalogue;
- `BALATRO_STRATEGIES_MECHANICS.md` — mechanic catalogue;
- `BALATRO_STRATEGIES_NICHE.md` — narrow synergy catalogue.

The documentation grouping does not create runtime subclasses. Every Balatro strategy is a peer in one universal strategy pool.

## 2. Run-scoped strategy scoring

Every live run begins with strategy scores derived from its **current public build state**. For a normal unmodified start, these scores are approximately zero.

Strategy evidence is recomputed from the current state rather than accumulated as historical memory.

Conceptually:

```text
Gold relationship      -> strong positive evidence
Silver relationship    -> medium positive evidence
Bronze relationship    -> weak positive evidence
Neutral                 -> no strategy evidence
Banned/conflict         -> strong negative evidence
```

Initial tunable weights may be approximately `+5 / +3 / +1 / 0 / -8`, but exact values belong to implementation and testing.

Current-state evidence may also include persistent deck and hand investment such as:

- rank/suit structure;
- enhancements;
- seals;
- editions;
- poker-hand levels;
- actual hand-use structure where relevant;
- permanent effects created by used Tarot/Spectral/Planet cards.

Buying or selling a Joker changes the next strategy score immediately because the current build changed. Selling The Duo, for example, removes its Pair evidence.

Unopened/held consumables do **not** raise strategy score merely because they are owned. Their potential effect may influence acquisition/use value; their actual result becomes evidence only after use.

Used Planets provide small persistent evidence through the resulting poker-hand level investment.

The strategy state should be recomputed after meaningful public-state mutations rather than relying on stale incremental history.

## 3. Strategy-aware candidate valuation

Strategy score and candidate purchase score are separate quantities.

A shop Joker still has ordinary/meta, survival, economy, affordability, slot, and context value. Strategy contributes an additional adjustment.

Conceptually:

```text
candidate value
=
base/meta value
+ survival/economy/context
+ Ante pressure * strategy alignment
```

Strategy alignment is derived from the candidate's exact Gold/Silver/Bronze/banned relationships multiplied by the **current positive relevance** of those strategies.

Therefore:

- a Gold Joker for a zero-score strategy receives little/no strategy bonus;
- a Gold Joker for a highly ranked strategy receives a large strategy bonus;
- Silver/Bronze reinforce high-ranked strategies more weakly;
- a banned/conflicting Joker is penalized when it clashes with a high-ranked strategy;
- Neutral Jokers remain buyable through ordinary/meta value.

Negative strategy scores must not create accidental positive purchase bonuses through negative-times-negative arithmetic.

This feedback loop is the core Balatro build-discovery mechanism:

```text
current build
    -> strategy scores
    -> ranked strategies
    -> strategy-aware shop/use/sell values
    -> action
    -> changed current build
    -> recompute strategy scores
```

## 4. Ante-dependent strategy pressure

Ante changes how strongly strategy affects decisions; it does not create strategy evidence by itself.

```text
Antes 1-2: weak strategy pressure; explore useful/meta-strong Jokers and transformative Tarot/Spectral options
Antes 3-5: increasing strategy pressure; converge on higher-scoring strategies
Ante 6+:   strong strategy pressure; one dominant strategy + up to two relevant strategies
```

At the start, with all strategy scores near zero, Joker buying is therefore driven mostly by ordinary/meta value. The first purchases create the first strategy evidence.

By Ante 6, future buying, replacement, rerolling, pack selection, deck shaping, and consumable use should strongly favor the dominant strategy and up to two relevant strategies while still allowing survival-critical Neutral/off-strategy purchases.

Banned/conflicting Jokers create replacement pressure rather than unconditional immediate selling. Direct functional contradictions, such as Pareidolia + Ride the Bus, may receive exceptional replacement urgency.

Survival and guaranteed blind clears remain higher priority than strategy purity.

## 5. Deck/stake cartridge

A Balatro deck/stake cartridge does **not** define the universal strategies.

It only modifies how effective those universal strategies are in the current environment.

Conceptually:

```python
StrategyModifier(
    strategy_id="flush",
    enabled=True,
    effectiveness=1.10,
    score_bonus=0.0,
)
```

A cartridge may:

- amplify a strategy;
- suppress a strategy;
- disable a genuinely infeasible/unsupported strategy;
- adjust economy, pivot, commitment, or strategy-pressure thresholds for that environment.

It must not redefine the universal Gold/Silver/Bronze/banned relationships.

This preserves the intended cartridge model:

```text
Permanent Balatro mechanics/state/execution stack
                +
Universal Balatro strategy catalogue
                +
Run-scoped current-state strategy scoring
                +
Replaceable deck/stake environment cartridge
                =
Current production policy
```

---

# Dependency Rules

## Rule 1: Framework Independence

Framework components must not depend on specific games.

Incorrect:

```text
Framework -> Balatro strategy catalogue
```

Correct:

```text
Framework <- Balatro adapter/policy layer
```

---

## Rule 2: Interface-Based Communication

Games communicate with the framework through shared interfaces.

```text
GameEnvironment
       ^
       |
Specific Game Environment
```

---

## Rule 3: Strategy Knowledge Stays Game-Specific

Universal **within one game** does not mean universal across the framework.

Balatro's universal strategy catalogue is shared across Balatro decks/stakes, but remains inside the Balatro game layer.

---

## Rule 4: Environment Configuration Must Not Duplicate Game Knowledge

A deck/stake cartridge may alter effectiveness and thresholds but must not duplicate the full universal strategy definitions.

This keeps game knowledge centralized and makes cartridges small, replaceable environment-specific policy modules.

---

# Directory Structure

```text
agents/
    Game-specific or experimental agents

framework/
    Reusable AI framework components

games/
    Game mechanics, adapters, policy and strategy implementations

tests/
    Automated tests

docs and root design files/
    Architecture, roadmap and game-specific design contracts
```

---

# Design Philosophy

The framework prioritizes:

- modularity;
- extensibility;
- reusability;
- clear separation of concerns;
- inspectable decision logic;
- incremental development.

The goal is not to put one game's intelligence into the framework core.

The goal is to provide an architecture capable of supporting autonomous agents whose game-specific mechanics and strategic knowledge can be added cleanly below a reusable reasoning/execution layer.
