# Roadmap

> The roadmap tracks active milestones, not release notes. Detailed implementation evidence belongs in tests, logs, commits, `CHANGELOG.md`, and release documentation.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. The current universal strategic layer is the canonical **Bond/composition system**. A replaceable **deck/stake cartridge** modifies effectiveness, feasibility, economy, and thresholds for the observed live run.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. Hidden future information remains excluded: no RNG-state/seed exploitation and no ordered future draw pile.
>
> The active Red/White competence doctrine and semantic/runtime repair queue are defined in [`docs/balatro/BALATRO_RED_WHITE_COMPETENCE_ROADMAP.md`](docs/balatro/BALATRO_RED_WHITE_COMPETENCE_ROADMAP.md). Future contributors must read that document before changing D1/D2/D14 valuation or adding live-run corrections.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 Foundation + autonomous integration | Complete | — |
| **v1.0.0 Red Deck / White Stake competence** | **Complete** | Released 2026-08-20 |
| **v1.0.x Red/White semantic/runtime competence repair** | **In progress / calibration frozen** | Repair current live contradictions → clean 3-run baseline → Phase-A candidates → ≥20-episode-per-arm promotion/holdout |
| **Offline Bond numerical tuning (Optuna)** | **Foundation implemented / frozen pending clean semantics** | No candidate search while semantic/runtime defects remain |
| v1.1–v1.7 Red Deck stake progression | Next | Begins from Red Stake after Red/White competence gate |
| Fresh-profile collection progression | **Retired from active roadmap** | Winning is the sole gameplay objective; collection-first may not override competence |
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
- [x] Keep ordinary undiscovered-item preference bounded to a one-ULP tie-break so discovery metadata cannot override competence.
- [x] Add strategy/build diagnostics to the live monitor and structured run logs.
- [x] Preserve normal Steam progression and hidden-information restrictions.

### Acceptance evidence

- [x] Full deterministic repository suite passed after the v1.0.0 release migration: **1,787 tests on 2026-08-18**.
- [x] Completed an **unseeded, fully autonomous Red Deck / White Stake win** on 2026-08-18 against Amber Acorn with no manual gameplay input after activation and normal Steam progression preserved.
- [x] Fixed the `won=true` / `ROUND_EVAL` terminal-detection gap exposed by that winning run and covered the fix deterministically.

---

## v1.0.x — Red/White semantic/runtime competence repair — IN PROGRESS

The initial Red/White release demonstrated competence, but repeated live calibration exposed a higher-level decision gap: the agent can own individually useful pieces while the **realized build remains inactive, incoherent, under-utilized, poorly valued, or too slow to scale**. The 2026-08-25 batch also showed that local correction layers can make this worse when they replace literal Balatro mechanics with synthetic scoring categories.

Canonical architecture references:

- [`docs/balatro/BALATRO_RED_WHITE_COMPETENCE_ROADMAP.md`](docs/balatro/BALATRO_RED_WHITE_COMPETENCE_ROADMAP.md) — active competence doctrine, examples, and current repair queue.
- [`docs/balatro/BALATRO_STRATEGY_FORMATION.md`](docs/balatro/BALATRO_STRATEGY_FORMATION.md) — strategy formation, R0 evidence, pinning, construction/preservation/execution authority.
- [`docs/balatro/BALATRO_BUILD_HEALTH.md`](docs/balatro/BALATRO_BUILD_HEALTH.md) — literal score projection vs structural Build Health.
- [`docs/balatro/BALATRO_BOND_TUNING.md`](docs/balatro/BALATRO_BOND_TUNING.md) — numerical tuning boundary and promotion protocol.

### Non-negotiable competence doctrine

- **Winning the run is the sole gameplay objective.** Collection-first / unlock-chasing behavior is retired from the active roadmap and must not sacrifice win probability.
- Ante 1–2 is a **survival phase, not a strategy-free phase**. Buy enough temporary scoring to survive while already recognizing and developing coherent Bonds/strategies from the first relevant evidence.
- Scoring is evaluated by **literal Balatro arithmetic and exact modeled mechanics**. Bond rank, motif state, strategy commitment, composition coherence, or broad “chips/Mult coverage” categories cannot manufacture scoring power.
- Positive R0 evidence is strategically visible from the beginning of the run. Strategy does not suddenly switch on at Ante 3.
- Context-sensitive Joker value must come from exact mechanics and current state. Stencil empty-slot value, Card Sharp repetition, Ride the Bus resets, Bull/Bootstraps cash scaling, Banner discard count, Green Joker no-discard pressure, and copy-Joker targeting are examples.
- Shop, replacement, pack, consumable, reroll, economy, and D1 choices must be judged by expected contribution to **winning the current run**, not incompatible local utility totals.
- Mechanically contradictory or clearly dominated actions are **semantic/runtime defects first**, not numerical-tuning noise.

### Canonical Bond/composition migration and completed work

- [x] Replace active Gold/Silver/Bronze strategy-tree machinery with canonical weighted Bonds, R1–R5 development, realization, sparse relationships, motifs, composition, power-engine selection, and prescriptions.
- [x] Keep `LOCKED` / `R0` / `R1–R5` development separate from `DORMANT` / `PARTIAL` / `ACTIVE` / `MATURE` realization.
- [x] Make live monitor diagnostics Bond-native: power engine, relevant Bonds, contribution/next rank, realization, motifs, synergies/conflicts, and prescriptions.
- [x] Remove retired tracker/tier dependencies from active Build Health, D1, D2, Mouth, Planet compatibility, and runtime paths found by deterministic/live validation.
- [x] Remove the remaining pre-Bond `PlaystyleIntent`/Ante-lock authority from D1, D2, D7, D9, D13, telemetry, and production runner wiring; retain only mechanical build profiling beneath canonical Bond/composition strategy.
- [x] Retire neutral playstyle compatibility shells and replace timestamp/batch/release-named installed modules with stable mechanic/policy names.
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
- [x] Audit the 2026-08-24/25 Red/White run batch and correct false hand-Bond membership, random lifecycle drift that fabricated component relationships, and held-The-Sun searches that escaped D1's hard deadline.
- [x] Audit every decision in the fresh three-run `28342616` baseline and correct the production/canonical Joker/pack/shop class split; Burglar coexistence with dormant discard triggers, discard-count payoffs, extra-discard sources, vouchers, and Purple Seals; negative raw replacements rescued by Bond bonuses; X1 full-roster Joker Stencil admission; hand-specific Blueprint ordering; Eternal Dagger feed projection; held Steel/Gold/Seal shortlist substitution; post-deadline D1 re-evaluation; and zero-demand Standard-pack deck bloat. This semantic/runtime correction invalidates that baseline.
- [x] Audit every decision in the subsequent three-run `817ac2b3` batch and correct phantom strategy formation from stock-deck card counts, false Mime/Blackboard/Raised-Fist relationships, under-recruitment of coherent shop engines, isolated Obelisk admission, missed Campfire fuel transactions, weak late rerolls, D1 search/controller disagreement, destructive timeout discards, five-Joker Blueprint ordering, off-route Planet promotion, stale Mouth telemetry, and new-attempt sequence resets. This semantic/runtime correction invalidates that batch as a calibration baseline.
- [x] Remove the unvalidated synthetic Red/White “chips axis / Mult axis” correction layer after the 2026-08-25 live batch showed that category-level overrides distorted decision making.
- [x] Complete literal current/candidate score authority: D2 includes played-card chips, secret hands, public stochastic score expectation, stateful conditional contexts, post-transaction cash/resource state, next-round Banner resources, and legal copy-Joker ordering; the final category-only early-Joker force-buy is removed.
- [x] Complete the named contextual-Joker implementation audit for Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm, including post-transaction cash, next-round Banner resources, and prospective copy-Joker ordering.
- [x] Repair D2 replacement implementation around literal common-baseline score, post-transaction cash, economy, Negative retention, realized-engine/strategy disruption, and exact selected shop-copy identity.
- [x] Complete the static Boss-Blind production authority inventory; omitted dispatch-table names are accounted for by authoritative live state or explicit D1 transition/score transforms, with centralized Chicot bypass.
- [x] Replace D11's fixed future Joker/Planet utility priors with public-pool D2/D4/D14 expectation and fail closed on unresolved Tarot future value.
- [x] Replace all five D8 booster-family fixed hit/value priors with public-mechanics expectation: Buffoon uses the current eligible Joker pool and D2/D14; Celestial uses the eligible Planet pool and literal permanent-level projection; Standard uses the exact rank/suit/enhancement/seal/edition generator plus literal Blue-Joker/Hologram deck-growth mechanics; Arcana uses public Tarot/Spectral pools, Omen Globe's exact 80/20 branch and soulable overrides; Spectral uses the public Spectral pool plus the exact soulable Black-Hole/Soul override. Unresolved visible outcomes fail to opened-pack Skip=0 and conservative one-offer lower bounds avoid hidden-content assumptions.
- [x] Extend the shared literal score/D2 probe catalogue to Five of a Kind, Flush House, and Flush Five so secret-hand development is not ignored by shop valuation.
- [x] Replace Hanged Man's blanket Blue-Joker veto with a target-level tradeoff using Blue Joker's exact +2-Chips-per-card deck-size coefficient on B6's existing chip-normalized intrinsic scale.
- [x] Complete the pack/consumable semantic audit: opened-pack Skip is sunk-cost zero; High Priestess, Judgement, Emperor, Ouija, Ectoplasm, Wheel, Soul, Cryptid, Familiar, Grim, Incantation, Immolate, Black Hole and the five D8 booster families use public-mechanics expectation/targeting with semantic execution guards where required. Shared hand-size opportunity cost now prices Ouija/Ectoplasm without fixed penalties, and Ectoplasm values Negative through marginal future-Joker capacity rather than a universal edition constant.

### Current semantic/runtime repair queue — BLOCKS CALIBRATION

- [x] Make literal current/candidate score projection authoritative and audit any layer that substitutes synthetic categories for actual marginal scoring. Implementation audit complete; current-HEAD regression validation remains pending.
- [x] Audit contextual Joker valuation beginning with Joker Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm. Implementation audit complete; current-HEAD regression validation remains pending.
- [ ] Verify R0/FORMING/PINNED strategy authority affects acquisition from Ante 1 without delaying survival or collecting unrelated Bond labels. Implementation is installed; local verification remains pending.
- [ ] Repair D14 cross-family shop arbitration so visible Jokers, vouchers, packs, consumables, rerolls, and economy are compared on run-winning value rather than incompatible local utility units. D11 Joker/Planet and all five D8 booster families are implementation-repaired; held-Tarot/future-consumable value remains open.
- [x] Repair D2 replacement so incumbent and candidate are compared by actual current score, prospective scaling/economy, strategy realization, and disruption. Implementation audit complete; local regressions remain part of the current-HEAD suite gate.
- [x] Repair D1 discard selection at the actual planner/controller authority; repeated one-card discards must be exceptional when several dead cards can safely be cycled.
- [x] Audit pack and consumable decisions for both unjustified skipping and unjustified speculative spending. Implementation audit complete across all five D8 booster families and the known D9/D10 semantic blockers; current-HEAD regression validation remains pending.
- [x] Re-audit boss-specific execution against exact mechanics and legality. Static production inventory complete; newest Verdant/Crimson regressions remain pending the current-HEAD suite run.
- [x] Diagnose and fix the three-attempt supervisor/shutdown crash observed after the 2026-08-25 batch; the bounded supervisor now stops after attempt 3 and the historical post-`run_finished` crash is retired unless reproduced on unchanged current HEAD.
- [ ] Add direct regressions for every live defect before another authoritative batch.
- [ ] Run `tests/balatro` on the current semantic-repair HEAD and require green before live validation. The latest validated checkpoint predates the current pack/consumable completion, all-family D8 expectations, D2 played-card-chip/stochastic expectation, Hanged Man/Blue Joker, and subsequent corrections.
- [ ] Execute and inspect a clean 3-run production-default authoritative live baseline only after the semantic/runtime repair queue is clear.
- [ ] Run Phase-A candidate trials only after that baseline is clean; any semantic/runtime fix invalidates and restarts the study under the new repository SHA.

### Automated Bond numerical tuning — FOUNDATION IMPLEMENTED / FROZEN

Detailed contract: [`docs/balatro/BALATRO_BOND_TUNING.md`](docs/balatro/BALATRO_BOND_TUNING.md).

Purpose: replace endless manual coefficient guessing with reproducible offline optimization of **approved numerical parameters**, while preserving human-defined Bond semantics and live-agent determinism.

Implementation status:

- [x] Document architecture, objective, anti-overfitting rules, storage/provenance, pruning constraints, and promotion gates.
- [x] Introduce a typed immutable Bond calibration snapshot whose defaults exactly reproduce current production behavior.
- [x] Route one small audited parameter family through that snapshot and add default-equivalence/validation tests.
- [x] Add offline seeded and authoritative-live batch evaluator boundaries with structured trial metrics and exact run/seed provenance.
- [x] Add Optuna as an optional development/tuning dependency only; normal live-agent imports do not depend on it.
- [x] Add persistent Optuna study storage, parameter/objective schema versions, resumable compatibility checks, and production-baseline queuing.
- [x] Implement the first low-dimensional Phase-A composition/pivot search space.
- [x] Add fresh-boundary live preflight, baseline-aware reports, holdout validation, and conservative live promotion comparison.
- [ ] Unfreeze candidate search only after the current semantic/runtime repair queue and a clean unchanged-HEAD production baseline pass.
- [ ] Promote only after a fresh comparison with **at least 20 completed episodes per arm** and all implemented non-regression/pathology checks pass.
- [ ] Expand to realization, D1 execution, D2/shop/resource, and cross-system calibration only after earlier phases are stable.

The optimizer may tune bounded numerical values such as contributor weights, R1–R5 thresholds, realization cutoffs where empirical, synergy/conflict coefficients, pivot resistance, motif values, bounded prescription strengths, and resource-policy thresholds. It may **not** invent/remove Bonds, change mechanical truth, weaken boss/legal/survival authority, use hidden information, or automatically promote its own output.

The historical `e0cb0984` and subsequent invalidated live baselines are forensic/reference evidence only because later semantic/runtime fixes changed the repository SHA. Do not resume or compare a current candidate against those studies as if they were unchanged-code controls.

### Calibration gate before Red Stake

Do not begin Red/Red `1.1.0` implementation until:

- [x] the Balatro deterministic suite is green on the current architecture baseline;
- [ ] the current semantic/runtime competence repair queue is complete;
- [ ] repeated live losses no longer show obvious mechanically contradictory, dominated, “full board but non-functioning build,” or “recognized engine but unused mechanic” failures;
- [ ] at least one fresh unchanged-HEAD Red/White validation batch contains an Ante-8 clear without a repeated release-blocking decision defect;
- [ ] the post-run batch supervisor/shutdown path completes without crashing.

Automated Optuna tuning is not itself a prerequisite for Red Stake if Red/White reaches the competence gate first, but once semantics are correct it remains the preferred method for systematic coefficient refinement.

---

## Fresh-profile collection progression — RETIRED FROM ACTIVE ROADMAP

Collection-first mode is no longer an active gameplay objective. The permanent Balatro agent is evaluated on winning the current run.

Rules going forward:

- Collection/unlock state may be observed for diagnostics or bounded exact-tie metadata only.
- Collection state must not turn a losing or strategically inferior action into the selected action.
- No collection campaign may intentionally sacrifice blind-clear probability, a functioning engine, economy required for survival, or a superior win-oriented purchase.
- Existing legacy collection tooling may remain in the repository until separately removed, but it is not part of the Red/White competence contract and must not leak authority into normal play.

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

Each stake milestone modifies effectiveness, feasibility, economy, thresholds, and Bond realization/prescription behavior only where the stake genuinely changes them. Stake milestones must reuse the permanent canonical Balatro Bond/composition system rather than reintroduce categorical strategy trees.

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