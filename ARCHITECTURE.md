# General Game AI Framework Architecture

## Overview

The General Game AI Framework is a reusable architecture for autonomous agents across different games.

The framework separates general AI capabilities from game-specific mechanics, state translation, strategy knowledge, and environment-specific policy configuration.

Core principle:

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

## State Representation

Represents the current condition of a game: board position, player resources, available information, and game history. Each game provides its own state implementation.

## Action Representation

Represents possible decisions available to an agent, such as playing a card, selecting a move, choosing an ability, or taking another game-specific action.

## Game Environment

The environment connects the framework to the game. It provides current state and available actions, executes actions, determines terminal conditions, and provides rewards/results.

## Agent

The reusable agent architecture selects actions. The generic agent does not embed one game's rules or strategic catalogue. It receives game-specific state, available actions, evaluation/policy services, and game-specific context through the adapter/policy layer.

## Decision Engine

Possible implementations include random selection, heuristic evaluation, search algorithms, reinforcement-learning policies, and game-specific strategy-aware evaluation supplied below the framework boundary.

## Evaluation System

Reusable evaluation infrastructure belongs in the framework. Game-specific evaluation rules and strategic knowledge belong in the game's implementation.

## Experience System

Stores interactions between agents and environments: previous state, selected action, reward, and resulting state. This supports future learning systems.

---

# Game-Specific Strategy Knowledge

Some games require persistent strategic knowledge beyond isolated action heuristics. That knowledge belongs to the **game implementation**, not the framework core.

A game may provide:

- persistent strategic axes or abstractions;
- component/state contribution models;
- sparse synergy/conflict relationships;
- composition or motif logic;
- environment/deck/difficulty modifiers;
- run-scoped strategic state derived from current public information;
- strategy-aware candidate-value adjustments;
- offline calibration/tuning infrastructure specific to that game.

The generic framework must not depend on Balatro-specific Bond IDs, Jokers, poker hands, consumables, or calibration constants.

---

# Balatro Strategy Architecture

The active Balatro strategic architecture is the canonical Currency-Wars-style **Bond/composition system**, documented in [`docs/balatro/BALATRO_STRATEGY_SYSTEM.md`](docs/balatro/BALATRO_STRATEGY_SYSTEM.md).

The historical v1.0.0 Gold/Silver/Bronze strategy-tree architecture is retained only in release history and old documentation where explicitly marked historical. It is not the current production strategy authority.

## 1. Canonical Bond layer

Balatro components and persistent public state contribute weighted value to one or more Bonds.

```text
Balatro components/state
      ↓ weighted contribution
Bonds
      ↓ independent development
R1-R5 rank + realization
      ↓
compatible Bond mixture
      ↓
composition motifs / combined build
      ↓
power engine + prescriptions
      ↓
actual D1-D14 decisions
```

A Joker is not normally itself a Bond. A Bond represents a developable strategic axis such as Held Cards, Burnt, Steel, or another persistent mechanic. Exact famous packages such as Baron-Mime-Steel belong above the Bond layer as motifs/compositions.

### Bond rank

Bond rank describes accumulated structural development:

```text
LOCKED
R0
R1 Emerging
R2 Established
R3 Strong
R4 Power-engine capable
R5 Capstone
```

`LOCKED` means a defining prerequisite is absent. `R0` means the axis exists but has not yet crossed its first meaningful contribution threshold.

Rank is computed from weighted contributions. It is not chip output and must not be summed into a fake score estimate.

### Realization

Realization is separate from development:

```text
DORMANT
PARTIAL
ACTIVE
MATURE
```

Development answers how much structure has been assembled. Realization answers whether that structure is actually functioning in the current state/environment.

A boss may temporarily suppress realization without erasing underlying Bond development.

## 2. Composition

The composer selects compatible R1+ Bonds, resolves explicit sparse conflicts, records synergies, evaluates motifs, calculates coherence, and produces prescriptions.

The system does not choose one fixed build template. It composes whatever coherent mixture current RNG and permanent state support.

Composition exposes:

- relevant Bonds;
- power engine;
- motifs;
- synergies;
- conflicts;
- coherence;
- pivot resistance;
- motif distance;
- prescriptions.

## 3. Pivot behavior

Existing structure creates resistance to abandonment, but never an absolute lock.

A functioning ACTIVE/MATURE engine requires a materially better projected replacement before it may be dismantled. A fresh partial Bond cannot destroy a realized power engine merely because it creates more nominal axes.

Pivot decisions consider current realized strength, projected new structure, motif changes, slot/economy cost, buildup time, runway, and survival risk.

## 4. Build Health

Bond structure does not replace score/survival modeling.

```text
Bond ranks + realization + composition
              +
actual scoring / whole-blind projection
              ↓
Build Health
```

Build Health tracks Survival, Immediate Scoring, Scaling, Coherence, and Runway. It is used to detect builds that look structurally interesting but cannot actually keep pace with upcoming blinds.

## 5. D1 execution boundary

Survival and legality remain authoritative. Bond/composition logic shapes choices beneath those constraints.

Important distinction:

- a Bond may identify a preferred strategic action;
- D1 must still prove that action is legal and sufficiently safe;
- a defining engine mechanic may receive explicit execution authority when ordinary local-value logic would otherwise suppress it.

Example: an ACTIVE Burnt engine may intentionally spend the first safe discard to level its target hand even when Banner is owned. Banner's temporary remaining-discard chip value is not allowed to nullify Burnt's defining permanent scaling mechanic.

## 6. D2 / shop boundary

Joker acquisition and replacement combine ordinary scoring/economy value with bounded canonical Bond-transition value.

A candidate may gain value by:

- crossing a useful Bond threshold;
- advancing a relevant selected Bond;
- creating or maturing a motif;
- improving composition coherence;
- filling a structural role efficiently.

These structural bonuses do not fabricate direct chip output. Affordability, reserve, survival, and child-policy admission remain independent constraints.

## 7. Deck/stake cartridge

Deck/stake cartridges do not redefine the universal Bond catalogue. They adjust environment-specific effectiveness, feasibility, economy, and thresholds only where the deck/stake changes them.

```text
Permanent Balatro mechanics/state/execution stack
                +
Universal Bond/composition strategy layer
                +
Run-scoped public-state Bond evaluation
                +
Replaceable deck/stake cartridge
                =
Current production policy
```

Higher-stake/deck work must not reintroduce categorical strategy trees.

---

# Offline Bond Numerical Tuning

The planned numerical calibration subsystem is documented in [`docs/balatro/BALATRO_BOND_TUNING.md`](docs/balatro/BALATRO_BOND_TUNING.md).

Its purpose is to automate empirical coefficient search after semantic/runtime correctness is stable.

The planned architecture is:

```text
human-defined Bond semantics
        ↓
typed immutable calibration snapshot
        ↓
reproducible offline Balatro batches
        ↓
Optuna study
        ↓
trial metrics / best or Pareto candidates
        ↓
manual + deterministic + holdout validation
        ↓
reviewed production defaults
```

Optuna is an optional offline development dependency only. The normal live-agent import path must not depend on it.

The optimizer may tune explicitly approved bounded numerical values such as contributor weights, R1-R5 thresholds, empirical realization cutoffs, synergy/conflict coefficients, pivot resistance, motif values, bounded prescription strengths, and resource-policy thresholds.

The optimizer may **not**:

- invent or remove Bonds;
- change mechanical truth;
- weaken legality or boss rules;
- expose hidden RNG or ordered future draws;
- change parameters during an episode;
- automatically promote its own output;
- learn around known semantic/execution bugs.

Default calibration snapshots must reproduce current production behavior exactly.

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

## Rule 2: Interface-Based Communication

Games communicate with the framework through shared interfaces.

## Rule 3: Strategy Knowledge Stays Game-Specific

Universal **within one game** does not mean universal across the framework. Balatro's Bond catalogue is shared across Balatro decks/stakes, but remains inside the Balatro game layer.

## Rule 4: Environment Configuration Must Not Duplicate Game Knowledge

A deck/stake cartridge may alter effectiveness and thresholds but must not duplicate or redefine the universal Bond semantics.

## Rule 5: Offline Tuning Must Not Leak Into Runtime Authority

Optimization libraries and trial databases belong to development/evaluation tooling. Production decision code consumes only validated calibration values and must remain usable without the tuner installed.

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

Future tuning implementation should remain clearly separated, for example under a Balatro-specific offline tuning/evaluation package rather than the live runtime package.

---

# Design Philosophy

The framework prioritizes:

- modularity;
- extensibility;
- reusability;
- clear separation of concerns;
- inspectable decision logic;
- incremental development;
- reproducible calibration.

The goal is not to put one game's intelligence into the framework core.

The goal is to provide an architecture capable of supporting autonomous agents whose game-specific mechanics and strategic knowledge can be added, evaluated, and calibrated cleanly below a reusable reasoning/execution layer.
