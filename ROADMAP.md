# Roadmap

> The roadmap tracks active milestones, not release notes. Detailed implementation evidence belongs in tests, logs, commits, `CHANGELOG.md`, and release documentation.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. The current universal strategic layer is the canonical **Bond/composition system**. A replaceable **deck/stake cartridge** modifies effectiveness, feasibility, economy, and thresholds for the observed live run.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. Hidden future information remains excluded: no RNG-state/seed exploitation and no ordered future draw pile.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 Foundation + autonomous integration | Complete | — |
| **v1.0.0 Red Deck / White Stake competence** | **Complete** | Released 2026-08-20 |
| **v1.0.x Red/White Bond calibration** | **In progress** | Semantic/runtime correctness + unchanged-HEAD live validation |
| **Offline Bond numerical tuning (Optuna)** | **Planned / documentation complete** | Begins only after known runtime defects are corrected and a typed calibration layer exists |
| v1.1–v1.7 Red Deck stake progression | Next | Begins from Red Stake after Red/White calibration |
| Fresh-profile collection progression | In progress, non-blocking | May continue alongside stake progression |
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
| v0.9 | Autonomous real-game observe → decide → execute → verify → log → restart/stop loop; authoritative live state, injected execution, stochastic projection, 150/150 Joker validation and Boss Blind coverage |
| **v1.0.0** | **Red Deck / White Stake competence release baseline: coherent build planning, strategy-aware D1–D14 decisions, bounded live search, economy/shop competence, boss handling, ordering, diagnostics, and autonomous unseeded win validation** |

---

## v1.0.0 — Red Deck / White Stake Competence — COMPLETE

Released: **2026-08-20**

Goal achieved: the permanent Balatro agent can play Red Deck / White Stake autonomously using coherent run-level strategy rather than isolated local-value decisions.

The original v1.0.0 release used the historical strategy-tree/Gold-Silver-Bronze architecture. That release evidence remains historical record. During v1.0.x calibration, the active production architecture was intentionally migrated to the canonical Currency-Wars-style **Bond/composition system**; the retired categorical strategy tree is not the current runtime contract.

### Completed release scope

- [x] Make blind-clear probability and feasible remaining clear paths the dominant D1 objective while preserving hand efficiency and unused-hand economy.
- [x] Preserve strategically useful held structure, including Steel cards and Blue Seals, when survival-equivalent lines permit it.
- [x] Maintain coherent build intent across hand play, discards, Joker acquisition/replacement, consumables, Planets, packs, rerolls, vouchers, boosters, and blind skips.
- [x] Model anti-synergies and explicit conflicts without treating every competing strategy as mechanically banned.
- [x] Complete the historical universal strategy-tree release baseline.
- [x] Separate portable universal Joker value from route-bound strategic evidence.
- [x] Protect Negative Jokers from ordinary sales, replacement, and unrelated sacrifice; retain explicit measured-harm, active-Dagger, and Verdant Leaf exceptions.
- [x] Add autonomous Joker-board ordering for Blueprint/Brainstorm copy targeting, additive-before-XMult scoring, and Ceremonial Dagger sacrifice planning.
- [x] Add authoritative pre-play hand ordering for first-card effects such as Hanging Chad and Photograph.
- [x] Wire Cerulean Bell forced-card handling and Verdant Leaf emergency sales through authoritative injected actions.
- [x] Bound Boss-Blind, late-Ante, Joker-order, and complete D1 search by interactive node/time budgets.
- [x] Add paid-reroll stop losses, survival reserves, Gold Card/Gold Seal economy protection, and Bull/Bootstraps cash-spending opportunity cost.
- [x] Keep ordinary undiscovered-item preference bounded to a one-ULP tie-break so collection interest cannot override competence.
- [x] Add strategy/build diagnostics to the live monitor and structured run logs.
- [x] Preserve normal Steam progression and hidden-information restrictions.

### Acceptance evidence

- [x] Full deterministic repository suite passed after the v1.0.0 release migration: **1,787 tests on 2026-08-18**.
- [x] Completed an **unseeded, fully autonomous Red Deck / White Stake win** on 2026-08-18 against Amber Acorn with no manual gameplay input after activation and normal Steam progression preserved.
- [x] Fixed the `won=true` / `ROUND_EVAL` terminal-detection gap exposed by that winning run and covered the fix deterministically.

---

## v1.0.x — Red/White Bond calibration — IN PROGRESS

The initial Red/White release demonstrated competence, but repeated five-run calibration exposed a higher-level decision gap: the agent can own several individually useful Jokers while the **realized build remains inactive, incoherent, under-utilized, or too slow to scale**.

The active architecture contract is [`docs/balatro/BALATRO_STRATEGY_SYSTEM.md`](docs/balatro/BALATRO_STRATEGY_SYSTEM.md). Build Health / realization details remain documented in [`docs/balatro/BUILD_HEALTH_AND_REALIZED_STRENGTH.md`](docs/balatro/BUILD_HEALTH_AND_REALIZED_STRENGTH.md).

### Canonical Bond/composition migration and calibration

- [x] Replace active Gold/Silver/Bronze strategy-tree machinery with canonical weighted Bonds, R1–R5 development, realization, sparse relationships, motifs, composition, power-engine selection, and prescriptions.
- [x] Keep `LOCKED` / `R0` / `R1–R5` development separate from `DORMANT` / `PARTIAL` / `ACTIVE` / `MATURE` realization.
- [x] Make live monitor diagnostics Bond-native: power engine, relevant Bonds, contribution/next rank, realization, motifs, synergies/conflicts, and prescriptions.
- [x] Remove retired tracker/tier dependencies from active Build Health, D1, D2, Mouth, Planet compatibility, and runtime paths found by deterministic/live validation.
- [x] Make D2 Joker acquisition/replacement include bounded canonical Bond-transition value rather than relying on categorical strategy-tier shortcuts.
- [x] Make canonical pivot authority compare projected combined-build coherence/distance against realized disruption and protect established engines without making them immortal.
- [x] Apply bounded motif prescriptions beneath existing pack/shop safety authorities.
- [x] Add a pure `BuildHealth` evaluator with auditable Survival, Immediate Scoring, Scaling, Coherence, and Runway dimensions.
- [x] Detect midgame scaling deficits when present strength can clear current blinds but is unlikely to keep pace with the next one to two Antes.
- [x] Make shop buy/replace/reroll decisions sensitive to Build Health and Bond transition rather than Joker count or isolated item value alone.
- [x] Add bounded short-horizon multi-action planning for complementary shop pairs and activation sequences.
- [x] Expose Build Health and inactive-engine/scaling-deficit warnings in the live monitor and structured logs.
- [x] Correct Burnt execution so a safe first discard can level its target hand even when Banner is present; Banner's temporary discard-chip value cannot suppress the defining Burnt engine mechanic.
- [x] Add active/mature power-engine preservation so fresh partial Bonds cannot casually destroy an already-realized engine unless the projected replacement is materially stronger.
- [x] Add late-game cash protection against marginal side-development packs when doing so would drain a functioning but still vulnerable build.
- [x] Cache per-decision Bond hand intents so D1 does not repeatedly recompute the full composition inside candidate tie-breaks.
- [ ] Run a fresh unchanged-HEAD five-run Red/White validation batch after the latest execution/pivot/resource fixes.

### Automated Bond numerical tuning — PLANNED

Detailed contract: [`docs/balatro/BALATRO_BOND_TUNING.md`](docs/balatro/BALATRO_BOND_TUNING.md).

Purpose: replace endless manual coefficient guessing with reproducible offline optimization of **approved numerical parameters**, while preserving human-defined Bond semantics and live-agent determinism.

Implementation order:

- [x] Document architecture, objective, anti-overfitting rules, storage/provenance, pruning constraints, and promotion gates.
- [ ] Introduce a typed immutable Bond calibration snapshot whose defaults exactly reproduce current production behavior.
- [ ] Route one small audited parameter family through that snapshot and add default-equivalence/validation tests.
- [ ] Add an offline batch evaluator that emits structured trial metrics and exact run/seed provenance.
- [ ] Add Optuna as an optional development/tuning dependency only; normal live-agent imports must not depend on it.
- [ ] Add persistent Optuna study storage, parameter/objective schema versions, and resumable study compatibility checks.
- [ ] Begin with a low-dimensional composition/pivot study rather than exposing the whole catalogue.
- [ ] Add holdout/fresh-batch validation and promotion reports.
- [ ] Expand to realization, D1 execution, D2/shop/resource, and cross-system calibration only after earlier phases are stable.

The optimizer may tune bounded numerical values such as contributor weights, R1–R5 thresholds, realization cutoffs where empirical, synergy/conflict coefficients, pivot resistance, motif values, bounded prescription strengths, and resource-policy thresholds. It may **not** invent/remove Bonds, change mechanical truth, weaken boss/legal/survival authority, use hidden information, or automatically promote its own output.

Do not start broad optimization while known runtime/semantic defects remain. The optimizer must tune a correct agent, not learn around bugs.

### Calibration gate before Red Stake

Do not begin Red/Red `1.1.0` implementation until:

- [x] the full Balatro deterministic suite is green on the current architecture baseline;
- [x] Build Health diagnostics are stable and auditable;
- [ ] repeated five-run losses no longer show obvious "full board but non-functioning build" or "recognized engine but unused mechanic" failures;
- [ ] at least one fresh unchanged-HEAD Red/White batch contains an Ante-8 clear without a repeated release-blocking decision defect.

Automated Optuna tuning is not itself a prerequisite for Red Stake if Red/White reaches the competence gate first, but once implemented it becomes the preferred method for systematic coefficient refinement.

---

## Fresh-profile collection progression — IN PROGRESS, NON-BLOCKING

Collection-first mode is intentionally separate from ordinary competence. It may sacrifice current-run strength for permanent profile progress and therefore does **not** define the v1.0.0 Red/White competence gate.

Already implemented:

- [x] Explicit collection-first operating mode with hard `COLLECTION_CRITICAL` action priority.
- [x] Guaranteed legal/affordable acquisition of explicitly undiscovered visible Jokers, consumables, Vouchers, boosters, and pack choices.
- [x] Capacity-aware Joker replacement while excluding Eternal and Negative incumbents from collection-capacity sales.
- [x] Hit the Road and Stuntman collection campaigns may intentionally sacrifice blind-clear probability in collection-first mode.
- [x] Preserve the normal automatic stop at the first Ante-8 win while allowing a newly started agent to resume a manually continued Endless run.

Remaining collection work:

- [ ] Expose authoritative unlocked/discovered state for every relevant collection entry while preserving unknown state as unknown.
- [ ] Rank unopened boosters by expected missing-collection opportunity.
- [ ] Add a declarative unlock-condition registry rather than hard-coding conditions into the permanent agent.
- [ ] Model repeatable Voucher prerequisites and account-wide counters.
- [ ] Cover deterministic/collection targets including Golden Ticket, Arrowhead, Merry Andy, Seeing Double, Satellite, and Astronomer.
- [ ] Extend Soul-opportunity diagnostics for undiscovered Legendary Jokers without pretending the random Legendary outcome is controllable.
- [ ] Add campaign progress/impossibility diagnostics and deterministic regressions.
- [ ] Confirm ordinary competence behavior remains unchanged when collection-first mode is disabled.

---

## v1.1–v1.7 — Red Deck stake progression

| Version | Stake | New adaptation focus |
|---|---|---|
| **v1.1** | **Red** | **No Small Blind reward money** |
| v1.2 | Green | Green Stake score scaling |
| v1.3 | Black | Eternal Joker adaptation |
| v1.4 | Blue | Reduced-discard adaptation |
| v1.5 | Purple | Purple Stake score scaling |
| v1.6 | Orange | Perishable Joker adaptation |
| v1.7 | Gold | Rental Joker adaptation and Red Deck all-stakes validation |

Each stake milestone modifies effectiveness, feasibility, economy, thresholds, and Bond realization/prescription behavior only where the stake genuinely changes them. Stake milestones must reuse the permanent canonical Bond/composition system rather than reintroduce categorical strategy trees.

### Higher-stake economy and hand-efficiency requirement

- [ ] Explicitly prioritize clearing blinds with as few hands as safely possible to maximize unused-hand cash-out.
- [ ] Pursue >2× blind-target finishes for extra-cash benefit when the line is strategically safe and EV-positive.

---

## v2+ — Additional decks

Planned deck order after Red Deck completion:

1. **Blue Deck — v2.x**
2. **Yellow Deck — v3.x**
3. **Green Deck — v4.x**
4. **Black Deck — v5.x**

Additional-deck cartridges reuse the same canonical Balatro Bond/composition architecture and supply only deck/stake-specific modifiers and thresholds where necessary.
