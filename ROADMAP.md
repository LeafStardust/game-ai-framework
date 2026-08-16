# Roadmap

> The roadmap is milestone-based. General game-AI infrastructure remains reusable; Balatro mechanics, planning, execution and playbooks stay inside the Balatro adapter/agent stack.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. Deck/stake strategy is supplied by a replaceable **playbook cartridge** selected from the observed live run.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. Hidden future information remains excluded: no RNG-state/seed exploitation and no ordered future draw pile.

## Status snapshot

| Milestone | Status | Remaining gate |
|---|---|---|
| v0.1–v0.8 Foundations | Complete | — |
| **v0.9 Autonomous integration** | **Complete** | — |
| **v1.0 Red/White competence** | **In progress** | One deliberate unseeded Red Deck / White Stake win |
| v1.1–v1.7 Red Deck stakes | Not started | Begins after v1.0 |
| v2+ Additional decks | Not started | Begins after Red Deck progression |

## v0.1.0 — Foundation — COMPLETE

- [x] Repository setup
- [x] Core abstractions
- [x] Game runner
- [x] Dummy environment
- [x] Type annotations

## v0.2.0 — Framework Infrastructure — COMPLETE

- [x] Configuration system
- [x] Logging system
- [x] Metrics system
- [x] Event system

## v0.3.0 — Decision Systems — COMPLETE

- [x] Agent architecture
- [x] Decision engine interface
- [x] Decision pipeline
- [x] Policy interface
- [x] Greedy action policy
- [x] Balatro agent integration

## v0.4.0 — Evaluation Framework — COMPLETE

- [x] Generic evaluator abstraction
- [x] Heuristic evaluation system
- [x] Balatro evaluator integration
- [x] Play cards value heuristic
- [x] Discard cards value heuristic
- [x] Basic risk heuristic

## v0.5.0 — Decision Strategy Expansion — COMPLETE

- [x] Softmax action policy
- [x] Configurable policy selection
- [x] Policy factory
- [x] Agent builder
- [x] Reproducible random seed handling

## v0.6.0 — Experiment Infrastructure — COMPLETE

- [x] Agent evaluation runner
- [x] Multi-episode execution
- [x] Policy comparison framework
- [x] Experiment result tracking
- [x] Extended metrics collection

## v0.7.0 — Balatro Intelligence Layer — COMPLETE

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

## v0.8.0 — Balatro Search and Planning Foundation — COMPLETE

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

---

## v0.9.0 — Autonomous Real-Game Integration — COMPLETE

The v0.9 milestone is closed. The production agent can observe, decide, execute, verify, log, restart and stop through real Balatro without manual gameplay input after activation.

### Accepted production stack

- [x] Read-only Windows process-memory observation and authoritative `LiveBalatroSnapshot -> BalatroState` translation
- [x] Repository-owned first-party injected bridge; no silent mouse fallback
- [x] Native readiness/quiescence barriers and stale-state replan protection
- [x] Semantic execution and authoritative post-action reconciliation
- [x] Full autonomous phase loop: blind select, hand play/discard, round eval, shop, pack flows and consumables
- [x] Native loss -> fresh same-deck/stake restart
- [x] Cooperative manual OFF before the next gameplay action
- [x] Append-only experience logs, per-run summaries, session summaries and separate diagnostics
- [x] Automatic OFF after a real win path
- [x] Unbounded per-attempt execution; no hidden gameplay-step cap

### Mechanics/planning foundation accepted for v0.9

- [x] Deterministic and stochastic score projection without hidden RNG sampling
- [x] Public unordered remaining-deck composition
- [x] Bounded multi-action blind-clear planning with re-observation after every real action
- [x] Correct scoring/effect ordering, retriggers, destruction and generated-consumable behavior
- [x] **150/150 canonical Jokers validated**
- [x] Mutable Joker audit: **34 hydrated / 116 stateless / 0 gaps**
- [x] All Boss Blind scoring/state mechanics covered by the production projection architecture
- [x] D1–D14 decision-layer foundations connected to production execution
- [x] D9/D10 pack choice/targeting validated through authentic process-memory transitions

### v0.9 live acceptance evidence

Accepted session:

`balatro-20260816T142551Z-2af9747a`

Observed in one production session:

- **4 attempts / 3 losses** with repeated native restart and fresh-attempt continuation
- BLIND_SELECT, SELECTING_HAND, ROUND_EVAL, SHOP
- BUFFOON_PACK, STANDARD_PACK, PLANET_PACK and TAROT_PACK
- 25 real D9 pack-policy decisions
- 1 real targeted D10 follow-up
- purchases, sales, consumable use, booster skip, blind skip and normal hand actions
- manual cooperative OFF
- complete terminal attempts and internally consistent run/session artifacts

The session produced 21 diagnostic rows. Classification confirmed **21/21 were recovered stale-state replans and 0 were actionable failures**. Future production runs no longer misclassify this recoverable guard condition as an execution failure.

### Known limitations carried forward

These are competence/strategy limitations rather than v0.9 integration blockers:

- **Cerulean Bell:** deeper hypothetical forced-card choice remains inexact until authoritative re-observation.
- **Verdant Leaf:** card-debuff mechanics are exact, but proactive mid-blind Joker selling is not yet a D1 action.
- Remaining legacy save-backed utilities are fallback/debug only and must not re-enter the normal autonomous path.

---

## v1.0.0 — Red Deck / White Stake Competence — IN PROGRESS

Target: **one deliberate, unseeded Red Deck / White Stake win with no manual gameplay input after activation**, while preserving normal Steam progression and a replayable authoritative run log.

### 1.0A — Blind-clear objective and hand efficiency

- [ ] Make current-blind clear probability the dominant D1 objective
- [ ] Preserve a concrete clear path across remaining hands/discards
- [ ] Enforce remaining-score / remaining-hands pace discipline
- [ ] Prefer fewer hands among sufficiently safe clear lines
- [ ] Value unused hands as end-of-round economy without sacrificing meaningful clear probability
- [ ] Model held-in-hand value explicitly, including Steel and Blue Seal incentives
- [ ] Tune recovery/discard behavior around survival probability and the active clear path

### 1.0B — Build identity and coherent Joker-supported play

- [ ] Maintain persistent public build/archetype intent
- [ ] Integrate B3–B7 reasoning consistently across D1–D14
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

- [ ] Final Red/White thresholds for D1–D14
- [ ] Live-confirm automatic OFF after a successful run
- [ ] Preserve normal Steam profile progression/unlocks
- [ ] Produce a complete replayable winning run-experience log with per-layer/build rationales
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

1. **Red Deck — v1.x**
2. **Blue Deck — v2.x**
3. **Yellow Deck — v3.x**
4. **Green Deck — v4.x**
5. **Black Deck — v5.x**

## Completion criteria

`v1.0.0` is complete only when the permanent agent, using the Red Deck / White Stake playbook and no manual gameplay input after activation, completes one full unseeded run while producing the required authoritative experience log and preserving normal game progression.
