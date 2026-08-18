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

## v1.0 — Red Deck / White Stake Competence — IN PROGRESS

Goal: turn the completed autonomous stack into a **deliberate, repeatable Red Deck / White Stake player** that discovers and reinforces coherent strategies from the current run instead of relying on isolated local-value purchases.

### 1.0A — Blind survival and hand efficiency

- [x] Make clear probability and a feasible remaining clear path the dominant D1 objective, with pace discipline across remaining hands/discards.
- [x] Among similarly safe clear lines, prefer fewer hands and capture unused-hand economy.
- [x] Preserve future hand value explicitly, including retained structure, Steel cards, Blue Seals and other build-relevant held cards.
- [x] Tune discard/recovery behavior around the active clear path rather than isolated hand value.
- [x] Bound Boss-Blind D1 search to an interactive live budget so debuff bosses such as The Club cannot stall autonomy for minutes; retain single-step re-observation and pace fallback.

### 1.0B — Initial build coherence

- [x] Maintain persistent public build/archetype intent and apply B3–B7 reasoning consistently across D1–D14.
- [x] Make Joker, hand, discard, Planet, consumable and pack decisions reinforce the active build.
- [x] Detect and penalize anti-synergies/conflicts, including a Ride the Bus + Business Card regression case.
- [x] Give Joker editions strategy-independent acquisition/retention value; Negative is slot-neutral and buyable even on a full board, while explicit mechanical/strategy conflict remains authoritative.
- [x] Log meaningful build-intent changes and detected conflicts.

> 1.0B established the first build-intent layer. 1.0F replaces its loose archetype inference with explicit universal strategy-tree evidence while preserving useful public-state/build profiling work.

### 1.0C — Planet and consumable competence

- [x] Value Planets by expected future hand frequency, marginal level gain, build synergy and feasibility; suppress speculative upgrades such as unsupported early Straight Flush/Neptune lines.
- [x] Align consumable acquisition with use timing and finalize held-consumable use/target thresholds.

> The universal strategy system in 1.0F becomes the authoritative strategic relevance layer: Tarot/Spectral effects may seed strategies early, unopened consumables do not count as achieved strategy evidence, and paid Planet acquisition normally requires real poker-hand evidence. A used Planet contributes small persistent evidence through the resulting hand-level investment.

### 1.0D — Shop, pack and economy competence

- [x] Calibrate D3/D8/D9/D10/D11 acquisition, reroll and pack thresholds around survival, build value and economy; keep D12 threshold-free and calibrate D14 shared resource valuation on the same scale.
- [x] Keep full-roster Joker replacement search in reroll EV while enforcing paid-reroll stop losses: a cost cap, a larger Ante-6+ survival reserve, and stricter Gold Card/Gold Seal economy reserves; free rerolls remain exempt.
- [x] Memoize deterministic Joker behavior descriptors by complete modeled Joker state so full-slot shop comparisons reuse analysis without making stale assumptions about stateful Jokers.
- [x] Model run-wide voucher value plus reserve/interest breakpoints, including observable voucher-modified caps or thresholds.
- [x] Keep undiscovered-item acquisition bias bounded so it never overrides survival or build coherence. Explicitly undiscovered positive options receive only a one-ULP tie-break, never a value-changing exploration bonus.
- [x] Add explicit default-off collection unlock campaigns for Hit the Road and Stuntman. Campaign actions require authoritative locked status and may not reduce the selected D1 clear probability; ordinary runs remain unchanged.

### 1.0E — Blind skip/tag strategy

- [x] Evaluate skip/tag EV against blind reward, lost shop/economy opportunity, build strength, ante and boss preparation.
- [x] Validate skip/tag behavior with real-run examples before freezing thresholds.

### 1.0F — Universal strategy tree and scoring

The first flat universal-strategy implementation proved current-state evidence, candidate alignment, Ante pressure, D1/D13 integration, replacement, consumable, and conditional-relationship concepts. Its flat catalogue/topology is now **legacy design**. The frozen replacement topology is in `BALATRO_STRATEGY_TREE.md`; implementation now migrates that tree into the runtime without discarding already-green strategic consumers.

Current migration snapshot: Sections 1–4 are production-owned and tested (65 topology nodes). Seven coarse legacy standalone definitions still preserve behavior for the not-yet-expanded Sections 5–12.

- [x] Establish zero-evidence early buying: ordinary/meta/context value leads before the run owns strategic evidence.
- [x] Preserve the bounded explicitly-undiscovered item tie-break; discovery may separate otherwise equal positive options but must never override survival, economy, or strategy.
- [x] Establish current-state recomputation, used-Planet evidence, unopened-consumable exclusion, Ante pressure, dominant/relevant diagnostics, candidate alignment, and negative-times-negative protection in the prototype runtime.
- [x] Integrate strategy awareness into major deterministic slices already completed, including D1 hand hierarchy, D13 blind skip/tag, booster acquisition, consumable timing/targeting, and Joker replacement/retention.
- [x] Add state-aware conditional relationship infrastructure and conservative runtime guards for unresolved conditional catalogue entries.
- [x] Replace the four obsolete flat strategy Markdown files with separate topology (`BALATRO_STRATEGY_TREE.md`) and rules (`BALATRO_STRATEGY_TREE_RULES.md`) documents; align `ARCHITECTURE.md` with the redesign.
- [x] **Freeze the v1.0F strategy forest topology.** Roots/children/leaves cover the audited poker-hand, rank, suit, enhancement, seal, named-engine, economy, discard, deck-growth, consumable, and Joker-board strategies. Further topology changes require a real defect or live-validation finding.
- [x] Define leaf-only ranking, parent-foundation semantics, descendant-upward evidence, no blind downward activation, no natural poker-hand transition graph, and Negative-Joker retention rules in the design contract.
- [x] Add the first runtime topology scaffold with validated node IDs, parent links, roots, leaves, ancestor paths, fallback-leaf metadata, cycle rejection, and the initial High Card subtree.
- [x] Add the topology-only evidence-scoring kernel and deterministic regressions for discounted upward foundation, no blind downward activation, no recursive self-double-counting, fallback suppression, and leaf-only ranking.
- [x] Wire the tree scorer into the production tracker with separate node direct evidence, ancestor foundation, leaf effective evidence, child-gated inheritance, fallback suppression, and leaf-only actionable rankings.
- [x] Migrate the High Card subtree into the production catalogue: `High Card -> Core / Stuntman-Small-Hand / Baron-Mime`, remove the obsolete competing-hand High Card Banned list, inherit the parent hand/Planet semantics, and preserve zero-start candidate economics with tree-aware pivot projection.
- [x] Finish the High Card node-by-node relationship pass: Core remains a true fallback; Baron/Mime evidence is state-dependent on real held-King infrastructure; Stuntman conflicts with Baron-Mime only when the held-card engine is materially established; Obelisk conflicts with committed High Card only through its explicit most-played-hand mechanic, never as generic play-count evidence.
- [x] Keep all not-yet-migrated strategies numerically identical to the legacy tracker as standalone root/leaves, including negative conflict scores, until each subtree is explicitly migrated.
- [x] Migrate frozen Sections 1–4—poker hands, ranks/faces, suits/held cards, and enhancements—onto topology-owned `StrategyDefinition` node IDs without parent/child component duplication.
- [ ] Expand the seven remaining legacy standalone definitions into the frozen Section 5–12 topology and move their catalogue ownership onto the resulting node IDs.
- [x] Remove generic poker-hand play count from universal strategy evidence. Preserve hand history only for mechanics that explicitly use it; retain persistent hand-level/Planet investment evidence.
- [ ] Implement the global Negative-Joker retention rule in sell/replace policy: protect Negative Jokers from ordinary replacement pressure unless their active mechanic materially harms the build or intentional sacrifice/destruction is justified by the active strategy.
- [x] Finish the Gold/Silver/Bronze/Banned/conditional relationship audit for Sections 1–4. Route-bound support is Neutral off-path, and Banned means genuine strategic conflict rather than support for a competing route.
- [ ] Finish the Gold/Silver/Bronze/Banned/conditional relationship audit node by node for Sections 5–12: seals; destruction/thinning; deck growth/training; consumable engines; economy; Joker-board composition; discard rotation; and hand scheduling.
- [ ] Rebuild the inverse `component -> strategy/relationship` index from fully tree-owned catalogue data without editing all 150 Joker classes.
- [x] Keep strategy evidence separate from candidate purchase/retention value: candidate tree projection can reveal a pivot, but a candidate cannot fund its own current-strategy purchase bonus before it is owned.
- [x] Separate portable universal Joker value from route-bound strategy value. Portable mapped Jokers retain intrinsic value; only mechanically route-bound Jokers receive dynamic `OFF_PATH` pressure.
- [x] Enforce exclusive dominant-strategy behavior from Ante 6: secondary strategies remain diagnostic but cannot add purchase value, prescribe hands, or authorize pivots.
- [x] Keep exact held Steel/Blue-Seal preservation ahead of universal hand-strategy fit when D1 clear safety and hand efficiency are equivalent.
- [x] Add autonomous Joker-board reordering through the validated injected action, including Blueprint/Brainstorm copy targeting, additive-before-XMult scoring, and projected Ceremonial Dagger sacrifice.
- [x] Add authoritative pre-play hand reordering so Hanging Chad and Photograph place the strongest scoring trigger first, then replan before committing the play.
- [x] Bound Joker-order search on late-run/Negative-edition boards and keep ordinary scoring-order optimization out of the blind-selection critical path.
- [x] Bound every Ante-7+ D1 replan, including Small/Big blinds, to an interactive horizon/node envelope; re-observe after every real action instead of blocking on deep late-run trees.
- [x] Apply universal-strategy alignment to Tarot/Spectral pack choices so highlighted routes such as Aces prefer aligned deck shaping over unrelated enhancement value.
- [x] Price cash spent while Bootstraps or Bull is owned by the scoring value lost across every paid shop-action family, in addition to ordinary interest/reserve economics.
- [x] Keep early Tarot/Spectral strategy-seeding available while requiring real active poker-hand strategy evidence before meaningful paid Planet investment; preserve inherited component semantics across migrated leaves.
- [ ] Add Red Deck / White Stake cartridge modifiers over the full universal strategy tree without redefining topology or component relationships.
- [ ] Migrate remaining D1–D14 direct-definition lookups to inherited path semantics where required; guaranteed blind survival remains superior to strategy purity. D1 hand fit, D8 Celestial evidence and D13 tag support already honor the migrated High Card path.
- [x] Log production leaf rankings plus node path, direct evidence, ancestor foundation and effective leaf evidence; richer contributor/pivot/conflict/Negative diagnostics remain pending.
- [x] Add deterministic regressions for evidence removal on sale, used-Planet investment, conflicts, Ante pressure, consumable seeding, pack selection, and D1 hand preference across the currently migrated forest.
- [ ] Add Negative-retention regressions and repeat the completed behavior suite across Sections 5–12 as those subtrees migrate.
- [x] Use the first unseeded live Red/White win to identify late-run latency, reroll overspending, held-Steel ordering, boss handling, and post-win finalization defects; preserve each correction with deterministic regressions.
- [ ] Run final specialized live validation after the complete deterministic tree is stable.

### 1.0G — Final freeze and acceptance gate

The earlier Red/White threshold freeze was performed against the pre-tree policy and is therefore **historical/provisional**, not the final v1.0 freeze.

- [ ] Run the full test suite only after 1.0F is complete; re-tune only where strategy integration proves it necessary, then freeze the final Red/White D1–D14 thresholds and strategy evidence/pressure/effectiveness parameters.
- [x] Complete **one unseeded Red Deck / White Stake win** with no manual gameplay input after activation and normal Steam progression preserved (2026-08-18, Amber Acorn; the authoritative transition records `won=true`).
- [ ] Validate a complete replayable authoritative winning run log with decision/build/strategy rationales and automatic OFF immediately after the win. The first win exposed and fixed a `won=true`/`ROUND_EVAL` terminal-detection gap, so this finalization half of the gate still requires one live confirmation.

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
