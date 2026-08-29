# Balatro Red/White Competence Roadmap

Status: **ordinary Red/White competence and the expectation-layer runtime fixes are clean. The previous Phase-A baseline was valid on gameplay SHA `9457bc7b...`, but a new ROUND_EVAL checkout fast path is now a gameplay/runtime change and therefore invalidates that study for further tuning. Deterministic revalidation and a fresh baseline are the current gate.**

This is the active handoff contract for branch `feat/v1.0-red-white-competence`. Historical detail belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; decision ownership belongs in `BALATRO_DECISION_AUTHORITY_MAP.md`; Phase-A tuning rules belong in `BALATRO_BOND_TUNING.md`.

## NEXT CHAT — START HERE

Do **not** reopen ordinary D1 competence, Mouth, Green Joker, discard authority, Hook, the falsified default-calibration ContextVar hypothesis, or closed SHOP recursion roots without fresh evidence.

The current gate is validation of the **ROUND_EVAL checkout fast path**.

## Previous clean baseline — retained as historical evidence only

Study: `phase-a-expectation-boundary-final-20260829`

Validated gameplay/runtime SHA: `9457bc7b4dd8053f224ae7525e2a174bde88b58d`

Session: `balatro-20260829T080258Z-b183b79c`

Runs:

- attempt 001: Ante 1 boss `The Manacle`, loss 290 / 600;
- attempt 002: reached Ante 5 Big Blind, loss 9511 / 16500;
- attempt 003: Ante 1 boss `The Club`, loss 262 / 600.

Batch metrics included average Ante 2.6667, boss clear rate 0.5, build diversity 0.6667, power-engine utilization 0.42135, zero illegal actions, zero cash-reserve failures and objective 13.5926966292. No SHOP stall or BLIND_SELECT deadlock reproduced.

That study remains valid evidence for SHA `9457bc7b...`, but **must not receive more candidate trials** after the checkout runtime change.

## ROUND_EVAL checkout fast path — implemented, validation pending

The user-visible goal is simple: click Check Out as soon as the actual result/check-out screen is present, rather than waiting on generic presentation-settling delays.

Implementation:

- `games/balatro/live/runtime/round_eval_checkout_fastpath.py` installs a ROUND_EVAL-only runtime fast path.
- Native ROUND_EVAL readiness now requires both the real `G.round_eval` UI object and the native `G.FUNCS.cash_out` callback.
- Once that condition is met, ROUND_EVAL bypasses the supervisor's generic 1-second full-state quiet window.
- ROUND_EVAL also bypasses the autonomous loop's generic two-snapshot / 100 ms stability confirmation.
- The runner's mandatory pre-execution stale-state guard and the injected dispatcher's `ROUND_EVAL` phase guard remain authoritative immediately before cash-out.
- SHOP, pack, hand and all other phases keep their existing readiness/quiescence behavior unchanged.
- Regression coverage: `tests/balatro/test_balatro_round_eval_checkout_fastpath.py`.

Gameplay/runtime HEAD immediately before this roadmap-only update: `a84631af9d365598608030be0c1509bf1dc5ec23`.

## Immediate gate

Because this is gameplay/runtime code, the previous active Phase-A study is frozen and cannot be resumed.

Run:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_round_eval_checkout_fastpath.py
```

If green:

```powershell
python -m pytest -q tests/balatro
```

Do not rerun already-green earlier focused suites unless these tests expose a related regression.

If the full suite is green, restore a fresh Red Deck / White Stake / Ante-1 `BLIND_SELECT` and create a **new** baseline-only study. Do not reuse the old study name:

```powershell
python balatro_tune_bonds_live.py --study phase-a-checkout-ready-fastpath-20260829-a --baseline-only
```

If that three-attempt baseline completes normally, resume that same new study for Phase-A candidates. If any runtime/semantic defect appears, stop at the first reproduction and inspect the durable trace.

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
- Focused compatibility repair and full `tests/balatro` were reported green before the checkout change.

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

Once the new runtime baseline is clean, tune only realization priority weight, generic synergy bonus, generic conflict penalty and monotonic R1-R5 pivot resistance.

- exploratory trial: 3 completed attempts;
- promotion/holdout: at least 20 completed episodes per arm;
- persistent SQLite provenance includes repo SHA, playbook, deck/stake, schema/objective, run IDs, calibration and metrics;
- normal studies stop on a real win for review;
- unseeded live deltas are descriptive, not automatic promotion evidence;
- any semantic/runtime gameplay change changes the SHA and invalidates the active live study.

## Core doctrine

Primary objective: **maximize probability of winning the run**.

Literal Balatro scoring and native legality are authoritative. Bond rank, motif strength, Build Health, collection/discovery or tuning convenience must never become fake score or justify a strategically worse action. D1 survival/legal authority outranks preference. D2/D14 compare real scoring/build contribution, economy, slots, runway and bounded transition value. Boss mechanics override ordinary strategy when they alter legality or realization.

## Current queue

- [x] D1 Red/White ordinary competence/runtime stabilization.
- [x] SHOP expectation recursion/root-cause fixes.
- [x] BLIND_SELECT quiescence deadlock fix.
- [x] Expectation-layer architectural audit and compatibility repair.
- [x] Full `tests/balatro` green before checkout change.
- [x] Clean three-attempt baseline on gameplay SHA `9457bc7b...`.
- [x] Implement actual-UI-gated ROUND_EVAL checkout fast path.
- [x] Add focused checkout fast-path regression coverage.
- [ ] **Current gate:** focused checkout regression green.
- [ ] Full `tests/balatro` green on the new gameplay HEAD.
- [ ] Fresh three-attempt baseline-only study on the new SHA.
- [ ] Resume Phase-A exploratory candidates only after that baseline is clean.

## Operating contract

- Repository: `LeafStardust/game-ai-framework`.
- Branch: `feat/v1.0-red-white-competence`.
- Canonical update command: `git pull`.
- Never reuse interrupted or SHA-invalidated Optuna study names.
- Interrupted trials are not baseline or promotion evidence.
- Do not repeatedly rerun a reproduced stall; inspect the newest durable trace.
- Documentation-only commits do not invalidate green gameplay evidence; gameplay/runtime changes do.
