# Roadmap

> The roadmap tracks active milestones, not release notes. Completed implementation history is retained in [`docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`](docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md).
>
> Production observation remains repository-owned read-only process memory. Production execution remains the repository-owned first-party bridge. Hidden future information remains excluded.
>
> **Course correction — 2026-08-27:** feature growth is frozen until Red Deck / White Stake competence is measured, stable, and reproducible. Feature coverage, a green unit suite, or one isolated win are not sufficient evidence of competence.

# New-chat handoff: read this first

A fresh development chat should be able to continue from this section without relying on prior conversation history.

## Repository / branch / working rules

- Repository: `LeafStardust/game-ai-framework`
- Active branch: `feat/v1.0-red-white-competence`
- Work only on that branch unless the user explicitly changes scope.
- Do **not** run tests on the assistant side. The user pulls and runs tests locally.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Do not hard-code arbitrary Joker tier lists or named shop-combination strategy tables.
- Do not start Optuna/numerical tuning until deterministic tests and the semantic competence gate are stable.
- Do not resume Red Stake or new-deck feature work until the Red/White competence gate passes.
- A live three-run batch is **not** a progress metric. Live runs are integration smoke tests and sources of new benchmark counterexamples.
- Before fixing a newly observed semantic defect, add a benchmark/property case for the defect whenever practical.
- Prefer moving semantics into canonical evaluators/arbiters over adding another late monkeypatch/rescue layer.
- Obsolete/redundant tests may be removed when they protect retired behavior or duplicate stronger semantic coverage. Preserve mechanics, legality, production authority boundaries, and distinct failure modes.
- **Repository-operation rule:** when the repository, branch, and exact target file paths are already known, use direct branch-scoped file fetch/update/delete operations immediately. Do **not** spend time on repository-wide search, commit-history probing, connector/tool rediscovery, or schema rediscovery merely to relocate known files. Broad search/discovery is justified only when the exact path or relevant implementation is genuinely unknown. Once a needed GitHub action schema has been loaded in the current session, reuse it instead of repeatedly rediscovering the same tool.

## Validation workflow

Do **not** require the user to run the entire Balatro suite after every small implementation change.

During an active consolidation or runtime-performance batch:

1. The assistant should complete several logically related items before requesting validation.
2. After a batch, request only the smallest useful targeted tests for the files/behavior changed, plus the semantic benchmark when the batch changes decision semantics.
3. If a targeted test fails because it protects behavior that has now been deliberately retired, inspect it and remove/update it only when the newer semantic contract is stronger and correct.
4. Continue batching and targeted validation until the current consolidation group is complete.
5. Only then ask the user for the full deterministic Balatro suite.
6. Fix all remaining full-suite regressions as the final integration pass for that batch.
7. A full deterministic suite is mandatory before live validation, release promotion, or moving to another major roadmap phase.

Typical targeted commands should name the affected files explicitly, for example:

```powershell
python -m pytest -q tests/balatro/test_balatro_generation_pool_metadata_cache.py
```

Final deterministic integration gate:

```powershell
python -m pytest -q tests/balatro
```

The semantic benchmark remains available when decision semantics change:

```powershell
python -m games.balatro.red_white_semantic_benchmark
```

This workflow is intended to avoid repeatedly spending full-suite runtime while architecture is still changing, without weakening the final deterministic gate.

## Current active objective

> **Red Deck / White Stake, normal mode, maximize probability of winning the current run.**

No collection-first, Endless-first, new deck/stake, or feature-expansion work is active.

## Current architecture findings

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- D1 action arbitration: `LiveHandActionPolicy` and production `StrategyAwareLiveHandActionPolicy` wrappers.
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / path-aware live hand engine.
- D14 intended cross-family shop authority: `BuildAwareShopArbiter`.
- Bond/composition and Build Health are **evidence**, not separate final authorities.
- SHOP latency currently occurs primarily **before D14 receives a SHOP observation**; once an observation is emitted, D14 decisions are generally immediate in the latest live traces.
- Current production still contains ordered monkeypatch-style wrappers. See [`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md`](docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md).
- Historical implementation detail is retained in [`docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`](docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md).

## Current checkpoint — 2026-08-27 late live gate

The semantic/runtime correctness gate is substantially cleaner than the earlier 2026-08-25/26 state. The **current release blocker is SHOP observation latency**, not ordinary D14 decision computation.

Validated before the newest latency-cache batch:

- full deterministic `tests/balatro` suite reported green by the user;
- Mouth discard-only legality now recovers through a legal discard instead of crashing D1;
- sticky post-win `won` state no longer creates false victories after an actual loss;
- five-slot Joker ordering is bounded, and SHOP ordering is skipped entirely when the roster has no order-sensitive Joker;
- D1 repeated-singleton recovery was corrected at multiple authority layers: wider discard candidates survive the prefilter, non-clearing discard recovery quality outranks exactness in the scoped final/planner paths, and zero-signal recovery prefers broader redraws after genuine strategy evidence;
- secret-hand base scores and representative B3 probes are native to canonical owners; the installer was retired;
- outer D1 evaluation caching is native; its retired installer/shim is gone;
- recent three-run live batches terminate naturally without the prior Mouth crash, false terminal state, or SHOP Joker-order stall.

Latest production evidence:

- Session `balatro-20260827T193453Z-4dfd2a3e` completed all three attempts naturally.
- Attempt 1 reached Ante 4 and lost `3932 / 5000`; attempts 2 and 3 reached Ante 3 and Ante 2 respectively. Losses themselves are tuning/strength evidence, not correctness failures.
- Attempts 2 and 3 were responsive, but attempt 1 repeatedly showed roughly **31–57 second gaps** between SHOP-causing actions/transitions and the next emitted SHOP observation.
- Once those SHOP observations existed, D14 decisions followed essentially immediately. Therefore do **not** diagnose the current blocker as cross-family shop arbitration without new evidence.
- The first metadata cache (`2a6ae76`, `a248a12`, `cb41f8e`) memoized center `string_fields` decoding and improved some runs, but attempt 1 proved that was insufficient.
- Static inspection then found that every public observation still re-enumerated the entire Joker rarity arrays and Tarot/Spectral pool arrays. SHOP readiness/quiet settlement performs multiple public observations per checkpoint, multiplying that cost.

Newest unvalidated latency batch on current HEAD:

- `dbed73b3` — `fix(balatro): cache live Joker pool enumeration`
- `1fca5439` — `fix(balatro): cache live consumable pool enumeration`
- `2ea3d5e7` — `test(balatro): cover generation pool enumeration cache`

The widened cache stores only attempt-static pool membership and center metadata. These remain live on every observation: used/owned duplicate eligibility, Showman, challenge bans, pool flags, enhancement gates, round-specific Joker public state, edition rate, voucher state, and other run-dependent predicates. Partial catalogue reads are not frozen. Caches reset at `GAME_OVER` so profile unlock changes are reread next attempt.

### Immediate next sequence

1. User validates current HEAD locally; the most relevant targeted test is `python -m pytest -q tests/balatro/test_balatro_generation_pool_metadata_cache.py`, followed by `python -m pytest -q tests/balatro` when appropriate.
2. If green, perform a **focused live SHOP latency check first**, not another blind generic three-run batch solely for latency. Observe several SHOP transitions/purchases and confirm the old 30–60+ second observation gaps are gone.
3. If SHOP observation latency remains high, instrument/profile the observer path before changing D14 semantics or lowering a global timeout. Candidate remaining costs include other large live-memory table walks, public-payload reconstruction/fingerprinting, and semantic quiet observation multiplication.
4. If SHOP latency is clean, resume/close the live correctness gate. Occasional difficult D1 decisions may be slower, but recurring >60-second decisions remain a v1.0 competence defect and require a dedicated latency-budget pass.
5. After correctness + interactive latency are clean, move to numerical calibration/tuning. Do not keep changing architecture merely because a run loses.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 foundation + autonomous integration | Complete | Historical implementation retained separately |
| **v1.0.0 Red/White release baseline** | **Complete / historical** | Released 2026-08-20 |
| **v1.0.x Red/White competence stabilization** | **IN PROGRESS** | Current blocker: interactive SHOP observation latency, then live gate → numerical calibration |
| New gameplay features | **FROZEN** | No expansion before v1.0.x competence gate |
| Bond numerical tuning / Optuna | **Implemented / frozen** | Resume only after semantics + latency are trustworthy |
| v1.1–v1.7 Red Deck stake progression | Blocked | Begins after Red/White competence gate |
| Collection-first progression | Retired from active roadmap | Winning is the sole gameplay objective |
| v2+ additional decks | Not started | Begins after Red Deck progression |

---

# Active doctrine

Until v1.0.x is complete, the project has one gameplay target:

> **Red Deck / White Stake, normal mode, maximize the probability of winning the current run.**

No new collection objective, Endless objective, deck/stake adaptation, strategic framework, or speculative mechanics work should be added unless a benchmarked Red/White competence failure proves it necessary.

Existing mechanics, Joker implementations, Bond/composition code, pack models, diagnostics, collection tooling, and previous strategy implementations remain useful repository assets. They stop expanding the active scope.

## What counts as progress now

The project uses four validation layers:

1. **deterministic tests** — implementation contracts and mechanics do not regress;
2. **mechanics coverage** — modeled Balatro behavior remains accurate;
3. **semantic competence benchmark** — known important states produce sensible behavior;
4. **live runs** — integration/runtime smoke tests and sources of new counterexamples.

During active architectural batching, deterministic validation is intentionally split into targeted tests first and one full-suite integration gate at the end of the batch.

---

# v1.0.x — Red/White competence stabilization

## Why the previous approach stalled

The agent accumulated many individually reasonable policies, evaluators, guards, rescue rules, and diagnostics. Several can influence the same final action. This produced **policy accretion**: local components can be correct while their composition makes an obviously poor decision.

The goal of v1.0.x is therefore not “add more intelligence.” It is:

> **make the intelligence already present compose into one reliable run-winning decision process.**

## Target authority shape

```text
Authoritative public state
        ↓
Literal Balatro mechanics
        ↓
Legal candidates
        ↓
Bounded projection
        ↓
One run-winning evaluator
        ↓
One final arbiter
        ↓
Action
```

Bond/composition and Build Health remain evidence. They must not become independent competing definitions of value.

---

## Phase 0 — Freeze and simplify authority

**Goal:** know exactly which component has final authority for each action family.

Canonical inventory: [`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md`](docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md).

- [x] Freeze new gameplay features.
- [x] Inventory production components currently capable of changing a D1 action and identify `LiveBlindClearPlanner`/`D1LiveBlindClearPlanner` as projection/search authority, `LiveHandActionPolicy` as action arbiter, and `LiveHandActionDecisionEngine` as D1 orchestration/final-return authority.
- [x] Inventory production components currently capable of changing D2/D14 shop decisions and identify `BuildAwareShopArbiter` as intended cross-family final authority.
- [ ] Complete per-wrapper M/P/E/S/A/G/D classification for every installed D1 and shop wrapper.
- [ ] Remove or merge late rescue/correction policies when their logic belongs inside the canonical evaluator/arbiter.
- [ ] Verify all diagnostics/monitoring paths are D-only and cannot launch independent planning that affects runtime or action selection.

**Exit gate:** one documented and enforced final authority exists for each action family, with late semantic rescue layers consolidated.

---

## Phase 1 — Semantic competence benchmark

**Goal:** create a stable progress meter instead of judging progress from random runs.

Build a checked-in benchmark of roughly **50–100 captured or reconstructed public checkpoints**. Each case should test a behavioral property rather than a fragile exact action unless exactness is mechanically required.

Implementation:

- [x] Add reusable property-based benchmark framework with overall and per-category scores.
- [x] Add CLI runner: `python -m games.balatro.red_white_semantic_benchmark`.
- [x] Add deterministic pytest gate for the semantic suite.
- [x] Seed benchmark with reconstructed Red/White semantic cases across D1 recovery/authority, shop authority, build, resource, and boss behavior.
- [ ] Expand the suite using the existing live-run failure archive and important mechanical boundaries as needed by new defects.
- [ ] Ensure every known recent obvious stupid-play class has at least one semantic/property regression before its next architectural fix when practical.

### Initial D1 cases

- guaranteed clear must be taken;
- useful discards must be used when current pace is inadequate;
- trivial one-card plays must not burn hands while useful discards remain;
- repeated one-card discards must be exceptional unless mechanics make precision relevant;
- survival-equivalent lines may preserve valuable held cards;
- forced selections and boss rules must be obeyed;
- impossible-clear states should maximize remaining progress rather than preserve irrelevant resources;
- timeout must retain completed canonical D1 evidence;
- late adaptive evidence cannot reverse the finalized Play/Discard survival class.

### Initial shop cases

- affordable obvious immediate scoring must be bought when underpowered and strategically legal;
- mechanical/Bond conflicts must still veto inappropriate buys;
- obviously dead components must be replaceable by materially better legal candidates;
- interest/economy should be preserved for marginal purchases;
- rich underpowered builds should reroll when the visible shop is inadequate;
- rerolls must not violate survival reserve.

### Initial build cases

- functioning engines must survive marginal side-development offers;
- real scaling deficits must be detected before current-blind survival collapses;
- dormant/theoretical synergy cannot count as realized scoring;
- coherent pivots must remain possible when projected whole-build value is genuinely better.

### Initial pack/consumable/boss cases

- hidden future value is never predicted;
- deterministic visible improvements are not skipped without adequate reason;
- speculative pack EV cannot override immediate survival;
- boss mechanics/legality remain exact.

**Exit gate:** every known recent obvious stupid-play class has a regression/semantic case and the benchmark is broad enough to detect cross-policy regressions before live testing.

---

## Phase 2 — D1 survival competence FIRST

**Goal:** with current resources fixed, play the blind sensibly.

Until this phase passes, shop sophistication is secondary.

### Default D1 comparison order

1. probability of clearing the blind;
2. feasibility/confidence of remaining clear paths, including proven exact vs sampled where trust matters;
3. expected progress toward the target;
4. expected hands remaining;
5. expected discards remaining;
6. expected score/economy/generated resources as later tie-breaks.

Exact boss mechanics and forced actions remain authoritative. `exact` is confidence/safety evidence where it distinguishes a proven line from a sampled/uncertain one; it is not arbitrary bonus utility.

### Required work

- [ ] Continue auditing D1 candidate generation only when live evidence identifies a remaining defect.
- [x] Ensure timeout/fallback reuses completed canonical D1 survival evidence.
- [x] Prevent the path-aware post-policy layer from reversing the finalized Play/Discard class.
- [x] Ensure useful multi-card discards survive the candidate beam.
- [x] Scope recovery ranking so non-clearing discard quality outranks exactness without changing exact PLAY behavior.
- [x] Prefer broader redraws in degenerate zero-signal recovery states after genuine strategy evidence.
- [ ] Remove late D1 guards after their semantics are represented canonically where doing so is low-risk and justified.
- [ ] Continue boss-sensitive coverage when a new production failure is observed.
- [ ] Keep interactive runtime bounded without silently switching objectives.

**Exit gate:** D1 benchmark is effectively clean and fresh live runs show no known dominated hand/discard behavior.

---

## Phase 3 — Simple shop survival

**Goal:** make the shop behave like a competent conservative player before complicated long-horizon cleverness.

The shop should first answer:

- Am I strong enough for the next blind?
- Does this visible purchase materially improve survival/scaling?
- Is this replacement genuinely better than what I own?
- Can I afford it without destroying required reserve/economy?
- If nothing useful is visible and I am weak but rich, should I reroll?

### Required work

- [ ] Establish/verify one shared final comparison scale across Jokers, vouchers, boosters, consumables, rerolls, and END_SHOP.
- [ ] Immediate legal survival/scoring value cannot be blocked by a generic adequacy threshold.
- [ ] Mechanical/Bond conflicts remain authoritative.
- [ ] Replace repeated runtime rescue monkeypatches with canonical D14 terms where possible.
- [ ] Keep future-public-pool expectations bounded and subordinate to visible current-shop survival.
- [x] Bound five-slot Joker ordering and bypass order evaluation for rosters with no order-sensitive Joker.
- [ ] **Current blocker:** make normal SHOP observation/settlement responsive; do not confuse observer latency with D14 compute latency.
- [ ] Preserve paid-reroll stop-loss while allowing rerolls for rich, underpowered builds with inadequate visible offers.

**Exit gate:** shop benchmark is clean and normal SHOP decisions are responsive.

---

## Phase 4 — Coherent build authority

**Goal:** use Bond/composition and Build Health as evidence inside one final run-winning decision process.

- [ ] Keep literal scoring separate from structural Build Health.
- [ ] Keep Bond development separate from realization.
- [ ] R0/partial Bonds may affect future value but cannot manufacture immediate scoring power.
- [ ] Mature realized engines receive preservation credit based on real disruption cost.
- [ ] Pivots remain legal when complete projected-build value materially exceeds the incumbent after transaction/economy/disruption costs.
- [ ] Full-board replacement compares complete resulting builds rather than isolated Joker values.
- [ ] Ante-1 strategy evidence may guide purchases but cannot outrank survival when weak.

**Exit gate:** no known “full board but non-functioning build” failure remains in benchmark/live validation.

---

## Phase 5 — Reintegrate complex packs, consumables, vouchers, economy

The extensive implementations already present remain valuable. This phase audits their authority rather than rebuilding them.

- [ ] Keep/re-enable complex future-value models only when they improve benchmark behavior at acceptable runtime cost.
- [ ] One-layer public expectation remains the normal unopened stochastic boundary.
- [ ] Actual opened/held choices may use full modeled mechanics when the decision becomes real.
- [ ] Hidden future shop contents, draw order, and RNG state remain forbidden.
- [ ] Long-horizon option value cannot override clearly necessary immediate survival without explicit projected evidence.

**Exit gate:** complex resource behavior preserves every earlier competence category.

---

## Phase 6 — Live validation

Live runs return only after the deterministic/semantic gate is stable enough for integration evidence.

Sequence from the current checkpoint:

1. validate the current SHOP-observer cache batch locally;
2. use a focused live SHOP check to verify observation latency before spending another full three-run batch;
3. if latency remains bad, profile/instrument observation and settlement rather than changing D14 semantics blindly;
4. once SHOP responsiveness is clean, resume one unchanged-HEAD three-attempt Red/White smoke batch;
5. inspect questionable decisions, not only the loss screen;
6. when a new semantic defect appears, add its checkpoint/property before fixing it where practical;
7. after a semantically clean live gate, perform the dedicated broader latency-budget pass before numerical tuning if recurring slow decisions remain.

### Red/White competence gate before Red Stake

- [x] deterministic Balatro suite green at the latest user-validated checkpoint;
- [ ] current HEAD deterministic suite green after the latest latency-cache batch;
- [ ] semantic benchmark stable and near-clean across D1, shop, build, and boss categories;
- [ ] no known mechanically contradictory or clearly dominated production decision;
- [ ] normal decision latency within the interactive runtime budget, with slow outliers instrumented and explained;
- [ ] repeated live batches do not reproduce the same obvious failure class;
- [ ] at least one fresh unchanged-HEAD batch clears Ante 8 without a release-blocking semantic defect;
- [x] recent supervisor/restart/shutdown attempts complete naturally without the former fourth-restart/false-terminal failures.

---

## Phase 7 — Numerical tuning only after semantics

The existing Optuna/Bond calibration foundation remains useful, but tuning stays frozen until numerical search is optimizing preferences rather than compensating for wrong mechanics or conflicting authorities.

Allowed examples: contributor weights, empirical thresholds, synergy/conflict coefficients, pivot resistance, motif strengths, and resource-policy thresholds.

Forbidden targets: mechanical truth, legality, boss rules, hidden information, or categorical overrides created solely to hide benchmark failures.

Promotion still requires fresh controlled comparison with **at least 20 completed episodes per arm** and implemented non-regression/pathology gates.

---

# Collection progression — RETIRED FROM ACTIVE ROADMAP

Collection/unlock state may remain for diagnostics or exact-tie metadata, but it must not turn a strategically inferior action into the selected action or intentionally sacrifice run-winning probability.

---

# v1.1–v1.7 — Red Deck stake progression — BLOCKED

| Version | Stake | New adaptation focus |
|---|---|---|
| **v1.1** | **Red** | No Small Blind reward money |
| v1.2 | Green | Green Stake score scaling |
| v1.3 | Black | Eternal Joker adaptation |
| v1.4 | Blue | Reduced-discard adaptation |
| v1.5 | Purple | Purple Stake score scaling |
| v1.6 | Orange | Perishable Joker adaptation |
| v1.7 | Gold | Rental Joker adaptation and all-stakes validation |

Stake progression begins only after the v1.0.x semantic/live competence gate passes. New stakes must reuse the permanent architecture rather than introduce another strategy framework.

---

# v2+ — Additional decks

Planned order after Red Deck completion:

1. Blue Deck — v2.x
2. Yellow Deck — v3.x
3. Green Deck — v4.x
4. Black Deck — v5.x

Additional-deck cartridges reuse the same permanent Balatro architecture and add only genuine deck/stake-specific modifiers where necessary.