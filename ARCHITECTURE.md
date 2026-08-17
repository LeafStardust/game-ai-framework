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
- parent/child specialization relationships when they are strategically real;
- component-to-strategy relationships;
- strategy conflicts;
- strategy evidence derived from current public state;
- environment/deck/difficulty modifiers;
- run-scoped strategy ranking and commitment state;
- strategy-aware candidate-value adjustments.

The generic framework may expose interfaces for these concepts later, but it must not depend on Balatro-specific strategy IDs, Jokers, poker hands, or consumables.

---

# Balatro Strategy Architecture

The target v1.0F strategy architecture is defined in [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md).

The current Python implementation still contains the previous flat strategy catalogue while the redesign is being specified. The tree document is the design target; runtime migration should begin only after the tree is frozen.

## 1. Universal Balatro strategy forest

Balatro uses a **forest of strategy trees** rather than one flat peer list.

A tree edge means only that the child is a more specific realization of the parent strategy. It does not encode a natural poker-hand progression and it does not make descendants globally better than ancestors.

Examples:

```text
High Card
├── Core High Card
├── Stuntman / Small-Hand High Card
└── Baron-Mime Held-Card High Card
```

Different poker hands such as Pair, Three of a Kind, Four of a Kind, and Five of a Kind are separate roots unless a real specialization relationship is proven. Poker-hand adjacency itself is never a reason to create a parent/child edge.

Every strategy node may eventually own exact named relationships:

```text
Strategy Node
    Gold components
    Silver components
    Bronze components
    Banned/conflict components
    conditions
    structural evidence
    support
```

Individual Joker classes do **not** store duplicated strategy-tier metadata.

At initialization, Balatro should generate inverse component indices from the strategy data rather than duplicating relationships across item implementations.

Unlisted component means **Neutral** for that strategy. Neutral is distinct from Bronze and from banned/conflict.

### Leaf-only ranking

Only leaves are actionable ranked strategies.

Internal nodes retain evidence/foundation scores because their foundation contributes to eligible descendants, but they never consume separate ranking slots beside those descendants.

A root with no children is itself a leaf and can therefore be ranked.

Split roots may define a core/fallback leaf so a valid unspecialized strategy remains rankable without placing the internal parent in the ranking.

## 2. Run-scoped strategy evidence

Strategy state describes the **current public build**, not historical ownership.

The redesign distinguishes:

```text
direct_evidence(node)
    evidence that belongs to this exact strategy node

foundation / branch score
    non-ranked internal evidence used for ancestry/readiness/diagnostics

effective_score(leaf)
    actionable score used to rank a leaf
```

Specific descendant evidence propagates upward with decay because a specific package also supports the credibility of its broader ancestors.

Ancestor evidence does **not** blindly propagate downward. A specific non-fallback child must have qualifying child evidence before it may inherit appropriate ancestor direct foundation.

The implementation must prevent recursive double counting: a leaf cannot propagate evidence into an ancestor and then re-inherit that same evidence through the ancestor's total branch score.

Current-state evidence may include:

- owned Jokers and other persistent components;
- rank/suit structure;
- enhancements;
- seals;
- persistent card editions where strategically relevant;
- poker-hand levels created by actual permanent investment;
- used Tarot/Spectral effects reflected in the current deck;
- used Planet investment;
- environment/deck/stake modifiers.

Buying or selling a Joker changes the next strategy evidence immediately because the current build changed.

Unopened/held consumables do **not** raise strategy score merely because they are owned. Their potential effect may influence acquisition/use value; their actual result becomes evidence only after use.

### Poker-hand play counts

Poker-hand play counts are **not universal strategy evidence**.

A hand may be played early because of draw quality rather than intent, and persistent current-build structure is a more reliable signal later. Hand history remains available to mechanics that explicitly depend on it, but strategy inference must not treat generic play frequency as commitment.

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

At a normal zero-evidence start, strategy alignment contributes approximately zero. The first useful purchases are therefore selected mostly by ordinary value and create the first strategy evidence.

Once evidence exists, candidate strategic value is derived from the relationships between the candidate and the currently evidenced/ranked strategy leaves and their foundations.

Therefore:

- a strong relationship to an unestablished strategy does not force an early purchase;
- a strong relationship to an established leaf gains increasing value as strategy pressure rises;
- Silver/Bronze relationships reinforce more weakly than Gold;
- Banned/conflicting relationships reduce value when they genuinely harm an established strategy;
- Neutral Jokers remain buyable through ordinary/meta value.

Negative strategy scores must not create accidental positive purchase bonuses through negative-times-negative arithmetic.

## 4. Ante-dependent strategy pressure

Ante changes how strongly strategy affects decisions; it does not manufacture strategy evidence.

```text
Antes 1-2: exploration/foundation
Antes 3-5: convergence
Ante 6+:   specialization
```

### Antes 1-2

- Strategy pressure is weak.
- Empty Joker slots may be populated by independently useful Jokers.
- Multiple roots/leaves may accumulate evidence.
- A lucky deep package may establish a specific leaf immediately; parent completion is a preference, not a hard gate.

### Antes 3-5

- Strategy pressure increases.
- Filled Joker slots make retention/replacement decisions strategically important.
- Specific leaf evidence separates coherent branches from incidental early purchases.
- The agent increasingly concentrates resources on its strongest branch while retaining pivot capability when RNG supplies materially stronger evidence.

### Ante 6+

- One viable highest-ranked leaf normally becomes dominant.
- Up to two compatible, materially supported leaves may remain relevant.
- Buying, replacement, rerolling, pack selection, deck shaping, consumable use, and hand behavior should strongly reinforce this established state.
- Survival-critical Neutral/off-strategy actions remain legal.

Survival and guaranteed blind clears remain higher priority than strategy purity.

## 5. Negative Joker retention

Negative Jokers are protected from ordinary sell/replace pressure by default because their +1 Joker slot normally makes them effectively slot-neutral.

A Negative Joker should not be sold merely because it is Neutral, weakly aligned, or lower-value than another ordinary Joker.

Removal is justified only when its active mechanic materially harms the current run, creates a hard functional contradiction that cannot be safely neutralized, or is intentionally consumed by an active strategy whose expected benefit justifies the sacrifice.

Destructive engines such as Ceremonial Dagger or Vampire must therefore be evaluated in context: their destructive behavior is not automatically considered harmful when the run is deliberately following the corresponding strategy.

## 6. Deck/stake cartridge

A Balatro deck/stake cartridge does **not** define the universal strategy forest.

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
- adjust economy, pivot, commitment, evidence, or strategy-pressure thresholds for the environment.

It must not redefine the universal Gold/Silver/Bronze/Banned relationships or parent/child topology.

This preserves the intended cartridge model:

```text
Permanent Balatro mechanics/state/execution stack
                +
Universal Balatro strategy forest
                +
Run-scoped current-state evidence/ranking
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
Framework -> Balatro strategy knowledge
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

Balatro's universal strategy forest is shared across Balatro decks/stakes, but remains inside the Balatro game layer.

---

## Rule 4: Environment Configuration Must Not Duplicate Game Knowledge

A deck/stake cartridge may alter effectiveness and thresholds but must not duplicate the universal strategy definitions or topology.

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
