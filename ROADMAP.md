# Roadmap

> The roadmap is milestone-based. Individual game intelligence is developed on top of the general framework through game adapters, evaluators, decision systems, search, planning, and deck-specific agents rather than being embedded into the framework itself.
>
> For Balatro, each deck has its own independent agent/"thinking brain". Decks are developed sequentially. A new deck is not started until the previous deck has completed all stakes from White through Gold.
>
> Completion does **not** require a high win rate or optimal play. A stake is considered completed once the agent successfully completes one full run at that stake.

## v0.1.0 — Foundation

* [x] Repository setup
* [x] Core abstractions
* [x] Game runner
* [x] Dummy environment
* [x] Type annotations

## v0.2.0 — Framework Infrastructure

* [x] Configuration system
* [x] Logging system
* [x] Metrics system
* [x] Event system

## v0.3.0 — Decision Systems

* [x] Agent architecture
* [x] Decision engine interface
* [x] Decision pipeline
* [x] Policy interface
* [x] Greedy action policy
* [x] Balatro agent integration

## v0.4.0 — Evaluation Framework

* [x] Generic evaluator abstraction
* [x] Heuristic evaluation system
* [x] Balatro evaluator integration
* [x] Play cards value heuristic
* [x] Discard cards value heuristic
* [x] Basic risk heuristic

## v0.5.0 — Decision Strategy Expansion

* [x] Softmax action policy
* [x] Configurable policy selection
* [x] Policy factory
* [x] Agent builder
* [x] Reproducible random seed handling

## v0.6.0 — Experiment Infrastructure

* [x] Agent evaluation runner
* [x] Multi-episode execution
* [x] Policy comparison framework
* [x] Experiment result tracking
* [x] Extended metrics collection

## v0.7.0 — Balatro Intelligence Layer

* [x] Balatro card representation
* [x] Poker hand recognition
* [x] Balatro scoring calculation
* [x] Play cards evaluation
* [x] Discard cards evaluation
* [x] Blind-aware decision evaluation
* [x] Balatro terminology alignment
* [x] Joker framework
* [x] Consumable framework
* [x] Planet card effects
* [x] Tarot card effects
* [x] Spectral card effects
* [x] Card enhancements and editions
* [x] Seals and card modifiers

## v0.8.0 — Balatro Search and Planning Foundation

- [x] Card selection search
- [x] Future state prediction
- [x] Hand/discard probability analysis
- [x] Expected value estimation
- [x] Goal-directed path planning
- [x] Blind completion path synthesis
- [x] Tactical path commitment
- [x] Stake system
- [x] Deck-specific agent architecture
- [x] Red Deck starting-state support

# v1.0.0 — Red Deck — White Stake

> First complete Balatro agent milestone. The Red Deck agent must be capable of independently playing a complete Red Deck White Stake run from start to finish.

* [ ] Red Deck agent
* [ ] Red Deck decision-making brain
* [ ] Shop decision-making
* [ ] Joker evaluation and selection
* [ ] Consumable evaluation and selection
* [ ] Tarot/Spectral/Planet decision-making
* [ ] Blind strategy
* [ ] Economy management
* [ ] Deck-building decisions
* [ ] Complete one successful Red Deck White Stake run
* [ ] Validate Red Deck White Stake agent

# v1.1.0 — Red Deck — Red Stake

* [ ] Red Stake support
* [ ] Adapt decision-making to Red Stake rules
* [ ] Complete one successful Red Deck Red Stake run
* [ ] Validate Red Stake agent

# v1.2.0 — Red Deck — Green Stake

* [ ] Green Stake support
* [ ] Adapt decision-making to Green Stake rules
* [ ] Complete one successful Red Deck Green Stake run
* [ ] Validate Green Stake agent

# v1.3.0 — Red Deck — Black Stake

* [ ] Black Stake support
* [ ] Eternal Joker handling
* [ ] Adapt decision-making to Black Stake rules
* [ ] Complete one successful Red Deck Black Stake run
* [ ] Validate Black Stake agent

# v1.4.0 — Red Deck — Blue Stake

* [ ] Blue Stake support
* [ ] Reduced discard handling
* [ ] Adapt decision-making to Blue Stake rules
* [ ] Complete one successful Red Deck Blue Stake run
* [ ] Validate Blue Stake agent

# v1.5.0 — Red Deck — Purple Stake

* [ ] Purple Stake support
* [ ] Increased Ante requirements
* [ ] Adapt decision-making to Purple Stake rules
* [ ] Complete one successful Red Deck Purple Stake run
* [ ] Validate Purple Stake agent

# v1.6.0 — Red Deck — Orange Stake

* [ ] Orange Stake support
* [ ] Perishable Joker handling
* [ ] Adapt decision-making to Orange Stake rules
* [ ] Complete one successful Red Deck Orange Stake run
* [ ] Validate Orange Stake agent

# v1.7.0 — Red Deck — Gold Stake

* [ ] Gold Stake support
* [ ] Rental Joker handling
* [ ] Adapt decision-making to Gold Stake rules
* [ ] Complete one successful Red Deck Gold Stake run
* [ ] Validate Red Deck across all stakes
* [ ] Complete Red Deck agent

## Balatro Deck Progression

> A deck begins only after the previous deck has completed every stake through Gold.

1. **Red Deck** — Active

   * White → Red → Green → Black → Blue → Purple → Orange → Gold
2. **Blue Deck** — Locked until Red Deck Gold Stake completion
3. **Yellow Deck** — Locked until Blue Deck Gold Stake completion
4. **Green Deck** — Locked until Yellow Deck Gold Stake completion
5. **Black Deck** — Locked until Green Deck Gold Stake completion

## Stake Progression

| Stake  | Added difficulty                              |
| ------ | --------------------------------------------- |
| White  | Base difficulty                               |
| Red    | Small Blind gives no reward money             |
| Green  | Higher Ante score requirements                |
| Black  | 30% chance for shop/pack Jokers to be Eternal |
| Blue   | -1 discard                                    |
| Purple | Higher Ante score requirements                |
| Orange | 30% chance for Jokers to be Perishable        |
| Gold   | 30% chance for Jokers to be Rental            |

## Completion Criterion

A deck/stake milestone is complete when:

* [ ] The deck-specific agent can independently play the game
* [ ] The agent completes one full run at the target stake
* [ ] The run passes the relevant validation tests

> **Win rate is not a completion requirement.** The objective is to build an agent capable of completing Balatro, not an optimal or highly competitive Balatro AI.
