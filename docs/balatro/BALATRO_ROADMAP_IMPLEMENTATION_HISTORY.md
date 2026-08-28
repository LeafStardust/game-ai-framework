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

## D1 authority-latency stabilization — 2026-08-28 — ACTIVE

After SHOP latency closed, the broader v1.0 authority-latency pass moved to D1. `PathAwareLiveHandActionDecisionEngine` now records a non-overlapping `D1LatencyBreakdown` across `base_policy`, `adaptive_search`, `confirmation_search`, `immediate_fallback_search`, `adaptive_authority`, `consensus_recovery`, `strategy_health`, and residual. This diagnostic does not change D1 action authority or search thresholds.

### Focused D1 evidence

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

The pathological decision was approximately **8.701761 s total**, of which **8.693686 s** was `immediate_fallback_search`, with adaptive/confirmation search at zero. Its rationale reported `D1 wall-clock budget exhausted before pace fallback completed`. Excluding that one event, D1 mean was about **1.38 s**, max about **3.60 s**, fallback mean about **0.54 s**, and fallback max about **1.72 s**. Therefore the general D1 architecture is not the measured blocker; the immediate-fallback candidate-ranking boundary is.

### Root cause and canonical repair

`LiveBlindClearPlanner._candidate_actions()` historically generated every legal Play/Discard and ranked them using `_play_priority` / `_discard_priority`. `_play_priority` calls the expensive live evaluator. The planner's wall-clock deadline was previously checked only by `_consume_node()` when `_estimate_action()` began, so candidate ranking could consume most or all of the nominal search budget while `nodes_evaluated == 0`.

An older module, `games/balatro/d1_candidate_deadline_policy.py`, had already attempted to patch this hole and later added a 0.75 s initial-root bootstrap. **That wrapper was not installed by the current `games/balatro/__init__.py`**, so it did not protect the focused live run. Future work must not “fix” this by reinstalling the old wrapper and creating two `_candidate_actions` authorities.

The deadline invariant now lives directly in canonical `LiveBlindClearPlanner`:

- hard deadline checks occur before/after candidate generation and before/after each expensive candidate-priority evaluation;
- `_consume_node()` uses the same canonical hard-deadline check;
- the initial root has a **0.75 s candidate-bootstrap envelope**, capped by the hard search deadline;
- after at least one Play candidate has been scored, the initial root may stop expanding candidate breadth once that soft envelope expires and proceed with the bounded evidence already available;
- if that initial Play bootstrap has consumed the soft envelope, it does not spend another root pass ranking Discards before any usable plan exists;
- child/later ranking retains the ordinary configured hard deadline; the 0.75 s soft bootstrap is initial-root-only;
- D1 survival objective, planner authority, hidden-information restrictions, and downstream strategy-health semantics are unchanged.

`games/balatro/d1_candidate_deadline_policy.py` is now a compatibility-only no-op shim. `LiveBlindClearPlanner` is the **sole D1 candidate-deadline authority**. Do not restore the monkeypatch unless a future architecture explicitly replaces the canonical implementation.

Focused deterministic coverage lives in `tests/balatro/test_balatro_d1_candidate_deadline.py` and covers: expired hard deadline before first projection, hard expiry between expensive candidate projections, bounded initial-root bootstrap, and unchanged priority ordering when the bootstrap is effectively disabled. The assistant wrote/updated this coverage but did **not** execute it.

### Next validation gate

Because code and tests changed after the previously green suite, local validation must now run:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_d1_candidate_deadline.py tests/balatro/test_balatro_d1_latency_breakdown.py
python -m pytest -q tests/balatro
```

If green, run exactly one normal focused live attempt:

```powershell
.\BalatroAgentToggle.bat
```

Then compare `D1 latency` breakdowns against the 41-decision baseline above. The specific success condition is that the ~8.69 s `immediate_fallback_search` class of spike disappears or materially collapses without creating a new dominant D1 bucket. Do not tune adaptive-search budgets, Strategy Health, or unrelated D1 scoring unless the new profile measures them as the next blocker.

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
