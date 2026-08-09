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
- [x] Joker framework
- [x] Consumable framework
- [x] Planet card effects
- [x] Tarot card effects
- [x] Spectral card effects
- [x] Card enhancements and editions
- [x] Seals and card modifiers

## v0.8.0 — Balatro Search and Planning

> Decks are developed sequentially. A deck is not started until the previous deck has a complete agent and passes its validation criteria. The current target is the Red Deck.

### Deck progression

1. **Red Deck** — active
2. **Blue Deck** — locked until Red Deck completion
3. **Yellow Deck** — locked until Blue Deck completion
4. **Green Deck** — locked until Yellow Deck completion
5. **Black Deck** — locked until Green Deck completion

### Red Deck Agent

- [ ] Red Deck rules and starting-state support
- [ ] Card selection system
- [ ] Future state prediction
- [ ] Hand/discard probability analysis
- [ ] Search-based decision making
- [ ] Expected value estimation
- [ ] Goal-directed path planning
- [ ] Blind completion path synthesis
- [ ] Tactical path commitment
- [ ] Complete Red Deck agent
- [ ] Validate Red Deck agent across full runs

### Deck completion gate

- [ ] Current deck agent completes its full validation criteria
- [ ] Current deck agent is considered complete before the next deck begins

## v1.0.0 — General Game AI Framework

- [ ] Stable framework API
- [ ] Multiple game adapters
- [ ] Reusable decision systems
- [ ] Learning integration
