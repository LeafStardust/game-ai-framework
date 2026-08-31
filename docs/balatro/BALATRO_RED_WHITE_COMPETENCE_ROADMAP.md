# Balatro Red/White Competence Roadmap

Status: **ordinary Red/White competence/runtime stabilization is clean. Phase-A Bond composition calibration has completed its current exploratory gate on gameplay/runtime SHA `87c10f69ba43fb6fb4069b8c93fa8c48962fad54`; the production-default calibration remained best after 10 completed exploratory trials, so no candidate advances to holdout and Phase-A tuning stops here. Phase-0 D1 authority consolidation is now the active implementation queue.**

This is the active handoff contract for branch `feat/v1.0-red-white-competence`. Historical detail belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; decision ownership belongs in `BALATRO_DECISION_AUTHORITY_MAP.md`; tuning rules belong in `BALATRO_BOND_TUNING.md`.

## NEXT CHAT — START HERE

Do **not** reopen ordinary D1 competence, Mouth, Green Joker, discard authority, Hook, the falsified default-calibration ContextVar hypothesis, closed SHOP recursion roots, BLIND_SELECT quiescence, ROUND_EVAL checkout fast-path semantics, or the now-fixed D1 root pre-beam budget defect without fresh evidence.

The current Phase-A numerical calibration gate is **closed with no promotion**. The active engineering task is Phase-0 D1 authority consolidation: remove remaining installation-order-dependent D1 wrappers by moving exact mechanics, projection, caching and evidence into their canonical owners without changing production behavior.

### Current authoritative exploratory study

Study: `phase-a-native-ready-restart-20260830-c`

Gameplay/runtime SHA: `87c10f69ba43fb6fb4069b8c93fa8c48962fad54`

Protocol:

- Red Deck / White Stake;
- authoritative live unseeded mode;
- 3 completed attempts per exploratory trial;
- 10 completed trials total;
- no winning trial;
- no live-trial runtime failure in the completed study.

Production baseline, Trial 0:

- objective: **19.4166666667**;
- production baseline: `true`;
- won: `false`.

Best candidate was Trial 6:

- objective: **18.2347883598**;
- realization priority weight: `0.6687104229635565`;
- synergy bonus: `1.207997695442928`;
- conflict penalty: `1.0811626666601495`;
- pivot R1: `0.44962420618802224`;
- pivot deltas R2-R5: `0.987199166325901`, `0.8391515230280804`, `2.0031881523643964`, `3.4241511095039354`.

Because every candidate finished below the production baseline objective, **no 20-run candidate-vs-baseline promotion holdout is justified**. Production Bond calibration remains unchanged.

## Invalidated historical Phase-A evidence

Earlier study `phase-a-native-ready-restart-20260830-a` produced an apparently strong Trial 8 (`25.4396657042`, average Ante `5.33`), but its D1 telemetry exposed a real runtime defect: root structural ranking could spend tens of seconds before consuming node 1 despite an 8-second budget. That study is therefore historical/forensic evidence only and must not be used for promotion.

The D1 root-budget repair was committed at `9653f1a0...`, with regression coverage at `222f27af...`.

A later study `phase-a-native-ready-restart-20260830-b` was also frozen after a separate live-tuning failure exposed that one failed trial could leave Balatro in `SELECTING_HAND` and cascade guaranteed preflight failures into subsequent Optuna trials. The live tuner was changed to halt on the first non-COMPLETE trial (`a745473e...`, regression `87c10f69...`).

The `-c` study is the first current-SHA exploratory study after both fixes and is therefore the active numerical evidence.

## Closed/root-fixed

- Ordinary Red/White competence/runtime stabilization.
- Production-default tuning ContextVar hypothesis falsified.
- Durable SHOP diagnostics localized historical stalls to nested expectation work.
- Judgement expectation bounded and conservative.
- D11 future-Joker evaluation no longer recursively enters full D2.
- Buffoon/Antimatter shared Joker expectation bounded.
- Paid rerolls fail closed without public future-Joker pool.
- Native-ready `BLIND_SELECT` bypasses inappropriate raw-sequence quiescence.
- D8 Arcana/Spectral hypothetical outcomes do not enter D9.
- Visible Emperor remains D9 authority; generated hypothetical Tarots use bounded leaf valuation.
- D11 future-Tarot expectation does not enter held-option/D9 authority.
- Standard unopened expectation retains finite exact generator, bounded 64-call B6 factorization and literal deck-growth valuation.
- Architectural regression coverage locks the expectation-layer boundary.
- ROUND_EVAL checkout fast path is native-readiness gated.
- D1 root structural pre-beam now observes the wall-clock budget before node 1.
- Live tuning halts immediately on a failed/non-COMPLETE live trial instead of cascading invalid trials.
- Full `tests/balatro` was reported green after the current runtime/tuner fixes.

## Phase-0 D1 authority consolidation checkpoint

The following formerly installation-order-dependent D1 behavior has been moved into canonical production ownership and reported green locally:

- safe-pace adaptive-search schedule -> native `PathAwareLiveHandActionDecisionEngine` scheduling;
- safe-pace timeout/fallback authority -> native path-aware D1 orchestration;
- Hook/log-resilience search reserve -> native production D1 budget path;
- boss-unconfirmed projection confidence -> native `StrategyAwareLiveHandActionPolicy`;
- per-decision Bond intent cache -> native `StrategyAwareLiveHandActionPolicy`;
- Castle discard evidence -> native strategy-fit evidence path;
- Burnt Joker discard evidence -> native strategy-fit evidence path;
- DNA/Aces evidence -> native strategy-fit evidence path;
- hand-repetition evidence and Green Joker survival-equivalent preservation -> native strategy policy/arbitration path.

These changes are ownership refactors, not a new tuning family. Their purpose is to eliminate late mutation and make one canonical D1 path responsible for scheduling, projection evidence and Play/Discard arbitration.

Remaining D1 wrappers should be handled one at a time with the same contract: preserve exact behavior, move ownership to the canonical component, remove the installer, add focused regression coverage, then require a local green result before proceeding.

## Expectation-layer authority contract

1. Hypothetical/unseen SHOP outcomes may use public deterministic metadata and explicitly bounded leaf/context mechanics.
2. D8 unopened Arcana/Spectral expectation must not call D9 opened-pack authority.
3. D11 future-offer expectation must not call full D2/D14 or recursively invoke parent reroll authority.
4. A real visible D9 effect may own actual action semantics, but hypothetical outcomes it creates must not recursively re-enter D9.
5. Bounded finite contextual work is allowed when it has no upward policy edge and a fixed work budget.
6. Unsupported, stochastic, generative, omitted or unsafe probability mass contributes literal zero and is never renormalized away.
7. Small public spaces may be exact. Large public spaces use deterministic bounded subsets while preserving the full public denominator.
8. Hidden RNG state, seeds, pool order and future identities are never inspected.
9. Actual visible decisions retain normal D1-D14 authority and native legality checks.

## Decision authority

1. D1 final hand authority: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`; effective production policy is `StrategyAwareLiveHandActionPolicy`.
2. D14 SHOP authority: `BuildAwareShopArbiter`.
3. D11 reroll authority: `BuildAwareShopRerollPolicy`.
4. D9 opened-pack authority: `BalatroPackPolicy`.
5. Bond/composition and Build Health are evidence, not final gameplay action authority.
6. Production still contains ordered wrappers/monkeypatches outside the already-consolidated D1 paths; install order must remain deliberate until each remaining owner is made native.

## Phase-A evaluation contract

Phase A tunes only realization priority weight, generic synergy bonus, generic conflict penalty and monotonic R1-R5 pivot resistance.

- exploratory trial: 3 completed attempts;
- promotion/holdout: at least 20 completed episodes per arm;
- persistent SQLite provenance includes repo SHA, playbook, deck/stake, schema/objective, run IDs, calibration and metrics;
- normal studies stop on a real win for review;
- unseeded live deltas are descriptive, not automatic promotion evidence;
- any semantic/runtime gameplay change changes the SHA and invalidates the active live study;
- if no exploratory candidate materially beats baseline, stop rather than manufacture a holdout candidate.

## Core doctrine

Primary objective: **maximize probability of winning the run**.

Literal Balatro scoring and native legality are authoritative. Bond rank, motif strength, Build Health, collection/discovery or tuning convenience must never become fake score or justify a strategically worse action. D1 survival/legal authority outranks preference. D2/D14 compare real scoring/build contribution, economy, slots, runway and bounded transition value. Boss mechanics override ordinary strategy when they alter legality or realization.

## Current queue

- [x] D1 Red/White ordinary competence/runtime stabilization.
- [x] SHOP expectation recursion/root-cause fixes.
- [x] BLIND_SELECT quiescence deadlock fix.
- [x] Expectation-layer architectural audit and compatibility repair.
- [x] ROUND_EVAL native-ready checkout fast path.
- [x] D1 root pre-beam wall-clock budget repair.
- [x] Live tuner fail-fast behavior after a failed trial.
- [x] Full `tests/balatro` green after the current runtime/tuner fixes.
- [x] Fresh production-default baseline on SHA `87c10f69...`.
- [x] Complete 10-trial Phase-A exploratory checkpoint on the same SHA.
- [x] Review candidate results: production baseline remains best.
- [x] **Phase-A promotion gate closed with no candidate promoted.**
- [x] Select the next roadmap item outside Phase-A numerical calibration.
- [x] Begin Phase-0 D1 authority consolidation and retire safe-pace/runtime/log-resilience/cache/Castle/Burnt/DNA/strategy-execution installers already reported green.
- [ ] Continue remaining D1 exact-mechanics/projection/evidence wrapper consolidation, prioritizing narrow ownership moves before mixed/large wrappers.
- [ ] Refresh `BALATRO_DECISION_AUTHORITY_MAP.md` after the next stable consolidation checkpoint so wrapper classifications match current code.

## Operating contract

- Repository: `LeafStardust/game-ai-framework`.
- Branch: `feat/v1.0-red-white-competence`.
- Canonical update command: `git pull`.
- Never reuse interrupted or SHA-invalidated Optuna study names.
- Interrupted/failed trials are not baseline or promotion evidence.
- Stop the live tuning invocation at the first failed/non-COMPLETE trial.
- Do not repeatedly rerun a reproduced stall; inspect the newest durable trace.
- Documentation-only commits do not invalidate green gameplay evidence; gameplay/runtime changes do.
