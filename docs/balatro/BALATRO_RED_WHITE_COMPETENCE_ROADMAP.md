# Balatro Red/White Competence Roadmap

Status: **ordinary Red/White competence is clean; known SHOP/BLIND_SELECT stalls are root-fixed; the expectation-layer recursion audit plus compatibility repair are deterministically green; a fresh three-attempt production-default live baseline completed normally, so Phase-A candidate tuning is reopened.**

This is the active handoff contract for branch `feat/v1.0-red-white-competence`. Historical detail belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; decision ownership belongs in `BALATRO_DECISION_AUTHORITY_MAP.md`; Phase-A tuning rules belong in `BALATRO_BOND_TUNING.md`.

## NEXT CHAT — START HERE

Do **not** reopen ordinary D1 competence, Mouth, Green Joker, discard authority, Hook, the falsified default-calibration ContextVar hypothesis, or closed SHOP recursion roots without fresh evidence.

The current gate is **Phase-A exploratory candidate tuning** on study:

`phase-a-expectation-boundary-final-20260829`

Validated gameplay/runtime SHA:

`9457bc7b4dd8053f224ae7525e2a174bde88b58d`

Documentation-only commits after that SHA do not change evaluated gameplay. Because the persistent Optuna study records the exact gameplay SHA, resume it with `--repo-sha 9457bc7b4dd8053f224ae7525e2a174bde88b58d` after pulling later documentation commits.

## Closed/root-fixed

- Ordinary Red/White competence/runtime stabilization is closed.
- Production-default tuning ContextVar hypothesis was falsified.
- Durable SHOP diagnostics localized historical stalls to nested expectation work.
- Judgement expectation is bounded and conservative.
- D11 future-Joker evaluation no longer recursively enters full D2.
- Buffoon/Antimatter shared Joker expectation is bounded.
- Paid rerolls fail closed without public future-Joker pool; free-reroll tie behavior remains intentional.
- Native-ready complete `BLIND_SELECT` no longer waits for generic raw-sequence quiescence.
- D8 Arcana/Spectral hypothetical outcomes do not enter D9.
- Visible Emperor remains a real D9 action; hypothetical generated Tarots use bounded leaf valuation.
- D11 future-Tarot expectation does not enter held-option/D9 authority.
- Standard unopened expectation keeps the finite exact generator, bounded 64-call B6 factorization and literal deck-growth valuation; this is bounded contextual work rather than upward policy recursion.
- Obsolete Arcana/Spectral runtime `_visible_value` wrappers are retired.
- Architectural regression coverage locks the expectation-layer boundary.

## Deterministic validation — PASSED

The repaired focused failure cluster was reported green.

The full `tests/balatro` suite was then reported green on the same gameplay HEAD.

Do not request those same tests again unless gameplay/runtime code changes.

## Production-default live baseline — PASSED

Study: `phase-a-expectation-boundary-final-20260829`

Session: `balatro-20260829T080258Z-b183b79c`

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
- reported D1 mean seconds: 0.87684;
- reported `d1_max_seconds`: 3.004;
- objective: 13.5926966292.

`BatchMetrics.to_dict()` reports `d1_max_seconds` as the mean of each episode's maximum, not the single worst raw decision. Attempt 002 contains two bounded D1 timeout-recovery decisions around 6.15 s. They completed through the existing fallback and did not stall the run. They are runtime evidence to watch during holdout, not a blocker for exploratory Phase-A tuning.

No SHOP stall or BLIND_SELECT deadlock reproduced. Runtime baseline gate passed.

## Current Phase-A command

Calibration semantics remain frozen. Tune only realization priority weight, generic synergy bonus, generic conflict penalty and monotonic R1-R5 pivot resistance. Per-Bond thresholds, contributor weights, motif values and later-phase policy parameters remain locked.

After pulling documentation updates, resume the same study with the validated gameplay SHA explicitly:

```powershell
git pull
python balatro_tune_bonds_live.py --study phase-a-expectation-boundary-final-20260829 --repo-sha 9457bc7b4dd8053f224ae7525e2a174bde88b58d --trials 20
```

If the local checkout is still exactly gameplay HEAD `9457bc7b4dd8053f224ae7525e2a174bde88b58d`, the explicit `--repo-sha` is optional, but keeping it is harmless and preserves the study contract.

Rules:

1. Exploratory candidate trial = 3 completed authoritative live attempts.
2. Preflight requires fresh Ante-1 Red/White `BLIND_SELECT` before every trial.
3. A real win stops the study for review; do not auto-restart a won terminal frame.
4. If a runtime/semantic defect appears, stop at the first reproduced defect, inspect the durable trace, fix the agent, and invalidate the study because gameplay SHA changes.
5. Do not promote a 3-run exploratory winner directly.
6. Promotion/holdout requires a fresh minimum of 20 completed episodes per arm plus manual review.

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
6. Production uses ordered wrappers/monkeypatches; install order is behavior and must be preserved deliberately.

## Phase-A evaluation contract

- exploratory trial: 3 completed attempts;
- promotion/holdout: at least 20 completed episodes per arm;
- persistent SQLite provenance includes repo SHA, playbook, deck/stake, schema/objective, run IDs, calibration and metrics;
- normal studies stop on a real win for review;
- unseeded live deltas are descriptive, not automatic promotion evidence;
- compare variance/pathologies as well as objective/win rate;
- any semantic/runtime gameplay change changes the SHA and invalidates the active live study.

## Core doctrine

Primary objective: **maximize probability of winning the run**.

Literal Balatro scoring and native legality are authoritative. Bond rank, motif strength, Build Health, collection/discovery or tuning convenience must never become fake score or justify a strategically worse action. D1 survival/legal authority outranks preference. D2/D14 compare real scoring/build contribution, economy, slots, runway and bounded transition value. Boss mechanics override ordinary strategy when they alter legality or realization.

## Current queue

- [x] D1 Red/White ordinary competence/runtime stabilization.
- [x] Clean ordinary competence baseline.
- [x] Durable SHOP diagnostics.
- [x] Bound Judgement expectation.
- [x] Remove future-Joker reroll recursion into D2.
- [x] Restore bounded shared Joker expectation for Buffoon/Antimatter.
- [x] Enforce paid-reroll public-pool gate.
- [x] Falsify calibration-context hypothesis.
- [x] Fix BLIND_SELECT quiescence deadlock.
- [x] Remove D8 Arcana/Spectral -> D9 hypothetical edges.
- [x] Remove Emperor generated-Tarot -> D9 edge.
- [x] Remove D11 future-Tarot -> D9 edge.
- [x] Preserve bounded Standard generator/B6/deck-growth semantics.
- [x] Add architectural expectation-layer regression coverage.
- [x] Repair audit compatibility/semantic regressions.
- [x] Focused tests green.
- [x] Full `tests/balatro` green on gameplay HEAD.
- [x] Fresh three-attempt production-default baseline completed normally.
- [ ] **Current gate:** run Phase-A exploratory candidate trials on the existing baseline study.
- [ ] Inspect candidates/pathologies; stop on real win or runtime/semantic defect.
- [ ] Select candidate(s) for fresh >=20-episode-per-arm holdout.
- [ ] Promote only after deterministic, holdout, runtime, diversity and manual-review gates pass.

## Operating contract

- Repository: `LeafStardust/game-ai-framework`.
- Branch: `feat/v1.0-red-white-competence`.
- Canonical update command: `git pull`.
- Never reuse interrupted Optuna study names.
- Resume this valid active study while its gameplay SHA/contract remain compatible.
- Interrupted trials are not baseline or promotion evidence.
- Do not repeatedly rerun a reproduced stall; inspect the newest durable trace.
- Documentation-only commits do not invalidate green deterministic/gameplay evidence; gameplay/runtime changes do.
