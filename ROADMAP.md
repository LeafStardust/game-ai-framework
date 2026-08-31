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

> **Phase 4 COMPLETE. Phase 5 live validation is ACTIVE. 72/72 is validated; the new D2 scoring-foothold semantic is implemented for validation at expected 73/73.**

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
- Phase 5 baseline runtime: **3/3 attempts completed without supervisor crash after pack stale-replan repairs**
- Phase 5 live D1 made-hand discard-recovery semantic: **GREEN / 71/71**, `D1_SURVIVAL` **23/23**
- Phase 5 D1 timeout final-arbiter semantic: **GREEN / 72/72**, `D1_SURVIVAL` **24/24**
- Phase 5 live D2 first-Joker scoring-foothold semantic: **IMPLEMENTED / VALIDATION PENDING**, expected **73/73**, `SHOP_SURVIVAL` +1

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

## Fresh production baseline — completed

Session: `balatro-20260831T083950Z-38168e59`.

The three-attempt baseline completed normally after the Phase-5 pack-race repairs (`ec289256` and `bac63e23`): the stale pack-choice guard no longer crashes the supervisor and stale pack plans are discarded/replanned rather than executed.

Results:

1. attempt 1 — loss, Ante 6 boss **The Arm**, `23355 / 40000`, `hands_left=0`, `discards_left=4`, `discards_used=0`;
2. attempt 2 — loss, Ante 4 **Big Blind**, `1575 / 7500`, `hands_left=0`, `discards_left=4`, `discards_used=0`;
3. attempt 3 — loss, Ante 5 boss **The Mark**, `14466 / 22000`, `hands_left=0`, `discards_left=4`, `discards_used=0`.

This was fresh semantic evidence: all three independent losing blinds exhausted every scoring hand while leaving the entire four-discard recovery resource untouched.

## Live D1 finding 1 — under-pace made-hand discard suppression — GREEN

Canonical owner: `LiveHandDecisionEvaluator._discard_value`.

Correction:

- `cb2058cc` adds `d1.live.underpace_made_hand_keeps_discard_recovery`;
- `820e096d` applies made-hand preservation only when the visible made hand meets current survival pace;
- `4ecf9bc5` wires the new Phase-5 semantic into the benchmark.

Validated locally at **71/71**, `D1_SURVIVAL` **23/23**. No threshold or weight changed.

## Post-correction live baseline — completed

Session: `balatro-20260831T091211Z-8eae7b51`.

Results:

1. attempt 1 — loss, Ante 4 boss **The Mark**, `7353 / 10000`, `hands_left=0`, `discards_left=4`, `discards_used=0`;
2. attempt 2 — loss, Ante 1 **Big Blind**, `74 / 450`, `hands_left=0`, `discards_left=5`, `discards_used=0` (Drunkard increased the available discard total to five);
3. attempt 3 — loss, Ante 2 **Big Blind**, `939 / 1200`, `hands_left=0`, `discards_left=3`, `discards_used=1`.

The first correction changed behavior in one run, but the systemic failure persisted: two independent losses still exhausted every scoring hand without spending any discard, including an extremely weak Ante-1 loss at only 74/450.

## Live D1 finding 2 — timeout planner ranking bypasses final arbiter — GREEN

Canonical owner: `PathAwareLiveHandActionDecisionEngine._structural_timeout_fallback`.

Observed authority defect:

- when the D1 wall-clock deadline expired after a canonical adaptive root completed, the timeout path used `plans[0]` directly as the action;
- that root ordering comes from the full-blind search objective, but it bypassed `LiveHandActionPolicy`'s final Play-vs-Discard pace/recovery arbitration;
- therefore timeout could turn a planner-ranked Play into the executed action even when the canonical recovery evaluator would prefer a discard;
- stopping additional search is valid; replacing the final arbiter is not.

Correction:

- `dcdbefe4` adds `d1.live.timeout_preserves_final_arbiter` from the second live baseline;
- `d7ec97f3` changes timeout behavior so a retained completed plan set with authoritative public hand state is passed through `LiveHandActionPolicy` before execution;
- no new search is performed and no hidden information is used;
- incomplete synthetic states without a visible hand retain raw-root fallback because literal immediate pace/recovery cannot be recomputed from missing public state.

Validated locally at **72/72**, `D1_SURVIVAL` **24/24**. This remains an authority correction, not numerical tuning.

## Post-timeout-correction live baseline — completed

Session: `balatro-20260831T093436Z-9a84e993`.

Results:

1. attempt 1 — loss, Ante 2 **Small Blind**, `544 / 800`, `hands_left=0`, `discards_left=0`, `discards_used=4`; only owned Joker at death was **Midas Mask**;
2. attempt 2 — loss, Ante 7 **Big Blind**, `47112 / 52500`, `hands_left=0`, `discards_left=0`, `discards_used=5`;
3. attempt 3 — loss, Ante 3 boss **The Needle**, `300 / 2000`, `hands_left=0`, `discards_left=0`, `discards_used=4`.

The previous discard-hoarding failure is resolved in this live pass: all three losing blinds spent every available discard. Phase-5 attention therefore moves away from D1 discard authority unless fresh evidence reopens it.

## Live D2 finding — first-Joker bootstrap conflates structural value with scoring foothold — validation pending

Canonical owner: `JokerAcquisitionPolicy`.

Fresh evidence:

- attempt 1 spent its full four-discard recovery resource and still died at `544 / 800` on Ante 2;
- its only Joker at death was Midas Mask, which provides deck-development/economy utility but is not a current literal scoring foothold;
- D2's special Ante-1/2 first-Joker relaxation was documented as a scoring-engine bootstrap but required only positive whole-build gain, so structural/economy value could inherit the scoring emergency exception.

Correction:

- `0f1fd70f` makes the early first-Joker bootstrap require positive `direct_scoring_gain` from the already-computed canonical `JokerBuildValue`;
- this field is derived from public literal whole-build score projection and therefore adds no second scorer, hidden information, or extra shop probe;
- support/economy Jokers remain eligible for ordinary D2 purchase when their normal build value and economics justify them; they simply cannot use the special first-scoring-foothold reserve relaxation without current scoring power;
- `9470907a` adds `d2.live.first_joker_bootstrap_requires_scoring_foothold`, holding positive structural build gain constant while verifying that only the candidate with current direct scoring gain receives the bootstrap.

This is an authority/semantic correction, not numerical tuning. Expected checkpoint: **73/73**, with `SHOP_SURVIVAL` increasing by one and all prior categories unchanged.

# EXACT NEXT ACTION

Validate the new D2 live semantic on the full Red/White benchmark:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

Expected: **73/73**, `D1_SURVIVAL` **24/24**, `SHOP_SURVIVAL` +1, all prior categories unchanged.

If green, continue Phase-5 live validation from the 73/73 stack. The discard-hoarding failure is considered resolved by the latest live pass; next live analysis should focus on build/shop quality, boss-specific survival, and runtime evidence before any Phase-6 numerical tuning.

Do not run tests or live games from ChatGPT.

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
