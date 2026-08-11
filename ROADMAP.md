# Roadmap

> The roadmap is milestone-based. Individual game intelligence is developed on top of the general framework through game adapters, evaluators, decision systems, search, planning, and deck-specific agents rather than being embedded into the framework itself.
>
> For Balatro, each deck has its own independent agent/"thinking brain". Decks are developed sequentially. A new deck is not started until the previous deck has completed all stakes from White through Gold.
>
> Completion does **not** require a high win rate or optimal play. A stake is considered completed once the agent successfully completes one full run at that stake.
>
> The production Balatro agent targets the normal Steam game through read-only external observation and normal mouse input. Read-only observation may use the normal Balatro save state and/or screen pixels, but production must not modify or inject into the game process or save. Agent-facing state must exclude hidden future/RNG information that a normal player could not know. Runtime injection/mod APIs may be used as optional development and testing tools, but a modded/injected backend does not satisfy the real-game completion criterion.
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

## v0.9.0 — Balatro External Real-Game Integration

> Connect the framework-level Balatro agent to the normal Steam version of Balatro without modifying or injecting into the game process or save. The production backend may read the normal save state and screen pixels externally, and must execute gameplay actions through normal input. This milestone is complete when the agent can autonomously operate an unmodified Red Deck White Stake run. Winning the run is reserved for v1.0.0.

### Shared live-integration infrastructure

- [x] Live-game bridge/action interfaces
- [x] Live state → `BalatroState` translation architecture
- [x] Live console telemetry
- [x] Integration error/recovery architecture
- [x] BalatroBot API backend for optional development/testing

### External Steam observation

- [x] Read-only vanilla `save.jkr` discovery and parser
- [x] Save snapshot change detection and stale-state rejection
- [x] Agent-facing observable-state whitelist excluding RNG seed/future-only data
- [x] Selecting-hand structured state extraction: phase, deck/stake, ante/round, money, score, blind, hands/discards and visible hand
- [x] Blind-selection phase/state extraction and validation
- [x] Joker and consumable structured state extraction and validation
- [x] Shop structured state extraction and validation, including visible-area indices
- [x] Structured translation for validated `BLIND_SELECT`, `SELECTING_HAND`, `ROUND_EVAL`, `SHOP` and checkpoint transitions
- [x] Save-disappearance/race handling at terminal run states
- [ ] Public skip-tag identity/reward extraction for blind planning
- [ ] Complete production-state translation for every remaining run/menu phase
- [ ] Full observation recovery validation across an entire run

### Optional visual fallback

- [x] Steam Balatro window discovery and client-area tracking
- [x] External screen-capture backend
- [x] Resolution/scale-independent viewport normalization
- [x] Visual phase signature/calibration infrastructure
- [x] Visual game-phase detection
- [x] Playing-card location/order detection for external clicking
- [ ] HUD visual extraction fallback
- [ ] Blind-selection visual information fallback
- [ ] Joker/consumable visual fallback
- [ ] Shop visual fallback

> Visual fallback work is not a v0.9.0 completion blocker when the same observable state is available reliably through the read-only structured observer.

### External Steam control

- [x] Normal mouse input backend with foreground/focus safety
- [x] Dynamic hand-card coordinate mapping and save-order validation
- [x] External `PLAY_CARDS` execution
- [x] External `DISCARD_CARDS` execution
- [x] Calibrated Small/Big/Boss Blind Select controls
- [x] Calibrated Small/Big Blind Skip controls
- [x] Calibrated Cash Out control with validated `ROUND_EVAL` → `SHOP` checkpoint transition
- [x] Deterministic shop purchase controls for Joker/consumable/voucher targets
- [x] External End Shop control and delayed checkpoint reconciliation
- [x] Post-action checkpoint synchronization for hand, blind-select, round-eval and validated shop transitions
- [x] Guard against already-selected hand cards before external execution
- [x] Fresh post-purchase visual observation and dynamic retargeting for safe multi-buy main-shop chaining
- [ ] Booster-opening control and immediate post-open observation
- [ ] Reroll control and immediate refreshed-shop observation
- [ ] Consumable-use interaction controls
- [ ] Run start/restart controls for Red Deck White Stake

### Live hand scoring and blind-clear planning

> The live agent is moving from local turn-by-turn heuristics to goal-directed blind completion. The target architecture is: **score outcomes → model possible future draws → search for the highest-probability blind-clear policy → execute one action → observe the authoritative save checkpoint → replan**.
>
> Deterministic visible effects must produce an exact score. Nondeterministic effects must not be collapsed into one guessed score: the planner should track at minimum a **guaranteed score floor**, an **expected score**, and the relevant **outcome distribution / clear probability**. A Lucky-style bonus therefore contributes to expected/upside scoring but is not counted in the guaranteed floor unless the non-random part already provides it.

- [x] Exact deterministic visible-hand scoring including played-card chip values
- [x] Exact projected blind total and immediate-clear detection
- [x] Live preview telemetry for poker hand, calculated score, projected total, remaining chips and clear status
- [x] Pace-aware one-step play/discard evaluator as an interim policy
- [x] Checkpointed hand loop: observe → choose → execute → persist → replan
- [x] Preserve terminal action when Balatro removes the run save after a loss
- [x] Visible-card score-outcome model with guaranteed minimum, expected value, maximum/relevant outcomes and clear probability
- [x] Deterministic/probabilistic separation for Lucky card scoring effects
- [ ] Extend score-outcome modelling to remaining stochastic Joker/effect sources
- [x] Side-effect-free Joker scoring projection architecture with live-validated stateful Ice Cream support
- [ ] Extend side-effect-free hypothetical scoring across remaining relevant Joker implementations
- [ ] Boss-blind modifier integration into hypothetical score/legality calculations
- [x] Public remaining-deck composition model that never exposes hidden draw order
- [x] Draw/discard outcome distributions from public deck composition
- [x] Bounded two-action blind-clear planner over play/discard branches
- [ ] Generalize blind-clear planning across all remaining hands and discards
- [ ] Contingent plans validated on a real discard/draw checkpoint rather than only deterministic retained-card continuations
- [ ] Resource-aware plan objective: maximize clear probability first, then preserve hands/discards/economy and avoid unnecessary overkill
- [ ] Consumable-use branches inside blind-clear planning
- [x] Replan after every real planner-controlled hand checkpoint using the newly observed state
- [x] Guarded planner-controlled real blind clear with authoritative stateful-Joker checkpoint restoration and replanning
- [ ] Blind-skip/tag valuation integrated with run-level planning
- [ ] Replace the interim pace heuristic as the primary live hand policy once the planner is validated

### Shop intelligence and safe execution

- [x] Visible shop item translation with live identity and original area index
- [x] Buffered deterministic purchase transaction model for stale in-shop saves
- [x] Delayed money reconciliation after leaving shop
- [x] One-shot policy-recommended external purchase with exact-label guard
- [x] Projected re-ranking after one purchase
- [x] Optional guarded End Shop when the projected next recommendation is to stop buying
- [x] Joker-aware shop value probes using existing Joker implementations
- [ ] Identity/inventory reconciliation in addition to money reconciliation
- [x] Safe fresh-layout observation before a second main-card purchase, with combined delayed multi-buy checkpoint validation
- [ ] Booster valuation/opening
- [ ] Reroll valuation/execution
- [ ] Joker sell/replace decisions
- [ ] Broader semantic valuation for non-scoring Jokers, consumables and vouchers

### End-to-end validation

- [ ] External autonomous game loop spanning blind select → hand play → round evaluation → shop → next blind
- [x] Production hand actions require no Lovely/Steamodded/BalatroBot injection
- [x] Production blind-selection and validated deterministic shop actions require no injection
- [ ] Validate one actual unseeded Red Deck White Stake run operates without manual gameplay input
- [ ] Validate normal Steam profile/save progression remains in use
- [ ] Verify achievement/progression behavior empirically rather than assuming it

> Lovely/Steamodded/BalatroBot may remain available as an optional development oracle for comparing extracted state against internal game state. Runs performed through that backend do **not** count toward v0.9.0 or later deck/stake completion.

# v1.0.0 — Red Deck — White Stake

> First complete Balatro agent milestone. The Red Deck agent must independently play the normal Steam game through the external production backend and successfully complete an unseeded Red Deck White Stake run from start to finish.

* [ ] Red Deck agent
* [ ] Red Deck decision-making brain
* [ ] Probabilistic blind-clear planning validated in live play
* [ ] Shop decision-making
* [ ] Joker evaluation and selection
* [ ] Consumable evaluation and selection
* [ ] Tarot/Spectral/Planet decision-making
* [ ] Blind strategy, including skip/tag decisions
* [ ] Economy management
* [ ] Deck-building decisions
* [ ] Complete one successful unseeded Red Deck White Stake run in actual Steam Balatro
* [ ] Validate normal profile progression/unlocks are preserved
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
* [ ] Increased Ante score requirements
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

* [ ] The deck-specific agent independently plays the normal Steam game through the external production backend
* [ ] The agent completes one full run at the target stake
* [ ] The run uses the normal Steam profile/save path without injected gameplay control
* [ ] The run passes the relevant validation tests

> **Win rate is not a completion requirement.** The objective is to build an agent capable of completing Balatro, not an optimal or highly competitive Balatro AI.
