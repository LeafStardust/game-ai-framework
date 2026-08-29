# Balatro Red/White Competence Roadmap

Status: **ordinary Red Deck / White Stake competence is clean; the known tuner SHOP/BLIND_SELECT stalls are root-fixed; the expectation-layer recursion audit and compatibility repair are deterministically green; a fresh three-attempt production-default live baseline completed normally on current gameplay SHA, so Phase-A candidate tuning is reopened.**

This is the active handoff contract for branch `feat/v1.0-red-white-competence`. Historical detail belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; decision ownership belongs in `BALATRO_DECISION_AUTHORITY_MAP.md`; Phase-A tuning rules belong in `BALATRO_BOND_TUNING.md`.

## NEXT CHAT — START HERE

Do **not** reopen ordinary D1 competence, Mouth, Green Joker, discard authority, Hook, the falsified default-calibration ContextVar hypothesis, or the closed SHOP recursion roots without fresh evidence.

The current gate is **Phase-A exploratory candidate tuning** on the completed baseline study `phase-a-expectation-boundary-final-20260829`.

### Current exact state — 2026-08-29

Current gameplay/runtime SHA validated by the live baseline:

`9457bc7b4dd8053f224ae7525e2a174bde88b58d`

Subsequent documentation-only commits do not invalidate that gameplay baseline.

Closed/root-fixed:

- Ordinary production Red/White gameplay has a clean competence baseline.
- Production-default tuning ContextVar hypothesis was falsified.
- Durable SHOP diagnostics localized historical stalls to nested expectation work.
- Judgement expectation is bounded and conservative.
- D11 future-Joker reroll evaluation no longer recursively enters full D2.
- Shared Joker expectation used by Buffoon/Antimatter is bounded.
- Paid rerolls fail closed without the required public future-Joker pool; free rerolls retain intentional tie behavior.
- Native-ready complete `BLIND_SELECT` no longer waits for generic raw-sequence quiescence.
- D8 Arcana/Spectral hypothetical outcomes no longer enter D9.
- Visible Emperor stays a real D9 action, but generated hypothetical Tarots use the bounded leaf evaluator.
- D11 future-Tarot expectation no longer enters held-option/D9 policy authority.
- Standard unopened expectation retains its finite exact generator, bounded 64-call B6 factorization and literal deck-growth valuation; this is explicitly bounded contextual work, not recursive policy re-entry.
- Obsolete Arcana/Spectral runtime `_visible_value` wrappers are retired.
- Architectural regression coverage locks the expectation-layer boundary.

## Deterministic validation

The repaired focused failure cluster was reported green.

The full `tests/balatro` suite was then reported green on the same gameplay HEAD.

Do not request those same tests again unless gameplay/runtime code changes.

## Fresh production-default live baseline — PASSED

Study:

`phase-a-expectation-boundary-final-20260829`

Repository SHA recorded by study:

`9457bc7b4dd8053f224ae7525e2a174bde88b58d`

Session:

`balatro-20260829T080258Z-b183b79c`

Runs:

- attempt 001: Ante 1 boss `The Manacle`, loss 290 / 600;
- attempt 002: reached Ante 5 Big Blind, loss 9511 / 16500;
- attempt 003: Ante 1 boss `The Club`, loss 262 / 600.

Batch metrics:

- episodes: 3;
- win rate: 0.0;
- average Ante: 2.6667;
- median Ante: 2.0;
- boss clear rate: 0.5;
- build diversity: 0.6667;
- power-engine utilization: 0.42135;
- destructive pivots: 0;
- unused active engines: 0;
- cash reserve failures: 0;
- illegal actions: 0;
- reported batch D1 mean seconds: 0.87684;
- reported batch `d1_max_seconds`: 3.004;
- objective: 13.5926966292.

The report's `d1_max_seconds` field is currently the mean of each episode's maximum D1 latency because `BatchMetrics.to_dict()` applies `mean("d1_max_seconds")`; it is not the single worst raw D1 decision across the batch. Raw attempt 002 contains two bounded D1 timeout-recovery decisions around 6.15 s. They completed through the existing fallback path and did not stall the run, so they are recorded as runtime evidence but are not a blocker for exploratory Phase-A tuning. Promotion still requires runtime non-regression on larger holdout evidence.

No SHOP stall or BLIND_SELECT transition deadlock reproduced in the three-attempt baseline. The runtime gate is therefore passed.

## Current Phase-A gate

Calibration semantics remain frozen. The optimizer may tune only:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1-R5 pivot resistance.

Per-Bond thresholds, contributor weights, motif values and later-phase policy parameters remain locked.

Resume the **same completed baseline study** for exploratory candidates; do not create a replacement study while the gameplay SHA and study contract remain unchanged.

```powershell
python balatro_tune_bonds_live.py --study phase-a-expectation-boundary-final-20260829 --trials 20
```

Rules:

1. Every candidate trial uses 3 completed authoritative live runs by default.
2. The tuner preflights fresh Ante-1 Red/White `BLIND_SELECT` before each trial.
3. A real win stops the study for review; do not auto-restart a won terminal frame.
4. If a runtime/semantic defect appears, stop at the first reproduced defect, inspect the durable trace, fix the agent, and invalidate the study because the gameplay SHA changes.
5. Do not promote a 3-run exploratory winner directly.
6. Promotion/holdout requires a fresh minimum of 20 completed episodes per arm and manual review.

## Expectation-layer authority contract

Expectation work must be bounded by construction, not by a timeout around an unbounded graph.

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
6. Production uses ordered wrappers/monkeypatches; install order is behavior and must be preserved deliberately.

## Phase-A evaluation contract

- exploratory trial: 3 completed attempts;
- promotion/holdout: at least 20 completed episodes per arm;
- persistent SQLite Optuna provenance includes repo SHA, playbook, deck/stake, schema/objective, run IDs, calibration and metrics;
- normal studies stop on a real win for review;
- unseeded live deltas are descriptive, not automatic promotion evidence;
- compare variance/pathologies as well as objective/win rate;
- any semantic/runtime gameplay change changes the SHA and invalidates the active live study.

## Core gameplay doctrine

Primary objective: **maximize probability of winning the run**.

Literal Balatro scoring and native legality are authoritative. Bond rank, motif strength, Build Health, collection/discovery or tuning convenience must never become fake score or justify a strategically worse action. D1 survival/legal authority outranks preference. D2/D14 compare real scoring/build contribution, economy, slots, runway and bounded transition value. Boss mechanics override ordinary strategy when they alter legality or realization.

## Current queue

- [x] D1 Red/White ordinary competence/runtime stabilization.
- [x] Clean ordinary competence baseline.
- [x] Durable SHOP stage instrumentation.
- [x] Bound Judgement expectation.
- [x] Remove future-Joker reroll recursion into D2.
- [x] Restore bounded shared Joker expectation for Buffoon/Antimatter.
- [x] Enforce paid-reroll public-pool gate.
- [x] Falsify production-default calibration-context hypothesis.
- [x] Fix native-ready BLIND_SELECT quiescence deadlock.
- [x] Remove D8 Arcana/Spectral -> D9 hypothetical edges.
- [x] Remove Emperor generated-Tarot -> D9 edge.
- [x] Remove D11 future-Tarot -> D9 edge.
- [x] Preserve bounded Standard generator/B6/deck-growth semantics.
- [x] Add architectural expectation-layer regression coverage.
- [x] Repair compatibility/semantic regressions from the audit.
- [x] Focused repaired tests green.
- [x] Full `tests/balatro` green on the same gameplay HEAD.
- [x] Fresh three-attempt production-default `--baseline-only` study completed normally.
- [ ] **Current gate:** run Phase-A exploratory candidate trials on the existing baseline study.
- [ ] Inspect candidate metrics and pathologies; stop immediately on a real win or runtime/semantic defect.
- [ ] Select candidate(s) for fresh >=20-episode-per-arm holdout.
- [ ] Promote only after deterministic, holdout, runtime, diversity and manual-review gates pass.

## Operating contract

- Repository: `LeafStardust/game-ai-framework`.
- Branch: `feat/v1.0-red-white-competence`.
- Canonical update command: `git pull`.
- Do not reuse interrupted Optuna study names.
- Do not replace a valid active study merely because its baseline trial completed; resume it for candidates while the recorded contract/SHA remains compatible.
- Interrupted trials are not baseline or promotion evidence.
- Do not require a win for the runtime baseline gate.
- Do not repeatedly rerun a reproduced stall; inspect its newest durable trace.
- Documentation-only commits do not invalidate a green deterministic/gameplay baseline; gameplay/runtime changes do.
