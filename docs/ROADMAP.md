# General Game AI Framework Roadmap

## v0.1.0 — Foundation

Goal: Establish a reusable framework capable of running different game agents through a common architecture.

### Core Framework

- [x] Repository setup
- [x] Project structure
- [x] GameState abstraction
- [x] Action abstraction
- [x] GameEnvironment abstraction
- [x] Agent abstraction
- [x] DecisionEngine abstraction
- [x] Evaluator abstraction
- [x] GameRunner
- [x] Experience data structure

### Validation

- [x] Dummy game environment
- [x] Random agent
- [x] End-to-end execution loop
- [x] Automated tests

### Remaining

- [ ] Add type annotations
- [ ] Add logging system
- [ ] Add configuration system
- [ ] Improve documentation


---

## v0.2.0 — Framework Expansion

Goal: Improve extensibility and maintainability.

### Configuration

- Configurable framework settings
- Agent/environment parameters
- Experiment configuration

### Event System

- Agent action events
- Environment state events
- Episode lifecycle events

### Metrics

- Episode statistics
- Reward tracking
- Performance measurements

### Developer Experience

- Improved testing utilities
- Better error handling
- Framework documentation


---

## v0.3.0 — Decision Systems

Goal: Provide reusable decision-making components.

### Decision Engines

- Random decision engine
- Greedy decision engine
- Heuristic decision engine
- Search-based decision engines
- Monte Carlo Tree Search
- Expectimax


---

## v0.4.0 — Learning Infrastructure

Goal: Add reusable learning capabilities.

### Learning Components

- Experience replay
- Memory systems
- Training pipeline
- Model saving/loading
- Evaluation pipeline


---

## v0.5.0 — First Game Adapter

Goal: Build the first complete game-specific implementation.

### Adapter Components

- State representation
- Action representation
- Environment integration
- Evaluation logic
- Agent experiments


---

## v0.6.0+ — Additional Game Adapters

Goal: Validate framework generality.

Possible environments:

- Strategy games
- Roguelikes
- Card games
- Turn-based games
- Imperfect information games