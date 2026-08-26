# Roadmap

> The roadmap tracks active milestones, not release notes. Completed implementation history has been retained in [`docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`](docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md).
>
> Production observation remains repository-owned read-only process memory. Production execution remains the repository-owned first-party bridge. Hidden future information remains excluded.
>
> **Course correction — 2026-08-27:** feature growth is frozen until Red Deck / White Stake competence is measured, stable, and reproducible. Feature coverage, a green unit suite, or one isolated win are no longer sufficient evidence of competence.

# New-chat handoff: read this first

A fresh development chat should be able to continue from this section without relying on prior conversation history.

## Repository / branch / working rules

- Repository: `LeafStardust/game-ai-framework`
- Active branch: `feat/v1.0-red-white-competence`
- Work only on that branch unless the user explicitly changes scope.
- Do **not** run tests on the assistant side. The user pulls and runs tests locally.
- User validation command:
  ```powershell
  python -m pytest tests/balatro -q
  ```
- Semantic competence command:
  ```powershell
  python -m games.balatro.red_white_semantic_benchmark
  ```
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Do not hard-code arbitrary Joker tier lists or named shop-combination strategy tables.
- Do not start Optuna/numerical tuning until deterministic tests and the semantic competence gate are stable.
- Do not resume Red Stake or new-deck feature work until the Red/White competence gate below passes.
- A live three-run batch is **not** a progress metric. Live runs are integration smoke tests and sources of new benchmark counterexamples.
- Before fixing a newly observed semantic defect, add a benchmark/property case for the defect whenever practical.
- Prefer moving semantics into canonical evaluators/arbiters over adding another late monkeypatch/rescue layer.

## Current active objective

> **Red Deck / White Stake, normal mode, maximize probability of winning the current run.**

No collection-first, Endless-first, new deck/stake, or feature-expansion work is active.

## Current architecture findings

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- D1 action arbitration: `LiveHandActionPolicy` and production `StrategyAwareLiveHandActionPolicy` wrappers.
- D1 orchestration/final return: `LiveHandActionDecisionEngine`.
- D14 intended cross-family shop authority: `BuildAwareShopArbiter`.
- Bond/composition and Build Health are intended to be **evidence**, not separate final authorities.
- Current production still contains many ordered monkeypatch-style wrappers. See [`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md`](docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md).
- Historical implementation detail is retained in [`docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`](docs/balatro/BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md).

## Current checkpoint

Completed so far:

- feature-growth freeze established;
- authority-map document created;
- semantic benchmark framework created;
- CLI semantic benchmark runner created;
- pytest semantic gate created;
- benchmark currently seeded with **6** reconstructed Red/White semantic cases;
- the attempted change that moved D1 `exact` evidence below progress was reverted after it regressed proven exact-clear behavior (`retained_pair` and Psychic full-house clear). The benchmark case encoding that invalid premise was removed.

Current known architectural defect to tackle next **after the suite/semantic benchmark are green**:

> **D1 timeout/fallback objective divergence.** `LiveHandActionDecisionEngine._structural_timeout_fallback()` can abandon already-established canonical D1 survival reasoning and switch to a structural heuristic based on poker-hand category/ranks and a separate discard rule. Timeout must not invent a second strategy.

Next implementation sequence:

1. Confirm `python -m pytest tests/balatro -q` is green on the current HEAD.
2. Confirm `python -m games.balatro.red_white_semantic_benchmark` is green.
3. Add a semantic property/regression covering timeout consistency.
4. Refactor timeout handling so that, when any bounded D1 search evidence completed before the deadline, timeout reuses that canonical evidence instead of switching to the structural poker-hand/rank heuristic.
5. Keep a minimal emergency legal-action fallback only for the pathological case where **no canonical search evidence completed at all**.
6. Re-run the two user-side gates before proceeding further.
7. Continue per-wrapper D1 authority classification and consolidation; do not jump to live runs yet.

If new deterministic failures appear, treat them as a batch and identify the shared architectural cause before proceeding. Do not weaken proven mechanics tests merely to satisfy the new roadmap.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 foundation + autonomous integration | Complete | Historical implementation retained separately |
| **v1.0.0 Red/White release baseline** | **Complete / historical** | Released 2026-08-20 |
| **v1.0.x Red/White competence stabilization** | **IN PROGRESS** | Semantic benchmark → D1 survival → simple shop → coherent build → live validation |
| New gameplay features | **FROZEN** | No expansion before v1.0.x competence gate |
| Bond numerical tuning / Optuna | **Implemented / frozen** | Resume only after semantics are trustworthy |
| v1.1–v1.7 Red Deck stake progression | Blocked | Begins after Red/White competence gate |
| Collection-first progression | Retired from active roadmap | Winning is the sole gameplay objective |
| v2+ additional decks | Not started | Begins after Red Deck progression |

---

# Active doctrine

Until v1.0.x is complete, the project has one gameplay target:

> **Red Deck / White Stake, normal mode, maximize the probability of winning the current run.**

No new collection objective, Endless objective, deck/stake adaptation, strategic framework, or speculative mechanics work should be added unless a benchmarked Red/White competence failure proves it necessary.

Existing mechanics, Joker implementations, Bond/composition code, pack models, diagnostics, collection tooling, and previous strategy implementations remain useful repository assets. They are preserved in the implementation-history document; they simply stop expanding the active scope.

## What counts as progress now

The project uses four validation layers:

1. **deterministic tests** — implementation contracts do not regress;
2. **mechanics coverage** — modeled Balatro behavior remains accurate;
3. **semantic competence benchmark** — known important states produce sensible behavior;
4. **live runs** — integration/runtime smoke test and source of new counterexamples.

A random three-run batch is **not** the competence score. It is a way to discover states the semantic benchmark is missing.

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
- [x] Inventory production components currently capable of changing a D1 action and identify `LiveBlindClearPlanner`/`D1LiveBlindClearPlanner` as the projection/search authority, `LiveHandActionPolicy` as the action arbiter, and `LiveHandActionDecisionEngine` as the D1 orchestration/final-return authority.
- [x] Inventory production components currently capable of changing D2/D14 shop decisions and identify `BuildAwareShopArbiter` as the intended cross-family final authority.
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
- [x] Seed the benchmark with the first six reconstructed cases covering D1 recovery/authority, early scoring admission, conflict authority, early voucher survival, and reachable conditional scoring.
- [ ] Expand the seed to roughly 50–100 cases using the existing live-run failure archive and important mechanical boundaries.
- [ ] Ensure every known recent obvious stupid-play class has at least one semantic property case before its next architectural fix.

### Initial D1 cases

- guaranteed clear must be taken;
- useful discards must be used when current pace is inadequate;
- trivial one-card plays must not burn hands while useful discards remain;
- repeated one-card discards must be exceptional unless mechanics make precision relevant;
- survival-equivalent lines may preserve valuable held cards;
- forced selections and boss rules must be obeyed;
- impossible-clear states should maximize remaining progress rather than preserve irrelevant resources.

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

**Benchmark output:** overall pass count plus category scores.

**Exit gate:** every known recent obvious stupid-play class has a regression/semantic case and the benchmark is broad enough to detect cross-policy regressions before live testing.

---

## Phase 2 — D1 survival competence FIRST

**Goal:** with current resources fixed, play the blind sensibly.

Until this phase passes, shop sophistication is secondary.

### Default D1 comparison order

1. probability of clearing the blind;
2. feasibility/confidence of remaining clear paths, including whether a line is proven exact or sampled where that distinction affects trustworthiness;
3. expected progress toward the target;
4. expected hands remaining;
5. expected discards remaining;
6. expected score/economy/generated resources as later tie-breaks.

Exact boss mechanics and forced actions remain authoritative. `exact` must not be treated as arbitrary bonus utility, but it **is** valid confidence/safety evidence when distinguishing a proven line from a sampled/uncertain one.

### Required work

- [ ] Audit D1 candidate generation before tuning weights.
- [ ] Ensure useful multi-card discards survive the candidate beam.
- [ ] Prevent recovery behavior from oscillating between “discard everything” and “never discard”.
- [ ] Ensure timeout/fallback paths use the same survival objective as normal search.
- [ ] Remove late D1 guards after their semantics are represented canonically.
- [ ] Benchmark boss-sensitive states including The Hook, The Club, Cerulean Bell, Verdant Leaf, and Crimson Heart.
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

- [ ] Establish one shared final comparison scale across Jokers, vouchers, boosters, consumables, rerolls, and END_SHOP.
- [ ] Immediate legal survival/scoring value cannot be blocked by a generic adequacy threshold.
- [ ] Mechanical/Bond conflicts remain authoritative.
- [ ] Replace repeated runtime rescue monkeypatches with canonical D14 terms where possible.
- [ ] Keep future-public-pool expectations bounded and subordinate to visible current-shop survival.
- [ ] Remove nested planning whose runtime cost is disproportionate to its authority.
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

**Exit gate:** no known “full board but non-functioning build” failure remains in the benchmark/live validation.

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

Live runs return only after the semantic benchmark is stable.

Sequence:

1. `tests/balatro` green;
2. semantic benchmark passes required category gates;
3. one three-attempt Red/White smoke batch;
4. inspect questionable decisions, not only the loss screen;
5. when a new semantic defect appears, add its checkpoint/property to the benchmark **before fixing it**;
6. rerun deterministic + semantic gates;
7. repeat live validation on the new SHA.

### Red/White competence gate before Red Stake

- [ ] deterministic Balatro suite green;
- [ ] semantic benchmark stable and near-clean across D1, shop, build, and boss categories;
- [ ] no known mechanically contradictory or clearly dominated production decision;
- [ ] normal decision latency within the interactive runtime budget, with slow outliers instrumented and explained;
- [ ] repeated live batches do not reproduce the same obvious failure class;
- [ ] at least one fresh unchanged-HEAD batch clears Ante 8 without a release-blocking semantic defect;
- [ ] supervisor/restart/shutdown path completes cleanly.

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
