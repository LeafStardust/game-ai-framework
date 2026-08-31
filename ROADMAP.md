# ROADMAP — SINGLE SOURCE OF TRUTH

This is the only authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests locally. **Do not run tests from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every command block shown must end with a trailing blank line after the final command.
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

> **Phase 4 — complex packs/consumables/vouchers/economy audit. Batches 1-5 green through 67/67; Batch 6 cross-family D14 parent-normalization semantics implemented, validation pending.**

Validated checkpoints:

- Phase 0 authority consolidation: **COMPLETE / 24/24 semantic green**
- Full deterministic Balatro suite: **GREEN**
- Phase 1 D1 survival expansion: **COMPLETE / 33/33 green**
- Phase 2 simple shop survival: **COMPLETE / 42/42 green**
- Phase 3 coherent build evidence: **COMPLETE / 52/52 green**, `BUILD_COHERENCE` 12/12
- Phase 4 Batch 1 resource boundary: **GREEN / 55/55**, `RESOURCE_COHERENCE` 3/3
- Phase 4 Batch 2 opened-pack legality/fail-closed: **GREEN / 58/58**, `RESOURCE_COHERENCE` 6/6
- Phase 4 Batch 3 consumable slot/mode authority: **GREEN / 61/61**, `RESOURCE_COHERENCE` 9/9
- Phase 4 Batch 4 voucher reserve/downside authority: **GREEN / 64/64**, `RESOURCE_COHERENCE` 12/12
- Phase 4 Batch 5 bounded outcome-model authority: **GREEN / 67/67**, `RESOURCE_COHERENCE` 15/15

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc`.

# Phase 1 — CLOSED

Intentionally capped at five batches. Do not add Batch 6 absent fresh evidence.

# Phase 2 — CLOSED

Intentionally capped at four batches. Do not add Batch 5 absent fresh evidence.

# Phase 3 — CLOSED

Phase 3 validated five coherent build-evidence batches:

1. scoring engine vs support/economy role separation;
2. scaling potential vs realized scoring power;
3. contextual pair interaction vs standalone intrinsic value;
4. Bond/composition evidence vs literal score arithmetic;
5. replacement/pivot authority downstream of legal and economically positive D2 options.

Batch 2 exposed and fixed one genuine canonical lifecycle defect: score-sequence checkpoints now carry the matching synthetic `HAND_SCORED` event so event-driven scalers such as Ride the Bus expose scaling evidence without mutating live state.

Final Phase-3 result: **52/52 GREEN**, `BUILD_COHERENCE` 12/12.

Numerical weighting remains deferred to Phase 6.

# Phase 4 — COMPLEX PACKS / CONSUMABLES / VOUCHERS / ECONOMY AUDIT

Goal: make resource-heavy decisions respect transaction checkpoints, sunk-cost boundaries, target legality, deterministic vs stochastic outcome ownership, and current-run survival value without predicting hidden contents.

Initial audit order:

1. D8 unopened-booster transaction cost vs D9 opened-pack sunk-cost boundary — **Batch 1 GREEN**;
2. opened-pack target legality and unsupported stochastic effects failing closed — **Batch 2 GREEN**;
3. consumable inventory/slot pressure and BUY vs BUY_AND_USE authority — **Batch 3 GREEN**;
4. voucher purchase value vs permanent downside and current-run resource reserve — **Batch 4 GREEN**;
5. destructive/generative Spectral/Tarot choices only through explicit bounded outcome models — **Batch 5 GREEN**;
6. cross-family D14 arbitration only after child resource semantics are trustworthy — **active Batch 6**.

## Batch 1 — GREEN

Validated locally at **55/55**, `RESOURCE_COHERENCE` **3/3**.

- D8 pays unopened-pack money/interest/reserve cost once.
- D9 opened-pack Skip baseline is zero after cost is sunk.
- Negative visible marginal can still Skip.
- D8 never reasons from hidden future pack identities.

## Batch 2 — GREEN

Validated locally at **58/58**, `RESOURCE_COHERENCE` **6/6**.

- targeted Tarot/Spectral choices require a positive admitted D10/B6 target;
- non-admitted stochastic/destructive effects remain below Skip=0;
- unclassified visible effects fail closed rather than inheriting generic category/strategy utility.

## Batch 3 — GREEN

Validated locally at **61/61**, `RESOURCE_COHERENCE` **9/9**.

- full inventory blocks persistent `BUY`;
- explicit `BUY_AND_USE` remains legal because it does not occupy a persistent slot;
- unsupported candidates cannot synthesize immediate-use authority;
- D14 does not re-price consumable-slot opportunity cost for immediate-use transactions.

## Batch 4 — GREEN

Validated locally at **64/64**, `RESOURCE_COHERENCE` **12/12**.

- D3 cannot buy through its hard post-purchase money floor;
- expensive early non-structural vouchers cannot crowd out the first scoring foothold;
- policy-contingent voucher effects such as Hieroglyph/Petroglyph contribute zero D14 parent value until benefit and permanent downside share a grounded common-unit model;
- D3 strategic admission remains child-owned while D14 cross-family normalization stays literal/resource-aware.

## Batch 5 — GREEN

Commits:

- `18006528` — adds `red_white_semantic_phase4_outcome_model_cases.py`.
- `9d22be05` — wires Batch-5 outcome-model cases into the semantic benchmark.

Validated locally at **67/67**, with `RESOURCE_COHERENCE` **15/15**.

- generative/stochastic effects may be admitted only when an explicit public-state expectation owns the outcome space;
- Judgement requires the authoritative observed eligible-Joker catalogue;
- large public Judgement pools use a deterministic bounded lower bound with omitted mass fixed at zero;
- no RNG seed, pseudoseed, selected future outcome, or future pool order is read;
- destructive Immolate remains below Skip when its current public-state expectation is unavailable.

No production code or tuning values changed in Batches 1-5.

## Batch 6 — IMPLEMENTED / VALIDATION PENDING

Commits:

- `84bd534c` — adds `red_white_semantic_phase4_cross_family_cases.py`.
- `eeb7dc52` — wires Batch-6 cross-family cases into the semantic benchmark.

Audit findings:

- D14 owns the final SHOP comparison only after D2/D3/D4/D8/D11 child admission;
- `END_SHOP` is the explicit zero normalized parent baseline, so a child may be locally admitted yet still lose after shared parent normalization;
- `ShopUtilityScale` recomputes shared money/interest/reserve/slot cost at the parent rather than comparing child-local totals directly;
- `consumable_d14_literal_policy` strips B4 structural units from non-Planet `BUY_AND_USE` parent comparison and retains only explicitly modeled immediate value plus shared resource cost;
- family identity must not become a second arbiter: a stronger normalized consumable may beat a booster, and the reverse must also hold.

New semantics:

1. `resource.shop.cross_family_negative_child_holds`
   - a locally admitted child with negative normalized parent utility loses to `END_SHOP=0`.
2. `resource.shop.cross_family_structural_units_do_not_leak`
   - a huge D4 child structural/build-path number cannot overpower a stronger D8 option when literal immediate consumable value is weak.
3. `resource.shop.cross_family_literal_consumable_can_win`
   - a materially stronger literal immediate consumable beats a weaker booster after common-scale normalization.

Batch 6 changes semantic coverage only. No production code or tuning values changed.

Expected benchmark: **70/70**, with `RESOURCE_COHERENCE` **18/18**.

# EXACT NEXT ACTION

Validate Phase-4 Batch 6 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

Do not run it from ChatGPT.

### If 70/70 green

Record Batch 6 green and close the planned Phase-4 audit. Then begin **Phase 5 live validation** from the installed production stack. Do not add a Phase-4 Batch 7 absent fresh semantic evidence from live runs.

### If any Batch-6 case fails

Classify fixture mismatch vs a real D14 parent-normalization defect. Fix the smallest canonical owner. Do not compare child-local totals cross-family, do not duplicate resource charges, do not let structural evidence leak into literal parent utility, and do not introduce family-priority overrides.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — ACTIVE
6. Phase 5 — live validation
7. Phase 6 — numerical tuning only after semantics are trustworthy

Future stake/deck progression remains blocked until Red/White competence passes.

# Closed / do not reopen without fresh evidence

- Phase-0 ownership migrations and installer retirements
- Phase-1 expansion beyond five validated batches
- Phase-2 expansion beyond four
- Phase-3 build-evidence expansion beyond validated authority semantics absent fresh evidence
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
