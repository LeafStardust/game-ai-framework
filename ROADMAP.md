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

> Decks are developed sequentially. A deck is not started until the previous deck has a complete agent and passes its validation criteria. The current target is the Red Deck. For each deck, the agent progresses through White → Red → Green → Black → Blue → Purple → Orange → Gold Stake. A deck is complete after one successful full run at every stake; win-rate optimization is not a completion requirement.

### Deck progression

1. **Red Deck** — active; complete White → Gold Stake
2. **Blue Deck** — locked until Red Deck Gold Stake completion
3. **Yellow Deck** — locked until Blue Deck Gold Stake completion
4. **Green Deck** — locked until Yellow Deck Gold Stake completion
5. **Black Deck** — locked until Green Deck Gold Stake completion

### Red Deck Agent

- [x] Red Deck rules and starting-state support
- [x] Card selection system
- [x] Future state prediction
- [x] Hand/discard probability analysis
- [x] Search-based decision making
- [x] Stake system
- [ ] Expected value estimation
- [ ] Goal-directed path planning
- [ ] Blind completion path synthesis
- [ ] Tactical path commitment
- [ ] White Stake completion
- [ ] Red Stake completion
- [ ] Green Stake completion
- [ ] Black Stake completion
- [ ] Blue Stake completion
- [ ] Purple Stake completion
- [ ] Orange Stake completion
- [ ] Gold Stake completion
- [ ] Complete Red Deck agent
- [ ] Validate Red Deck agent across full runs

### Deck completion gate

- [ ] Agent completes one full run at every stake from White through Gold
- [ ] Current deck agent is considered complete before the next deck begins

### Stake progression

| Stake | Added difficulty |
| --- | --- |
| White | Base difficulty |
| Red | Small Blind gives no reward money |
| Green | Higher Ante score requirements |
| Black | 30% chance for shop/pack Jokers to be Eternal |
| Blue | -1 discard |
| Purple | Higher Ante score requirements |
| Orange | 30% chance for Jokers to be Perishable |
| Gold | 30% chance for Jokers to be Rental |

## v1.0.0 — General Game AI Framework

- [ ] Stable framework API
- [ ] Multiple game adapters
- [ ] Reusable decision systems
- [ ] Learning integration
