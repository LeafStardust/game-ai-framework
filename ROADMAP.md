# Roadmap

> The roadmap tracks active milestones, not release notes. Completed work is summarized; detailed implementation evidence belongs in tests, logs, commits and release documentation.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. Universal Balatro strategies are shared game knowledge. A replaceable **deck/stake cartridge** only modifies the effectiveness, feasibility, economy, and thresholds of those strategies for the observed live run.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. Hidden future information remains excluded: no RNG-state/seed exploitation and no ordered future draw pile.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 Foundation + autonomous integration | Complete | — |
| **v1.0 Red Deck / White Stake competence** | **In progress** | Universal strategy-tree system + final acceptance |
| v1.1–v1.7 Red Deck stake progression | Not started | Begins after v1.0 |
| v2+ Additional decks | Not started | Begins after Red Deck progression |

## Completed milestones

| Version | Completed scope |
|---|---|
| v0.1 | Repository foundation, core abstractions and game runner |
| v0.2 | Configuration, logging, metrics and events |
| v0.3 | Agent architecture, decision pipeline and policy system |
| v0.4 | Evaluation framework and Balatro play/discard/risk heuristics |
| v0.5 | Softmax policy, configurable policy selection and reproducible seeds |
| v0.6 | Experiment runner, multi-episode evaluation, comparisons and metrics |
| v0.7 | Balatro cards, hands, scoring, Jokers, consumables and card modifiers |
| v0.8 | Search/planning, probability/EV analysis, blind-clear paths, stakes and deck architecture |
| v0.9 | Autonomous real-game loop: observe -> decide -> execute -> verify -> log -> restart/stop; authoritative live state, injected execution, stochastic projection, 150/150 Joker validation and Boss Blind coverage |

---

## v1.0.0 — Red Deck / White Stake Competence — IN PROGRESS

Goal: turn the completed autonomous stack into a **deliberate, repeatable Red Deck / White Stake player** that discovers and reinforces coherent strategies from the current run instead of relying on isolated local-value purchases.

### 1.0A — Blind survival and hand efficiency

- [x] Make clear probability and a feasible remaining clear path the dominant D1 objective, with pace discipline across remaining hands/discards.
- [x] Among similarly safe clear lines, prefer fewer hands and capture unused-hand economy.
- [x] Preserve future hand value explicitly, including retained structure, Steel cards, Blue Seals and other build-relevant held cards.
- [x] Tune discard/recovery behavior around the active clear path rather than isolated hand value.

### 1.0B — Initial build coherence

- [x] Maintain persistent public build/archetype intent and apply B3–B7 reasoning consistently across D1–D14.
- [x] Make Joker, hand, discard, Planet, consumable and pack decisions reinforce the active build.
- [x] Detect and penalize anti-synergies/conflicts, including a Ride the Bus + Business Card regression case.
- [x] Give useful Negative Jokers explicit slot-free acquisition value.
- [x] Log meaningful build-intent changes and detected conflicts.

> 1.0B established the first build-intent layer. 1.0F replaces its loose archetype inference with explicit universal strategy-tree evidence while preserving useful public-state/build profiling work.

### 1.0C — Planet and consumable competence

- [x] Value Planets by expected future hand frequency, marginal level gain, build synergy and feasibility; suppress speculative upgrades such as unsupported early Straight Flush/Neptune lines.
- [x] Align consumable acquisition with use timing and finalize held-consumable use/target thresholds.

> The universal strategy system in 1.0F becomes the authoritative strategic relevance layer: Tarot/Spectral effects may seed strategies early, unopened consumables do not count as achieved strategy evidence, and paid Planet acquisition normally requires real poker-hand evidence. A used Planet contributes small persistent evidence through the resulting hand-level investment.

### 1.0D — Shop, pack and economy competence

- [x] Calibrate D3/D8/D9/D10/D11 acquisition, reroll and pack thresholds around survival, build value and economy; keep D12 threshold-free and calibrate D14 shared resource valuation on the same scale.
- [x] Model run-wide voucher value plus reserve/interest breakpoints, including observable voucher-modified caps or thresholds.
- [x] Keep undiscovered-item acquisition bias bounded so it never overrides survival or build coherence.

### 1.0E — Blind skip/tag strategy

- [x] Evaluate skip/tag EV against blind reward, lost shop/economy opportunity, build strength, ante and boss preparation.
- [x] Validate skip/tag behavior with real-run examples before freezing thresholds.

### 1.0F — Universal strategy tree and scoring

The first flat universal-strategy implementation proved the current-state evidence, candidate alignment, Ante-pressure, D1/D13 integration, replacement, consumable, and conditional-relationship concepts. Its flat catalogue/topology is now **legacy design** and is being replaced by the tree model in `BALATRO_STRATEGY_TREE.md` before further catalogue work.

- [x] Establish zero-evidence early buying: ordinary/meta/context value leads before the run owns strategic evidence.
- [x] Establish current-state recomputation, used-Planet evidence, unopened-consumable exclusion, Ante pressure, dominant/relevant diagnostics, candidate alignment, and negative-times-negative protection in the prototype runtime.
- [x] Integrate strategy awareness into major deterministic slices already completed, including D1 hand hierarchy, D13 blind skip/tag, booster acquisition, consumable timing/targeting, and Joker replacement/retention.
- [x] Add state-aware conditional relationship infrastructure and conservative runtime guards for unresolved conditional catalogue entries.
- [x] Replace the four obsolete flat strategy Markdown files with one `BALATRO_STRATEGY_TREE.md` design contract and align `ARCHITECTURE.md` with the redesign.
- [ ] **Freeze the strategy forest topology before assigning new tiers.** Confirm every current flat strategy is retained, split, replaced, or explicitly removed; admit new named-engine leaves only when they materially change multiple downstream decisions.
- [ ] Finalize the first known structural splits: High Card (`Core`, `Stuntman/Small-Hand`, `Baron-Mime`), Face Cards (`Played`, `Held`), Gold Cards (`Held Economy`, `Golden Ticket Scoring`), and Red Seal (`Played`, `Held`), then audit the remaining roots for any similarly real specialization.
- [ ] Encode node IDs, parent IDs, internal/leaf roles, core/fallback-leaf behavior, and the rule that **only leaves appear in the actionable ranking**.
- [ ] Separate `direct_evidence`, internal `foundation/branch_score`, and leaf `effective_score`.
- [ ] Implement discounted descendant -> ancestor evidence propagation while preventing recursive self-evidence double counting.
- [ ] Do not automatically propagate ancestor evidence downward. A specific non-fallback child must first have qualifying child evidence before inheriting ancestor direct foundation.
- [ ] Remove generic poker-hand play count from universal strategy evidence. Preserve hand history only for mechanics that explicitly use it.
- [ ] Implement the global Negative-Joker retention rule: protect Negative Jokers from ordinary replacement pressure unless their active mechanic materially harms the build or intentional sacrifice/destruction is justified by the active strategy.
- [ ] Add explicit destructive/named-engine strategy contexts where required, including Ceremonial Dagger and Vampire, rather than handling them as unexplained one-off exceptions.
- [ ] Audit and assign exact Gold/Silver/Bronze/Banned/conditional relationships **one tree node at a time**, beginning only after topology freeze. Banned must mean genuine strategic conflict, not merely support for a competing strategy.
- [ ] Rebuild the inverse `component -> strategy/relationship` index from the tree-owned catalogue without editing all 150 Joker classes.
- [ ] Keep strategy evidence separate from candidate purchase/retention value: inherent/meta/survival/economy value remains independently available at every Ante.
- [ ] Preserve the intended Ante behavior: broad exploration/foundation in Antes 1–2, convergence in Antes 3–5 as Joker slots become scarce, and specialization from Ante 6 around the highest-ranked viable leaf plus up to two compatible relevant leaves.
- [ ] Keep early Tarot/Spectral strategy-seeding available while requiring real poker-hand evidence before meaningful paid Planet investment.
- [ ] Add Red Deck / White Stake cartridge modifiers over the universal strategy tree without redefining topology or component relationships.
- [ ] Migrate D1–D14 consumers from the legacy flat ranking to leaf rankings while guaranteed blind survival remains superior to strategy purity.
- [ ] Log leaf rankings, node direct evidence, ancestor foundation, score contributors, candidate strategy adjustment, Ante pressure, pivots, conflicts, Negative-Joker protection, sell/replacement rationale, and final decision decomposition.
- [ ] Add deterministic regressions for tree propagation, no downward auto-activation, no recursive double count, fallback-leaf suppression, leaf-only ranking, zero-evidence buying, removal on sale, Planet investment, Negative retention, conflicts, Ante pressure, consumables, packs, and D1 hand preference.
- [ ] Run specialized live validation only after deterministic tree behavior is stable.

### 1.0G — Final freeze and acceptance gate

The earlier Red/White threshold freeze was performed against the pre-tree policy and is therefore **historical/provisional**, not the final v1.0 freeze.

- [ ] Run the full test suite only after 1.0F is complete; re-tune only where strategy integration proves it necessary, then freeze the final Red/White D1–D14 thresholds and strategy evidence/pressure/effectiveness parameters.
- [ ] Complete **one unseeded Red Deck / White Stake win** with no manual gameplay input after activation, normal Steam progression preserved, a complete replayable authoritative run log with decision/build/strategy rationales, and automatic OFF after the win.

---

## v1.1–v1.7 — Red Deck stake progression

| Version | Stake | New adaptation focus |
|---|---|---|
| v1.1 | Red | No Small Blind reward money |
| v1.2 | Green | Green Stake score scaling |
| v1.3 | Black | Eternal Joker strategy |
| v1.4 | Blue | Reduced-discard strategy |
| v1.5 | Purple | Purple Stake score scaling |
| v1.6 | Orange | Perishable Joker strategy |
| v1.7 | Gold | Rental Joker strategy and Red Deck all-stakes validation |

Each stake milestone modifies the effectiveness/feasibility/economy of the universal Balatro strategies as required by that stake, retunes the Red Deck cartridge when necessary, and requires one successful unseeded run. Stake milestones should not duplicate or redefine the universal strategy tree.

### Higher-stake economy and hand-efficiency requirement

- [ ] In higher-stake runs, explicitly prioritize clearing blinds with as few hands as safely possible to maximize unused-hand cash-out, and pursue >2× blind-target finishes for their extra-cash benefit when the line is strategically safe and EV-positive.

## v2+ — Additional decks

Planned deck order after Red Deck completion:

1. **Blue Deck — v2.x**
2. **Yellow Deck — v3.x**
3. **Green Deck — v4.x**
4. **Black Deck — v5.x**

Additional-deck cartridges reuse the same universal Balatro strategy tree and supply only deck/stake-specific strategy modifiers and thresholds.
