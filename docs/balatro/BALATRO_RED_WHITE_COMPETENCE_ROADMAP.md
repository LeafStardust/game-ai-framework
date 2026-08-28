# Balatro Red/White Competence Roadmap

Status: **Red Deck / White Stake competence-repair gate closed; D14/D11 SHOP and D1 runtime gates closed; offline Bond calibration / decision-quality improvement is OPEN**

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

### SHOP / D11 latency — CLOSED

Reroll-active D11 future evaluation was reduced from about **20.8 s** to about **3.17 s** while preserving public-information semantics and conservative omitted-mass treatment. The authoritative nested future-family timings are Joker/Tarot/Planet/residual. Do not resume SHOP micro-optimization without new measured evidence.

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

Current runtime/authority protections include:

- projection-free initial root ranking;
- bounded semantic Play/Discard prefiltering;
- bounded structural timeout recovery;
- no projected pre-adaptive bootstrap;
- no projected post-budget immediate fallback;
- projection-free legal discard reserve on ordinary initial roots;
- active The Hook excluded from that reserved discard candidate;
- active The Hook temporarily capped at **3.0 s** search budget, with the configured engine budget restored after the decision.

The targeted Hook/root/fallback regressions and the full `tests/balatro` suite were reported **green by the user** on the current gameplay/test HEAD.

### Clean unchanged-HEAD competence baseline — PASS

Focused run `balatro-20260828T201428Z-24fd819b-attempt-001` reached Ante 3 The Wall and showed ordinary D1 remained bounded: **21 D1 decisions, ~1.06 s mean, ~1.26 s median, ~4.04 s max, one >3 s, zero >5 s**, with projected immediate fallback effectively zero. The run used all four discards on the terminal Wall attempt and exposed no new runtime/legality blocker.

Replacement batch `balatro-20260828T202157Z-b3fc8c0a` is the current clean competence baseline:

- attempt 1: lost Ante 4 Big Blind at **6624 / 7500** with Card Sharp/Banner/Scholar/Delayed Gratification/Joker; **29 D1 decisions, ~1.067 s mean, ~1.226 s median, 2.153 s max, zero >3 s, zero true `budget_exceeded`**;
- attempt 2: lost Ante 2 The Manacle at **918 / 1600** with Photograph/Joker; **25 D1 decisions, ~0.959 s mean, ~1.152 s median, 1.782 s max, zero >3 s, zero true `budget_exceeded`**;
- attempt 3: lost Ante 2 Small Blind at **480 / 800** with no Jokers; **13 D1 decisions, ~0.988 s mean, ~1.174 s median, 1.393 s max, zero >3 s, zero true `budget_exceeded`**;
- projected `immediate_fallback_search` was effectively zero in all three;
- no action-result / illegal-action / runtime failures were observed;
- adaptive search remained active and produced completed evidence rather than collapsing to zero-node fallback.

The batch did **not** encounter The Hook. Do not fish indefinitely for a particular boss: deterministic Hook coverage is green, the old Hook signatures are no longer present in current ordinary-path evidence, and no current live artifact reproduces the prior Hook defect.

### Remaining weak play is now a tuning problem, not a competence-repair blocker

The clean batch still contains poor-looking decisions, especially terminal rounds where the agent sometimes spends all hands while legal discards remain. This is no longer evidence that discard authority is missing:

- attempt 1 used real `DISCARD_CARDS` actions during Ante 4 Small/Big Blind;
- attempt 2 opened an Ante 2 Big Blind with a real discard;
- attempt 3 used two real discards against The Window.

Therefore the ordinary root contains usable discard evidence and canonical adaptive authority can select it. Cases such as The Manacle and the Ante 2 Small Blind where the agent chose to play through all hands with discards remaining are now classified as **decision-quality / valuation weaknesses** to improve through calibration and targeted policy analysis, unless a future trace proves a concrete authority/mechanics contradiction.

Natural losses and low win rate alone do not reopen the competence gate.

## Current phase — OFFLINE BOND CALIBRATION / PLAY QUALITY IMPROVEMENT

Calibration is now **unfrozen** under `docs/balatro/BALATRO_BOND_TUNING.md`.

Phase A remains low-dimensional and should tune only the documented global composition/pivot parameters first:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1–R5 pivot resistance.

Per-Bond thresholds and motif-specific values remain locked until Phase A is validated.

### Evaluation contract

- exploratory Optuna work: **3 completed runs per trial** is acceptable for directional search;
- quick baseline sanity / repeated-defect discovery: **3 runs** is enough;
- promotion / holdout comparison: **>=20 completed episodes per arm**;
- compare confidence, variance, and pathological behavior, not raw win rate alone;
- any new semantic/runtime gameplay fix changes the SHA and invalidates the current baseline.

The immediate objective is no longer to keep adding generic repair wrappers. It is to improve win probability and decision quality using the existing calibration/evaluation infrastructure, while reopening competence repair only for reproducible mechanics/authority/runtime defects.

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

- [x] D14/D11 SHOP latency stabilization.
- [x] D1 stage profiler and deadline instrumentation.
- [x] Green Joker safe no-discard execution guard.
- [x] Mouth zero-score wide-recovery repair.
- [x] Projection-free root ranking.
- [x] Bounded structural timeout recovery and bounded legal timeout discards.
- [x] Remove projected pre-adaptive bootstrap.
- [x] Reject projected post-adaptive immediate fallback under hard D1 budget.
- [x] Preserve legal root discard evidence on ordinary initial roots.
- [x] Exclude active Hook from the reserved root discard candidate.
- [x] Add active-Hook 3 s D1 search cap and deterministic coverage.
- [x] Focused unchanged-HEAD validation after Hook cap.
- [x] Clean unchanged-HEAD three-run competence baseline.
- [x] **Close Red/White competence-repair gate and unfreeze offline calibration.**
- [ ] Run Phase-A calibration / baseline comparison under `BALATRO_BOND_TUNING.md`.
- [ ] Use calibration and trace review to improve weak Play-vs-Discard valuation, build formation, pivoting, shop decisions, and overall win probability.
- [ ] Reopen repair mode only if a reproducible semantic/runtime/mechanics defect appears.
- [ ] Keep new decks, stake progression, gameplay features, and broader v1.1+ work frozen until the Red/White play-quality/calibration checkpoint is satisfactory.
