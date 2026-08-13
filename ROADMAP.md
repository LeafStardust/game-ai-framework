# Roadmap

> The roadmap is milestone-based. General game-AI infrastructure stays reusable; game-specific mechanics, planning and playbooks live in game adapters and agents.
>
> For Balatro there is **one permanent agent and one permanent mechanics/state/execution stack**. Deck/stake strategy is supplied by a replaceable **playbook cartridge** selected automatically from the live run. A new deck begins only after the previous deck has completed every stake through Gold.
>
> **Release scope is intentionally progressive.** `v0.9.0` is the autonomous decision-coverage milestone: every reachable run juncture must have a real decision path, execution path and authoritative re-observation path so the agent can continue by itself to a terminal win/loss state. `v1.0.0` is the first competence milestone: the same permanent agent must actually win one unseeded Red Deck / White Stake run with no manual gameplay help after activation. Later stake releases add stake-specific procedures only when that stake becomes current rather than prebuilding future-stake logic early.
>
> Production Balatro integration should require no third-party bot/mod runtime if technically possible. External repositories may be studied for Balatro internals, but production code should live in this repository. The preferred observer is our own zero-dependency, read-only Windows process-memory reader. `save.jkr` is fallback/debug state only, not live truth.
>
> Agent-facing observation must exclude hidden future information: no RNG state/seed exploitation and no ordered future draw pile. Current live objects and public deck composition are allowed.
>
> **Decision intelligence and execution are tracked separately.** Being able to execute an action does not mean the agent knows when that action is correct. Every strategically distinct choice is developed as its own decision-threshold layer with independent inputs, thresholds, rationale, tests and validation. For `v0.9.0`, a conservative or suboptimal decision procedure is acceptable if it covers the juncture autonomously; strategic quality sufficient to win Red/White is the `v1.0.0` gate.
>
> **Roadmap maintenance rule:** when implementation, deterministic tests or live validation clears a milestone, update this roadmap in the same development checkpoint instead of deferring documentation cleanup.
>
> **Current strategic priority: B6 + D6/D7 build-aware consumable targeting and Planet decisions.** D4 consumable acquisition is complete, and the D5 autonomy foundation now routes held-consumable USE/HOLD timing through the autonomous blind path plus explicitly validated shop-safe no-target uses. The remaining B6 work is complete target-family choice/verification in D6 and dedicated Planet selection/use-versus-hold strategy in D7; targeted shop/pack effects remain fail-closed until those layers clear their own contracts.

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

> **Completion gate:** after one activation on an already-started supported run, every reachable decision juncture has an autonomous decision procedure and executable semantic action path. The agent repeatedly observes, decides, executes, verifies and replans until a terminal **win or loss** without manual gameplay input. Winning is not required for `v0.9.0`; successful Red Deck / White Stake completion is the `v1.0.0` gate.
>
> Target user flow: start normal Steam Balatro, enter any supported deck/stake run manually, then activate the agent once. The agent reads the **current running game**, detects deck/stake, loads the matching playbook, chooses and executes one action through the repository-owned in-process bridge, observes the resulting live state, verifies it, and repeats until win/loss.
>
> Target loop:
>
> `live Balatro state -> translate -> build profile -> select playbook -> decision layer -> execute -> live Balatro state -> verify -> log -> replan`

### 0.9A — Authoritative live-state observation

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
- [x] Add semantic stability checks and bounded stale-state replanning
- [ ] Validate state freshness across remaining rapid events such as targeted consumable resolution and Joker creation/destruction
- [ ] Validate observation across every remaining required run phase/effect family

> If a stable read-only memory decoder proves infeasible across a future normal Balatro build, the fallback architecture remains repository-owned. Third-party bot/mod repositories are not production dependencies.

### 0.9B — First-party in-process control

> Production execution uses the repository-owned action bridge injected into Balatro's fused LÖVE archive. It invokes Balatro's normal internal callbacks and lets the game perform ordinary scoring, animations, Joker triggers, draws, resource changes, progression and achievement logic. The process-memory observer remains read-only and independently verifies each resulting semantic checkpoint. Mouse tooling is diagnostic/experimental only and must never be a silent production fallback.

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
- [ ] Robust held-consumable use for all supported target patterns
- [ ] Robust pack-effect targeting for Tarot/Spectral/Standard modifier flows
- [ ] Blind skip/tag execution in the first-party production bridge
- [ ] Emergency stop / safe agent deactivation
- [ ] Validate an actual normal Steam achievement/unlock from agent gameplay

### 0.9C — Shared mechanics and blind planning — MUTABLE-JOKER RUNTIME GATE CLEARED

> Mechanics do not change when a playbook cartridge changes. The shared engine owns Balatro rules; a playbook only changes strategic preferences and planning parameters. Mutable live-state hydration and runtime projection support are separate contracts. Both contracts are complete for the 33 mutable hydrated Jokers; unsupported stateless/event semantics remain conservative and fail closed until separately validated.

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
- [x] Resolve and admit all previously deferred mutable hydrated Jokers/effects (`33 SUPPORTED / 0 DEFERRED / 0 GAP / 0 ERROR`)
- [ ] Extend score projection to relevant remaining stateless Jokers/effects separately from hydration
- [ ] Generalize boss-blind integration
- [ ] Integrate consumable actions into the normal blind planner after build-aware consumable strategy exists
- [ ] Resource-aware blind objective: clear probability first, then preserve hands/discards/economy
- [ ] Blind skip/tag valuation
- [ ] Replace temporary unsupported-Joker hard stops with complete supported mechanics

### 0.9D — Playbook cartridge system

> There is one Balatro agent. The cartridge answers **how to play this deck/stake**, not **how Balatro works**. Each decision layer owns a separate threshold block so changing, for example, voucher appetite cannot silently alter discard behavior.

- [x] Define playbook interface
- [x] Playbook registry keyed by `(deck, stake)`
- [x] Auto-select playbook from live deck/stake at activation
- [x] Separate factual deck/stake mechanics from strategic playbook preferences
- [x] Playbook controls for risk tolerance
- [x] Playbook controls for planner/search budgets
- [ ] Per-decision-layer threshold configuration
- [ ] Independent hand-action thresholds
- [x] Independent Joker acquisition/replacement thresholds
- [ ] Independent voucher thresholds
- [ ] Independent consumable acquisition/use/target thresholds
- [ ] Independent booster/pack thresholds
- [ ] Independent reroll/shop-exit thresholds
- [ ] Independent blind skip/tag thresholds
- [ ] Build-intent/preferences supplied to relevant decision layers without duplicating mechanics
- [ ] Red Deck / White Stake first production threshold set
- [x] Playbook version identifier included in every run log

### 0.9E — Run experience logging and later learning

> **Recording and learning are separate.** Every run should produce a durable experience log now. The agent must not silently rewrite its active playbook during a run. Controlled offline analysis/adaptation can be added once enough trustworthy runs exist.

- [x] Generic framework console logging/metrics foundation
- [x] Append-only Balatro per-run JSONL experience logger
- [x] Run identity includes deck/stake/playbook/playbook version
- [ ] Integrate run logger into the autonomous live loop
- [ ] Log sanitized observation before decisions
- [ ] Log build profile, detected synergies and build-intent changes
- [ ] Log decision-layer name, candidate scores, thresholds and chosen rationale
- [ ] Log execution success/failure and authoritative post-action state
- [ ] Log purchases, sells, consumable uses and blind outcomes
- [ ] Log terminal win/loss and final run summary
- [ ] Build replay/analysis utility over stored runs
- [ ] Aggregate per-playbook and per-decision-layer statistics across runs
- [ ] Identify repeated failure patterns and weak thresholds from logs
- [ ] Add controlled offline playbook tuning/learning only after log quality is validated
- [ ] Keep automatic online self-modification out of the critical live loop unless later evidence justifies it

### 0.9F — Decision-threshold stack and run-level intelligence — ACTIVE STRATEGIC STACK

> Strategic decisions are developed **one layer at a time**. A layer is not complete merely because the corresponding action works. Each layer must define its own public-state inputs, legal candidate actions, threshold/config block, scoring or comparison rule, explicit abstain/hold option where legal, rationale output, deterministic tests, read-only live validation and armed live validation before it is enabled in the autonomous loop.
>
> Cross-layer state such as money, remaining hands/discards, ante, blind risk, slots and owned effects may be shared as **inputs**, but one layer's threshold constants must not be reused implicitly by another layer. The final shop/run arbiter compares normalized outputs from completed child layers instead of hiding all decisions inside one utility score.
>
> **The mutable-Joker 0.9C runtime projection correctness gate, D2 Joker lifecycle checkpoint, B5 + D12 shop-integration checkpoint, D4 consumable-acquisition checkpoint, and D5 held-consumable autonomy foundation are cleared.** B1–B4 contextual build intelligence reaches D2 and D4; B5 exposes contextual shop value and build-gap reroll context; D12 compares admitted child actions against an explicit `END_SHOP` baseline and relies on fresh authoritative re-observation after each executed shop action. D5 now arbitrates held USE/HOLD before D1 during blinds and before D12 during SHOP for explicitly validated no-target effects. The next strategic work is D6 target completeness and D7 Planet selection/timing.

#### B1–B7 — Shared build intelligence and synergy strategy — ACTIVE STRATEGIC PRIORITY

**Question:** What is the current run good at, what compatible engines can it deliberately build toward, and how much does each candidate item/action improve the whole build rather than itself in isolation?

Design rules:

- existing modeled Joker implementations are executable semantic sources, not discarded data-entry work
- existing Tarot/Planet/Spectral implementations are executable semantic sources where their behavior is modeled
- prefer behavior probing on deep-copied/synthetic state over a giant duplicate static tier list
- allow explicit semantic metadata only where behavior alone cannot expose a long-horizon relationship cleanly
- unknown/unmodeled effects remain conservative and visible rather than receiving invented synergy
- public state only: deck composition is allowed; hidden draw order, future RNG and seed exploitation are forbidden
- distinguish **realized build features** from **prospective transformations** a held/shop/pack consumable could create
- make the same build model reusable by Joker purchase/replacement, consumables, packs, rerolls and eventually D1

Milestones:

- [x] **B1 Effect vocabulary:** compositional `produces` / `requires` / `amplifies` / `scales_with` / `transforms` descriptors
- [x] **B1 Behavior-backed Joker inference:** probe the actual `Joker.apply()` implementation on copied synthetic contexts
- [x] **B1 Behavior-backed consumable inference:** probe modeled `can_use()` / `use()` transformations conservatively
- [x] **B2 Public BuildProfile:** aggregate deck composition, hand levels, slots, owned Jokers, held consumables and realized feature strengths without card-order dependence
- [x] **B3 Contextual Joker synergy evaluator:** compare candidate marginal value against the current build and expose interaction gain separately from intrinsic gain
- [x] **B3 Multi-Joker interaction probing:** measure meaningful combinations/retriggers/copy effects rather than only isolated Joker probes
- [x] **B4 Consumable/deck synergy evaluator:** value permanent rank/suit/enhancement/seal/edition changes against current and prospective engines
- [x] **B4 Build-path reasoning:** value enabling pieces before a combo is fully assembled when the relationship is supported by observable semantics
- [x] **B5 Build-aware shop policy:** feed contextual build delta into Joker/consumable/voucher/booster comparisons
- [x] **B5 Joker replacement planning:** compare every legal replacement against the complete current build and slot opportunity cost
- [x] **B5 Build-aware reroll policy:** value missing engine pieces and current-shop opportunity quality
- [ ] **B6 Build-aware consumable timing and targeting:** use/hold/target based on whole-build delta rather than generic card value
- [ ] **B6 Build-aware pack choice:** evaluate visible offers as candidate build transitions
- [ ] **B7 Build intent feedback into D1:** hand/discard choices should respect engines such as held-card, rank, suit, retrigger and hand-level strategies
- [ ] **B7 Build rationale logging:** record which synergies caused a purchase/use/target decision and how build intent changed

#### Decision-layer contract

For every decision layer:

- [ ] Define semantic question and legal outputs
- [ ] Define required observable/public inputs
- [ ] Define a dedicated threshold/config dataclass or playbook block
- [ ] Define scoring/comparison rule and confidence/rationale output
- [ ] Define explicit `HOLD`, `SKIP`, `END_SHOP` or equivalent no-action alternative where legal
- [ ] Unit-test boundary cases around every important threshold
- [ ] Read-only live validator prints candidates, scores, thresholds and recommendation
- [ ] Armed live validator executes exactly the recommended semantic action
- [ ] Log enough data to explain and tune the layer independently later

#### D1 — Hand action: play vs discard and card subset — FOUNDATION VALIDATED; QUALITY TUNING DEFERRED

**Question:** Given the current hand, should the agent play or discard, and exactly which cards?

Threshold/signals owned by this layer:

- minimum blind-clear probability before preferring a play
- expected score and score-margin requirement
- discard improvement EV
- hand/discard reserve value
- remaining hands/discards and blind progress
- overkill/resource-preservation penalty
- Joker/card-effect consequences of the selected subset
- build intent once B7 is available

Status:

- [x] Legal play/discard subset generation
- [x] First-party live selection and Play/Discard execution
- [x] Probability/search foundation
- [x] Adaptive multi-horizon clear-path search with stronger sampled confirmation
- [x] Pace play/recovery fallback
- [x] Persistent fresh re-observation/replanning after every settled action
- [x] Live autonomous sequence demonstrated through natural `GAME_OVER`
- [ ] Feed B7 build intent into D1 before final quality lock
- [ ] Further resource/recovery tuning after build intelligence is operational unless a blocker appears

#### D2 — Joker acquisition, replacement and sale — COMPLETE

**Question:** Should the agent buy this Joker, keep current Jokers, replace one, or sell one?

Threshold/signals owned by this layer:

- marginal scoring gain
- economy/resource gain
- synergy with current deck/Jokers/consumables
- scaling potential and remaining antes
- Joker-slot pressure
- replacement delta versus weakest owned Joker
- sell value and replacement cost
- Eternal/Perishable/Rental consequences when relevant

Status:

- [x] Direct Joker Buy execution
- [x] Joker value-probe foundation
- [x] Shared B1/B2 effect/build context foundation
- [x] Replace isolated intrinsic valuation with B3 contextual whole-build delta
- [x] Broader semantic valuation for non-scoring/economy Jokers, including requirement-aware conditional value
- [x] Replacement policy with whole-build delta, sell-credit economics and explicit HOLD baseline
- [x] Read-only live D2 validator implementation
- [x] Live-validate D2 recommendation/rationale against a real SHOP checkpoint
- [x] Standalone sell-only policy when selling without an immediate replacement is strategically justified
- [x] First-party Joker sell execution with authoritative live re-observation
- [x] Joker replacement execution through `SELL -> fresh observation/replan -> BUY`

#### D3 — Voucher acquisition

**Question:** Is this persistent voucher worth buying now?

Threshold/signals owned by this layer:

- persistent run-wide expected value
- remaining antes/rounds over which the effect can pay back
- immediate money and interest loss
- reserve floor and survival risk
- prerequisite/upgrade-chain value
- deck/Joker strategy compatibility

Status:

- [x] Voucher observation and redeem execution
- [x] Initial voucher valuation foundation
- [ ] Dedicated voucher threshold policy independent of ordinary item-buy thresholds
- [ ] Consume BuildProfile compatibility where the voucher changes build capacity or resource engines
- [ ] Validate buy-versus-save boundary cases

#### D4 — Consumable acquisition mode: do not buy vs Buy vs Buy & Use — COMPLETE

**Question:** For a shop Tarot/Planet/Spectral card, should the agent ignore it, buy it for later, or buy and use it immediately?

Threshold/signals owned by this layer:

- immediate-use utility
- stored option value
- consumable-slot pressure
- current target quality/availability
- money/interest/reserve cost
- expected future target quality
- interactions that reward holding a specific consumable
- build transition enabled by the consumable

Status:

- [x] Buy execution
- [x] Buy & Use execution foundation
- [x] Modeled Tarot/Planet/Spectral behavior foundation
- [x] Dedicated three-way acquisition policy using B4/B6 contextual build delta
- [x] Never infer Buy & Use merely because the button exists

#### D5 — Held consumable timing: use now vs hold — AUTONOMY FOUNDATION COMPLETE

**Question:** Once a consumable is owned, when should it actually be used?

Threshold/signals owned by this layer:

- immediate effect value now
- expected option value of keeping it
- blind survival urgency
- consumable-slot pressure
- expected future shop/pack opportunities
- synergies that reward holding, copying or preserving a consumable
- whether delaying changes the quality of available targets

Status:

- [x] General held-consumable action generation
- [x] Timing policy independent of acquisition policy
- [x] B6 build-aware use-versus-hold comparison
- [x] Live execution for non-targeted held consumables
- [x] Integrate timing decisions into blind/shop phases as appropriate

> D5's autonomy foundation is intentionally conservative in SHOP: only validated no-hand-target held effects (currently The Hermit, Temperance, and The Wheel of Fortune) can preempt the shop arbiter. Targeted effects remain blind-only pending D6, and Planet-specific shop/timing policy remains D7. The shared decision-layer quality gate still owns configurable thresholds, dedicated live validators, and independent logging before final quality lock.

#### D6 — Consumable targeting

**Question:** If a consumable should be used, what card(s), Joker(s), hand type or other legal target should it affect?

Threshold/signals owned by this layer:

- immediate score delta
- permanent deck-quality delta
- synergy delta with current build
- target scarcity and future draw frequency
- destruction/duplication/opportunity cost
- legal target count and effect-specific constraints

Status:

- [ ] Effect-family target generators
- [ ] Target scoring interface
- [ ] Multi-card target selection
- [ ] B6 whole-build target delta
- [ ] Live target execution and verification
- [ ] Tarot/Spectral pack follow-up targeting

#### D7 — Planet choice and Planet use timing

**Question:** Which Planet is valuable, and should an owned Planet be consumed immediately or intentionally held?

> Default expectation is that a Planet's permanent hand-level upgrade favors immediate use, but the policy must still compare that against any **observable hold-specific utility**, consumable-slot considerations, copying/holding synergies and effects whose value depends on consumable history. "Planet cards are always used immediately" must be a learned/validated policy result, not a hardcoded assumption.

Threshold/signals owned by this layer:

- expected frequency/value of the upgraded poker hand
- level-up score gain
- current build's hand distribution
- hold-specific synergy value
- consumable-slot pressure
- last-used/history-dependent consumable interactions where observable

Status:

- [x] Planet representation and basic value estimation
- [x] Planet effect represented in B1 vocabulary as hand-specific permanent scaling
- [ ] Dedicated Planet selection policy
- [ ] Immediate-use-versus-hold threshold
- [ ] Live validation across at least one case where immediate use wins and one where holding has positive modeled value

#### D8 — Booster acquisition

**Question:** Should the agent spend money to open this booster pack at all?

Threshold/signals owned by this layer:

- expected opportunity value of pack type
- current deck/Joker/consumable needs
- money/interest/reserve loss
- slot availability
- probability that at least one offered choice exceeds Skip
- run stage and scaling needs

Status:

- [x] Booster observation and two-click opening execution
- [x] Integrated `SHOP -> *_PACK` live validation
- [ ] Booster expected-value model informed by current BuildProfile needs
- [ ] Buy-versus-save threshold

#### D9 — Pack choice: take which offer vs Skip

**Question:** After a pack is open, which visible offer should be taken, or should the pack be skipped?

Threshold/signals owned by this layer:

- marginal value of each visible choice
- slot/legal constraints
- immediate versus long-term value
- synergy with the current build
- Skip baseline/opportunity value
- whether the chosen item requires another unresolved target decision

Status:

- [x] Read visible pack choices from live memory
- [x] Pack card/Joker selection and confirmation execution
- [x] Pack Skip execution
- [x] Initial conservative pack-policy foundation
- [ ] Complete valuation across Joker/Standard/Planet/Tarot/Spectral packs using B3/B4/B6
- [ ] Validate recommendation quality across pack families

#### D10 — Pack effect targeting

**Question:** When the selected pack item requires a follow-up target, what should it be used on?

> This is intentionally separate from D9. "The Emperor is the best card in this pack" and "which card(s) should this Tarot affect?" are different decisions and must not share one hidden threshold.

Threshold/signals owned by this layer:

- effect-specific target utility
- permanent deck transformation value
- current blind impact
- future synergy
- target legality/count
- option value of declining/choosing a different pack item if no good target exists

Status:

- [ ] Follow-up target observation
- [ ] Effect-specific target policy
- [ ] Build-aware target delta shared with D6
- [ ] First-party target execution
- [ ] End-to-end targeted Tarot/Spectral/Standard-pack validation

#### D11 — Reroll decision

**Question:** Is another shop roll worth its cost compared with buying current offers or leaving?

Threshold/signals owned by this layer:

- expected value of unseen replacement offers
- reroll cost and next reroll cost
- money reserve and interest breakpoints
- current shop opportunity quality
- build urgency and missing pieces
- remaining shop opportunities before future blinds

Status:

- [x] Reroll execution
- [x] B5 build-gap/opportunity model
- [ ] Reroll EV model
- [x] Dedicated reroll threshold policy foundation

#### D12 — Shop arbiter: what to do next in the shop — AUTONOMY FOUNDATION COMPLETE

**Question:** Given the outputs of the completed child decision layers, should the agent buy a Joker, buy/redeem a voucher, acquire/use a consumable, buy a booster, reroll, or end the shop?

> The arbiter does **not** reimplement Joker, voucher, consumable or booster valuation. It compares their normalized recommendations while enforcing shared money/slot legality. Child layers that are still strategically provisional can be replaced as their dedicated D3–D11 policies mature without reopening the parent arbitration contract.

Threshold/signals owned by this layer:

- minimum action advantage over `END_SHOP`
- hard survival/economy reserve floor
- interest breakpoints
- maximum acceptable aggregate spend this shop
- normalized confidence from child layers

Status:

- [x] Visible shop action generation
- [x] Initial purchase ranking foundation
- [x] Live-memory shop controller and unified dispatcher integration
- [x] Replace isolated shop item scores with build-aware child-layer recommendations
- [x] Normalize child-layer recommendations around their no-action baselines
- [x] Make `END_SHOP` an explicit baseline against every action
- [x] Multi-action shop loop with fresh re-observation after each action

#### D13 — Blind selection and skip/tag decision

**Question:** Should the next blind be played or skipped for its tag/reward tradeoff?

Threshold/signals owned by this layer:

- blind clear probability
- blind reward money
- tag expected value
- lost shop/economy opportunity
- boss preparation value
- current deck strength and ante risk

Status:

- [x] Blind selection execution
- [ ] First-party blind skip execution
- [ ] Tag valuation
- [ ] Play-versus-skip threshold

#### D14 — Run-level resource arbitration

**Question:** How should money, hands, discards, slots and growth opportunities be valued consistently across otherwise independent decision layers?

> This layer provides shared **state valuations and constraints**, not one giant action selector. Child layers still own their own thresholds.

- [ ] Money/interest marginal-value model
- [ ] Survival reserve model
- [ ] Hand/discard resource value
- [ ] Joker/consumable slot shadow prices
- [ ] Remaining-ante horizon value
- [ ] Shared normalized utility scale for the shop arbiter

#### Required implementation order

The mutable-hydrated 0.9C Joker runtime projection correctness gate, D2 Joker lifecycle checkpoint, B5 + D12 shop-integration checkpoint, D4 consumable-acquisition checkpoint, and D5 held-consumable autonomy foundation are complete. B6 + D6/D7 is now the current active implementation step. Work remains deliberately narrow: clear one autonomy blocker, verify it, update this roadmap, then advance.

1. [x] **0.9C Joker runtime projection fidelity** — `33/33` mutable hydrated Jokers supported with `0 deferred / 0 gap / 0 error`; unsupported stateless/event semantics remain fail-closed until separately validated
2. [x] **D2 completion** — contextual scoring/economy/non-scoring valuation, standalone sell, first-party sell execution and fresh-replan replacement are complete
3. [x] **B5 + D12 Build-aware shop** — contextual buying, replacement, build-gap reroll opportunity quality, normalized arbitration, explicit `END_SHOP`, and fresh post-action re-observation are complete
4. [x] **D4 Consumable acquisition mode** — dedicated contextual `HOLD` / `BUY` / `BUY_AND_USE` policy with first-party Buy & Use execution and explicit immediate-use gating is complete
5. **B6 + D6/D7 — CURRENT** — D5 held-consumable autonomy foundation is cleared; complete target selection/verification and Planet decisions next
6. **B6 + D8/D9/D10** — booster/pack valuation and target follow-up
7. **D3 Voucher acquisition** — integrate capacity/economy/build compatibility
8. **D11 Reroll decision** — complete reroll EV and remaining-shop/horizon quality
9. **D13 Blind skip/tag decision**
10. **D14 Run-level resource arbitration and normalization**
11. **B7 + D1 final refinement** — feed build intent into hand/discard decisions, then lock final D1 quality
12. **0.9E + 0.9G final integration** — complete per-layer logging, remove temporary phase policies, and validate the unbounded autonomous run loop

Completion gate for each decision layer:

- [ ] Policy/config threshold block exists
- [ ] Boundary tests exist
- [ ] Read-only live validator exposes recommendation and rationale
- [ ] Armed live validator executes recommendation correctly
- [ ] Decision is logged independently
- [ ] Layer is enabled in the autonomous orchestrator only after all above are complete

### 0.9G — Single-command autonomous orchestrator

- [ ] One activation command for an already-started Balatro run
- [x] Attach to current Balatro process automatically
- [x] Read current deck/stake and load playbook automatically
- [x] Unified semantic live-action dispatcher foundation
- [x] Persistent observer/bridge session with a fresh decision after every settled checkpoint
- [x] Bounded stale-state replanning without consuming gameplay-step budget
- [x] Multi-step autonomous execution validated from SHOP across normal gameplay to a natural loss
- [x] Natural `GAME_OVER` after a played hand is a clean terminal checkpoint
- [ ] Route each phase to its completed decision layer rather than temporary conservative policies
- [ ] Full blind select -> hand play -> round eval -> shop -> every pack/consumable subflow -> next blind coverage without manual gameplay input
- [ ] Continue automatically across all antes until win/loss with no bounded test-step cap
- [ ] Detect and validate successful run terminal state as well as loss
- [ ] Clean shutdown and complete run log
- [ ] Validate a fresh unseeded Red Deck / White Stake autonomous run reaches terminal win/loss with no manual gameplay input

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

> **First competence/win milestone.** `v0.9.0` proves complete autonomous decision coverage and run continuation; `v1.0.0` proves those decisions are strategically competent enough to win. The permanent Balatro agent must activate against a normal unseeded Red Deck / White Stake run, automatically select the Red/White playbook, deliberately construct and exploit a viable build, and complete the run successfully without manual gameplay input after activation.

- [ ] B3–B7 build intelligence integrated into the relevant decision layers
- [ ] Contextual Joker/consumable/deck synergy is used instead of isolated item tiers
- [ ] Red / White per-decision threshold set
- [ ] D1 Hand action threshold validated with build-intent feedback across a complete run
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
- [ ] Complete one successful unseeded Red Deck / White Stake run
- [ ] Preserve normal Steam profile progression/unlocks
- [ ] Produce a complete replayable run-experience log with per-layer and build-synergy rationales

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

`v0.9.0` is complete when the permanent agent, after one activation and with no manual gameplay input, can autonomously make a decision at every reachable run juncture, execute through the production bridge, re-observe/replan after each settled action, and continue until a terminal win/loss state. A win is not required for the `v0.9.0` autonomy milestone.

From `v1.0.0` onward, a deck/stake milestone is complete only when the permanent agent, using the matching threshold cartridge and no manual gameplay input after activation, **successfully completes** one full unseeded run while producing the required authoritative experience log. High win rate and optimal play remain future optimization goals, not milestone gates.