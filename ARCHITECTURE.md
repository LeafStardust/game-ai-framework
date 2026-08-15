# General Game AI Framework Architecture

## Overview

The General Game AI Framework is designed as a reusable architecture for building autonomous agents across different games.

The framework separates general AI capabilities from game-specific implementations.

The core principle:

> The agent should know how to reason, while the game adapter defines what it is reasoning about.

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

        Game Adapter Layer

-----------------------------------------
|              |                        |
 Game A       Game B                Game C
```

---

# Component Responsibilities

## Framework Core

The framework core contains reusable abstractions shared by all games.

Responsibilities:

* Define common interfaces
* Manage agent execution
* Store experiences
* Provide decision-making infrastructure

---

## State Representation

Represents the current condition of a game.

Examples:

* Board position
* Player resources
* Available information
* Game history

Each game provides its own state implementation.

---

## Action Representation

Represents possible decisions available to an agent.

Examples:

* Playing a card
* Selecting a move
* Choosing an ability
* Taking an action

---

## Game Environment

The environment acts as the connection between the framework and the game.

Responsibilities:

* Provide current state
* Provide available actions
* Execute actions
* Determine terminal conditions
* Provide rewards

---

## Agent

The agent is responsible for selecting actions.

The agent does not contain game-specific rules.

It receives:

* Current state
* Available actions

It returns:

* Selected action

---

## Decision Engine

The decision engine determines how an agent selects actions.

Possible implementations:

* Random selection
* Heuristic evaluation
* Search algorithms
* Reinforcement learning policies

---

## Evaluation System

Evaluates states or actions.

Game-specific evaluation logic should be implemented outside the framework core.

---

## Experience System

Stores interactions between agents and environments.

A single experience contains:

* Previous state
* Selected action
* Reward
* Resulting state

This enables future learning systems.

---

# Dependency Rules

## Rule 1: Framework Independence

Framework components must not depend on specific games.

Incorrect:

```text
Framework → Specific Game
```

Correct:

```text
Framework ← Game Adapter
```

---

## Rule 2: Interface-Based Communication

Games communicate with the framework through shared interfaces.

Example:

```text
GameEnvironment
       ↑
       |
Specific Game Environment
```

---

## Rule 3: Agent Independence

Agents should remain separate from game implementations.

The same agent architecture should be reusable across different environments.

---

# Directory Structure

```text
agents/
    Game-specific or experimental agents

framework/
    Reusable AI framework components

games/
    Game adapters and implementations

tests/
    Automated tests

docs/
    Project documentation
```

---

# Design Philosophy

The framework prioritizes:

* Modularity
* Extensibility
* Reusability
* Clear separation of concerns
* Incremental development

The goal is not to create one powerful game bot.

The goal is to create an architecture capable of supporting many autonomous game agents.
