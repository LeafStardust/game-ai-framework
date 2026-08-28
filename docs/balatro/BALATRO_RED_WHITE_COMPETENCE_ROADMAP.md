# Balatro Red/White Competence Roadmap

Status: **D14 / D11 SHOP latency gate closed; D1 authority-latency gate closed; calibration frozen on The Mouth recovery semantic blocker**

This document is the handoff contract for Red Deck / White Stake competence work. It exists so future contributors do not have to reconstruct the intended Balatro play philosophy or operational workflow from live-run postmortems.

## Future-chat operating contract

This section is authoritative for future chats working on this roadmap. Do not guess commands, branch names, validation state, entrypoints, artifact locations, or runtime workflow when the repository or this roadmap can answer them.

### Repository and branch

- Repository: `LeafStardust/game-ai-framework`.
- Active competence branch: `feat/v1.0-red-white-competence`.
- Stay on that branch unless the user explicitly changes the target.
- After the assistant pushes any commit the user needs locally, the first command given to the user must be exactly:

```powershell
git pull
```

Do not replace this with a longer remote/branch form unless the user's local Git setup actually requires it.

### Canonical Windows commands

Normal persistent Balatro live mode:

```powershell
git pull
.\BalatroAgentToggle.bat
```

Explicit bounded one-attempt validation:

```powershell
git pull
.\BalatroAgentToggle.bat --one
```

Three-attempt batch, only when a three-run batch is explicitly required by the current gate:

```powershell
git pull
.\BalatroAgentToggle.bat --three
```

Five-attempt batch, only when a five-run batch is explicitly required:

```powershell
git pull
.\BalatroAgentToggle.bat --five
```

Full deterministic Balatro test suite:

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

`BalatroAgentCollectionToggle.bat` exists only for compatibility. Collection-first behavior is retired from the ordinary Red/White competence path.

Never tell the user to run `python main.py` for the Balatro live agent. Never invent a Python live entrypoint when a repository batch entrypoint already provides the supported command.

### Validation ownership and cadence

- The assistant must **not run tests or live Balatro attempts**. The user performs local validation and reports results / uploads artifacts.
- Reading tests, writing tests, and adding regression coverage is allowed; executing them is not.
- Do not request the full suite again when it is already green for the exact current code HEAD and no later code/test commit invalidated that result.
- Documentation-only commits do not invalidate a green gameplay/test checkpoint.
- After a code/test commit, give `git pull` followed by every exact command needed.
- When a focused single live run is sufficient for a profiler/performance gate, request `.\BalatroAgentToggle.bat --one`, not `--three` or `--five`.
- For live evidence, use the generated JSONL trace and run summary. If their path convention is uncertain, inspect the runtime instead of guessing.

### No-guess handoff rule

Missing operational knowledge is a repository-reading task, not an invitation to improvise. Before giving a command or claiming a checkpoint, verify it against this roadmap, the relevant implementation, recent commits, or supplied evidence.

Durable details that materially affect future work must be persisted in repository documentation. Record changed commands, branch/gate constraints, validation ownership, artifact conventions, decision-authority boundaries, profiler semantics, measured blockers, wrapper ordering, important fixed failure signatures, and the exact next validation step. Detailed dated evidence belongs in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; authority boundaries belong in `BALATRO_DECISION_AUTHORITY_MAP.md`.

## Current checkpoint — 2026-08-28

### SHOP latency remains closed

The D14/D11 SHOP latency blocker remains **closed**. Reroll-active D11 future evaluation fell from approximately **20.8 s** before the Joker/Tarot bounds to approximately **3.17 s**, with no meaningful hidden residual. Do not resume SHOP micro-optimization unless new profiling evidence reopens it.

### D1 latency is closed again

The earlier 20–30 second recurrence came from the installed `semantic_search_guard_policy` candidate prefilter doing large amounts of pre-node work outside the planner deadline. Commit `76dc7b90451bf82c3d0535913b1cbd380311c896` bounded that semantic prefilter and commit `2ceb8a6b20c6c1b519417370177c33022cb4a081` added regression coverage.

Focused run `balatro-20260828T143847Z-9f14b7a1-attempt-001` validated the repair with approximately **1.23 s mean / 2.42 s max** D1 latency, `immediate_fallback_search` approximately **0.55 s mean / 1.07 s max**, and zero wall-clock budget-exhaustion messages.

Replacement competence batch `balatro-20260828T144652Z-379b8315` then kept the same property across all three attempts. Parsed D1 timing lines measured approximately:

- attempt 1: **1.70 s mean / 3.24 s max**, fallback **0.80 s mean / 1.34 s max**;
- attempt 2: **1.67 s mean / 3.68 s max**, fallback **0.69 s mean / 1.57 s max**;
- attempt 3: **1.36 s mean / 2.53 s max**, fallback **0.57 s mean / 1.16 s max**;
- zero `D1 wall-clock budget exhausted` messages in all three.

The old pathological fallback class is therefore closed again. Do not reopen D1 latency without new measured evidence.

### Current semantic blocker: The Mouth zero-score recovery

The same three-run batch finished **0/3**, all at Ante 2 bosses. Win rate alone is not the blocker. Attempt 2 exposed a mechanically dominated recovery sequence against **The Mouth** after the boss locked scoring to **Full House**.

At score 1136/1600 with no discards remaining, no Full House available, and two hands left, D1 played a single off-type card for zero score. On the final hand it again played a single off-type card for zero score. Once The Mouth is locked, every off-type Play scores zero; with no real discards remaining those Plays are effectively paid redraws. Peeling one card is dominated by cycling the widest set of dead cards that preserves the strongest available structure toward the forced hand.

The existing authority for this mechanic is `games/balatro/boss_hand_constraint_policy.py`. Commit `bc535051f83c295c7f1150f670598f17de092477` (`fix(balatro): recover from Mouth lock with wide plays`) adds the missing branch inside that authority:

- a valid forced-hand scoring Play remains authoritative;
- a real `DISCARD_CARDS` candidate remains authoritative when available;
- only when neither exists and no discards remain, off-type zero-score Plays are treated as recovery redraw candidates;
- retained structure toward the forced hand is maximized first;
- among structure-equivalent candidates, the widest legal Play is kept so more dead cards are cycled;
- this is a candidate filter, not synthetic score or Bond authority;
- unrelated bosses and ordinary D1 decisions are unchanged.

Regression commit `b93b2e0b92d274a39e76c02fc274c9d2eb48ab4a` (`test(balatro): cover Mouth zero-score redraw recovery`) covers the exact no-discard wide-redraw case, preserves matching Full House authority, and confirms a real discard still takes precedence.

### Immediate next gate

Run, in order:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_mouth_zero_score_recovery.py
python -m pytest -q tests/balatro
```

If both are green, the gameplay code change invalidates the uploaded three-run baseline. Run a replacement competence batch:

```powershell
.\BalatroAgentToggle.bat --three
```

Do **not** run another focused `--one` latency attempt first; D1 latency is already reclosed by the focused run plus the subsequent three-run batch. Calibration remains frozen until the replacement competence batch is free of another reproducible semantic/runtime defect.

## Git commit convention

All roadmap work uses the repository's Conventional Commit-style subjects. Prefer explicit Balatro scope for Balatro-specific implementation/regression work, for example:

- `fix(balatro): keep downgraded joker tiers exclusive`
- `test(balatro): expect Bronze Superposition support`
- `docs(balatro): move competence gate to Mouth recovery`

## Primary objective

The permanent Balatro agent has one gameplay objective:

> **Maximize the probability of winning the run.**

Collection-first / unlock-chasing behavior is retired from ordinary competence play. Discovery metadata may remain bounded metadata or an exact-tie signal but must never justify a strategically worse action or reduce blind-clear probability.

## Core gameplay doctrine

### Literal score authority

Scoring must reflect Balatro's actual mechanics: hand base chips/Mult, played-card chips, enhancements, editions, seals, Joker ordering, additive Mult, XMult, retriggers, held effects, hand levels, boss modifiers, and stateful Joker conditions. Bond rank, motif strength, composition coherence, or category labels must never be converted into fake chips/Mult.

### Strategy and Bond authority

Bond/composition is the canonical strategic representation from Ante 1 onward. Positive R0 evidence is strategically visible; candidate strategies may form and pin before high Bond rank; commitment is reversible when a materially stronger projected line exists. Recognition without execution is a defect: Card Sharp should repeat hands when viable, Green/no-discard engines should not discard casually, and held-card engines should preserve required cards when survival-equivalent.

### Shop and replacement doctrine

Every visible shop action competes on expected contribution to winning: immediate survival, literal marginal score, scaling runway, strategy formation/completion, economy/interest, slot opportunity cost, replacement quality, boss vulnerability, pack value, reroll opportunity, and conditional mechanics. Replacement compares the incumbent's actual current contribution plus prospective strategic value against the candidate. Strong realized/scaling engines require materially superior projected outcome before being destroyed.

### Economy doctrine

Money is both a purchase resource and, for builds such as Bull/Bootstraps, a scoring resource. Reserve, interest, rerolls, vouchers, and spending must be state-dependent. Economy is subordinate to immediate survival when weak and should not be burned on marginal speculation when healthy.

### Packs and consumables

Pack/consumable decisions use expected win value and exact mechanics. Do not skip positive-value opportunities with no meaningful downside, and do not buy blindly when money, slot, strategy, or visible-shop opportunity cost dominates. Tarot/Planet/Spectral use must respect the current strategy and target/held-card value.

### D1 hand-play doctrine

D1 maximizes blind-clear probability under exact score and boss mechanics, then uses survival-equivalent alternatives to preserve economy and strategic resources. It must preserve held Steel/Gold/Blue-Seal value when safe, execute repetition/no-discard/Burnt/DNA/Sixth Sense/Castle mechanics coherently, order first-card effects correctly, and obey boss legality.

### Discard doctrine

A discard token costs one discard whether one or several cards are redrawn. Repeated singleton discards are exceptional. Evaluate retained structure, dead-card count, multi-card redraw improvement, remaining resources, held-card value, discard/no-discard Joker mechanics, boss effects, and scoring pace at the authoritative planner/controller layer.

### Boss doctrine

Boss rules are authoritative mechanics, not soft preferences. Implement them as exact legality/state/score transformations where possible. Ordinary strategy is subordinate when a boss changes legal actions or score realization.

## Context-sensitive mechanics that require explicit care

- **Joker Stencil:** empty Joker slots are scoring value.
- **Card Sharp:** depends on actually repeating a realistically available hand.
- **Ride the Bus:** face-card play can reset it; face-heavy engines may conflict.
- **Bull / Bootstraps:** cash directly affects literal score.
- **Banner:** remaining discards affect chips but must not blindly suppress Burnt or other defining discard engines.
- **Green Joker:** discards directly reduce scaling; safe survival-equivalent Plays should preserve it.
- **Blueprint / Brainstorm:** value depends on legal copy target and exact order.

Known stable interactions and anti-interactions require deterministic regressions when generic semantics are insufficient.

## “Stupid behavior” classification

Clearly dominated or mechanically contradictory live decisions are semantic/runtime defects before they are numerical-tuning problems. Examples include destroying a high-cash Bull/Bootstraps engine, passing a strong context-sensitive visible upgrade for weaker utility, collecting unrelated Bonds instead of strengthening a functioning engine, repeated rerolls past a strong visible option, unnecessary sacrifice of held-value cards, breaking an ACTIVE/MATURE engine without a materially better replacement, or repeated singleton discards when several dead cards can safely cycle.

Any such reproducible defect on current HEAD reopens the semantic/runtime gate before calibration.

## Current repair queue

- [x] Literal current/candidate score authority and contextual Joker audits.
- [x] Ante-1 Bond/strategy visibility subordinate to survival.
- [x] Shop cross-family and replacement authority repair.
- [x] D11 future public-pool expectation and D8 booster-family public-mechanics expectation.
- [x] Major Tarot/Spectral/boss semantics and exact score/ordering audits.
- [x] D14/D11 SHOP latency stabilization: ~20.8 s → ~3.17 s reroll-future path; gate closed.
- [x] D1 stage timing and candidate-deadline repair.
- [x] Green Joker safe no-discard execution guard: commits `8f94d60a` / `b27e73d8`.
- [x] Bounded semantic D1 prefilter repair `76dc7b90` / `2ceb8a6b`; D1 latency reclosed by focused + three-run evidence.
- [x] Identify The Mouth zero-score singleton recovery defect in `balatro-20260828T144652Z-379b8315`.
- [x] Implement Mouth wide recovery filter `bc535051` and regression `b93b2e0b`.
- [ ] **Current deterministic gate:** targeted Mouth regression, then full `tests/balatro`.
- [ ] **Competence baseline gate:** replacement unchanged-HEAD `--three` batch after tests are green.
- [ ] Keep calibration frozen until that replacement batch has no reproducible semantic/runtime defect.
- [ ] Keep new gameplay features, decks, stake progression, and broader v1.1+ work frozen until the Red/White competence/performance gate closes.

## Calibration and promotion gate

Three live runs are sufficient for rapid defect discovery, not for proving a candidate is better. Any semantic/runtime fix invalidates the current calibration baseline because repository SHA changed.

After a clean unchanged-HEAD baseline exists, numerical tuning may resume under the existing Bond tuning contract. Promotion requires the documented fresh holdout/comparator gate, not a lucky three-run result.

Detailed dated implementation/performance evidence is retained in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`; exact active authority/wrapper boundaries are retained in `BALATRO_DECISION_AUTHORITY_MAP.md`.
