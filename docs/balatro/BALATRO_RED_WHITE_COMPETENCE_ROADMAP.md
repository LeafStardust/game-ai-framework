# Balatro Red/White Competence Roadmap

Status: **D14 / D11 SHOP latency gate closed; ordinary D1 latency stabilized; active-Hook D1 latency fix deterministic-green; calibration frozen pending focused Hook-cap live validation**

This document is the active handoff contract for Red Deck / White Stake competence work. Detailed dated evidence belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; authority boundaries belong in `BALATRO_DECISION_AUTHORITY_MAP.md`.

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

Three-attempt batch, only when the active gate requires it:

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

Reroll-active D11 future evaluation was reduced from about **20.8 s** to about **3.17 s** while preserving public-information semantics and conservative omitted-mass treatment. The authoritative nested future-family timings are Joker/Tarot/Planet/residual. Do not resume SHOP micro-optimization without new evidence.

### D1 historical latency classes already repaired

The following distinct classes were identified and repaired during the 2026-08-28 competence loop:

- semantic root prefilter doing unbounded pre-node work;
- initial root Joker-aware priority projection before node 1;
- structural timeout fallback re-entering expensive planner candidate machinery;
- projected post-adaptive immediate fallback starting after most of the D1 budget was already spent;
- projected pre-adaptive bootstrap whose individual estimate could not be interrupted;
- Play-only initial adaptive roots when semantic Play shaping consumed the soft candidate window;
- active-Hook reserved discard projection causing zero-node 8–9 s spikes.

The current ordinary-blind D1 path has repeatedly returned to the intended interactive envelope, generally around **~1–3 s** with projected immediate fallback effectively zero.

### Root discard evidence — CURRENT SEMANTIC CONTRACT

Live evidence showed initial adaptive roots could become Play-only while real discards remained. `d1_root_discard_reserve_policy.py` now appends a tiny **projection-free** legal discard reserve to an initial Play-only root when ordinary discard authority exists.

The reserve:

- does not choose Play vs Discard itself;
- appends at most two legal discard candidates;
- uses cheap structural ranking only;
- preserves a wide redraw candidate;
- does not duplicate existing discard evidence;
- is skipped on active The Hook because projecting that reserved discard caused a separate zero-node latency defect.

Focused and batch live evidence after this repair showed ordinary blinds actually selecting `DISCARD_CARDS`; the prior systematic pattern of spending all hands while all legal discards remained untouched is no longer the current blocker.

### Current blocker: active The Hook adaptive-search budget

Replacement unchanged-HEAD batch `balatro-20260828T195440Z-9ad96de1` contained:

- attempt 1: Ante 1 Big Blind loss, **332 / 450**, all 4 discards used, D1 approximately **0.81 s mean / 1.28 s max**;
- attempt 2: Ante 3 Big Blind loss, **2246 / 3000**, all 4 discards used, D1 approximately **0.96 s mean / 2.21 s max**;
- attempt 3: Ante 1 **The Hook** loss, **512 / 600**.

Attempts 1–2 are ordinary-path evidence that discard authority and D1 latency are functioning. Attempt 3 directly hit The Hook and showed the prior 8–9 s zero-node reserve projection was gone, but canonical Hook adaptive search still consumed essentially the entire ~7 s allowance on every decision:

- about **7.016 s / 26 nodes**;
- about **7.005 s / 33 nodes**;
- about **7.009 s / 34 nodes**;
- about **7.022 s / 32 nodes**;
- all four attempts `budget_exceeded=True`;
- projected immediate fallback effectively zero.

This is a bounded but still unacceptable interactive latency class. It is the only currently reproduced D1 runtime blocker.

### Current Hook repair

Active Hook now gets a temporary D1 search cap implemented in `d1_hook_search_budget_policy.py`:

```python
_HOOK_MAX_SEARCH_SECONDS = 3.0
```

Contract:

- only active The Hook is capped;
- disabled Hook is not capped;
- ordinary blinds and other bosses keep their configured D1 budget;
- an already tighter configured budget is not widened;
- the original engine budget is restored immediately after the decision;
- if canonical adaptive search cannot finish within the Hook cap, the existing bounded structural timeout recovery remains the fallback authority.

Relevant commits:

- `414de6b9` — `fix(balatro): bound active Hook D1 search`
- `ffeacc7d` — `refactor(balatro): isolate active Hook detection`
- `43677557` — `fix(balatro): install active Hook D1 search cap`
- `8b4a626a` — `test(balatro): bound active Hook D1 search window`
- `c2ad3b62` — `test(balatro): patch Hook activity helper directly`

The targeted Hook/root/fallback regressions and full `tests/balatro` suite were reported **green by the user** on this gameplay/test HEAD.

## Immediate next gate

The deterministic gate is closed. The next required evidence is a focused live run on the unchanged gameplay HEAD:

```powershell
git pull
.\BalatroAgentToggle.bat --one
```

Inspect that run for:

- active Hook, if encountered: no return of 8–9 s zero-node discard-projection spikes and no ~7 s full-budget adaptive-search pattern;
- ordinary blinds: D1 remains in the existing ~1–3 s envelope;
- projected immediate fallback remains effectively zero;
- real discard authority remains available off Hook;
- no new boss-specific semantic/runtime defect.

Do **not** require fishing indefinitely for The Hook. If the focused run is clean but does not encounter Hook, deterministic Hook coverage remains valid and a replacement `--three` batch may be used to seek broader unchanged-HEAD evidence.

Calibration remains **frozen** until a clean unchanged-HEAD competence baseline exists with no reproducible semantic/runtime blocker.

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

## Current repair queue

- [x] D14/D11 SHOP latency stabilization.
- [x] D1 stage profiler and deadline instrumentation.
- [x] Green Joker safe no-discard execution guard.
- [x] Semantic prefilter deadline repair.
- [x] Mouth zero-score wide-recovery repair.
- [x] Projection-free root ranking.
- [x] Bounded structural timeout recovery and bounded legal timeout discards.
- [x] Remove projected pre-adaptive bootstrap.
- [x] Reject projected post-adaptive immediate fallback under a hard D1 budget.
- [x] Preserve legal root discard evidence on ordinary initial roots.
- [x] Exclude active Hook from the reserved root discard candidate.
- [x] Add active-Hook 3 s D1 search cap and deterministic coverage.
- [ ] **Current live gate:** focused unchanged-HEAD validation after Hook cap.
- [ ] **Competence baseline gate:** clean unchanged-HEAD `--three` batch after focused validation if no new defect appears.
- [ ] Reopen offline Bond calibration only after that baseline is clean.
- [ ] Keep new decks, stake progression, gameplay features, and broader v1.1+ work frozen until Red/White competence closes.

## Calibration contract

Three live runs are sufficient for rapid defect discovery, not promotion. Numerical tuning is offline only. Any semantic/runtime gameplay change invalidates the calibration baseline. Promotion requires the documented holdout/comparator process in `BALATRO_BOND_TUNING.md`, including confidence/variance/pathology review rather than raw win rate alone.
