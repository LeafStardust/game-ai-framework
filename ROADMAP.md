# Roadmap

> The roadmap is milestone-based. General game-AI infrastructure remains reusable; Balatro-specific mechanics, planning, execution and playbooks stay inside the Balatro adapter/agent stack.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. Deck/stake strategy is supplied by a replaceable **playbook cartridge** selected from the observed live run.
>
> `v0.9.0` is the **autonomous integration** milestone. It proves that the production agent can observe, decide, execute, verify, log and continue through the supported real-game flow without manual gameplay input. A win is not required. `v1.0.0` is the first **competence** milestone and requires one unseeded Red Deck / White Stake win with no manual gameplay help after activation.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. `save.jkr` is fallback/debug/recovery input only. Hidden future information is excluded: no RNG-state/seed exploitation and no ordered future draw pile.

## Status snapshot

| Milestone | Status | Remaining gate |
|---|---|---|
| v0.1–v0.8 | Complete | — |
| 0.9A Observation/readiness | Complete | — |
| 0.9B Execution/safety | Complete | — |
| 0.9C Mechanics/planning foundation | **Complete** | — |
| 0.9D Playbook/build foundation | Complete for 0.9 | Strategic calibration moves to 1.0 |
| 0.9E Decision coverage | In progress | D9/D10 production validation |
| 0.9F Logging/diagnostics | In progress | Release-required diagnostic completeness |
| 0.9G Release validation | In progress | Full autonomous production-flow validation |
| v1.0 Red/White competence | Not started | Begins after 0.9 release gate |

## v0.1.0–v0.8.0 — Completed foundations

- [x] Framework abstractions, configuration, logging, metrics and events
- [x] Agent architecture, decision pipeline and policy system
- [x] Evaluation/experiment infrastructure
- [x] Balatro cards, poker hands, scoring, Jokers, consumables, enhancements, editions and seals
- [x] Search/planning foundation, expected-value estimation and blind-clear path synthesis
- [x] Stake/deck architecture foundation and Red Deck support

## v0.9.0 — Autonomous Real-Game Integration

### 0.9A — Authoritative live observation and transition readiness — COMPLETE

- [x] Zero-dependency read-only Windows process-memory observation
- [x] Reliable live `G` discovery and LuaJIT decoding
- [x] Live cards/Jokers/consumables/shop/deck/stake extraction
- [x] `LiveBalatroSnapshot -> BalatroState` translation
- [x] Direct-memory observer is the production default
- [x] Public-state-only observation; no hidden future draw/RNG exploitation
- [x] Mutable Joker reconstruction contract: **34 HYDRATED / 116 STATELESS / 0 GAP / 0 ERROR**
- [x] Native phase readiness gates and post-pack settlement guards
- [x] Global quiescence barrier before newly changed checkpoints can drive commands
- [x] State-freshness/readiness validation across rapid effects and multi-attempt soak testing

### 0.9B — First-party in-process execution and safety — COMPLETE

- [x] Repository-owned fused-archive bridge with backup/restore path
- [x] Unified semantic injected action dispatcher
- [x] Play, discard, blind select, blind skip/tag and cash-out execution
- [x] Shop buy, voucher redeem, booster open, reroll and end-shop execution
- [x] Pack choice, pack skip and targeted pack-effect execution
- [x] Held-consumable use and targeting
- [x] Joker buy/sell/replacement/reordering
- [x] Authoritative post-action reconciliation
- [x] Safe cooperative OFF, emergency hard stop and timeout cleanup
- [x] Native loss -> fresh same-deck/stake restart
- [x] No silent mouse fallback in production

### 0.9C — Shared mechanics and blind-planning foundation — COMPLETE

Mechanics fidelity is closed for the 0.9 scope. Strategic tuning remains intentionally deferred to v1.0.

- [x] Exact deterministic visible-hand scoring
- [x] Guaranteed/expected/upside stochastic score outcomes without sampling hidden RNG
- [x] Exact branching where tractable; expected-value fallback permitted when exact branch expansion is disproportionately expensive
- [x] Side-effect-free hypothetical state/Joker projection
- [x] Public remaining-deck composition without future draw order
- [x] Probabilistic draw/discard outcomes and bounded multi-action blind-clear search
- [x] Re-observe/replan after every real settled action
- [x] Correct played-card, held-card, retrigger, destruction and generated-consumable ordering
- [x] **150/150 canonical Jokers validated**
- [x] Complete supported mutable Joker mechanics with no temporary unsupported-Joker hard stop remaining
- [x] Generalized Boss Blind scoring/state integration
- [x] Boss debuff/nullification semantics and D1 regression coverage
- [x] Chicot/Luchador and Boss Blind interaction semantics
- [x] All Boss Blind scoring/state mechanics covered by the current projection architecture

Known non-0.9C limitations:

- **Cerulean Bell:** deeper hypothetical forced-card choice is treated as inexact until authoritative re-observation; the production agent does not exploit unavailable future forced-choice information.
- **Verdant Leaf:** scoring/state semantics are modeled, but proactive `SELL_JOKER` during the blind is not executed because production Joker selling is currently SHOP-only.

These are execution/planning limitations, not open mechanics-fidelity gaps.

### 0.9D — Playbook cartridge and build-intelligence foundation — COMPLETE FOR 0.9

There is one Balatro agent. Playbooks specify deck/stake strategy; they do not redefine mechanics.

- [x] Playbook interface/registry keyed by deck and stake
- [x] Automatic live playbook selection
- [x] Risk/search-budget controls and independent foundational thresholds
- [x] B1 semantic effect vocabulary and behavior-backed Joker/consumable inference
- [x] B2 public `BuildProfile`
- [x] B3 contextual Joker synergy and multi-Joker interaction evaluation
- [x] B4 consumable/deck synergy and build-path reasoning
- [x] B5 build-aware shop/Joker replacement/reroll reasoning
- [x] B6 consumable timing/targeting and pack-choice build deltas
- [x] B7 build-intent feedback into D1 and build-rationale logging

Per-layer production calibration and the first Red/White threshold cartridge are **v1.0 competence work**, not 0.9 integration blockers.

### 0.9E — Decision coverage inventory

| Layer | Decision | 0.9 status |
|---|---|---|
| D1 | Play vs discard + subset | Complete foundation; live exercised |
| D2 | Joker buy/keep/replace/sell | Complete foundation |
| D3 | Voucher acquisition | Complete foundation |
| D4 | Consumable ignore/buy/buy-and-use | Complete foundation |
| D5 | Held consumable use vs hold | Complete conservative foundation |
| D6 | Consumable targeting | Complete deterministic foundation |
| D7 | Planet choice/use timing | Complete foundation; live validated |
| D8 | Booster acquisition | Complete foundation; live validated |
| D9 | Pack choice vs Skip | **Implementation complete; production validation open** |
| D10 | Pack follow-up targeting | **Implementation complete; production validation open** |
| D11 | Reroll decision | Complete foundation |
| D12 | Shop arbiter | Complete foundation |
| D13 | Blind play vs skip/tag | Complete foundation |
| D14 | Run-level resource valuation | Complete conservative foundation |

**Remaining 0.9 decision work**

- [ ] **D9:** validate recommendations across Joker/Standard/Planet/Tarot/Spectral pack families at the production boundary
- [ ] **D9:** verify recommendation -> semantic injected action -> authoritative postcondition for choice and Skip
- [ ] **D10:** validate end-to-end targeted Tarot/Spectral/Standard-pack flows at the production boundary
- [ ] **D10:** verify target recommendation -> injected targeting/confirmation -> authoritative postcondition

D9/D10 live-validation boxes may only be satisfied by authentic production transitions using complete before/after process-memory snapshots and later authoritative checkpoints. Synthetic/unit fixtures remain regression evidence only.

### 0.9F — Run logging, diagnostics and recovery

**Implemented**

- [x] Append-only per-run JSONL experience log
- [x] Deck/stake/playbook/playbook-version run identity
- [x] Persistent `run_id` and resumable event sequencing
- [x] Sanitized public observations and chosen decision rationale
- [x] Successful-transition logging only after guarded execution
- [x] Terminal win/loss and per-run/session summaries
- [x] Supervisor traceback/crash-report capture
- [x] Read-only live monitor and agent toggle integration
- [x] Build profile, synergy, build-intent and selected-decision rationale events

**Remaining 0.9 logging gate**

- [ ] Log full decision-layer candidate scores and active thresholds where required for postmortem
- [ ] Log execution failures in a dedicated diagnostic stream without corrupting successful experience transitions
- [ ] Log purchases, sells, consumable uses and blind outcomes as dedicated semantic events
- [ ] Confirm clean shutdown produces a complete production run/session log

Replay analysis, aggregate statistics and offline playbook tuning are deferred to v1.0 competence work after log quality is validated.

### 0.9G — Single-command autonomous supervisor and release validation

**Implemented**

- [x] Single toggle command for an already-started supported run
- [x] Detached supervisor control plane and duplicate-start protection
- [x] Automatic attach, deck/stake detection and playbook selection
- [x] Persistent observe -> decide -> execute -> settle -> re-observe loop
- [x] Unbounded per-attempt step loop
- [x] Natural `GAME_OVER` terminal handling
- [x] Native automatic restart after loss
- [x] Automatic OFF after target-run win path
- [x] Reliability soak protocol completed without crash/UI corruption/premature injection

**Remaining v0.9 release gate**

- [ ] Live-validate repeated production loss -> native restart -> fresh-attempt continuation across multiple attempts
- [ ] Live-validate manual toggle OFF during an active run
- [ ] Confirm every required phase/subflow routes to a production decision layer with no temporary unsupported gap
- [ ] Validate full blind-select -> hand-play -> round-eval -> shop -> pack/consumable -> next-blind flow with no manual gameplay input
- [ ] Confirm complete attempts continue without an arbitrary gameplay-step cap
- [ ] Confirm clean shutdown and complete production run/session logging
- [ ] If a real win occurs during 0.9 validation, confirm automatic OFF and terminal logging; otherwise carry this live check into v1.0

### Legacy/fallback cleanup

`save.jkr` remains fallback/debug/recovery input only. The retired screen-capture/card-location/mouse-control stack must not return as a production fallback.

- [x] Vanilla `save.jkr` discovery/parser
- [x] Save-backed fallback extraction
- [x] Retired screen-capture/card-location/mouse-control production stack removed
- [x] Production autonomous path has no silent mouse fallback
- [ ] Remove remaining legacy-utility dependence on save-persistence timing where encountered
- [ ] Remove stale-save reconciliation from any remaining normal autonomous path

## v1.0.0 — Red Deck / White Stake competence

> Begins only after the v0.9 autonomous integration gate is stable. The target is one deliberate, unseeded Red Deck / White Stake win without manual gameplay input after activation.

### 1.0A — Blind-clear objective and hand efficiency

- [ ] Make current-blind clear probability the dominant D1 objective
- [ ] Preserve a concrete clear path across remaining hands/discards
- [ ] Enforce remaining-score / remaining-hands pace discipline
- [ ] Prefer fewer hands among sufficiently safe clear lines
- [ ] Value unused hands as end-of-round economy without sacrificing meaningful clear probability
- [ ] Model held-in-hand value explicitly (Steel, Blue Seal, etc.)
- [ ] Tune recovery/discard behavior around survival probability and the active clear path

### 1.0B — Build identity and coherent Joker-supported play

- [ ] Maintain persistent public build/archetype intent
- [ ] Integrate B3-B7 reasoning consistently across D1-D14
- [ ] Make Joker, hand, discard, Planet, consumable and pack choices reinforce one coherent build
- [ ] Add explicit anti-synergy/conflict modeling
- [ ] Add Ride the Bus + Business Card conflict regression
- [ ] Give useful Negative Jokers explicit slot-free acquisition value
- [ ] Log build-intent changes and detected anti-synergies

### 1.0C — Planet and consumable competence

- [ ] Rework Planet value around future hand frequency, marginal level gain, build synergy and feasibility
- [ ] Penalize low-feasibility hand upgrades unless the run supports them
- [ ] Prevent uncommitted early builds from overvaluing Straight Flush/Neptune
- [ ] Align D4 acquisition with D7 use timing
- [ ] Finalize held-consumable timing/target thresholds

### 1.0D — Pack, shop and economy competence

- [ ] Calibrate D3/D8/D9/D10/D11/D12/D14 thresholds to build value and survival
- [ ] Make voucher valuation explicitly run-wide/persistent
- [ ] Add interest-breakpoint awareness, including observable voucher-modified caps/thresholds
- [ ] Compare spending against reserve and foregone interest
- [ ] Add bounded undiscovered-item acquisition bias that never overrides survival/build coherence
- [ ] Preserve enough economy for later shops without sacrificing immediate survival

### 1.0E — Blind skip/tag strategy

- [ ] Calibrate tag EV against blind reward, lost shop/economy opportunity, build strength and boss preparation
- [ ] Make skip decisions build/ante aware
- [ ] Validate skip/tag choices through real-run examples

### 1.0F — Red/White production threshold set and win gate

- [ ] Final Red/White thresholds for D1-D14
- [ ] Live-confirm automatic OFF after a successful run
- [ ] Preserve normal Steam profile progression/unlocks
- [ ] Produce a complete replayable run-experience log with per-layer/build rationales
- [ ] **Complete one successful unseeded Red Deck / White Stake run**

## Later Red Deck stakes

| Version | Stake | Added adaptation |
|---|---|---|
| v1.1.0 | Red | No Small Blind reward money |
| v1.2.0 | Green | Higher score requirements |
| v1.3.0 | Black | Eternal Joker strategy |
| v1.4.0 | Blue | Reduced-discard strategy |
| v1.5.0 | Purple | Higher score requirements |
| v1.6.0 | Orange | Perishable Joker strategy |
| v1.7.0 | Gold | Rental Joker strategy and Red Deck all-stakes validation |

Each stake milestone requires an adapted threshold cartridge and one successful unseeded run.

## Deck progression

1. **Red Deck — v1.x** — active after v0.9
2. **Blue Deck — v2.x** — locked until Red Gold completion
3. **Yellow Deck — v3.x** — locked until Blue Gold completion
4. **Green Deck — v4.x** — locked until Yellow Gold completion
5. **Black Deck — v5.x** — locked until Green Gold completion

## Completion criteria

`v0.9.0` is complete when the permanent agent can, after one activation and without manual gameplay input, autonomously cover the required real-run phases/actions through the production bridge, wait for authoritative readiness/quiescence after each action, re-observe/replan, continue through complete attempts, produce complete diagnostics/logs, and terminate/restart safely without UI corruption or premature injection.

From `v1.0.0` onward, a deck/stake milestone is complete only when the permanent agent, using the matching threshold cartridge and no manual gameplay input after activation, successfully completes one full unseeded run while producing the required authoritative experience log.
