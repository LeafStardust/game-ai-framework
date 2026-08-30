# Balatro Roadmap Implementation History

This document preserves completed roadmap implementation history that remains useful and accurate after the 2026-08-27 roadmap reset. It is historical evidence, not an active instruction to keep expanding these systems before the Red/White competence gate passes.

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
| **v1.0.0** | **Red Deck / White Stake release baseline: coherent build planning, strategy-aware D1–D14 decisions, bounded live search, economy/shop competence, boss handling, ordering, diagnostics, and autonomous unseeded win validation** |

## v1.0.0 — Red Deck / White Stake Competence — COMPLETE

Released: **2026-08-20**

The original v1.0.0 release used the historical strategy-tree/Gold-Silver-Bronze architecture. That release evidence remains historical record even though current production later migrated to Bond/composition.

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

## v1.0.x Bond/composition and semantic implementation work already completed

- [x] Replaced active Gold/Silver/Bronze strategy-tree machinery with canonical weighted Bonds, R1–R5 development, realization, sparse relationships, motifs, composition, power-engine selection, and prescriptions.
- [x] Kept `LOCKED` / `R0` / `R1–R5` development separate from `DORMANT` / `PARTIAL` / `ACTIVE` / `MATURE` realization.
- [x] Added Bond-native live-monitor diagnostics.
- [x] Removed retired tracker/tier and pre-Bond `PlaystyleIntent` authority from active paths found by validation.
- [x] Added bounded canonical Bond-transition value to D2 Joker acquisition/replacement.
- [x] Added canonical pivot authority and realized-engine preservation.
- [x] Added a pure Build Health evaluator with Survival, Immediate Scoring, Scaling, Coherence, and Runway dimensions.
- [x] Added midgame scaling-deficit detection.
- [x] Integrated Build Health/Bond evidence into shop buy/replace/reroll decisions.
- [x] Added bounded complementary-shop planning.
- [x] Added Build Health and inactive-engine diagnostics.
- [x] Corrected Burnt/Banner execution interaction.
- [x] Added late-game cash protection.
- [x] Cached per-decision Bond hand intents.
- [x] Audited multiple 2026-08-24/25 live batches and corrected false hand-Bond membership, random lifecycle drift, D1 deadline leaks, production/canonical class splits, Burglar/discard interactions, replacement rescue defects, Joker Stencil admission, Blueprint ordering, Dagger feed projection, held-card shortlist behavior, Standard-pack bloat, phantom strategy formation, false relationships, missed Campfire fuel transactions, weak rerolls, D1 search/controller disagreement, timeout discards, Planet promotion, stale telemetry, and attempt-sequence reset issues.
- [x] Removed the unvalidated synthetic Red/White “chips axis / Mult axis” correction layer after live validation showed category-level overrides distorted decision making.
- [x] Extended literal current/candidate score authority across played-card chips, secret hands, public stochastic score expectation, stateful conditional contexts, post-transaction cash/resources, Banner resources, and legal copy-Joker ordering.
- [x] Completed contextual audits for Joker Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm.
- [x] Repaired D2 replacement around literal common-baseline score, economy, Negative retention, realized-engine disruption, and exact selected shop identity.
- [x] Completed static Boss-Blind production-authority inventory with centralized Chicot bypass.
- [x] Replaced D11 fixed future Joker/Planet priors with bounded public-pool expectation.
- [x] Replaced D8 Buffoon, Celestial, Standard, Arcana, and Spectral fixed family priors with public-mechanics expectation.
- [x] Extended shared score probes to Five of a Kind, Flush House, and Flush Five.
- [x] Replaced Hanged Man's blanket Blue-Joker veto with an exact deck-size tradeoff.
- [x] Completed major Tarot/Spectral/pack semantic audits including High Priestess, Judgement, Emperor, Ouija, Ectoplasm, Wheel, Soul, Cryptid, Familiar, Grim, Incantation, Immolate, and Black Hole.
- [x] Added SHOP runtime bounds for nested expectations and hypothetical planning.
- [x] Expanded live supervisor, monitor, diagnostics, logging, restart, and validation infrastructure.

## D14 / D11 SHOP latency stabilization — 2026-08-28 — CLOSED

D14 remains final SHOP authority and D11 remains reroll authority. The performance work preserved public-information boundaries, stop-loss/resource semantics, settlement behavior, and conservative omitted-mass treatment.

Pre-Joker-bound focused evidence localized reroll-active D11 `_future_shop_ev()` to approximately **20.8 s mean**. Subsequent bounded Joker and Tarot expectation work reduced reroll-active D11 future work to approximately **3.17 s mean** and total reroll-active D14 to approximately **3.59 s mean**, roughly an **85% reduction**. No remaining multi-second hidden residual was observed. The D14/D11 SHOP latency blocker is closed unless new evidence reopens it.

## D1 authority-latency stabilization — 2026-08-28/30 — CLOSED

Earlier focused runs exposed repeated 20–30 s D1 fallback spikes. Root causes included semantic prefilter rescans and later a passive-rule-aware root structural pre-beam that could spend tens of seconds before consuming node 1.

Repairs included:

- deadline-aware semantic D1 prefilter (`76dc7b9...`) with focused regression (`2ceb8a6...`);
- root structural ranking wall-clock checks (`9653f1a...`) with regression coverage (`222f27a...`).

The current validated production baseline after these fixes reported D1 mean approximately **1.53 s** and max approximately **2.70 s** across its three-run baseline, with zero illegal actions. The pre-node budget pathology is closed unless fresh evidence reproduces it.

## Live tuning failure containment — 2026-08-30 — CLOSED

Study `phase-a-native-ready-restart-20260830-b` exposed a runtime-control defect in the tuner itself. One candidate trial failed when `SELECTING_HAND` became public-state stable but native hand controls did not become ready before timeout. Because `study.optimize(... catch=(RuntimeError,))` returned normally, the outer loop started subsequent trials from the still-active `SELECTING_HAND` run, creating guaranteed preflight failures.

Repair:

- tuner halts the invocation immediately after any non-`COMPLETE` live trial (`a745473e...`);
- regression coverage locks the fail-fast behavior (`87c10f69...`).

The restart helper remains deliberately loss-only and does not force-reset an active run after an observation/runtime failure.

## Phase-A Bond composition tuning — 2026-08-30 — COMPLETE / NO PROMOTION

The first completed exploratory calibration cycle tuned only:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1-R5 pivot resistance.

### Historical invalidated studies

`phase-a-native-ready-restart-20260830-a` produced an apparently strong Trial 8 with objective **25.4396657042** and average Ante **5.33**, but detailed logs exposed the D1 pre-node runtime defect described above. The gameplay/runtime SHA changed, so the study is forensic evidence only.

`phase-a-native-ready-restart-20260830-b` was invalidated after the live-tuning failure-containment defect described above changed the tuner/runtime contract.

### Current completed study

Study: `phase-a-native-ready-restart-20260830-c`

Repository SHA: `87c10f69ba43fb6fb4069b8c93fa8c48962fad54`

Protocol:

- Red Deck / White Stake;
- authoritative live unseeded;
- 3 completed attempts per exploratory trial;
- 10 completed trials total.

Results:

- production-default Trial 0 objective: **19.4166666667**;
- strongest candidate Trial 6 objective: **18.2347883598**;
- no candidate exceeded baseline;
- no candidate won;
- no 20-vs-20 promotion holdout was justified.

Outcome: **production Bond calibration retained unchanged; Phase-A exploratory gate closed with no promotion.** Broader tuning families remain locked until explicitly selected by the active roadmap.

## Bond numerical tuning foundation — IMPLEMENTED

- [x] Architecture, objective, anti-overfitting, storage/provenance, pruning, and promotion contract documented.
- [x] Typed immutable Bond calibration snapshot implemented.
- [x] Audited parameter routing with default-equivalence/validation tests implemented.
- [x] Offline seeded and authoritative-live evaluator boundaries implemented.
- [x] Optional Optuna dependency isolated from normal live imports.
- [x] Persistent studies, parameter/objective schema versions, resumable compatibility checks, and production-baseline queuing implemented.
- [x] Initial low-dimensional Phase-A composition/pivot search space implemented.
- [x] Fresh-boundary live preflight, baseline reports, holdout validation, and conservative promotion comparison implemented.
- [x] First authoritative-live Phase-A exploratory cycle completed with no production promotion.

## Retained design principles

- Winning the run is the normal gameplay objective.
- Hidden future information remains forbidden.
- Literal Balatro mechanics remain authoritative over synthetic strategy labels.
- Bond/composition remains the canonical strategic representation unless a future roadmap explicitly replaces it after competence stabilization.
- Previous implementations may be refactored or simplified, but should not be deleted merely because they are not currently active development priorities.
