# ROADMAP — SINGLE SOURCE OF TRUTH

This is the only authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests locally. **Do not run tests from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every command block shown to the user must end with a trailing blank line after the final command.
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

> **Phase 4 — complex packs/consumables/vouchers/economy audit. Batch 1 validated at 55/55; Batch 2 opened-pack legality/fail-closed semantics implemented, validation pending.**

Validated checkpoints:

- Phase 0 authority consolidation: **COMPLETE / 24/24 semantic green**
- Full deterministic Balatro suite: **GREEN**
- Phase 1 D1 survival expansion: **COMPLETE / 33/33 green**
- Phase 2 simple shop survival: **COMPLETE / 42/42 green**
- Phase 3 coherent build evidence: **COMPLETE / 52/52 green**, `BUILD_COHERENCE` 12/12
- Phase 4 Batch 1 resource boundary: **GREEN / 55/55**, `RESOURCE_COHERENCE` 3/3

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

Numerical weighting remains deferred to Phase 6. No fresh semantic evidence justifies tuning before complex-resource and live validation.

# Phase 4 — COMPLEX PACKS / CONSUMABLES / VOUCHERS / ECONOMY AUDIT

Goal: make resource-heavy decisions respect transaction checkpoints, sunk-cost boundaries, target legality, deterministic vs stochastic outcome ownership, and current-run survival value without predicting hidden contents.

Initial audit order:

1. D8 unopened-booster transaction cost vs D9 opened-pack sunk-cost boundary — **Batch 1 GREEN**;
2. opened-pack target legality and unsupported stochastic effects failing closed — **active Batch 2**;
3. consumable inventory/slot pressure and BUY vs BUY_AND_USE authority;
4. voucher purchase value vs permanent downside and current-run resource reserve;
5. destructive/generative Spectral/Tarot choices only through explicit bounded outcome models;
6. cross-family D14 arbitration only after child resource semantics are trustworthy.

## Batch 1 — GREEN

Commits:

- `7b2fb576` — adds `red_white_semantic_phase4_resource_cases.py`.
- `961a889d` — wires Phase-4 cases into the semantic benchmark.

Validated locally at **55/55**, with `RESOURCE_COHERENCE` **3/3**.

Audit findings:

- D8 `BuildAwareShopBoosterPolicy` owns unopened-pack acquisition and prices public money, interest, reserve, pack family, layout, and build need without reading hidden pack contents.
- D9 `BalatroPackPolicy` owns visible choices after opening.
- production installs `pack_sunk_cost_policy`, making the default opened-pack Skip baseline exactly zero.
- pack acquisition money/interest/reserve cost is therefore paid once in D8 and must not be charged again after entering `*_PACK`.

Validated semantics:

1. `resource.booster.unopened_unaffordable_hold`
   - D8 HOLDs an unopened pack whose public price exceeds current money before family-level option value can authorize it.
2. `resource.pack.opened_positive_uses_sunk_cost_baseline`
   - after opening, default D9 Skip is zero;
   - a positive visible marginal beats Skip even when post-purchase cash is zero;
   - historical pack cost is not re-priced.
3. `resource.pack.opened_negative_can_skip`
   - a negative current visible marginal loses to zero Skip;
   - sunk cost does not force selection of a bad opened-pack outcome.

No production code or tuning values changed.

## Batch 2 — IMPLEMENTED / VALIDATION PENDING

Commits:

- `fcf9aceb` — adds `red_white_semantic_phase4_pack_cases.py`.
- `42ac455d` — wires Batch-2 opened-pack cases into the semantic benchmark.

Installed-stack audit findings:

- D9 production contains explicit public-state stochastic models for several effects that were historically deferred, including High Priestess, Emperor, Familiar/Grim/Incantation, Immolate, and Wraith.
- stochastic effects therefore must not be rejected merely for being stochastic; explicit complete public-state outcome ownership is the deciding boundary.
- deterministic targeted Tarot/Spectral effects delegate legal target admission and literal target value to D10/B6.
- `targeted_pack_literal_value_policy` keeps targeted effects below Skip when D10/B6 has no positive admitted target and does not add generic shop/category utility.
- `strategy_plan_pack_policy` only adds bounded preference to already-positive choices, so it remains subordinate to D9 admission.
- genuinely deferred or unclassified visible effects must remain below opened-pack Skip=0 until an explicit mechanics/outcome model owns them.

New semantics:

1. `resource.pack.target_requires_positive_legal_target`
   - a targeted visible Tarot with no positive admitted D10/B6 target must lose to Skip=0.
2. `resource.pack.deferred_stochastic_fails_closed`
   - a production-deferred stochastic Spectral remains below Skip and cannot inherit generic Spectral utility.
3. `resource.pack.unclassified_effect_fails_closed`
   - an unclassified visible Spectral fails closed rather than receiving generic category or strategy value.

Batch 2 changes semantic coverage only. No production code or tuning values changed.

Expected benchmark: **58/58**, with `RESOURCE_COHERENCE` **6/6**.

# EXACT NEXT ACTION

Validate Phase-4 Batch 2 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

Do not run it from ChatGPT.

### If 58/58 green

Record Batch 2 green and continue Phase 4 with **consumable inventory/slot pressure and BUY vs BUY_AND_USE authority**. Audit D4 admission, immediate-use execution, inventory capacity, and D14 normalization before adding semantics.

### If any Batch-2 case fails

Classify fixture mismatch vs a real installed-D9 admission defect. Fix the smallest canonical owner. Do not blanket-reject modeled stochastic effects, do not bypass D10/B6 target legality, and do not let strategy/category bonuses lift a non-positive D9 base choice.

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
- Phase-2 expansion beyond four validated batches
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
