# ROADMAP — SINGLE SOURCE OF TRUTH

This is the only authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests locally. **Do not run tests from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Preserve exact mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Do not tune broadly to hide semantic defects.

## Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical authority:

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

Canonical owners:

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`

Bond/composition and Build Health are evidence/planning layers, never immediate score/action authorities.

# Current state — 2026-08-31

> **Phase 3 — coherent build evidence/authority quality. Batch 3 validated 48/48; Batch 4 Bond/composition authority semantics implemented, validation pending.**

Validated checkpoints:

- Phase 0 authority consolidation: **COMPLETE / 24/24 semantic green**
- Full deterministic Balatro suite: **GREEN**
- Phase 1 D1 survival expansion: **COMPLETE / 33/33 green**
- Phase 2 simple shop survival: **COMPLETE / 42/42 green**
- Phase 3 Batch 1: **44/44 green**, `BUILD_COHERENCE` 4/4
- Phase 3 Batch 2: **46/46 green**, `BUILD_COHERENCE` 6/6
- Phase 3 Batch 3: **48/48 green**, `BUILD_COHERENCE` 8/8

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc`.

# Phase 1 — CLOSED

Intentionally capped at five batches. Validated D1 semantics include guaranteed-clear resource preservation, recursive boss legality, under-pace redraw quality, final-discard conservation, timeout authority, final-hand preservation, hidden draw-order invariance, and held-consumable re-observation. Do not add Batch 6 absent fresh evidence.

# Phase 2 — CLOSED

Intentionally capped at four batches. Validated simple-shop semantics include explicit `END_SHOP`, free/paid reroll boundaries, replacement re-observation, cash stop-loss, bounded first-engine reserve relaxation, reserve-crossing economics, and shared-scale cross-family ordering. Do not add Batch 5 absent fresh evidence.

Important runtime fact: installed post-transaction D2 Joker valuation recomputes candidate mechanical value through `transition_planner.evaluator.evaluate()` at actual post-purchase cash. Synthetic D2 fixtures must represent that path.

# Phase 3 — COHERENT BUILD EVIDENCE / AUTHORITY QUALITY

Goal: distinguish real scoring, support, scaling, economy, interaction, and composition without duplicate scoring authority or structural evidence becoming fake immediate power.

Audit order:

1. scoring engine versus support/economy — complete;
2. scaling potential versus realized scoring — complete;
3. contextual pair interaction versus standalone intrinsic — complete;
4. Bond/composition evidence versus literal score arithmetic — **active Batch 4**;
5. replacement/pivot evidence must remain downstream of legal D2 economics;
6. only then consider numerical weights.

## Batch 1 — VALIDATED GREEN

Commits: `0f5b0f3a`, `a89e8e6e`.

Validated:
- `build.roles.scoring_engine_direct_gain`
- `build.roles.economy_not_direct_scoring`

Result: **44/44**, BUILD 4/4.

## Batch 2 — VALIDATED GREEN AFTER CANONICAL FIX

Commits: `ab6cdee0`, `f2f5f4c8`.

Validated:
- `build.scaling.fresh_potential_is_contextual`
- `build.scaling.investment_increases_direct_power`

Initial 44/46 exposed a genuine lifecycle defect: score-sequence mutation carried a `HAND_SCORED` event but read-only checkpoints did not, so event-driven scalers such as Ride the Bus could grow public state without being classified as scaling. `f2f5f4c8` makes score checkpoints use the matching synthetic event on deep copies. Result after fix: **46/46**, BUILD 6/6.

## Batch 3 — VALIDATED GREEN

Commit: `e489d9dd`.

Validated:
- `build.interaction.blueprint_pair_only_value`
- `build.interaction.independent_scoring_not_pair_synergy`

Blueprint target-specific copy value is pair-only evidence; independent scoring output is not duplicated as pair synergy. Result: **48/48**, BUILD 8/8.

## Batch 4 — IMPLEMENTED / VALIDATION PENDING

Commit: `131dd37c`.

Audit findings:

- `JokerBuildValueEvaluator` owns literal score projection separately from contextual B3 value.
- D2 `_bond_transition_bonus()` projects public Bond/composition transitions after B3 mechanical value.
- raw composer `coherence_delta` is diagnostic only; coherence alone is intentionally not awarded as a purchase bonus.
- the installed post-transaction D2 layer adds the bounded Bond adjustment to the post-cash mechanical B3 marginal once.

New semantics:

1. `build.bond.coherence_not_scoring_bonus`
   - a synthetic composition transition that changes only `coherence_score` from 1 to 9 must produce zero Bond bonus;
   - composer coherence cannot manufacture chips or independent purchase value.
2. `build.bond.adjustment_added_once`
   - with mechanical whole-build gain fixed at 3 and Bond adjustment fixed at 2, D2 resulting build gain must be exactly 5;
   - protects against folding structural Bond evidence into B3 and then crediting it again.

No production code or numerical tuning changed in Batch 4.

Expected benchmark: **50/50**, `BUILD_COHERENCE` 10/10.

# EXACT NEXT ACTION

Validate Phase-3 Batch 4 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 50/50 green

Record Batch 4 green and continue Phase 3 with **replacement/pivot authority downstream of legal D2 economics**. Audit actual pivot/retention layers before adding cases. Add only concrete authority-boundary semantics; do not tune weights.

### If either Batch-4 case fails

Treat it as a credible Bond/D2 authority defect unless output shows a concrete fixture mismatch. Fix the smallest canonical owner. Do not add a D14 rescue or weaken the semantic.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — ACTIVE
5. Phase 4 — complex packs/consumables/vouchers/economy audit
6. Phase 5 — live validation
7. Phase 6 — numerical tuning only after semantics are trustworthy

Future stake/deck progression remains blocked until Red/White competence passes.

# Closed / do not reopen without fresh evidence

- Phase-0 ownership migrations and installer retirements
- Phase-1 expansion beyond five validated batches
- Phase-2 expansion beyond four validated batches
- Mouth discard-only legality defect
- Green Joker survival-equivalent authority
- Hook/log-resilience search reserve
- historical SHOP recursive expectation roots
- BLIND_SELECT quiescence deadlock
- ROUND_EVAL checkout fast path
- D1 root pre-beam wall-clock defect
- failed-trial tuner cascading
- Phase-A Bond exploratory tuning (no promotion)
- D14/D11 latency blocker absent fresh timing evidence
