# Balatro Red/White Competence Roadmap

Status: **Red/White ordinary competence baseline clean; live Phase-A baseline remains blocked by a tuner-only-context SHOP stall; Arcana bound is deterministic-green but not proven root cause; production-default tuning context isolation implemented, validation pending**

This document is the active handoff contract for Red Deck / White Stake work. Detailed dated evidence belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; authority boundaries belong in `BALATRO_DECISION_AUTHORITY_MAP.md`.

## Future-chat operating contract

### Repository and branch

- Repository: `LeafStardust/game-ai-framework`.
- Active branch: `feat/v1.0-red-white-competence`.
- Stay on that branch unless the user explicitly changes the target.
- Canonical update command:

```powershell
git pull
```

Never replace it with a longer remote/branch form unless the user's local setup actually requires one.

### Canonical Windows commands

Normal persistent mode:

```powershell
git pull
.\BalatroAgentToggle.bat
```

One-attempt validation:

```powershell
git pull
.\BalatroAgentToggle.bat --one
```

Three-attempt batch:

```powershell
.\BalatroAgentToggle.bat --three
```

Five-attempt batch, only when explicitly required:

```powershell
.\BalatroAgentToggle.bat --five
```

Full deterministic Balatro suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Other supported helpers:

```powershell
.\BalatroAgentDiagnosticsReport.bat
.\BalatroAgentCrashReport.bat
.\BalatroAgentMonitor.bat
```

`BalatroAgentCollectionToggle.bat` is compatibility-only. Collection-first play is retired from the competence path. Never invent `python main.py` or another unsupported live entrypoint.

### Validation ownership

- The assistant must **not run tests or live Balatro attempts**. The user runs them locally and reports results/uploads artifacts.
- Reading/writing tests and implementation is allowed; executing them is not.
- Do not request the full suite again when it is already green for the exact current gameplay/test HEAD and no later code/test commit invalidated it.
- Documentation-only commits do not invalidate a green gameplay/test checkpoint.
- A gameplay/semantic/runtime change invalidates the live calibration baseline because repository SHA changed.

## Decision authority

1. D1 final hand authority: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`; effective production policy is `StrategyAwareLiveHandActionPolicy`.
2. D14 SHOP authority: `BuildAwareShopArbiter`.
3. D11 reroll authority: `BuildAwareShopRerollPolicy`.
4. Bond/composition and Build Health are evidence, not final gameplay action authority.
5. Production uses ordered wrappers/monkeypatches; install order is part of behavior and must be preserved deliberately.

## Current checkpoint — 2026-08-29

### D11 reroll latency — CLOSED

Reroll-active D11 future evaluation was reduced from about **20.8 s** to about **3.17 s** while preserving public-information semantics and conservative omitted-mass treatment. The authoritative nested future-family timings are Joker/Tarot/Planet/residual. Do not resume D11 micro-optimization without new measured evidence.

### D1 runtime / authority repair — CLOSED

The 2026-08-28 competence loop identified and repaired multiple distinct D1 failure classes:

- semantic root prefilter doing unbounded pre-node work;
- initial-root Joker-aware priority projection before node 1;
- structural timeout fallback re-entering expensive planner candidate machinery;
- projected post-adaptive immediate fallback starting after most of the D1 budget was already spent;
- projected pre-adaptive bootstrap whose individual estimate could not be interrupted;
- Play-only initial adaptive roots when semantic Play shaping consumed the soft candidate window;
- active-Hook reserved discard projection causing zero-node 8–9 s spikes;
- active-Hook adaptive search consuming the full ~7 s allowance every hand.

Current runtime/authority protections include projection-free initial root ranking, bounded semantic Play/Discard prefiltering, bounded structural timeout recovery, no projected pre-adaptive bootstrap, no projected post-budget immediate fallback, projection-free legal discard reserve on ordinary initial roots, active Hook exclusion from that reserve, and a temporary active-Hook **3.0 s** search cap with restoration of the configured engine budget afterward.

The targeted Hook/root/fallback regressions and the full `tests/balatro` suite were reported **green by the user** before the later tuning-context isolation change.

### Clean ordinary competence baseline — PASS

Focused run `balatro-20260828T201428Z-24fd819b-attempt-001` reached Ante 3 The Wall and showed ordinary D1 remained bounded: **21 D1 decisions, ~1.06 s mean, ~1.26 s median, ~4.04 s max, one >3 s, zero >5 s**, with projected immediate fallback effectively zero.

Replacement batch `balatro-20260828T202157Z-b3fc8c0a` remains the clean pre-calibration competence evidence:

- attempt 1: Ante 4 Big Blind loss **6624 / 7500**, D1 ~**1.067 s mean / 2.153 s max**;
- attempt 2: Ante 2 The Manacle loss **918 / 1600**, D1 ~**0.959 s mean / 1.782 s max**;
- attempt 3: Ante 2 Small Blind loss **480 / 800**, D1 ~**0.988 s mean / 1.393 s max**;
- zero D1 decisions above 3 s in the three-run batch;
- zero true D1 `budget_exceeded` events;
- projected immediate fallback effectively zero;
- no illegal/action-result/runtime failures.

Weak Play-vs-Discard choices in that batch remain decision-quality/tuning targets rather than evidence of missing discard authority because the same HEAD selected real discards in ordinary live play.

## Live tuning SHOP blocker — CURRENT

Two fresh production-default baseline-only tuning attempts have now reproduced a hard stall after entering SHOP. Both stopped emitting decisions for multiple minutes until the user manually terminated the tuner.

### First interrupted tuning baseline

Run `balatro-20260828T204238Z-f12b2e9b-attempt-001` cleared Ante 1 Small and Big Blind, reached SHOP with **$13** and Abstract Joker, and exposed Red Card, Venus, Wasteful, Jumbo Arcana Pack, and Arcana Pack. The durable log ended after the settled `END_ROUND -> SHOP` transition; no SHOP decision followed.

D8 Arcana unopened-pack expectation had a real unbounded full-public-pool traversal. Commit `2a5b708e` (`perf(balatro): bound large-pool Arcana expectation`) keeps pools of 12 or fewer exact and, for larger pools, evaluates at most 8 deterministically spread public outcomes while dividing by the full eligible-pool denominator. Omitted mass is zero and is not renormalized. Regression commit `e2b6424b` covers the large-pool evaluation count/denominator and exact small-pool behavior.

The user reported the corrected targeted Arcana/SHOP set **green**, followed by the full `tests/balatro` suite **green** on that Arcana-bound gameplay/test HEAD.

### Second interrupted tuning baseline proves Arcana was not the full root cause

Fresh session `balatro-20260828T211444Z-555b26b7` began after the Arcana-bound deterministic checkpoint:

- attempt 1 completed normally, losing Ante 1 Small Blind at **268 / 300**;
- attempt 2 reached SHOP with **$9** and visible Odd Todd, Venus, Buffoon Pack, Arcana Pack, and Reroll Surplus;
- there was only **one Arcana Pack** in this shop;
- again the durable log ended after successful `END_ROUND -> SHOP` settlement and no SHOP decision was emitted afterward.

Therefore the Arcana bound remains a valid conservative runtime improvement but must **not** be described as the proven root cause of the multi-minute stall.

### Tuner-vs-production architecture audit

The tuning entrypoint does not use a separate gameplay agent implementation. `AuthoritativeLiveBatchEvaluator` constructs `BoundedBalatroAgentSupervisor`, which is the same bounded production supervisor family used by normal `--three` mode. Both ultimately use the same production observer, `LiveMemoryInjectedSingleStepRunner`, bridge, autonomous loop, D14 SHOP authority, D11 reroll authority, and action execution path.

The material tuning differences are:

- the tuner previously wrapped the entire production supervisor in `use_bond_calibration(calibration)`;
- tuning uses separate control/log/session directories;
- Optuna/preflight/final-reset lifecycle exists around the production supervisor.

The queued `--baseline-only` calibration values are numerically identical to `DEFAULT_BOND_CALIBRATION`, so the current isolator is not different numeric parameters. It is whether merely installing an equal-valued calibration `ContextVar` override changes initialization/cache/runtime behavior somewhere below SHOP authority.

### Production-default calibration-context isolation

Commit `1fc31919` (`fix(balatro): match production context for tuning baseline`) changes the authoritative live evaluator so the exact production default baseline does **not** call `use_bond_calibration` at all. It reads the normal `ContextVar` default exactly like ordinary gameplay. Non-default candidate calibrations still enter the explicit override context.

Regression commit `411bda21` (`test(balatro): isolate production tuning calibration context`) covers both sides:

- exact `DEFAULT_BOND_CALIBRATION` -> no override context call;
- non-default candidate -> override context remains active.

This is an isolation change, not yet a claim that the ContextVar caused the SHOP stall. If a fresh baseline still stalls after this change, the calibration override itself is ruled out and investigation must move to the remaining tuner lifecycle/control/log initialization differences or a generic SHOP path that normal competence batches simply did not encounter.

## Immediate gate

Calibration remains **refrozen**.

Required sequence now:

1. targeted deterministic validation of the production-default calibration-context isolation;
2. full `tests/balatro` on that gameplay/test HEAD;
3. manually restore Balatro to fresh Red Deck / White Stake / Ante 1 `BLIND_SELECT`;
4. start a **freshly named** baseline-only study;
5. require three completed production-default attempts with no multi-minute SHOP stall;
6. if the baseline still stalls, do not keep rerunning: treat the ContextVar hypothesis as falsified and instrument/compare the remaining tuner-specific lifecycle around the same production runner;
7. if clean, reopen Phase-A candidate calibration.

Interrupted Optuna trials must not be treated as baseline evidence. Fresh study names avoid inheriting stale/RUNNING trials from manually interrupted processes.

## Calibration phase after this gate

Once a fresh production-default live baseline completes cleanly, calibration reopens under `docs/balatro/BALATRO_BOND_TUNING.md`.

Phase A remains low-dimensional and tunes only:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1–R5 pivot resistance.

Per-Bond thresholds and motif-specific values remain locked until Phase A is validated.

Evaluation contract:

- exploratory Optuna work: **3 completed runs per trial**;
- quick baseline sanity / repeated-defect discovery: **3 runs**;
- promotion / holdout comparison: **>=20 completed episodes per arm**;
- compare confidence, variance, and pathological behavior, not raw win rate alone;
- any semantic/runtime gameplay fix changes the SHA and invalidates the previous calibration baseline.

## Core gameplay doctrine

### Primary objective

> **Maximize the probability of winning the run.**

Collection/discovery is never allowed to justify a strategically worse action.

### Literal score authority

Scoring must follow actual Balatro mechanics: hand base Chips/Mult, played cards, enhancements, editions, seals, Joker ordering, additive Mult, XMult, retriggers, held effects, hand levels, boss modifiers, and stateful conditions. Bond rank, motif strength, or composition coherence must never be converted into fake score.

### Strategy and Bond authority

Bond/composition is the canonical strategic representation from Ante 1 onward. It informs but does not replace final gameplay authority. Recognition without execution is a defect: Card Sharp should repeat when viable, Green/no-discard engines should not discard casually, and held-card engines should preserve required cards when survival-equivalent.

### Shop and replacement doctrine

Every visible shop action competes on expected contribution to winning: immediate survival, literal score, scaling runway, strategy formation/completion, economy, slot opportunity cost, replacement quality, boss vulnerability, pack value, reroll opportunity, and conditional mechanics. Strong realized/scaling engines require materially superior projected outcome before destruction.

### Economy doctrine

Money is both a purchase resource and, for some builds, a scoring resource. Reserve/interest/rerolls/vouchers/spending are state-dependent and subordinate to survival when weak.

### D1 hand-play doctrine

D1 maximizes blind-clear probability under exact score and boss mechanics, then uses survival-equivalent alternatives to preserve economy and strategic resources. Boss legality is authoritative.

### Discard doctrine

One discard token costs the same whether one or several cards are cycled. Repeated singleton discards are exceptional. Evaluate retained structure, dead-card count, redraw quality, remaining resources, held-card value, Joker mechanics, boss effects, and scoring pace at the authoritative planner/controller layer.

### Boss doctrine

Boss rules are mechanics, not soft preferences. Ordinary strategy is subordinate whenever a boss changes legality or score realization.

## Current queue

- [x] D11 reroll latency stabilization.
- [x] D1 authority/runtime stabilization and Hook cap.
- [x] Green Joker and Mouth semantic repairs.
- [x] Projection-free ordinary root discard evidence.
- [x] Clean ordinary unchanged-HEAD three-run competence baseline.
- [x] First production-default Phase-A baseline attempt exposed a multi-minute SHOP stall.
- [x] Add conservative large-pool Arcana bound and deterministic coverage.
- [x] Targeted Arcana/SHOP validation and full suite reported green.
- [x] Second fresh tuning baseline reproduced SHOP stall after Arcana bound.
- [x] Audit tuner vs normal `--three` architecture: same production gameplay supervisor/runner stack.
- [x] Verify queued baseline values equal production defaults.
- [x] Isolate exact production baseline from calibration ContextVar override.
- [x] Add regression coverage preserving candidate calibration overrides.
- [ ] **Current gate:** targeted calibration-context test(s).
- [ ] Full `tests/balatro` on the context-isolation HEAD.
- [ ] Fresh three-run production-default baseline-only live study.
- [ ] Reopen Phase-A candidate calibration only after a clean baseline.
- [ ] If stall persists, instrument remaining tuner-specific lifecycle/control/log differences instead of further speculative SHOP optimization.
- [ ] Use calibration and trace review to improve weak Play-vs-Discard valuation, build formation, pivoting, shop decisions, and overall win probability.
- [ ] Keep new decks, stake progression, gameplay features, and broader v1.1+ work frozen until the Red/White play-quality/calibration checkpoint is satisfactory.
