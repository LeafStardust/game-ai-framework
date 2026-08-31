# Balatro Implementation History

This document is historical evidence only. It is **not** a roadmap, queue, handoff, or source of current development priority.

The only authoritative roadmap is the repository-root `ROADMAP.md`. If this file conflicts with `ROADMAP.md`, ignore this file for current work.

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

## v1.0.0 — Red Deck / White Stake baseline — complete

Released 2026-08-20.

The original release used the historical strategy-tree/Gold-Silver-Bronze architecture. Later production migrated to Bond/composition; the release evidence remains historical.

Completed release scope included blind-clear probability authority, held-resource preservation, coherent build intent across D1-D14, explicit conflicts, Joker ordering, forced-card/boss handling, bounded interactive search, economy/reroll protections, diagnostics, normal Steam progression, and hidden-information restrictions.

Acceptance evidence included a full deterministic repository pass of 1,787 tests on 2026-08-18 and an unseeded autonomous Red Deck / White Stake win against Amber Acorn on 2026-08-18.

## v1.0.x implementation history

Completed work includes:

- migration from the old strategy tree to canonical weighted Bonds, R1-R5 development, realization, relationships, motifs, composition, power-engine selection and prescriptions;
- separation of Bond development from realization;
- Bond-native diagnostics;
- removal of retired tracker/tier and pre-Bond intent authority from active paths;
- bounded Bond-transition value, pivot authority, realized-engine preservation and Build Health;
- midgame scaling-deficit detection and Build Health/Bond integration into shop decisions;
- bounded complementary-shop planning;
- contextual fixes covering discard/Joker interactions, lifecycle drift, D1 deadlines, class splits, replacement rescue, ordering, Dagger projection, held-card shortlists, Standard-pack bloat, strategy formation, relationships, Campfire fuel, rerolls, timeout behavior, Planet promotion and stale telemetry;
- removal of the synthetic chips-axis/Mult-axis correction layer after it distorted decisions;
- extension of literal score authority across played-card chips, secret hands, public stochastic score expectation, conditional contexts, post-transaction cash/resources and copy-Joker ordering;
- D2 replacement repairs around literal score, economy, Negative retention, realized-engine disruption and exact shop identity;
- centralized Boss-Blind/Chicot handling;
- bounded public-pool expectation for future Jokers, Planets and booster families;
- extended score probes for secret hands;
- Hanged Man/Blue Joker exact deck-size tradeoff;
- Tarot/Spectral/pack semantic audits;
- SHOP runtime bounds for nested expectations;
- expanded supervisor, monitor, diagnostics, logging, restart and validation infrastructure.

## Closed runtime blockers

### D14 / D11 SHOP latency — closed 2026-08-28

D14 remains final SHOP authority and D11 remains reroll authority. Bounded Joker/Tarot expectation work reduced reroll-active D11 future work to about 3.17 s mean and total reroll-active D14 to about 3.59 s mean. The blocker stays closed unless fresh evidence reopens it.

### D1 authority latency — closed 2026-08-28/30

Root causes included semantic prefilter rescans and a passive-rule-aware root structural pre-beam that could spend tens of seconds before node 1. Deadline-aware prefiltering and root wall-clock checks repaired the known pathology. The validated production baseline reported D1 mean about 1.53 s and max about 2.70 s across its three-run baseline.

### Live tuning failure containment — closed 2026-08-30

The tuner now halts immediately after any non-COMPLETE live trial instead of cascading subsequent trials from an invalid active run.

## Phase-A Bond composition tuning — complete, no promotion

Study `phase-a-native-ready-restart-20260830-c`, repository SHA `87c10f69ba43fb6fb4069b8c93fa8c48962fad54`:

- Red Deck / White Stake, authoritative live unseeded;
- 3 completed attempts per exploratory trial;
- 10 completed trials;
- production-default Trial 0 objective: 19.4166666667;
- strongest candidate Trial 6 objective: 18.2347883598;
- no candidate exceeded baseline and no candidate won;
- no promotion holdout was justified.

Production Bond calibration remained unchanged.

Earlier `-a` and `-b` studies were invalidated by runtime defects and remain forensic evidence only.

## D1 authority-consolidation history through 2026-08-31

Former installation-order-dependent behavior already moved into canonical production ownership before the current handoff includes:

- safe-pace adaptive-search scheduling;
- timeout/fallback authority;
- Hook/log-resilience search reserve;
- boss-unconfirmed projection confidence;
- per-decision Bond intent cache;
- Castle discard evidence;
- Burnt Joker discard evidence;
- DNA/Aces evidence;
- hand-repetition evidence;
- Green Joker survival-equivalent Play/Discard preservation;
- Runner / To Do List target-hand evidence.

Important commits in the most recent target-hand sequence:

- `0defc8a7bb91d5b11b7d3e4905c996e0f50f0474` — make target-hand evidence native to D1;
- `65f352cbedae67a246f0c27774549d8e8a36a99a` — lock native target-hand evidence;
- `e32231503bc9aef72d76cd2c4f1818335afd77e0` — hand off D1 authority consolidation;
- `60f7245939fb29e7e63cadee1cd508efea61cdf6` — remove stale regression expecting the retired target-hand installer sentinel.

## Retained design principles

- Winning the run is the normal gameplay objective.
- Hidden future information is forbidden.
- Literal Balatro mechanics outrank synthetic strategy labels.
- Bond/composition is the canonical strategic representation unless the root roadmap explicitly replaces it.
- Historical implementations may remain as repository assets without being active development priorities.
