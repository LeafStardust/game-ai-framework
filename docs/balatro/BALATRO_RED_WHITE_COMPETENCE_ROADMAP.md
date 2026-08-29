# Balatro Red/White Competence Roadmap

Status: **ordinary Red Deck / White Stake competence is clean; known tuner SHOP and BLIND_SELECT stalls have root fixes; the expectation-layer recursion audit is implemented; the first full-suite pass exposed compatibility/semantic regressions from that refactor, which are now repaired and awaiting deterministic validation before another live baseline.**

This is the active handoff contract for branch `feat/v1.0-red-white-competence`. Historical detail belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; decision ownership belongs in `BALATRO_DECISION_AUTHORITY_MAP.md`; Phase-A tuning rules belong in `BALATRO_BOND_TUNING.md`.

## NEXT CHAT — START HERE

Do **not** reopen ordinary D1 competence, Mouth, Green Joker, discard authority, Hook, or the falsified default-calibration ContextVar hypothesis without fresh evidence.

The current gate is deterministic validation of the expectation-boundary audit plus its compatibility repair. Do not run another tuner baseline until that validation is green.

### Current exact state — 2026-08-29

Closed/root-fixed:

- Ordinary production Red/White gameplay has a clean three-run competence baseline.
- The production-default tuning ContextVar hypothesis was falsified.
- Durable SHOP diagnostics localized the historical stalls to nested expectation work.
- Judgement catalogue/edition/build expectation is bounded and conservative.
- D11 future-Joker reroll evaluation no longer recursively enters full D2.
- The shared Joker evaluator used by Buffoon/Antimatter uses bounded build transitions.
- Paid rerolls fail closed without the required public future Joker pool; free zero-cost rerolls retain their tie behavior.
- Native-ready complete `BLIND_SELECT` no longer waits for generic raw-sequence UI quiescence, fixing the post-SHOP transition deadlock.

Completed expectation-layer audit:

- Added `games/balatro/unopened_consumable_outcome_value.py`, a bounded leaf evaluator for hypothetical unopened Tarot/Spectral outcomes.
- D8 Arcana no longer instantiates/calls D9 `BalatroPackPolicy` for hypothetical outcomes.
- D8 Spectral no longer instantiates/calls D9 `BalatroPackPolicy` for hypothetical outcomes.
- Visible Emperor remains a real D9 action, but its hypothetical generated Tarots use the bounded leaf evaluator and cannot re-enter D9.
- D11 future-Tarot reroll EV no longer routes through sampled future-hand D9 scoring.
- D8 Standard retains its finite exact generator plus bounded B6 factorization and literal deck-growth valuation. This is allowed because it does not call D9/D11/D14 policy authority and was already measured as a bounded fast path; the audit boundary is recursion/policy re-entry, not a ban on all bounded contextual work.
- Obsolete Arcana/Spectral `_visible_value` runtime monkeypatches were removed from `shop_expectation_runtime_bound_policy.py`; the safe boundary now lives in the base evaluators themselves.
- Buffoon rationale/docs now reflect its bounded build-transition Joker expectation rather than the retired D2/D14 recursion route.
- Added `tests/balatro/test_balatro_expectation_layer_boundaries.py` to make upward policy edges deterministic regression failures.

First deterministic validation result after the audit:

- The targeted boundary regression was reported green.
- The first full `tests/balatro` run then exposed 17 failures. These were not 17 new runtime roots; they clustered into interface compatibility and over-conservative semantic regressions introduced by the refactor.
- Arcana/Spectral evaluator constructors had dropped the historical `pack_policy=` compatibility argument, and Arcana `_visible_value` had changed its monkeypatch-visible signature.
- D11 future-Tarot had removed public-pool preflight/test surfaces together with the forbidden held-D9 path.
- Standard had been over-pruned: bounded B6 factorization and deck-growth value were removed even though they were finite/non-recursive and part of established D8 semantics.
- Direct Hermit/Temperance/Black Hole unopened value was too dependent on the generic consumable factory path, causing legitimate zero-cost Arcana/Spectral admission tests to fail.
- Older runtime-bound tests still expected one injected D9 call for ordinary Arcana/Spectral outcomes, contradicting the new acyclic contract.

Compatibility/semantic repair now applied:

- Arcana/Spectral accept `pack_policy=` as an ignored compatibility-only argument; it is never stored or invoked.
- Arcana `_visible_value` again supports the prior two-positional-argument test/monkeypatch surface while inferring the consumable family from public record metadata.
- Hermit, Temperance and Black Hole receive direct constant-time public leaf values; they do not need D9 to preserve valid pack admission.
- D11 future-Tarot preflights every public record and keeps deterministic bounded sampling/full-denominator semantics, but its compatibility `held_option` surface is now a leaf adapter and never enters D9.
- Standard exact generator, bounded 64-call B6 factorization and literal deck-growth value are restored; no `score_action`, `rank_actions`, D11 or D14 recursion is introduced.
- Runtime-bound tests were aligned with the new zero-D9 Arcana/Spectral contract.
- Architectural boundary coverage now distinguishes bounded contextual computation from forbidden upward policy recursion.

Code HEAD immediately before this roadmap-only update: `14c357fd44cb1f20d6c65d2fed44733d3432b5e0`.

## Immediate gate

Calibration remains **frozen**.

Run the repaired failure cluster first:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_arcana_booster_recursion_guard.py tests/balatro/test_balatro_arcana_booster_runtime_bound.py tests/balatro/test_balatro_standard_booster_runtime_bound.py tests/balatro/test_balatro_reroll_tarot_expectation_latency_bound.py tests/balatro/test_balatro_shop_expectation_runtime_bounds.py tests/balatro/test_balatro_shop_runtime_final_bounds.py tests/balatro/test_balatro_supported_pack_admission.py tests/balatro/test_balatro_d8_booster_policy.py tests/balatro/test_balatro_red_white_shop_calibration.py tests/balatro/test_balatro_shop_arbiter.py tests/balatro/test_balatro_expectation_layer_boundaries.py
```

If green:

```powershell
python -m pytest -q tests/balatro
```

The assistant does **not** execute tests or live Balatro attempts; local validation belongs to the user.

If either deterministic step fails, repair that exact failure before any live run. A gameplay/runtime code change invalidates the previous deterministic checkpoint and must be retested.

If the full suite is green:

1. Restore Balatro to fresh Red Deck / White Stake / Ante 1 `BLIND_SELECT`.
2. Start a **freshly named** `--baseline-only` study. Never reuse an interrupted Optuna study name.
3. Require all three production-default attempts to terminate normally. Wins are not required for this gate.
4. If one attempt stalls, stop after the first reproduced stall and inspect the newest durable trace. Do not repeatedly rerun it.
5. If all three attempts complete normally, reopen Phase-A candidate tuning under `BALATRO_BOND_TUNING.md`.

## Expectation-layer authority contract

Expectation work must be bounded by construction, not by a timeout added around an unbounded call graph.

1. Hypothetical/unseen SHOP outcomes may use public deterministic metadata and explicitly bounded leaf/context mechanics.
2. D8 unopened Arcana/Spectral expectation must not call D9 opened-pack choice authority.
3. D11 future-offer expectation must not call full D2/D14 or recursively invoke parent reroll authority.
4. A real visible D9 effect may own its actual action semantics, but hypothetical outcomes it creates must not recursively re-enter D9.
5. Bounded finite contextual work is allowed when it has no upward policy edge and a fixed work budget. Whole-blind D1 projection, full shop arbitration, catalogue-wide nested policy, or unbounded whole-build recursion is not a legal child of unopened/future expectation.
6. Unsupported, stochastic, generative, omitted, or unsafe probability mass contributes literal zero; it is never renormalized away.
7. Small public spaces may be exact. Large public spaces use deterministic bounded subsets while preserving the full public denominator.
8. Hidden RNG state, seeds, pool order, or future identities are never inspected.
9. These restrictions apply to hypothetical expectation work. Actual visible decisions retain their normal D1-D14 authorities and native legality checks.

## Decision authority

1. D1 final hand authority: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`; effective production policy is `StrategyAwareLiveHandActionPolicy`.
2. D14 SHOP authority: `BuildAwareShopArbiter`.
3. D11 reroll authority: `BuildAwareShopRerollPolicy`.
4. D9 opened-pack authority: `BalatroPackPolicy`.
5. Bond/composition and Build Health are evidence, not final gameplay action authority.
6. Production uses ordered wrappers/monkeypatches; install order is behavior and must be preserved deliberately.

## Closed runtime blockers

### D1 runtime / authority

Closed. The branch contains bounded root ranking, semantic Play/Discard prefiltering, bounded timeout recovery, projection-free ordinary initial discard reserve, Hook-specific protection, and regressions. Do not resume D1 micro-optimization without fresh measured evidence.

### D11 Joker/reroll recursion

Closed as a known root cause. Hypothetical unseen Joker reroll outcomes do not call full D2. Shared Buffoon/Antimatter Joker expectation is a bounded build-transition model.

### SHOP Arcana/Judgement recursion

Closed as a known root cause. Judgement expectation is bounded, and the broader audit removes the architectural D8-to-D9 hypothetical edge rather than relying only on item-specific guards.

### BLIND_SELECT quiescence deadlock

Closed as a known root cause. Native-ready complete BLIND_SELECT is already actionable and no longer waits for presentation/UI geometry to become raw-sequence quiet.

## Ordinary competence evidence

Focused run `balatro-20260828T201428Z-24fd819b-attempt-001` reached Ante 3 The Wall with approximately 1.06 s mean D1 latency, 1.26 s median, 4.04 s maximum, one decision above 3 s and none above 5 s.

Replacement batch `balatro-20260828T202157Z-b3fc8c0a`:

- attempt 1: Ante 4 Big Blind loss, 6624 / 7500, D1 ~1.067 s mean / 2.153 s max;
- attempt 2: Ante 2 The Manacle loss, 918 / 1600, D1 ~0.959 s mean / 1.782 s max;
- attempt 3: Ante 2 Small Blind loss, 480 / 800, D1 ~0.988 s mean / 1.393 s max;
- zero D1 decisions above 3 s in the batch;
- zero true D1 `budget_exceeded` events;
- no illegal/action-result/runtime failures.

This evidence keeps ordinary competence closed, but it does not validate the latest tuning-runtime SHA.

## Phase-A after the runtime gate

Only after a fresh production-default baseline completes all three attempts normally, tune:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1-R5 pivot resistance.

Per-Bond thresholds and motif-specific values remain locked.

Evaluation contract:

- baseline/exploratory trial: 3 completed attempts;
- promotion/holdout: at least 20 completed episodes per arm;
- persistent SQLite Optuna storage with repo SHA, playbook, deck/stake, schema/objective, run IDs, calibration and metrics;
- normal studies stop on a real win for review;
- compare variance and pathological behavior, not raw win rate alone;
- any semantic/runtime gameplay change changes the SHA and invalidates the prior live calibration baseline.

## Core gameplay doctrine

Primary objective: **maximize probability of winning the run**.

Literal Balatro scoring and native legality are authoritative. Bond rank, motif strength, Build Health, collection/discovery, or tuning convenience must never become fake score or justify a strategically worse action. D1 survival/legal authority outranks preference. D2/D14 compare real scoring/build contribution, economy, slots, runway and bounded transition value. Boss mechanics override ordinary strategy when they alter legality or realization.

## Current queue

- [x] D1 Red/White ordinary competence/runtime stabilization.
- [x] Clean ordinary three-run competence baseline.
- [x] Durable SHOP stage instrumentation.
- [x] Bound Judgement catalogue/edition expectation.
- [x] Remove future-Joker reroll recursion into D2.
- [x] Restore bounded shared Joker expectation for Buffoon/Antimatter.
- [x] Enforce paid-reroll public-pool gate.
- [x] Falsify production-default calibration-context hypothesis.
- [x] Fix native-ready BLIND_SELECT quiescence deadlock.
- [x] Add acyclic unopened Tarot/Spectral leaf valuation.
- [x] Remove D8 Arcana -> D9 hypothetical edge.
- [x] Remove D8 Spectral -> D9 hypothetical edge.
- [x] Remove Emperor generated-Tarot -> D9 edge.
- [x] Remove D11 future-Tarot -> D9 edge.
- [x] Retire obsolete D8 runtime `_visible_value` monkeypatches.
- [x] Align Buffoon documentation with bounded implementation.
- [x] Add architectural expectation-layer regression coverage.
- [x] Targeted expectation-boundary regression reported green on the first audit HEAD.
- [x] First full-suite audit validation exposed 17 compatibility/semantic regressions.
- [x] Repair Arcana/Spectral compatibility surfaces without restoring D9.
- [x] Restore direct deterministic Hermit/Temperance/Black Hole leaf value.
- [x] Restore D11 Tarot full-pool preflight with leaf-only bounded evaluation.
- [x] Restore bounded Standard B6/deck-growth semantics without policy recursion.
- [x] Align stale runtime-bound tests with zero-D9 contract.
- [ ] **Current gate:** repaired failure-cluster deterministic tests green.
- [ ] Full `tests/balatro` green on the same HEAD.
- [ ] Fresh three-attempt production-default `--baseline-only` study completes normally.
- [ ] If clean, begin Phase-A candidate tuning.

## Operating contract

- Repository: `LeafStardust/game-ai-framework`.
- Branch: `feat/v1.0-red-white-competence`.
- Canonical update command: `git pull`.
- Do not reuse interrupted Optuna study names.
- Interrupted trials are not baseline evidence.
- Do not require a win for the runtime baseline gate.
- Do not repeatedly rerun a reproduced stall; inspect its newest durable trace.
- Documentation-only commits do not invalidate a green deterministic gameplay/test checkpoint; gameplay/runtime changes do.
