# Balatro Red/White Competence Roadmap

Status: **ordinary Red Deck / White Stake competence baseline is clean; the historical tuning SHOP and BLIND_SELECT stalls have root fixes; Phase-A remains frozen until the expectation-layer boundedness audit is deterministic-green and a fresh production-default tuning baseline completes normally.**

This is the active handoff contract for branch `feat/v1.0-red-white-competence`. Detailed historical evidence belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; decision ownership belongs in `BALATRO_DECISION_AUTHORITY_MAP.md`; tuning semantics belong in `BALATRO_BOND_TUNING.md`.

## NEXT CHAT — START HERE

Do **not** reopen ordinary D1 competence, Mouth, Green Joker, discard authority, Hook, or old ContextVar hypotheses without fresh evidence. The current task is narrower: prove that SHOP expectation models cannot recursively call higher policy authorities, validate the resulting HEAD, then run one fresh baseline-only tuner study.

### Current exact state — 2026-08-29

Completed root fixes:

- Ordinary production Red/White gameplay already has a clean unchanged-HEAD three-run competence baseline.
- The production-default tuning `ContextVar` hypothesis was tested and falsified; equal default calibration context was not the SHOP root cause.
- Durable SHOP stage diagnostics localized the original stalls to nested expectation work.
- Arcana/Judgement recursion was bounded; Judgement catalogue/edition/build valuation is now a deterministic conservative lower bound.
- D11 future-Joker/reroll recursion into full D2 was removed. Paid rerolls fail closed without the required public future Joker pool; free rerolls retain their zero-cost tie behavior.
- The shared Joker expectation used by Buffoon/Antimatter was restored as a bounded build-transition evaluator rather than D2 recursion.
- The post-SHOP BLIND_SELECT freeze was traced to generic raw-sequence quiescence after native BLIND_SELECT was already actionable. Native-ready complete BLIND_SELECT now skips that redundant quiescence gate; other phases retain it.

Latest expectation-layer audit work:

- Added `games/balatro/unopened_consumable_outcome_value.py`, a bounded leaf evaluator for hypothetical unopened Tarot/Spectral outcomes.
- D8 Arcana no longer instantiates or calls `BalatroPackPolicy`; hypothetical outcomes cannot re-enter D9.
- D8 Spectral no longer instantiates or calls `BalatroPackPolicy`; hypothetical outcomes cannot re-enter D9.
- Opened visible Emperor remains a D9 decision, but its hypothetical generated Tarots now use the bounded leaf evaluator instead of recursively calling D9.
- D11 future-Tarot reroll EV no longer routes through `HeldConsumableOptionEvaluator` and sampled future-hand D9 scoring. It uses the same bounded public-pool leaf model.
- The old `shop_expectation_runtime_bound_policy.py` D8 `_visible_value` monkeypatches were retired because the base D8 implementations now own the acyclic boundary directly.
- Added `tests/balatro/test_balatro_expectation_layer_boundaries.py` to prevent D8/future-Tarot/Emperor hypothetical expectation paths from regaining D9/D14-style authority edges.

Current code HEAD before this roadmap-only commit: `3f7c9ea46d6be00a6852f72b5d85781a51d9b3ae`.

## Immediate gate

Calibration remains **frozen**. Do not start Phase-A candidates yet.

Required sequence:

1. Pull the expectation-audit HEAD.
2. Run the targeted expectation-boundary regression.
3. If green, run the full Balatro deterministic suite.
4. If anything fails, repair deterministic semantics/tests before any live run.
5. If the full suite is green, manually restore Balatro to fresh Red Deck / White Stake / Ante 1 `BLIND_SELECT`.
6. Start a **freshly named** `--baseline-only` tuning study. Never reuse an interrupted Optuna study name.
7. Require all three production-default attempts to terminate normally. Wins are not required for this gate.
8. If a live stall occurs, stop after the first reproduced stall, inspect the newest durable trace, and localize the remaining stage. Do not repeatedly rerun the same failure.
9. If all three attempts complete normally, reopen Phase-A candidate tuning under `BALATRO_BOND_TUNING.md`.

### Deterministic validation commands

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_expectation_layer_boundaries.py
```

If green:

```powershell
python -m pytest -q tests/balatro
```

The assistant does **not** execute these tests or live Balatro attempts; the user owns local validation.

## Expectation-layer authority contract

Expectation code must be bounded by construction, not merely by timeout.

1. Hypothetical/unseen SHOP outcomes may use public deterministic metadata and bounded leaf mechanics.
2. D8 unopened booster expectation must not call D9 opened-pack choice authority.
3. D11 future-offer expectation must not call D2/D14 or recursively invoke the parent reroll authority.
4. A visible D9 effect may own its real action semantics, but any hypothetical outcomes it generates must not recursively re-enter D9.
5. Full BuildProfiler, whole-blind D1 projection, full shop arbitration, or catalogue-wide nested policy decisions are not legal children of unopened/future expectation loops.
6. Unsupported, stochastic, generative, omitted, or otherwise unsafe probability mass contributes literal zero. Probability mass is not renormalized away.
7. Small public spaces may be exact; large public spaces use deterministic bounded subsets while retaining the full public denominator.
8. Hidden RNG state, seeds, pool order, or future identities are never inspected.
9. Actual visible decisions retain their normal D1-D14 authorities; these bounds apply to hypothetical expectation work, not real action legality.

## Decision authority

1. D1 final hand authority: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`; effective production policy is `StrategyAwareLiveHandActionPolicy`.
2. D14 SHOP authority: `BuildAwareShopArbiter`.
3. D11 reroll authority: `BuildAwareShopRerollPolicy`.
4. D9 opened-pack authority: `BalatroPackPolicy`.
5. Bond/composition and Build Health are evidence, not final gameplay action authority.
6. Production uses ordered wrappers/monkeypatches; install order is behavior and must be preserved deliberately.

## Closed runtime blockers

### D1 runtime / authority

Closed. The branch contains bounded root ranking, semantic Play/Discard prefiltering, bounded timeout recovery, projection-free ordinary initial discard reserve, Hook-specific protection, and related regressions. Do not micro-optimize D1 without fresh measured evidence.

### D11 Joker/reroll recursion

Closed as a known root cause. Hypothetical unseen Joker reroll outcomes do not call full D2. Shared Buffoon/Antimatter Joker expectation uses bounded build transitions. Public-pool observability gates paid rerolls.

### SHOP Arcana/Judgement recursion

Closed as a known root cause. Judgement expectation is bounded. The broader audit now removes the higher-level D8-to-D9 edge rather than relying on item-specific recursion guards alone.

### BLIND_SELECT quiescence deadlock

Closed as a known root cause. Native-ready complete BLIND_SELECT is already an actionable strategic checkpoint and therefore does not wait for presentation/UI geometry to become raw-sequence quiet.

## Ordinary competence baseline

The pre-tuning ordinary baseline remains evidence that the production gameplay agent itself can complete normal live play with bounded D1 behavior.

Focused run `balatro-20260828T201428Z-24fd819b-attempt-001` reached Ante 3 The Wall with approximately 1.06 s mean D1 latency, 1.26 s median, 4.04 s maximum, one decision above 3 s and none above 5 s.

Replacement batch `balatro-20260828T202157Z-b3fc8c0a`:

- attempt 1: Ante 4 Big Blind loss, 6624 / 7500, D1 ~1.067 s mean / 2.153 s max;
- attempt 2: Ante 2 The Manacle loss, 918 / 1600, D1 ~0.959 s mean / 1.782 s max;
- attempt 3: Ante 2 Small Blind loss, 480 / 800, D1 ~0.988 s mean / 1.393 s max;
- zero D1 decisions above 3 s in the batch;
- zero true D1 `budget_exceeded` events;
- no illegal/action-result/runtime failures.

This baseline does **not** validate the latest tuning-runtime SHA; it only keeps ordinary competence from being reopened without new evidence.

## Phase-A tuning after the gate

Only after a fresh production-default baseline completes all three attempts normally:

Tune only:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1-R5 pivot resistance.

Keep per-Bond thresholds and motif-specific values locked.

Evaluation contract:

- baseline/exploratory trial: 3 completed attempts;
- promotion/holdout comparison: at least 20 completed episodes per arm;
- persistent SQLite Optuna study with repo SHA, playbook, deck/stake, schema/objective, run IDs, calibration and metrics;
- stop a normal study on a real win for review;
- compare behavior/pathologies and variance, not raw win rate alone;
- any semantic/runtime gameplay change changes the SHA and invalidates the previous live calibration baseline.

## Core gameplay doctrine

Primary objective: **maximize probability of winning the run**.

Literal Balatro scoring and native legality remain authoritative. Bond rank, motif strength, Build Health, collection/discovery, or tuning convenience must never become fake score or justify a strategically worse action. D1 survival authority outranks preferences. D2/D14 shop decisions compare real scoring/build contribution, economy, slots, runway and bounded transition value. Boss mechanics override ordinary strategy when they alter legality or realization.

## Current queue

- [x] D1 Red/White ordinary competence/runtime stabilization.
- [x] Clean ordinary three-run competence baseline.
- [x] Durable SHOP stage instrumentation.
- [x] Bound Judgement catalogue/edition expectation.
- [x] Remove future-Joker reroll recursion into D2.
- [x] Restore bounded shared Joker expectation for Buffoon/Antimatter.
- [x] Enforce paid-reroll public-pool gate.
- [x] Falsify production-default calibration-context hypothesis.
- [x] Fix native-ready BLIND_SELECT quiescence deadlock and add narrow regression.
- [x] Add acyclic unopened Tarot/Spectral leaf valuation.
- [x] Remove D8 Arcana -> D9 hypothetical edge.
- [x] Remove D8 Spectral -> D9 hypothetical edge.
- [x] Remove Emperor generated-Tarot -> D9 recursion edge.
- [x] Remove D11 future-Tarot -> held-option/D9 expectation edge.
- [x] Retire obsolete D8 runtime `_visible_value` monkeypatches.
- [x] Add architectural expectation-layer boundary regression.
- [ ] **Current gate:** targeted expectation-boundary regression green on current gameplay/test HEAD.
- [ ] Full `tests/balatro` green on that same HEAD.
- [ ] Fresh three-attempt production-default `--baseline-only` tuner study completes normally.
- [ ] If clean, begin Phase-A candidate tuning under `BALATRO_BOND_TUNING.md`.

## Operating contract

- Repository: `LeafStardust/game-ai-framework`.
- Branch: `feat/v1.0-red-white-competence`.
- Canonical update command: `git pull`.
- Do not reuse interrupted Optuna study names.
- Do not treat interrupted trials as baseline evidence.
- Do not require a win for the runtime baseline gate.
- Do not rerun a reproduced stall repeatedly; inspect its newest durable trace.
- Documentation-only commits do not invalidate a deterministic gameplay/test checkpoint, but gameplay/runtime changes do.
