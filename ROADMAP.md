# Roadmap

> The roadmap is milestone-based. Individual game intelligence is developed on top of the general framework through game adapters, evaluators, decision systems, search, planning, and deck-specific agents rather than being embedded into the framework itself.
>
> For Balatro, each deck has its own independent agent/"thinking brain". Decks are developed sequentially. A new deck is not started until the previous deck has completed all stakes from White through Gold.
>
> Completion does **not** require a high win rate or optimal play. A stake is considered completed once the agent successfully completes one full run at that stake.
>
> Once live-game integration is complete, major versions correspond to deck progression and patch versions correspond to stake progression within that deck. For example, Red Deck White Stake is v1.0.0 and Red Deck Gold Stake is v1.0.7; Blue Deck begins at v2.0.0 with White Stake.

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

## v0.9.0 — Balatro Real-Game Integration

> Connect the framework-level Balatro agent to the actual Balatro game. This milestone is complete when the agent can observe live game state, translate it into framework state, execute framework actions in the game, and autonomously operate the full interaction loop required for a Red Deck White Stake run. Winning the run is reserved for v1.0.0.

- [ ] Real-game integration architecture
- [ ] Live Balatro state acquisition
- [ ] Live state → `BalatroState` translation
- [ ] `BalatroAction` → live game input execution
- [ ] Synchronization and turn/phase detection
- [ ] Shop interaction support
- [ ] Consumable interaction support
- [ ] Blind selection and round-transition support
- [ ] Run start/restart support for Red Deck White Stake
- [ ] Integration error handling and recovery
- [ ] End-to-end autonomous game loop
- [ ] Validate agent can operate an actual Red Deck White Stake run without manual gameplay input

# v1.0.0 — Red Deck — White Stake

> First complete Balatro agent milestone. The Red Deck agent must be capable of independently playing and successfully completing an actual Red Deck White Stake run from start to finish.

* [ ] Red Deck agent
* [ ] Red Deck decision-making brain
* [ ] Shop decision-making
* [ ] Joker evaluation and selection
* [ ] Consumable evaluation and selection
* [ ] Tarot/Spectral/Planet decision-making
* [ ] Blind strategy
* [ ] Economy management
* [ ] Deck-building decisions
* [ ] Complete one successful Red Deck White Stake run in actual Balatro
* [ ] Validate Red Deck White Stake agent

# v1.0.1 — Red Deck — Red Stake

* [ ] Red Stake support
* [ ] Adapt decision-making to Red Stake rules
* [ ] Complete one successful Red Deck Red Stake run
* [ ] Validate Red Stake agent

# v1.0.2 — Red Deck — Green Stake

* [ ] Green Stake support
* [ ] Adapt decision-making to Green Stake rules
* [ ] Complete one successful Red Deck Green Stake run
* [ ] Validate Green Stake agent

# v1.0.3 — Red Deck — Black Stake

* [ ] Black Stake support
* [ ] Eternal Joker handling
* [ ] Adapt decision-making to Black Stake rules
* [ ] Complete one successful Red Deck Black Stake run
* [ ] Validate Black Stake agent

# v1.0.4 — Red Deck — Blue Stake

* [ ] Blue Stake support
* [ ] Reduced discard handling
* [ ] Adapt decision-making to Blue Stake rules
* [ ] Complete one successful Red Deck Blue Stake run
* [ ] Validate Blue Stake agent

# v1.0.5 — Red Deck — Purple Stake

* [ ] Purple Stake support
* [ ] Increased Ante requirements
* [ ] Adapt decision-making to Purple Stake rules
* [ ] Complete one successful Red Deck Purple Stake run
* [ ] Validate Purple Stake agent

# v1.0.6 — Red Deck — Orange Stake

* [ ] Orange Stake support
* [ ] Perishable Joker handling
* [ ] Adapt decision-making to Orange Stake rules
* [ ] Complete one successful Red Deck Orange Stake run
* [ ] Validate Orange Stake agent

# v1.0.7 — Red Deck — Gold Stake

* [ ] Gold Stake support
* [ ] Rental Joker handling
* [ ] Adapt decision-making to Gold Stake rules
* [ ] Complete one successful Red Deck Gold Stake run
* [ ] Validate Red Deck across all stakes
* [ ] Complete Red Deck agent

# v2.0.0 — Blue Deck — White Stake

> Begins only after Red Deck Gold Stake completion. Blue Deck follows the same stake-version progression: White v2.0.0, Red v2.0.1, Green v2.0.2, Black v2.0.3, Blue v2.0.4, Purple v2.0.5, Orange v2.0.6, Gold v2.0.7.

* [ ] Blue Deck agent
* [ ] Blue Deck decision-making adaptation
* [ ] Complete one successful Blue Deck White Stake run
* [ ] Validate Blue Deck White Stake agent

## Balatro Deck Progression

> A deck begins only after the previous deck has completed every stake through Gold. Each deck receives its own major version; stakes advance the patch version from `.0` for White through `.7` for Gold.

1. **Red Deck — v1.x** — Active
   * White `v1.0.0` → Red `v1.0.1` → Green `v1.0.2` → Black `v1.0.3` → Blue `v1.0.4` → Purple `v1.0.5` → Orange `v1.0.6` → Gold `v1.0.7`
2. **Blue Deck — v2.x** — Locked until Red Deck Gold Stake completion
   * White `v2.0.0` → Red `v2.0.1` → Green `v2.0.2` → Black `v2.0.3` → Blue `v2.0.4` → Purple `v2.0.5` → Orange `v2.0.6` → Gold `v2.0.7`
3. **Yellow Deck — v3.x** — Locked until Blue Deck Gold Stake completion
4. **Green Deck — v4.x** — Locked until Yellow Deck Gold Stake completion
5. **Black Deck — v5.x** — Locked until Green Deck Gold Stake completion

## Stake Progression

| Stake  | Version suffix | Added difficulty                              |
| ------ | -------------- | --------------------------------------------- |
| White  | `.0.0`         | Base difficulty                               |
| Red    | `.0.1`         | Small Blind gives no reward money             |
| Green  | `.0.2`         | Higher Ante score requirements                |
| Black  | `.0.3`         | 30% chance for shop/pack Jokers to be Eternal |
| Blue   | `.0.4`         | -1 discard                                    |
| Purple | `.0.5`         | Higher Ante score requirements                |
| Orange | `.0.6`         | 30% chance for Jokers to be Perishable        |
| Gold   | `.0.7`         | 30% chance for Jokers to be Rental            |

## Completion Criterion

A deck/stake milestone is complete when:

* [ ] The deck-specific agent can independently play the actual game
* [ ] The agent completes one full run at the target stake
* [ ] The run passes the relevant validation tests

> **Win rate is not a completion requirement.** The objective is to build an agent capable of completing Balatro, not an optimal or highly competitive Balatro AI.
