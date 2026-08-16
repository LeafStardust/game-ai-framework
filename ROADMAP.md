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
| 0.9E Decision coverage | Implementation/regression complete | Authentic D9/D10 live-transition evidence in 0.9G |
| 0.9F Logging/diagnostics | **Implementation/regression complete** | Clean production shutdown/log completeness in 0.9G |
| 0.9G Release validation | **Regression complete; live validation pending** | Authentic full-flow production run evidence |
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

### 0.9E — Decision coverage inventory — IMPLEMENTATION/REGRESSION COMPLETE

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
| D9 | Pack choice vs Skip | Implementation + production-boundary regression complete; authentic live evidence open |
| D10 | Pack follow-up targeting | Implementation + production-boundary regression complete; authentic live evidence open |
| D11 | Reroll decision | Complete foundation |
| D12 | Shop arbiter | Complete foundation |
| D13 | Blind play vs skip/tag | Complete foundation |
| D14 | Run-level resource valuation | Complete conservative foundation |

D9/D10 regression coverage now verifies the production recommendation -> semantic injected action -> authoritative-postcondition contract across Joker/Standard/Planet/Tarot/Spectral packs, Skip, and targeted Tarot/Spectral/Standard flows. Final acceptance still requires authentic process-memory before/after transitions during the 0.9G live release run; synthetic/unit fixtures are regression evidence, not substitutes for that live evidence.

### 0.9F — Run logging, diagnostics and recovery — IMPLEMENTATION/REGRESSION COMPLETE

- [x] Append-only per-run JSONL experience log
- [x] Deck/stake/playbook/playbook-version run identity
- [x] Persistent `run_id` and resumable event sequencing
- [x] Sanitized public observations and chosen decision rationale
- [x] Successful-transition logging only after guarded execution
- [x] Terminal win/loss and per-run/session summaries
- [x] Supervisor traceback/crash-report capture
- [x] Read-only live monitor and agent toggle integration
- [x] Build profile, synergy, build-intent and selected-decision rationale events
- [x] Decision-layer candidate scores and active thresholds required for postmortem, including ranked D9/D10 candidates and D1 search diagnostics
- [x] Dedicated append-only execution/supervisor failure diagnostic stream that does not contaminate successful experience transitions
- [x] Dedicated semantic events for purchases, sells, consumable uses and blind outcomes after successful authoritative transitions
- [x] Failure-safe session summary generation on unhandled supervisor errors

The remaining logging acceptance criterion is **live** rather than an implementation gap: 0.9G must confirm that cooperative shutdown and complete production attempts leave internally consistent run/session logs and diagnostics.

Replay analysis, aggregate statistics and offline playbook tuning are deferred to v1.0 competence work after log quality is validated.

### 0.9G — Single-command autonomous supervisor and release validation

**Implemented/regression-validated**

- [x] Single toggle command for an already-started supported run
- [x] Detached supervisor control plane and duplicate-start protection
- [x] Automatic attach, deck/stake detection and playbook selection
- [x] Persistent observe -> decide -> execute -> settle -> re-observe loop
- [x] Unbounded per-attempt step loop
- [x] Natural `GAME_OVER` terminal handling
- [x] Native automatic restart after loss
- [x] Automatic OFF after target-run win path
- [x] Reliability soak protocol completed without crash/UI corruption/premature injection
- [x] Contract-level D9/D10 production-boundary regression coverage
- [x] Logging/diagnostic recovery regression coverage, including unhandled supervisor failure artifacts
- [x] Canonical production phase-routing inventory covers blind select, hand play, round eval, shop and all five pack families
- [x] Unbounded-loop regression survives 128 consecutive gameplay actions with no hidden gameplay-step cap
- [x] Supervisor regression survives multiple consecutive losses, performs fresh restarts and continues into the next attempt

**Remaining v0.9 live release gate — authentic process execution only**

- [ ] Live-validate repeated production loss -> native restart -> fresh-attempt continuation across multiple attempts
- [ ] Live-validate manual toggle OFF during an active run before the next gameplay action
- [ ] Confirm every required phase/subflow encountered in the real run routes to a production decision layer with no temporary unsupported gap
- [ ] Validate full blind-select -> hand-play -> round-eval -> shop -> pack/consumable -> next-blind flow with no manual gameplay input
- [ ] Obtain authentic D9/D10 before/after process-memory evidence for pack choice/Skip and targeted follow-up flows encountered during release validation
- [ ] Confirm a complete real attempt continues without an arbitrary gameplay-step cap
- [ ] Confirm cooperative shutdown leaves complete, internally consistent production run/session logs and separate diagnostics
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
