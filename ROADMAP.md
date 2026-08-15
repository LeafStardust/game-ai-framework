# Roadmap

> The roadmap is milestone-based. General game-AI infrastructure stays reusable; game-specific mechanics, planning and playbooks live in game adapters and agents.
>
> For Balatro there is **one permanent agent and one permanent mechanics/state/execution stack**. Deck/stake strategy is supplied by a replaceable **playbook cartridge** selected automatically from the live run. A new deck begins only after the previous deck has completed every stake through Gold.
>
> **Release scope is intentionally progressive.** `v0.9.0` is the autonomous integration/coverage milestone: the production agent must be able to observe, decide, execute, verify and continue through the reachable run flow without manual gameplay intervention. `v1.0.0` is the first competence milestone: the same permanent agent must actually win one unseeded Red Deck / White Stake run with no manual gameplay help after activation.
>
> Production Balatro integration should require no third-party bot/mod runtime if technically possible. Production observation is repository-owned, zero-dependency, read-only Windows process memory; production execution is the repository-owned first-party in-process bridge. `save.jkr`, visual observation and OS input are fallback/debug tooling only.
>
> Agent-facing observation must exclude hidden future information: no RNG-state/seed exploitation and no ordered future draw pile. Current live objects and public deck composition are allowed.
>
> **Decision intelligence and execution are tracked separately.** Being able to execute an action does not mean the agent knows when that action is strategically correct. `v0.9.0` may use conservative/suboptimal policies where necessary to cover a juncture safely; strategic quality sufficient to deliberately win Red/White belongs to the `v1.0.0` competence work.
>
> **Roadmap maintenance rule:** when implementation, deterministic tests or live validation clears a milestone, update this roadmap in the same development checkpoint.

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

> **Purpose:** make the real-game agent complete, stable and safe enough to operate autonomously. A Red/White win is **not** required for this release; winning competence is the `v1.0.0` gate.
>
> **Completion gate:** after one activation on an already-started supported run, the production agent can continue through every supported reachable phase, execute the required semantic actions, wait for Balatro to finish transitions, re-observe/replan, log the attempt, terminate cleanly on win/loss, and restart a lost run when configured — all without manual gameplay input.
>
> **Current validation priority:** reliability and phase coverage, not brute-force retry-until-win. For current Red/White soak testing, stop after **3 consecutive clean complete attempts**, or **10 attempts / 2 hours** (whichever comes first). Stop immediately on crash, UI corruption or unsafe transition. A real win is useful evidence but is not a `v0.9.0` requirement.

### 0.9A — Authoritative live observation and transition readiness

**Implemented**

- [x] Live bridge/state protocol and `BalatroState` translation architecture
- [x] Zero-dependency Windows read-only process attachment through Python `ctypes`
- [x] Readable process-memory region enumeration
- [x] Narrow LuaJIT value/table decoder foundation
- [x] Initial live-memory `G` discovery probe
- [x] Unit coverage for LuaJIT-memory decoding primitives
- [x] Validate LuaJIT layout against a fresh live Balatro run
- [x] Reliably discover and validate Balatro global `G`
- [x] Read whitelisted current-run fields directly from live memory
- [x] Read current card/Joker/consumable/shop identities directly from live objects
- [x] Complete mutable Joker live-state reconstruction contract (`33 HYDRATED / 119 STATELESS / 0 GAP / 0 ERROR`)
- [x] Unit coverage for declared Joker state extraction and stateful factory hydration
- [x] Read live UI object geometry for diagnostics/fallback tooling where useful
- [x] Detect deck and stake directly from the active run
- [x] Translate direct-memory observation into `LiveBalatroSnapshot`
- [x] Make direct live-memory observer the production default
- [x] Cross-process cache validated `G` discovery while preserving structural validation
- [x] Warm observation latency suitable for persistent autonomous replanning
- [x] Keep `save.jkr` parser only as fallback/debug/recovery input
- [x] Exclude RNG state, seed exploitation and ordered future draw information from production observation
- [x] Semantic stability checks and bounded stale-state replanning
- [x] Native readiness gate for `BLIND_SELECT` before blind-control actions are exposed
- [x] Native readiness gate for `SHOP` before shop actions are exposed
- [x] Post-pack visual settlement guard for delayed Joker transfer/animation
- [x] Global production quiescence barrier: full observer sequence must remain unchanged for 1.0 continuous second before a newly changed checkpoint can drive another command
- [x] Cache already-certified quiescent sequences so repeated reads do not pay the 1-second barrier again

**Remaining 0.9 coverage**

- [x] Validate state freshness across remaining rapid events such as targeted consumable resolution and Joker creation/destruction
- [x] Validate observation/readiness across every remaining required run phase/effect family
- [x] Confirm the quiescence/readiness contract survives multi-attempt live soak testing without premature injections

### 0.9B — First-party in-process execution and safety

> Production execution uses Balatro's own callbacks through the repository-owned fused-archive bridge. Process-memory observation remains read-only and independently verifies resulting checkpoints. Mouse tooling must never become a silent production fallback.

**Implemented**

- [x] Repository-owned fused-archive bridge with exact original backup/restore path
- [x] Bridge status command and in-game achievement-gate validation
- [x] Injected `PLAY_CARDS` / `DISCARD_CARDS`
- [x] Small/Big/Boss Blind selection control
- [x] Cash Out control
- [x] Main-shop Buy control
- [x] Voucher redeem control
- [x] Booster opening
- [x] Reroll
- [x] End Shop / Next Round control
- [x] Booster-pack card selection and confirmation
- [x] Booster-pack Skip control
- [x] Unified semantic injected action dispatcher
- [x] Reconcile irreversible actions against the next authoritative live-state observation
- [x] Accept natural `GAME_OVER` as a valid terminal postcondition after a played hand
- [x] No silent mouse fallback in production autonomous execution
- [x] Joker sell execution through the first-party bridge with authoritative roster reconciliation
- [x] Joker replacement execution through `SELL -> fresh observation/replan -> BUY`
- [x] Cooperative safe agent deactivation request before the next gameplay action
- [x] Native lost-run restart through Balatro's own setup path with authoritative same-deck/stake `BLIND_SELECT` verification
- [x] Bridge timeout cleanup cancels only the exact still-pending command; already-consumed outcomes remain fail-closed/indeterminate
- [x] Bridge v2 command pump services traffic before Balatro update and from the outer LÖVE run loop
- [x] Compatible bridge protocol normalization keeps implementation revision separate from wire compatibility
- [x] First-party blind skip/tag execution through Balatro's native skip callback

**Remaining 0.9 coverage**

- [x] Robust held-consumable use for all supported target patterns
- [x] Robust pack-effect targeting for Tarot/Spectral/Standard modifier flows
- [ ] First-party Joker reordering with authoritative Joker-order reconciliation
- [ ] Emergency hard stop for a hung/unsafe supervisor
- [ ] Validate an actual normal Steam achievement/unlock from agent gameplay

### 0.9C — Shared mechanics and blind-planning foundation

> This section tracks reusable Balatro mechanics and the existing D1 planning foundation. Final strategic tuning is intentionally deferred to `v1.0.0`.

**Implemented**

- [x] Exact deterministic visible-hand scoring
- [x] Immediate-clear and projected blind-total calculations
- [x] Guaranteed/expected/upside score-outcome representation
- [x] Lucky stochastic separation
- [x] Side-effect-free Joker score projection architecture
- [x] Validated Ice Cream and Bootstraps projections
- [x] Validate hydrated Green Joker and Runner transitions on isolated hypothetical branches
- [x] Runtime Joker projection fidelity audit: every mutable hydrated Joker is explicitly classified
- [x] Fail closed on unsupported event/stochastic semantics rather than claim an exact projection
- [x] Expand deterministic hydrated runtime support to 33/33 mutable hydrated Jokers
- [x] Resolve and admit all previously deferred mutable hydrated Jokers/effects (`33 SUPPORTED / 0 DEFERRED / 0 GAP / 0 ERROR`)
- [x] Boss-blind legality foundation
- [x] The Psychic / The Head / The House planner paths validated during live development
- [x] Public remaining-deck composition model without future draw order
- [x] Probabilistic draw/discard outcomes
- [x] Bounded multi-action adaptive blind-clear search
- [x] Search node budgets and guarded one-action execution
- [x] Consensus setup-discard policy
- [x] Replan after each real action checkpoint
- [x] Initial The Sun escape planning
- [x] Persistent D1 execution validated across repeated real Play/Discard checkpoints
- [x] Live autonomous D1 sequence demonstrated through natural `GAME_OVER`

**Remaining mechanics coverage**

- [ ] Extend score projection to relevant remaining stateless Jokers/effects separately from hydration
- [ ] Generalize boss-blind integration
- [ ] Correct boss-blind **debuff/nullification scoring**: cards marked disabled/debuffed by the active boss must contribute zero chips/effects where Balatro rules suppress them, while still being allowed to participate structurally in a poker hand when legal
- [ ] Add regression coverage proving D1 does not value boss-disabled cards as ordinary scoring cards
- [ ] Integrate supported consumable actions into the normal blind planner where execution coverage requires it
- [ ] Replace temporary unsupported-Joker hard stops with complete supported mechanics

> **Moved to `v1.0.0` competence work:** stronger blind-clear path commitment, minimum-hands clearing, remaining-score/remaining-hands pace discipline, build-intent feedback, Joker-supported hand selection and final resource/economy tuning.

### 0.9D — Playbook cartridge and build-intelligence foundations

> There is one Balatro agent. Playbooks answer **how to play this deck/stake**; they do not redefine Balatro mechanics.
>
> **Naming:** `B` identifiers denote **build-intelligence** capabilities and `D` identifiers denote **decision layers**. Stable identifiers are retained where logs/tests already reference them; historical numbering gaps do not imply missing current architecture.

**Playbook system**

- [x] Define playbook interface
- [x] Playbook registry keyed by `(deck, stake)`
- [x] Auto-select playbook from live deck/stake at activation
- [x] Separate factual deck/stake mechanics from strategic playbook preferences
- [x] Playbook controls for risk tolerance
- [x] Playbook controls for planner/search budgets
- [x] Independent Joker acquisition/replacement thresholds
- [x] Playbook version identifier included in every run log
- [ ] Per-decision-layer threshold configuration
- [x] Independent hand-action thresholds
- [x] Independent voucher thresholds
- [ ] Independent consumable acquisition/use/target thresholds
- [ ] Independent booster/pack thresholds
- [ ] Independent reroll/shop-exit thresholds
- [ ] Independent blind skip/tag thresholds
- [ ] Build-intent/preferences supplied to relevant decision layers without duplicating mechanics
- [ ] Red Deck / White Stake first production threshold set

**Shared build intelligence already implemented**

- [x] **B1 Effect vocabulary:** compositional `produces` / `requires` / `amplifies` / `scales_with` / `transforms` descriptors
- [x] **B1 Behavior-backed Joker inference:** probe actual `Joker.apply()` behavior on copied synthetic contexts
- [x] **B1 Behavior-backed consumable inference:** conservatively probe modeled `can_use()` / `use()` transformations
- [x] **B2 Public BuildProfile:** deck composition, hand levels, slots, owned Jokers, held consumables and realized feature strengths without card-order dependence
- [x] **B3 Contextual Joker synergy evaluator:** candidate marginal value against the current build with interaction gain separated from intrinsic gain
- [x] **B3 Multi-Joker interaction probing:** meaningful combinations/retriggers/copy effects rather than isolated Joker probes only
- [x] **B4 Consumable/deck synergy evaluator:** permanent rank/suit/enhancement/seal/edition changes against current/prospective engines
- [x] **B4 Build-path reasoning:** value enabling pieces before a combo is fully assembled where observable semantics support the relationship
- [x] **B5 Build-aware shop policy:** contextual build delta in Joker/consumable/voucher/booster comparisons
- [x] **B5 Joker replacement planning:** legal replacements against complete build and slot opportunity cost
- [x] **B5 Build-aware reroll policy:** missing engine pieces and current-shop opportunity quality
- [x] **B6 Build-aware consumable timing and targeting:** use/hold/target based on whole-build delta

**Open build-intelligence integration**

- [x] **B6 Build-aware pack choice:** visible pack offers evaluated as build transitions
- [x] **B7 Build intent feedback into D1:** hand/discard choices should actively exploit the build's supported hand/archetype
- [x] **B7 Build rationale logging:** record which synergies caused a purchase/use/target choice and how build intent changed

### 0.9E — Decision coverage inventory

> `v0.9.0` requires a safe autonomous path through each required decision family. The policies do **not** need to be optimal yet. Their final thresholds and strategic quality are a `v1.0.0` concern.

| Layer | Decision | Current 0.9 status |
|---|---|---|
| D1 | Play vs discard + subset | Foundation implemented/live exercised |
| D2 | Joker buy/keep/replace/sell | Foundation complete |
| D3 | Voucher acquisition | Foundation complete |
| D4 | Consumable ignore/buy/buy-and-use | Foundation complete |
| D5 | Held consumable use vs hold | Foundation complete, conservative scope |
| D6 | Consumable targeting | Deterministic targeting foundation complete |
| D7 | Planet choice/use timing | Foundation implemented/live validated; quality tuning deferred |
| D8 | Booster acquisition | Foundation complete |
| D9 | Pack choice vs Skip | Execution exists; cross-family valuation open |
| D10 | Pack follow-up targeting | Partial deterministic coverage; broader flows open |
| D11 | Reroll decision | Execution + policy foundation; EV model open |
| D12 | Shop arbiter | Foundation complete |
| D13 | Blind play vs skip/tag | Foundation complete |
| D14 | Run-level resource valuation | Foundation complete |

**Implemented decision-layer details**

<details>
<summary>D1–D8 and D12 completed foundations</summary>

- [x] D1 legal play/discard subset generation
- [x] D1 first-party live selection and Play/Discard execution
- [x] D1 probability/search foundation
- [x] D1 adaptive multi-horizon clear-path search with stronger sampled confirmation
- [x] D1 pace play/recovery fallback
- [x] D1 persistent fresh re-observation/replanning after every settled action
- [x] D1 live autonomous sequence demonstrated through natural `GAME_OVER`
- [x] D2 direct Joker Buy execution
- [x] D2 Joker value-probe foundation
- [x] D2 shared B1/B2 effect/build context foundation
- [x] D2 B3 contextual whole-build delta
- [x] D2 broader semantic valuation for non-scoring/economy Jokers, including requirement-aware conditional value
- [x] D2 replacement policy with whole-build delta, sell-credit economics and explicit HOLD baseline
- [x] D2 read-only live validator
- [x] D2 live recommendation/rationale validation at a real SHOP checkpoint
- [x] D2 standalone sell-only policy
- [x] D2 first-party Joker sell execution with authoritative live re-observation
- [x] D2 replacement execution through `SELL -> fresh observation/replan -> BUY`
- [x] D3 voucher observation and redeem execution
- [x] D3 initial voucher valuation foundation
- [x] D4 Buy execution
- [x] D4 Buy & Use execution foundation
- [x] D4 modeled Tarot/Planet/Spectral behavior foundation
- [x] D4 dedicated three-way acquisition policy using B4/B6 contextual build delta
- [x] D4 never infer Buy & Use merely because the button exists
- [x] D5 general held-consumable action generation
- [x] D5 timing policy independent of acquisition policy
- [x] D5 B6 build-aware use-versus-hold comparison
- [x] D5 live execution for non-targeted held consumables
- [x] D5 timing decisions integrated into blind/shop phases as appropriate
- [x] D6 effect-family target generators
- [x] D6 target scoring interface
- [x] D6 multi-card target selection
- [x] D6 B6 whole-build target delta
- [x] D6 live target execution and verification
- [x] D6 Tarot/Spectral pack follow-up targeting
- [x] D7 Planet representation and basic value estimation
- [x] D7 Planet effect represented in B1 vocabulary as hand-specific permanent scaling
- [x] D7 dedicated Planet selection policy
- [x] D7 immediate-use-versus-hold threshold
- [x] D7 live validation where immediate use wins and where observable hold value wins
- [x] D8 booster observation and two-click opening execution
- [x] D8 integrated `SHOP -> *_PACK` live validation
- [x] D8 BuildProfile-informed booster expected-value model
- [x] D8 buy-versus-save threshold
- [x] D8 deterministic boundary coverage across pack families, BuildProfile need and reserve pressure
- [x] D8 read-only live validator with candidates/thresholds/rationale
- [x] D8 armed live validator executes exactly one recommended booster purchase and stops before pack choice
- [x] D12 visible shop action generation
- [x] D12 initial purchase ranking foundation
- [x] D12 live-memory shop controller and unified dispatcher integration
- [x] D12 build-aware child-layer recommendations
- [x] D12 normalized child-layer recommendations around no-action baselines
- [x] D12 explicit `END_SHOP` baseline
- [x] D12 multi-action shop loop with fresh re-observation after each action

</details>

**Shared decision-layer completion contract**

- [ ] Dedicated policy/config threshold block exists
- [ ] Boundary tests exist
- [ ] Read-only live validator exposes recommendation and rationale
- [ ] Armed live validator executes the recommendation correctly
- [ ] Decision is logged independently
- [ ] Layer is enabled in the autonomous orchestrator only after the required coverage above is safe

**Remaining 0.9 decision coverage**

- [x] D3 dedicated voucher threshold policy independent of ordinary item-buy thresholds
- [x] D3 consume BuildProfile compatibility where vouchers change build capacity/resource engines
- [x] D3 validate buy-versus-save boundary cases
- [x] D9 read visible pack choices from live memory
- [x] D9 pack card/Joker selection and confirmation execution
- [x] D9 Pack Skip execution
- [x] D9 initial conservative pack-policy foundation
- [x] D9 complete valuation coverage across Joker/Standard/Planet/Tarot/Spectral packs using B3/B4/B6
- [ ] D9 validate recommendations across pack families
- [x] D10 follow-up target observation for remaining required flows
- [x] D10 effect-specific target policy for remaining required flows
- [x] D10 Build-aware target delta shared with D6 for remaining required flows
- [x] D10 first-party target execution for remaining required flows
- [ ] D10 end-to-end targeted Tarot/Spectral/Standard-pack validation

> **D9/D10 live-validation evidence procedure (authoritative):** run `py -m games.balatro.live.external.live_pack_validation_coverage` before searching for or creating any other D9/D10 coverage checker. The canonical implementation is `games/balatro/live/external/live_pack_validation_coverage.py`; it scans `logs/balatro/runs/*.jsonl` by default and counts only successful production transitions backed by complete before/after snapshots with `live_state_source == "process_memory"` and a later authoritative checkpoint. D10 additionally requires the logged semantic selection/target evidence enforced by that analyzer. Exit status `0` means all required D9 families and D10 flows are covered; exit status `1` means authentic evidence is still missing.
>
> **Do not infer live validation from tests or fixtures.** `tests/test_balatro_live_pack_validation_coverage.py` is regression coverage for the analyzer itself, including rejection of non-process-memory evidence; synthetic/unit rows never satisfy ROADMAP live-validation work. Update D9/D10 live-validation checkboxes only from authentic natural production run logs. Future iterations should use this module and its report first; do not spend time searching for or building a replacement unless the canonical module is intentionally removed or superseded.

- [x] D11 reroll execution
- [x] D11 B5 build-gap/opportunity model
- [x] D11 dedicated reroll threshold policy foundation
- [x] D11 reroll EV model
- [x] D13 Blind selection execution
- [x] **D13 first-party blind skip execution**
- [x] **D13 Tag valuation** — public Small/Big skip-tag identity is observed from live process memory and scored with conservative tag-specific utility
- [x] **D13 Play-versus-skip threshold**
- [x] D14 money/interest marginal-value model
- [x] D14 survival reserve model
- [x] D14 hand/discard resource value
- [x] D14 Joker/consumable slot shadow prices
- [x] D14 remaining-ante horizon value
- [x] D14 shared normalized utility scale for the shop arbiter

> D14 may begin conservatively for `v0.9.0`; strategic calibration is part of `v1.0.0`.

### 0.9F — Run logging, diagnostics and recovery

> Recording and learning remain separate. The live agent must produce enough evidence to explain failures without silently changing its own active strategy.

**Implemented**

- [x] Generic framework console logging/metrics foundation
- [x] Append-only Balatro per-run JSONL experience logger
- [x] Run identity includes deck/stake/playbook/playbook version
- [x] Resume event sequencing across guarded one-action invocations using explicit persistent `run_id`
- [x] Successful guarded execution logging while preview/blocked/failed steps remain transition-log-free
- [x] Sanitized public observation logged before decisions
- [x] Resumable logging, UI sanitization and terminal-summary regression suite
- [x] Successful-transition logging in persistent supervisor with distinct run log per attempt
- [x] Terminal `GAME_OVER` win/loss from authoritative public `won` plus per-run summary JSON
- [x] Session summary spanning repeated supervisor attempts
- [x] Repository-local paste-ready crash reports under `logs/balatro/crash-reports/`
- [x] Automatic supervisor traceback/crash-report capture on unhandled failure
- [x] Supervisor failure preserves active attempt/run metadata for postmortem
- [x] Crash report includes supervisor status, Balatro process state, live snapshot where available, bridge files, current attempt tail, agent log, exception and Windows application events
- [x] Read-only live agent monitor terminal showing supervisor/Balatro process state, session/attempt/run identity, current phase/resources, last action and last logged decision rationale
- [x] Agent toggle automatically opens the live monitor in a separate Windows console; closing the monitor does not stop the supervisor
- [x] Structured build profile, detected synergy and build-intent change events in successful run logs
- [x] Selected-decision `build_rationale` records the actual policy-supplied build/synergy/intent signals without recomputing strategy in the logger

**Remaining**

- [ ] Log full decision-layer candidate scores and thresholds in addition to chosen rationale
- [ ] Log execution failures as a dedicated diagnostic stream without corrupting successful experience transitions
- [ ] Log purchases, sells, consumable uses and blind outcomes as dedicated semantic events
- [ ] Build replay/analysis utility over stored runs
- [ ] Aggregate per-playbook and per-decision-layer statistics across runs
- [ ] Identify repeated failure patterns and weak thresholds from logs
- [ ] Add controlled offline playbook tuning/learning only after log quality is validated
- [ ] Keep automatic online self-modification out of the critical live loop unless later evidence justifies it

### 0.9G — Single-command autonomous supervisor and release validation

**Implemented**

- [x] One toggle command for an already-started supported run (`BalatroAgentToggle.bat`)
- [x] Detached supervisor PID/status control plane with duplicate-start protection
- [x] Cooperative OFF request before another gameplay action
- [x] Attach to current Balatro process automatically
- [x] Detect current deck/stake and load playbook automatically for every attempt
- [x] Unified semantic live-action dispatcher foundation
- [x] Persistent observer/bridge session with fresh decision after every settled checkpoint
- [x] Bounded stale-state replanning without consuming gameplay-step budget
- [x] Unbounded `max_steps=None` per-attempt loop
- [x] Multi-step autonomous execution validated from SHOP through normal gameplay to natural loss
- [x] Natural `GAME_OVER` after a played hand is a clean terminal checkpoint
- [x] Attempt-scoped run IDs/logs and session summary foundation
- [x] Deterministic loss -> fresh attempt -> win lifecycle through injectable restart strategy
- [x] Deterministic automatic OFF after target run wins
- [x] First-party `GAME_OVER -> fresh unseeded same deck/stake run` execution live-validated on Red/White
- [x] Production restart wired to the persistent supervisor
- [x] Production supervisor uses native readiness-aware observation and global quiescence gating before subsequent commands

**Remaining release validation**

- [ ] Live-validate repeated production **loss -> native restart -> fresh attempt continuation** across multiple attempts
- [ ] Live-validate manual toggle OFF during an active run
- [ ] Route every required phase/subflow to its production decision layer rather than a temporary unsupported/conservative gap
- [ ] Full blind select -> hand play -> round eval -> shop -> pack/consumable subflows -> next blind coverage without manual gameplay input
- [ ] Continue automatically through complete attempts with no arbitrary gameplay-step cap
- [ ] Clean shutdown and complete production run/session log
- [x] Complete current reliability soak protocol: 3 consecutive clean complete attempts, or 10 attempts / 2 hours, without crash/UI corruption/premature injection
- [ ] If a real win occurs during 0.9 validation, live-confirm automatic OFF and successful terminal logging; otherwise carry this live check into `v1.0.0`

### Legacy/fallback observation and input

The existing `save.jkr`, visual observer and OS-input work remains useful for diagnostics and recovery, but it is no longer the production source of truth or production action backend.

- [x] Vanilla `save.jkr` discovery/parser
- [x] Save-backed phase/hand/Joker/consumable/shop extraction
- [x] Screen capture and visual phase/card-location infrastructure
- [x] Normal OS mouse-input diagnostics
- [x] Keep these paths isolated as fallback/debug tools
- [x] Production autonomous path has no silent mouse fallback
- [ ] Remove live-control dependence on save-persistence timing from any remaining legacy utilities
- [ ] Remove stale-save reconciliation from the normal autonomous loop

## v1.0.0 — Red Deck — White Stake

> **First competence/win milestone.** `v0.9.0` proves the production agent can safely operate and cover the real run flow. `v1.0.0` proves it can make coherent strategic decisions well enough to deliberately complete one normal unseeded Red Deck / White Stake run without manual gameplay help after activation.
>
> The optimization phase begins **after 0.9 integration is stable**. A lucky clear is useful, but the objective is not to brute-force attempts until RNG produces a win; it is to correct repeatable strategic failure modes and then earn the clear.
>
> **Observed baseline:** an exploratory Red Deck / White Stake soak was stopped after **10 autonomous attempts with no win**. Treat this as competence evidence, not a failure of the 0.9 integration milestone; the repeated strategic weaknesses below are now explicit 1.0 work.

### 1.0A — Blind-clear objective and hand efficiency

- [ ] Make **probability of clearing the current blind** the dominant D1 objective
- [ ] Engineer and preserve a concrete clear path across remaining hands/discards instead of repeatedly choosing locally acceptable hands
- [ ] Enforce a strong pace floor based on `remaining_required_score / remaining_hands`
- [ ] Among sufficiently safe clear lines, prefer the line that clears in the **fewest hands**
- [ ] Value unused hands as end-of-round economy; avoid spending extra hands after a safe earlier clear is available
- [ ] Do not trade away meaningful clear probability merely to save one hand
- [ ] Use durable D1 run records to postmortem fragile/incorrect play/discard choices
- [ ] Tune recovery/discard behavior around survival probability and the active clear path
- [ ] Treat **held-in-hand value** as an explicit opportunity cost: avoid playing cards whose important payoff comes from remaining in hand (for example Steel/Blue Seal effects) unless the clear path or a stronger tactical benefit justifies spending them
- [ ] Add regression cases for held-value cards so D1 distinguishes "good to hold" from "good to play"
- [ ] Validate D1 with build-intent feedback across a complete run

### 1.0B — Build identity and Joker-supported play

- [ ] Integrate B3–B7 build intelligence into all relevant decision layers
- [ ] Maintain a persistent public **build/archetype intent** derived from owned Jokers, deck composition, hand levels and consumables
- [ ] Feed B7 build intent into D1 so hand/discard choices actively exploit the hands/ranks/suits/retriggers the Joker engine supports
- [ ] Make Joker acquisition, replacement, hand selection, discard strategy, Planet choice and pack choice reinforce the same build rather than acting as mostly independent local policies
- [ ] Strengthen contextual Joker/consumable/deck synergy beyond isolated item quality
- [ ] Add explicit **anti-synergy/conflict modeling** for effects that demand mutually incompatible play patterns; conflict must reduce whole-build value even when both Jokers are individually useful
- [ ] Allow incompatible Jokers to coexist temporarily when selling/replacing immediately would reduce survival or economy, but identify the preferred build direction and phase out the weaker conflicting Joker as soon as a superior coherent configuration is available
- [ ] Make D2 replacement/sale compare **build coherence and future play constraints**, not only each Joker's isolated marginal score/economy value
- [ ] Add a concrete regression for **Ride the Bus + Business Card**: Business Card rewards scoring face cards, while Ride the Bus requires avoiding scoring face cards to scale; the agent must recognize the conflict, choose a build direction from current run evidence, and eventually remove the losing side of the conflict
- [ ] Model **Negative-edition Jokers** as unusually valuable because they do not consume normal Joker capacity; when reserve/survival constraints are satisfied, affordable Negative Jokers with positive marginal value should receive explicit acquisition priority rather than being treated like ordinary slot-consuming Jokers
- [ ] Add D2 regression coverage for spare-cash + open-economy cases where buying a useful Negative Joker dominates holding cash
- [ ] Log build-intent changes, detected anti-synergies and the interactions that caused purchase/replacement/sale decisions

### 1.0C — Planet and consumable competence

- [ ] Rework Planet choice around expected future hand frequency, marginal level-up score gain, build synergy and hand feasibility
- [ ] Heavily penalize low-feasibility Planet upgrades unless the current deck/build demonstrably supports that hand
- [ ] Add regression coverage preventing an uncommitted early Red/White build from preferring **Neptune / Straight Flush** merely because it is a permanent upgrade
- [ ] Ensure useful purchased/held Planets are actually consumed when immediate permanent value exceeds observable hold-specific utility
- [ ] Preserve intentional Planet holds only for explicit observable value such as duplication/holding synergy or slot-related considerations
- [ ] Ensure D4 acquisition and D7 use-timing agree so money is not spent on a Planet that the agent then pointlessly leaves unused
- [ ] Finalize held-consumable timing/target thresholds and broaden supported deterministic target flows as required

### 1.0D — Pack, shop and economy competence

- [ ] B6 build-aware pack choice across Joker/Standard/Planet/Tarot/Spectral offers
- [ ] D9 Pack choice/Skip threshold tuned to build value rather than generic item value
- [ ] D10 pack target-selection threshold and end-to-end targeted flows
- [ ] D3 Voucher threshold with build/economy compatibility
- [ ] Make voucher valuation explicitly **run-wide/persistent** so high-impact vouchers are not ignored merely because their immediate score delta is small
- [ ] Add voucher buy-versus-save regression cases for affordable high-impact vouchers with sufficient reserve
- [ ] D8 Booster acquisition threshold
- [ ] D11 Reroll EV threshold
- [ ] D12 Shop arbiter final calibration
- [ ] D14 money/interest marginal value, survival reserve, hand/discard value, slot shadow prices and remaining-ante horizon value
- [ ] Implement Balatro **interest breakpoint** awareness from the current run rules, including voucher-modified thresholds/caps where observable, so purchases/rerolls account for the next dollar of interest lost or preserved
- [ ] Make shop spending compare purchase EV against both cash reserve and foregone interest, not cash price alone
- [ ] Add an optional **undiscovered-item acquisition bias**: when public profile/collection state marks a visible shop item as undiscovered and survival/reserve constraints are already satisfied, grant bounded utility for buying it; discovery priority must never override run survival, build coherence or critical economy
- [ ] Preserve enough economy to strengthen later shops without sacrificing immediate run survival

### 1.0E — Blind skip/tag strategy

- [ ] First-party D13 blind-skip execution must already be covered by 0.9 integration
- [ ] Value tag expected value against blind reward money, lost shop/economy opportunity, current build strength and boss preparation
- [ ] Add dedicated play-versus-skip threshold
- [ ] Make skip decisions build/ante aware rather than always fighting every blind
- [ ] Validate skip/tag decisions through real-run examples

### 1.0F — Red/White production threshold set and win gate

- [ ] Red / White per-decision threshold set
- [ ] D1 Hand action threshold
- [ ] D2 Joker acquisition/replacement/sale threshold
- [ ] D3 Voucher threshold
- [ ] D4 Consumable Buy-vs-Buy-&-Use threshold
- [ ] D5 Held consumable timing threshold
- [ ] D6 Consumable target-selection threshold
- [ ] D7 Planet choice/use-timing threshold
- [ ] D8 Booster acquisition threshold
- [ ] D9 Pack choice/Skip threshold
- [ ] D10 Pack target-selection threshold
- [ ] D11 Reroll threshold
- [ ] D12 Shop arbiter
- [ ] D13 Blind skip/tag threshold
- [ ] D14 Run-level resource valuation
- [ ] Live-confirm automatic OFF after a real successful run
- [ ] Preserve normal Steam profile progression/unlocks
- [ ] Produce a complete replayable run-experience log with per-layer and build-synergy rationales
- [ ] **Complete one successful unseeded Red Deck / White Stake run**

> **Higher-stake scope rule:** from `v1.1.0` onward, implement new stake-specific mechanics, constraints and threshold adaptations only when that stake becomes the current milestone. Do not prebuild later-stake procedures during White Stake development unless they are already required by the base autonomous stack.

## v1.1.0 — Red Deck — Red Stake

- [ ] Red / Red threshold cartridge
- [ ] Adapt affected decision thresholds to Red Stake
- [ ] Complete one successful run

## v1.2.0 — Red Deck — Green Stake

- [ ] Red / Green threshold cartridge
- [ ] Adapt affected decision thresholds to Green Stake
- [ ] Complete one successful run

## v1.3.0 — Red Deck — Black Stake

- [ ] Red / Black threshold cartridge
- [ ] Eternal Joker strategy in D2/D12
- [ ] Complete one successful run

## v1.4.0 — Red Deck — Blue Stake

- [ ] Red / Blue threshold cartridge
- [ ] Reduced-discard strategy in D1/D14
- [ ] Complete one successful run

## v1.5.0 — Red Deck — Purple Stake

- [ ] Red / Purple threshold cartridge
- [ ] Higher-score-requirement strategy in D1/D13/D14
- [ ] Complete one successful run

## v1.6.0 — Red Deck — Orange Stake

- [ ] Red / Orange threshold cartridge
- [ ] Perishable Joker strategy in D2/D12
- [ ] Complete one successful run

## v1.7.0 — Red Deck — Gold Stake

- [ ] Red / Gold threshold cartridge
- [ ] Rental Joker strategy in D2/D12/D14
- [ ] Complete one successful run
- [ ] Validate Red Deck across all stakes

## v2.0.0 — Blue Deck — White Stake

> Begins after Red Deck Gold Stake. The permanent agent is unchanged; Blue Deck progression adds Blue-specific playbook threshold cartridges.

- [ ] Blue / White threshold cartridge
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

`v0.9.0` is complete when the permanent agent, after one activation and with no manual gameplay input, can autonomously cover the required real-run phases/actions through the production bridge, wait for authoritative native/state quiescence after each action, re-observe/replan, continue through complete attempts, and terminate/restart safely without UI corruption or premature injection. A win is not required for the `v0.9.0` autonomy milestone.

From `v1.0.0` onward, a deck/stake milestone is complete only when the permanent agent, using the matching threshold cartridge and no manual gameplay input after activation, **successfully completes** one full unseeded run while producing the required authoritative experience log. High win rate and optimal play remain future optimization goals, not milestone gates.