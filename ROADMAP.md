# Roadmap

> The roadmap is milestone-based. General game-AI infrastructure stays reusable; game-specific mechanics, planning and playbooks live in game adapters and agents.
>
> For Balatro there is **one permanent agent and one permanent mechanics/state/execution stack**. Deck/stake strategy is supplied by a replaceable **playbook cartridge** selected automatically from the live run. A new deck begins only after the previous deck has completed every stake through Gold.
>
> Completion does **not** require a high win rate or optimal play. A stake is complete once the agent independently completes one full run at that stake.
>
> Production Balatro integration should require no third-party bot/mod runtime if technically possible. External repositories may be studied for Balatro internals, but production code should live in this repository. The preferred observer is our own zero-dependency, read-only Windows process-memory reader. `save.jkr` is fallback/debug state only, not live truth.
>
> Agent-facing observation must exclude hidden future information: no RNG state/seed exploitation and no ordered future draw pile. Current live objects and public deck composition are allowed.

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
- [x] Play/discard value heuristics
- [x] Basic risk heuristic

## v0.5.0 — Decision Strategy Expansion

- [x] Softmax action policy
- [x] Configurable policy selection
- [x] Policy factory
- [x] Agent builder
- [x] Reproducible random seed handling for framework experiments

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
- [x] Play/discard evaluation
- [x] Blind-aware evaluation
- [x] Joker framework
- [x] Consumable framework
- [x] Planet/Tarot/Spectral effects
- [x] Enhancements, editions and seals

## v0.8.0 — Balatro Search and Planning Foundation

- [x] Card selection search
- [x] Future state prediction
- [x] Hand/discard probability analysis
- [x] Expected value estimation
- [x] Goal-directed path planning
- [x] Blind completion path synthesis
- [x] Tactical path commitment
- [x] Stake system
- [x] Deck-specific agent architecture foundation
- [x] Red Deck starting-state support

## v0.9.0 — Autonomous Real-Game Integration

> Target user flow: start normal Steam Balatro, enter any supported deck/stake run manually, then activate the agent once. The agent reads the **current running game**, detects deck/stake, loads the matching playbook, chooses and executes one action, observes the resulting live state, verifies it, and repeats until win/loss.
>
> Target loop:
>
> `live Balatro state -> translate -> select playbook -> plan -> execute -> live Balatro state -> verify -> log -> replan`

### 0.9A — Authoritative live-state observation — ACTIVE

- [x] Live bridge/state protocol and `BalatroState` translation architecture
- [x] Zero-dependency Windows read-only process attachment through Python `ctypes`
- [x] Readable process-memory region enumeration
- [x] Narrow LuaJIT value/table decoder foundation
- [x] Initial live-memory `G` discovery probe
- [x] Unit coverage for LuaJIT-memory decoding primitives
- [x] Validate LuaJIT layout against a fresh live Balatro run
- [x] Reliably discover and validate Balatro global `G`
- [x] Read whitelisted current-run fields directly from live memory
- [ ] Read current card/Joker/consumable/shop identities directly from live objects
- [x] Read live UI object geometry where stable enough for execution targeting
- [x] Detect deck and stake directly from the active run
- [x] Translate direct-memory observation into `LiveBalatroSnapshot`
- [x] Make direct live-memory observer the production default
- [x] Keep `save.jkr` parser only as fallback/debug/recovery input
- [x] Exclude RNG state, seed exploitation and ordered future draw information from production observation
- [ ] Validate state freshness across rapid events such as consumable use, Joker creation/destruction and shop purchases
- [ ] Validate observation across all required run phases

> If a stable read-only memory decoder proves infeasible across normal Balatro builds, the fallback architecture is a minimal bridge written entirely in this repository. Third-party bot/mod repositories are not production dependencies.

### 0.9B — Exact external control

> Baseline execution remains normal OS input. Direct invocation of Balatro internal callbacks may be explored later only if our own implementation is simpler and sufficiently safe; it is not required for autonomous play.

- [x] Normal mouse input backend with foreground/focus safety
- [x] External `PLAY_CARDS` / `DISCARD_CARDS`
- [x] Small/Big/Boss Blind selection controls
- [x] Blind skip controls
- [x] Cash Out control
- [x] Deterministic shop purchase controls
- [x] End Shop control
- [x] Consumable interaction foundation
- [x] Guard against already-selected hand cards
- [ ] Prefer live Balatro UI coordinates over visual inference where available
- [ ] Reconcile each action against the **next direct live-state observation**
- [ ] Booster opening
- [ ] Reroll
- [ ] Joker sell/replace
- [ ] Robust consumable use for all supported target patterns
- [ ] Optional direct internal action backend investigation using only repository-owned code
- [ ] Emergency stop / safe agent deactivation

### 0.9C — Shared mechanics and blind planning

> Mechanics do not change when a playbook cartridge changes. The shared engine owns Balatro rules; a playbook only changes strategic preferences and planning parameters.

- [x] Exact deterministic visible-hand scoring
- [x] Immediate-clear and projected blind-total calculations
- [x] Guaranteed/expected/upside score-outcome representation
- [x] Lucky stochastic separation
- [x] Side-effect-free Joker score projection architecture
- [x] Live-validated Ice Cream and Bootstraps projections
- [x] Boss-blind legality foundation
- [x] The Psychic / The Head / The House planner paths validated during live development
- [x] Public remaining-deck composition model without future draw order
- [x] Probabilistic draw/discard outcomes
- [x] Bounded multi-action adaptive blind-clear search
- [x] Search node budgets and guarded one-action execution
- [x] Consensus setup-discard policy
- [x] Replan after each real action checkpoint
- [x] Initial The Sun escape planning
- [ ] Extend score projection to relevant remaining Jokers/effects
- [ ] Generalize boss-blind integration
- [ ] Integrate consumable actions into the normal blind planner
- [ ] Resource-aware blind objective: clear probability first, then preserve hands/discards/economy
- [ ] Blind skip/tag valuation
- [ ] Replace temporary unsupported-Joker hard stops with complete supported mechanics

### 0.9D — Playbook cartridge system

> There is one Balatro agent. The cartridge answers **how to play this deck/stake**, not **how Balatro works**.

- [x] Define playbook interface
- [x] Playbook registry keyed by `(deck, stake)`
- [x] Auto-select playbook from live deck/stake at activation
- [x] Separate factual deck/stake mechanics from strategic playbook preferences
- [x] Playbook controls for risk tolerance
- [x] Playbook controls for planner/search budgets
- [ ] Shop/Joker/consumable priorities
- [ ] Economy thresholds and scaling priorities
- [ ] Blind skip/tag strategy
- [ ] Red Deck / White Stake first production playbook
- [x] Playbook version identifier included in every run log

### 0.9E — Run experience logging and later learning

> **Recording and learning are separate.** Every run should produce a durable experience log now. The agent must not silently rewrite its active playbook during a run. Controlled offline analysis/adaptation can be added once enough trustworthy runs exist.

- [x] Generic framework console logging/metrics foundation
- [x] Append-only Balatro per-run JSONL experience logger
- [x] Run identity includes deck/stake/playbook/playbook version
- [ ] Integrate run logger into the autonomous live loop
- [ ] Log sanitized observation before decisions
- [ ] Log chosen action and planner/playbook rationale
- [ ] Log execution success/failure and authoritative post-action state
- [ ] Log purchases, sells, consumable uses and blind outcomes
- [ ] Log terminal win/loss and final run summary
- [ ] Build replay/analysis utility over stored runs
- [ ] Aggregate per-playbook statistics across runs
- [ ] Identify repeated failure patterns and weak decisions from logs
- [ ] Add controlled offline playbook tuning/learning only after log quality is validated
- [ ] Keep automatic online self-modification out of the critical live loop unless later evidence justifies it

### 0.9F — Shop and run-level intelligence

- [x] Visible shop item translation and valuation foundation
- [x] Purchase policy/re-ranking foundation
- [x] Joker-aware shop value probes
- [ ] Booster valuation/opening
- [ ] Reroll valuation/execution
- [ ] Joker sell/replace decisions
- [ ] Broader semantic valuation for non-scoring Jokers, consumables and vouchers
- [ ] Run-level planning connecting blind risk, economy, shop and deck growth

### 0.9G — Single-command autonomous orchestrator

- [ ] One activation command for an already-started Balatro run
- [x] Attach to current Balatro process automatically
- [x] Read current deck/stake and load playbook automatically
- [ ] Observe/plan/execute/verify/log loop across all required phases
- [ ] Blind select -> hand play -> round eval -> shop -> next blind without manual gameplay input
- [ ] Continue automatically across antes
- [ ] Detect win/loss terminal state
- [ ] Clean shutdown and complete run log
- [ ] Validate a fresh unseeded Red Deck White Stake run end-to-end

### Legacy/fallback observation

The existing `save.jkr` and visual observer work remains useful for diagnostics and recovery, but it is no longer the production source of truth.

- [x] Vanilla `save.jkr` discovery/parser
- [x] Save-backed phase/hand/Joker/consumable/shop extraction
- [x] Screen capture and visual phase/card-location infrastructure
- [x] Keep these paths isolated as fallback/debug tools
- [ ] Remove live-control dependence on save-persistence timing
- [ ] Remove stale-save reconciliation from the normal autonomous loop

## v1.0.0 — Red Deck — White Stake

> First complete playbook milestone. The permanent Balatro agent must activate against a normal unseeded Red Deck White Stake run, automatically select the Red/White playbook, and complete the run without manual gameplay input.

- [ ] Red / White playbook
- [ ] Probabilistic blind-clear planning validated across a complete run
- [ ] Shop/Joker/consumable decisions
- [ ] Blind and skip/tag strategy
- [ ] Economy and deck-building decisions
- [ ] Complete one successful unseeded Red Deck White Stake run
- [ ] Preserve normal Steam profile progression/unlocks
- [ ] Produce a complete replayable run-experience log

## v1.1.0 — Red Deck — Red Stake

- [ ] Red / Red playbook
- [ ] Adapt strategy to Red Stake
- [ ] Complete one successful run

## v1.2.0 — Red Deck — Green Stake

- [ ] Red / Green playbook
- [ ] Adapt strategy to Green Stake
- [ ] Complete one successful run

## v1.3.0 — Red Deck — Black Stake

- [ ] Red / Black playbook
- [ ] Eternal Joker strategy
- [ ] Complete one successful run

## v1.4.0 — Red Deck — Blue Stake

- [ ] Red / Blue playbook
- [ ] Reduced-discard strategy
- [ ] Complete one successful run

## v1.5.0 — Red Deck — Purple Stake

- [ ] Red / Purple playbook
- [ ] Higher-score-requirement strategy
- [ ] Complete one successful run

## v1.6.0 — Red Deck — Orange Stake

- [ ] Red / Orange playbook
- [ ] Perishable Joker strategy
- [ ] Complete one successful run

## v1.7.0 — Red Deck — Gold Stake

- [ ] Red / Gold playbook
- [ ] Rental Joker strategy
- [ ] Complete one successful run
- [ ] Validate Red Deck across all stakes

## v2.0.0 — Blue Deck — White Stake

> Begins after Red Deck Gold Stake. The permanent agent is unchanged; Blue Deck progression adds Blue-specific playbooks.

- [ ] Blue / White playbook
- [ ] Complete one successful Blue Deck White Stake run

## Deck progression

1. **Red Deck — v1.x** — Active
   - White `v1.0.0` -> Red `v1.1.0` -> Green `v1.2.0` -> Black `v1.3.0` -> Blue `v1.4.0` -> Purple `v1.5.0` -> Orange `v1.6.0` -> Gold `v1.7.0`
2. **Blue Deck — v2.x** — Locked until Red Gold completion
3. **Yellow Deck — v3.x** — Locked until Blue Gold completion
4. **Green Deck — v4.x** — Locked until Yellow Gold completion
5. **Black Deck — v5.x** — Locked until Green Gold completion

## Stake progression

| Stake | Version | Primary added difficulty |
|---|---:|---|
| White | `.0.0` | Base difficulty |
| Red | `.1.0` | Small Blind gives no reward money |
| Green | `.2.0` | Higher score requirements |
| Black | `.3.0` | Eternal Jokers |
| Blue | `.4.0` | -1 discard |
| Purple | `.5.0` | Higher score requirements |
| Orange | `.6.0` | Perishable Jokers |
| Gold | `.7.0` | Rental Jokers |

## Completion criterion
