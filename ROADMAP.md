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

> **Phase 4 COMPLETE at 70/70 semantic green. Phase 5 live validation is ACTIVE.**

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
- Phase 4 Batch 6 cross-family D14 parent normalization: **GREEN / 70/70**, `RESOURCE_COHERENCE` 18/18

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

# Phase 4 — COMPLETE

Goal achieved: resource-heavy decisions now have explicit semantic coverage for transaction checkpoints, sunk-cost boundaries, target legality, deterministic vs stochastic outcome ownership, current-run survival reserve, and cross-family parent normalization.

Validated audit order:

1. D8 unopened-booster transaction cost vs D9 opened-pack sunk-cost boundary — **Batch 1 GREEN**;
2. opened-pack target legality and unsupported stochastic effects failing closed — **Batch 2 GREEN**;
3. consumable inventory/slot pressure and BUY vs BUY_AND_USE authority — **Batch 3 GREEN**;
4. voucher purchase value vs permanent downside and current-run resource reserve — **Batch 4 GREEN**;
5. destructive/generative Spectral/Tarot choices only through explicit bounded outcome models — **Batch 5 GREEN**;
6. cross-family D14 arbitration after child resource semantics are trustworthy — **Batch 6 GREEN**.

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

Validated locally at **67/67**, `RESOURCE_COHERENCE` **15/15**.

- generative/stochastic effects require explicit bounded public-state outcome ownership;
- Judgement requires the authoritative observed eligible-Joker catalogue;
- large public Judgement pools use a deterministic bounded lower bound with omitted probability mass fixed at zero;
- no RNG seed, pseudoseed, selected future outcome, or future pool order is read;
- destructive Immolate remains below Skip when its current public-state expectation is unavailable.

## Batch 6 — GREEN

Commits:

- `84bd534c` — adds cross-family D14 resource semantics.
- `eeb7dc52` — wires Batch-6 semantics into the benchmark.
- `e79c941c` — corrects the synthetic Tarot fixture so named Hermit transaction authority does not intercept the D14 normalization case.
- `c1b0888d` — hardens canonical `ShopUtilityScale` so BUY_AND_USE structural build gain cannot become parent utility.

Validated locally at **70/70**, `RESOURCE_COHERENCE` **18/18**.

- a locally admitted child with negative normalized parent utility loses to `END_SHOP=0`;
- D4 structural/build-path admission units do not leak into D14 cross-family value;
- stronger literal immediate consumable value may beat a weaker booster and the reverse also holds;
- named deterministic Hermit transaction authority remains a separate correct pre-D14 mechanic and is not confused with generic D4 parent normalization.

Phase 4 is closed. Do not add Batch 7 absent fresh semantic evidence from Phase-5 live runs.

# Phase 5 — LIVE VALIDATION — ACTIVE

Primary gate source: `docs/balatro/BALATRO_LIVE_VALIDATION_GATE.md`.

The installed production stack has previously completed three-attempt Red/White sessions after the systemic SHOP runtime pass, but ordinary SHOP checkpoints still showed roughly 10–15 second latency and some ~28–30 second states. The identified post-decision diagnostics double-planner overhead was repaired in `cb57f48` / `a185ad7`.

## Phase-5 first objective

Run a fresh three-attempt Red Deck / White Stake production baseline on the current Phase-4-green stack and inspect:

1. whether every settled SHOP reaches a decision without a permanent stall;
2. SHOP checkpoint decision latency, especially repeated >10 s and any ~20–30 s outliers;
3. whether the action path is semantically sensible at each large spend, replacement, booster open, consumable immediate-use, voucher purchase, and reroll;
4. whether any failure is an authority/mechanics defect, a runtime-bound defect, or only a numerical preference issue;
5. no numerical tuning until semantic/runtime defects are separated from preference calibration.

If the baseline exposes a new semantic defect, add the smallest evidence-driven semantic case and fix the canonical owner. If it exposes only bad tradeoffs with correct mechanics/authority, record the evidence for Phase 6 rather than tuning ad hoc during Phase 5.

# EXACT NEXT ACTION

Run one fresh three-attempt production baseline locally:

```powershell
git pull
.\BalatroAgentToggle.bat --three

```

Then provide the resulting session/run identifier(s) and any visible stall/crash symptom. If the run completes normally, provide the session prefix or diagnostics output so the JSONL timing/action trace can be audited.

Do not run live games from ChatGPT.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — ACTIVE
7. Phase 6 — numerical tuning only after semantics/runtime are trustworthy

Future stake/deck progression remains blocked until Red/White competence passes.

# Closed / do not reopen without fresh evidence

- Phase-0 ownership migrations and installer retirements
- Phase-1 expansion beyond five validated batches
- Phase-2 expansion beyond four
- Phase-3 build-evidence expansion beyond validated authority semantics absent fresh evidence
- Phase-4 expansion beyond six validated batches absent fresh live semantic evidence
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
