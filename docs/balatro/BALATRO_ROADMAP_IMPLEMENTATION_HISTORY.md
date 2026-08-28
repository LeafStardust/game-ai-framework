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

### Focused profiler evidence

Pre-Joker-bound focused evidence localized reroll-active D11 `_future_shop_ev()` to approximately **20.8 s mean**, split into approximately **11.3 s future Joker**, **9.3 s future Tarot**, **0.15 s future Planet**, and effectively zero expected-max residual.

After commit `1cdb6390` bounded large-pool Joker edition branches conservatively, focused run `balatro-20260828T103057Z-67e9b911-attempt-001` measured:

- reroll-active `_future_shop_ev()` mean: **~11.55 s**;
- nested future Joker mean: **~3.63 s**;
- nested future Tarot mean: **~7.89 s**;
- nested future Planet mean: **~0.03 s**;
- future residual: **0 s**.

The subsequent large-pool Tarot bound preserved full-pool preflight and divided evaluated positive gain by the full eligible-pool count so omitted mass remained literal zero rather than being renormalized. The next focused run measured:

- reroll-active `_future_shop_ev()` mean: **~3.17 s**;
- future Tarot mean: **~2.02 s**;
- future Joker mean: **~1.10 s**;
- future Planet mean: **~0.054 s**;
- future residual: **0 s**;
- total reroll-active D14 mean: **~3.59 s**.

This is approximately an **85% reduction** from the original ~20.8 s D11 future bottleneck. No remaining multi-second hidden residual was observed. The D14/D11 SHOP latency blocker is therefore closed unless new evidence reopens it; do not continue shaving Planet/residual or weaken Joker/Tarot semantics without a new measured reason.

## D1 authority-latency stabilization — 2026-08-28 — REOPENED

After SHOP latency closed, the broader v1.0 authority-latency pass moved to D1. `PathAwareLiveHandActionDecisionEngine` records a non-overlapping `D1LatencyBreakdown` across `base_policy`, `adaptive_search`, `confirmation_search`, `immediate_fallback_search`, `adaptive_authority`, `consensus_recovery`, `strategy_health`, and residual. This diagnostic does not change D1 action authority or search thresholds.

### Earlier pre-fix evidence

Focused run `balatro-20260828T114850Z-0fbca9a7-attempt-001` produced **41 D1 decisions** and reached Ante 6 / The Head before a natural `GAME_OVER`. The profile measured approximately:

- total D1 mean: **1.56 s**;
- total D1 median: **1.59 s**;
- total D1 maximum: **8.70 s**;
- `base_policy` mean: **0.34 s**;
- `adaptive_search` mean: **0.40 s**;
- `confirmation_search` mean: **0.07 s**;
- `immediate_fallback_search` mean: **0.74 s**;
- `immediate_fallback_search` maximum: **8.69 s**;
- Strategy Health mean: about **0.003 s**;
- residual: effectively zero.

The pathological decision was approximately **8.701761 s total**, of which **8.693686 s** was `immediate_fallback_search`, with adaptive/confirmation search at zero. Its rationale reported `D1 wall-clock budget exhausted before pace fallback completed`.

### Earlier repair and temporary closure

Hard deadline checks were moved into `LiveBlindClearPlanner` before/after candidate generation and around expensive candidate-priority evaluation, with a 0.75 s initial-root bootstrap. Focused run `balatro-20260828T123054Z-88fe4bcc-attempt-001` then produced **73 D1 decisions** with approximately **1.78 s mean / 1.97 s median / 4.37 s max**, no `budget_exceeded=True` records, and no `D1 wall-clock budget exhausted` messages. That evidence temporarily closed the gate.

### Replacement competence batch reopened the gate

After the Green Joker no-discard semantic fix, replacement three-run batch `balatro-20260828T133038Z-8d493563` was used as a new competence baseline. It finished **0/3**: attempt 1 lost at Ante 4 boss The Plant, attempt 2 at Ante 2 boss The Needle, and attempt 3 at Ante 1 Big Blind. The win rate itself is not the blocker; D1 latency is.

Attempt 1 contained 67 D1 decisions at approximately **3.62 s mean / 3.04 s median / 6.08 s max**, 28 explicit wall-clock-budget exhaustion messages, and 15 decisions above 5 s.

Attempt 2 exposed the severe recurrence:

- **34 D1 decisions**;
- total mean: **~16.62 s**;
- total median: **~23.51 s**;
- total max: **~30.64 s**;
- `immediate_fallback_search` mean: **~15.15 s**;
- `immediate_fallback_search` max: **~30.07 s**;
- **22** explicit `D1 wall-clock budget exhausted before pace fallback completed` decisions;
- **22** decisions above 20 s.

Representative fallback spikes were approximately 26.76 s, 26.82 s, 22.94 s, 23.44 s, 23.27 s, 30.07 s, 27.51 s, and 29.25 s. The final Needle decision was approximately **30.24 s total / 29.25 s fallback**. It is not valid to claim this latency caused the 720/800 loss, but the competence/calibration gate is blocked regardless.

Attempt 3 contained 15 D1 decisions at approximately **3.39 s mean / 3.10 s median / 6.78 s max**, with 6 budget-exhaustion messages.

### Root cause of recurrence and current repair

The canonical planner deadline was present, but `semantic_search_guard_policy.py` still overrides `LiveBlindClearPlanner._candidate_actions`. Its Play prefilter could classify hundreds of legal play subsets, then rescan the same subsets separately for every poker-hand family, with no hard or 0.75 s bootstrap checkpoint inside those loops. Larger live hands, especially Juggler's hand-size increase, made this pre-node semantic work explode into the observed 20–30 s fallback calls.

Commit `76dc7b90451bf82c3d0535913b1cbd380311c896` (`fix(balatro): bound semantic D1 candidate prefilter`) keeps the existing semantic `_candidate_actions` wrapper but makes that wrapper deadline-aware:

- each processed Play is classified once and cached instead of being rescanned per hand family;
- Play and Discard prefilters check the hard planner deadline between candidates;
- initial-root semantic work also observes the existing 0.75 s bootstrap between candidates;
- short-play reserve scanning stops at the same bounds;
- if initial Play work consumes the root bootstrap, the wrapper returns usable ranked Plays rather than spending another root pass on Discards;
- gameplay thresholds, search widths, hidden-information rules, and D1 survival/value semantics are unchanged.

Regression commit `2ceb8a6b20c6c1b519417370177c33022cb4a081` (`test(balatro): cover bounded semantic D1 prefilter`) verifies that a large Play prefilter classifies each candidate at most once and stops after the first processed candidate when the root soft deadline is considered expired.

The assistant did **not** execute these tests. Validation is pending. The next gate is: targeted semantic-prefilter regression → full `tests/balatro` → **one focused normal live run**. Do not run another three-attempt competence batch until that focused run shows the pathological 20–30 s fallback/budget-exhaustion class is gone again.

## Bond numerical tuning foundation — IMPLEMENTED / FROZEN

- [x] Architecture, objective, anti-overfitting, storage/provenance, pruning, and promotion contract documented.
- [x] Typed immutable Bond calibration snapshot implemented.
- [x] Audited parameter routing with default-equivalence/validation tests implemented.
- [x] Offline seeded and authoritative-live evaluator boundaries implemented.
- [x] Optional Optuna dependency isolated from normal live imports.
- [x] Persistent studies, parameter/objective schema versions, resumable compatibility checks, and production-baseline queuing implemented.
- [x] Initial low-dimensional Phase-A composition/pivot search space implemented.
- [x] Fresh-boundary live preflight, baseline reports, holdout validation, and conservative promotion comparison implemented.

## Retained design principles

- Winning the run is the normal gameplay objective.
- Hidden future information remains forbidden.
- Literal Balatro mechanics remain authoritative over synthetic strategy labels.
- Bond/composition remains the canonical strategic representation unless a future roadmap explicitly replaces it after competence stabilization.
- Previous implementations may be refactored or simplified, but should not be deleted merely because they are not currently active development priorities.
