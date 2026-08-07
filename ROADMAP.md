# Roadmap

> The roadmap is milestone-based. Individual game intelligence is developed on top of the general framework through game adapters, evaluators, and agents rather than being embedded into the framework itself.

## v0.1.0 — Foundation

- [x] Repository setup
- [x] Core abstractions
- [x] Game runner
- [x] Dummy environment
- [x] Type annotations

## v0.2.0 — Framework Infrastructure

- [x] Configuration system
- [x] Logging system
- [x] Metrics system
- [x] Event system

## v0.3.0 — Decision Systems

- [x] Agent architecture
- [x] Decision engine interface
- [x] Decision pipeline
- [x] Policy interface
- [x] Greedy action policy
- [x] Balatro agent integration

## v0.4.0 — Evaluation Framework

- [x] Generic evaluator abstraction
- [x] Heuristic evaluation system
- [x] Balatro evaluator integration
- [x] Play cards value heuristic
- [x] Discard cards value heuristic
- [x] Basic risk heuristic

## v0.5.0 — Decision Strategy Expansion

- [x] Softmax action policy
- [x] Configurable policy selection
- [x] Policy factory
- [x] Agent builder
- [x] Reproducible random seed handling

## v0.6.0 — Experiment Infrastructure

- [x] Agent evaluation runner
- [x] Multi-episode execution
- [x] Policy comparison framework
- [x] Experiment result tracking
- [x] Extended metrics collection

## v0.7.0 — Balatro Intelligence Layer

- [x] Balatro card representation
- [x] Poker hand recognition
- [x] Balatro scoring calculation
- [x] Play cards evaluation
- [x] Discard cards evaluation
- [x] Blind-aware decision evaluation
- [x] Balatro terminology alignment

## v0.8.0 — Balatro Search and Planning

- [ ] Card selection system
- [ ] Future state prediction
- [ ] Hand/discard probability analysis
- [ ] Search-based decision making
- [ ] Expected value estimation

## v1.0.0 — General Game AI Framework

- [ ] Stable framework API
- [ ] Multiple game adapters
- [ ] Reusable decision systems
- [ ] Learning integration