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

Current migration snapshot: Sections 1–12 are production-owned and tested. The complete frozen forest contains 136 definition-backed topology nodes; the seven coarse compatibility definitions and the obsolete standalone Edition strategy have been retired. Editions now contribute portable universal value, while route-specific edition interactions remain attached to the routes that actually use them.

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
- [x] Keep not-yet-migrated strategies numerically identical to the legacy tracker as standalone root/leaves, including negative conflict scores, until their subtrees migrate; retire those compatibility definitions after the complete forest takes ownership.
- [x] Migrate frozen Sections 1–4—poker hands, ranks/faces, suits/held cards, and enhancements—onto topology-owned `StrategyDefinition` node IDs without parent/child component duplication.
- [x] Expand the seven remaining legacy standalone definitions into the frozen Section 5–12 topology and move their catalogue ownership onto the resulting node IDs.
- [x] Remove generic poker-hand play count from universal strategy evidence. Preserve hand history only for mechanics that explicitly use it; retain persistent hand-level/Planet investment evidence.
- [x] Implement the global Negative-Joker retention rule across standalone sale, shop replacement and Ceremonial Dagger ordering. Ordinary sales require measured material whole-build harm; Negative Jokers cannot masquerade as replacement slots; intentional destruction requires the matching active route; Verdant Leaf remains a survival-scoped emergency exception.
- [x] Finish the Gold/Silver/Bronze/Banned/conditional relationship audit for Sections 1–4. Route-bound support is Neutral off-path, and Banned means genuine strategic conflict rather than support for a competing route.
- [x] Finish the Gold/Silver/Bronze/Banned/conditional relationship audit node by node for Sections 5–12: seals; destruction/thinning; deck growth/training; consumable engines; economy; Joker-board composition; discard rotation; and hand scheduling.
- [x] Rebuild the inverse `component -> strategy/relationship` index from fully tree-owned catalogue data without editing all 150 Joker classes.
- [x] Integrate the useful Section 14 support components into compatible routes instead of creating weak standalone strategies: copy engines, hand-size support, retrigger coverage, pack/reroll support, duplicate generation, and uncommon/board-slot enablers activate only with relevant infrastructure.
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
- [x] Apply Red Deck / White Stake cartridge modifiers over the full universal strategy tree without redefining topology or component relationships. Root modifiers inherit through descendant paths; otherwise-neutral routes retain the cartridge's default effectiveness.
- [x] Migrate D1–D14 direct-definition lookups to inherited path semantics where required; guaranteed blind survival remains superior to strategy purity. D1 play/discard shaping, D5/D6 consumable targeting, D8 Celestial evidence, Joker scoring probes and D13 tag support now honor complete root-to-leaf paths.
- [x] Log production leaf rankings plus node path, direct evidence, ancestor foundation and effective leaf evidence, together with candidate contributor/pivot/conflict rationales and structured Negative-retention protection/exception diagnostics.
- [x] Add deterministic regressions for evidence removal on sale, used-Planet investment, conflicts, Ante pressure, consumable seeding, pack selection, and D1 hand preference across the currently migrated forest.
- [x] Repeat the deterministic topology, relationship, conflict, conditional-support, inverse-index, cartridge-inheritance and production-consumer behavior suite across Sections 5–12.
- [x] Add global Negative-retention regressions for ordinary standalone sale, measured-harm exceptions, replacement-slot protection, ordinary-incumbent selection, Dagger protection, and active-Dagger intentional sacrifice.
- [x] Use the first unseeded live Red/White win to identify late-run latency, reroll overspending, held-Steel ordering, boss handling, and post-win finalization defects; preserve each correction with deterministic regressions.
- [ ] Run final specialized live validation after the complete deterministic tree is stable.

### 1.0G — Final freeze and acceptance gate

The earlier Red/White threshold freeze was performed against the pre-tree policy and is therefore **historical/provisional**, not the final v1.0 freeze.

- [x] Run the full deterministic suite after the 1.0F implementation is complete (1,787 passing on 2026-08-18). No integration regression required retuning; freeze the final Red/White D1–D14 thresholds and strategy evidence/pressure/effectiveness parameters pending live acceptance.
- [x] Complete **one unseeded Red Deck / White Stake win** with no manual gameplay input after activation and normal Steam progression preserved (2026-08-18, Amber Acorn; the authoritative transition records `won=true`).
- [ ] Validate a complete replayable authoritative winning run log with decision/build/strategy rationales and automatic OFF immediately after the win. The first win exposed and fixed a `won=true`/`ROUND_EVAL` terminal-detection gap, so this finalization half of the gate still requires one live confirmation.

### 1.0H — Autonomous fresh-profile collection progression — IN PROGRESS

The bounded collection preference is already production-complete for explicitly
undiscovered positive Jokers, consumables, Vouchers, boosters and visible pack
choices. It is exactly one floating-point ULP and therefore cannot override a
stronger option, rescue a rejected purchase, trigger destructive replacement, or
compete with survival/strategy/economy. That bounded preference remains the rule
for ordinary competence runs.

1.0H adds a separate, explicit **collection-first mode** intended to let the agent
own and progress a fresh Balatro profile. In this mode, permanent profile progress
is the primary objective and winning the current run is secondary. Losing early
runs is acceptable; survival and strategy value are tie-breakers used to reach
more shops and collection opportunities per run, not gates that may veto progress.

For an authoritative `discovered=false` shop or pack item, collection-first mode
uses a hard lexicographic priority class rather than a very large floating-point
score. The item must be bought or selected whenever the action is legal and
affordable. A full Joker area triggers capacity-aware replacement of the least
valuable sellable incumbent. Eternal Jokers are ineligible, and selling a Negative
Joker is not treated as freeing capacity because its extra slot disappears with it.
Missing or unreadable discovery state remains unknown and does not trigger a
destructive action.

That general rule discovers every already-unlocked item that can appear. Truly
**locked** entries cannot appear yet, so they additionally require declarative
condition/progress planning beyond the current Hit the Road and Stuntman handlers.
Vouchers use the same model: buy an undiscovered visible Voucher unconditionally,
and deliberately repeat already-discovered prerequisite actions when the unlock
registry identifies account-wide or within-run progress such as Blank -> Antimatter.

The initial locked-Joker backlog reported from the live collection on 2026-08-18
is deliberately split by acquisition mechanism. A "locked" collection tile does
not imply that every target should receive a hand override:

| Joker | Requirement / acquisition route | 1.0H handling | Status |
|---|---|---|---|
| Golden Ticket | Play a five-card hand containing only Gold cards | Declarative deck-shaping and play campaign; universal discovery priority buys it afterward | Planned |
| Arrowhead | Have at least 30 Spade cards in the deck | Declarative suit-conversion campaign | Planned |
| Merry Andy | Win a run in 12 or fewer rounds | Declarative run-length and skip-planning campaign | Planned |
| Seeing Double | Play a hand containing four 7s of Clubs | Declarative rank-and-suit shaping campaign | Planned |
| Hit the Road | Discard five Jacks simultaneously | Existing handler may intentionally sacrifice blind-clear probability in collection-first mode | Implemented |
| Stuntman | Score at least 100,000,000 Chips in one hand | Existing handler may intentionally sacrifice blind-clear probability in collection-first mode | Implemented |
| Satellite | Hold at least $400 | Declarative long-horizon cash-reserve campaign | Planned |
| Astronomer | Discover every Planet card | Collection-state-driven Planet discovery campaign | Planned |
| Triboulet | Obtain the random Legendary from The Soul | Preserve a free Joker slot and maximize Soul opportunities; no fabricated condition override | Partially covered by current early-Ante Soul policy |
| Yorick | Obtain the random Legendary from The Soul | Preserve a free Joker slot and maximize Soul opportunities; no fabricated condition override | Partially covered by current early-Ante Soul policy |

Triboulet and Yorick are discovery targets, not ordinary condition-locked targets.
The Soul remains random, so 1.0H may improve opportunity capture and diagnostics
but must not claim that it can deterministically select either Legendary.

- [ ] Expose authoritative unlocked/discovered state for every relevant Joker, consumable, Voucher, booster and other collection center while preserving unknown state as unknown.
- [x] Add the explicit collection-first operating mode and hard `COLLECTION_CRITICAL` action priority; never emulate this guarantee with `inf` or an arbitrary numeric score inside ordinary utility arithmetic. This priority outranks strategy, economy, blind-clear probability, and the Ante-6 single-strategy commitment.
- [x] Guarantee purchase/selection of every legal, affordable, explicitly undiscovered visible Joker, consumable, Voucher, booster and pack choice, including capacity-aware Joker replacement and consumable-slot handling. Eternal and Negative incumbents are excluded from collection-capacity sales.
- [ ] Rank unopened boosters by expected missing-collection opportunity, then hard-prioritize explicitly undiscovered choices after the pack is opened.
- [ ] Add a declarative unlock-condition registry instead of hard-coding conditions into the permanent agent.
- [ ] Model repeatable Voucher prerequisites and account-wide counters even when the prerequisite item itself is already discovered.
- [ ] Cover the six new deterministic/collection targets in the observed backlog: Golden Ticket, Arrowhead, Merry Andy, Seeing Double, Satellite and Astronomer.
- [ ] Extend Soul-opportunity diagnostics to identify which Legendary collection entries remain undiscovered while retaining the existing early-Ante priority and free-slot requirement.
- [ ] Add opt-in planning for unlock progress, including action progress, run prerequisites, conflicts and impossible conditions. Collection progress may intentionally weaken or sacrifice the current run. The existing Hit the Road and Stuntman campaigns now support this sacrifice rule; the declarative condition set remains open.
- [x] Preserve the normal automatic stop at the first Ante-8 win, but allow a newly started agent to resume after the player manually clicks Continue into Endless. This supplies the run path needed for Ante-12 collection progress without forcing every competence win into Endless.
- [ ] Keep ordinary Red/White competence unchanged when collection-first mode is disabled; its one-ULP discovery preference and clear-probability safeguards remain intact.
- [ ] Add live-monitor/log diagnostics and deterministic regressions for campaign admission, progress, completion, impossible conditions, and safe fallback.

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
