# ROADMAP — SINGLE SOURCE OF TRUTH

This is the only authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every command block shown must end with a trailing blank line after the final command.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Do not numerically tune during Phase 5; numerical weighting remains Phase 6 work.

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
- D4 consumable acquisition: `ConsumableAcquisitionPolicy`
- D3 voucher acquisition: `VoucherAcquisitionPolicy`

Bond/composition and Build Health are evidence/planning layers, never immediate score/action authorities.

# Current state — 2026-08-31

> **Phase 4 COMPLETE. Phase 5 live validation is ACTIVE. 73/73 is the last locally validated semantic checkpoint. A new final-hand discard-chain search-scope correction is implemented for validation at expected 74/74.**

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
- Phase 5 live D1 made-hand discard-recovery semantic: **GREEN / 71/71**, `D1_SURVIVAL` 23/23
- Phase 5 D1 timeout final-arbiter semantic: **GREEN / 72/72**, `D1_SURVIVAL` 24/24
- Phase 5 D2 first-Joker scoring-foothold semantic: **GREEN / 73/73**, `SHOP_SURVIVAL` 19/19
- Phase 5 D1 final-hand discard-chain search semantic: **IMPLEMENTED / VALIDATION PENDING**, expected **74/74**, `D1_SURVIVAL` +1

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc`.

# Phase 1 — CLOSED

Intentionally capped at five batches. Do not add another Phase-1 batch absent fresh Phase-5 evidence.

# Phase 2 — CLOSED

Intentionally capped at four batches. Do not add another Phase-2 batch absent fresh Phase-5 evidence.

# Phase 3 — CLOSED

Validated coherent build-evidence semantics:

1. scoring engine vs support/economy role separation;
2. scaling potential vs realized scoring power;
3. contextual pair interaction vs standalone intrinsic value;
4. Bond/composition evidence vs literal score arithmetic;
5. replacement/pivot authority downstream of legal and economically positive D2 options.

Final Phase-3 result: **52/52 GREEN**, `BUILD_COHERENCE` 12/12.

# Phase 4 — COMPLETE

Validated six resource-heavy semantic batches:

1. D8 unopened-booster transaction cost vs D9 opened-pack sunk-cost boundary — **55/55**;
2. opened-pack target legality and unsupported stochastic effects failing closed — **58/58**;
3. consumable inventory/slot pressure and BUY vs BUY_AND_USE authority — **61/61**;
4. voucher purchase value vs permanent downside/current-run reserve — **64/64**;
5. destructive/generative Spectral/Tarot choices through explicit bounded outcome models — **67/67**;
6. cross-family D14 arbitration after child resource semantics — **70/70**.

Important Batch-6 commits:

- `84bd534c` — cross-family D14 resource semantics
- `eeb7dc52` — benchmark wiring
- `e79c941c` — synthetic Tarot fixture correction
- `c1b0888d` — prevent BUY_AND_USE structural build gain leaking into parent utility

Phase 4 is closed. Do not add Batch 7 absent fresh Phase-5 live semantic evidence.

# Phase 5 — LIVE VALIDATION — ACTIVE

Primary gate source: `docs/balatro/BALATRO_LIVE_VALIDATION_GATE.md`.

## Runtime stabilization already completed

Historical Phase-5 runtime blockers included stale pack-choice pointers, stale pack plans becoming fatal instead of replanning, and post-decision diagnostics rerunning expensive SHOP planning. Relevant repairs include:

- `ec289256` — ignore volatile pack pointers in stale-plan signature
- `bac63e23` — bounded replan when visible pack choices change before submit
- `cb57f48` / `a185ad7` — remove post-decision diagnostics double-planner overhead

Fresh production sessions complete normally after these repairs.

## Baseline A — systemic discard hoarding

Session: `balatro-20260831T083950Z-38168e59`.

1. Ante 6 boss The Arm — `23355 / 40000`, 0/4 discards used
2. Ante 4 Big Blind — `1575 / 7500`, 0/4 discards used
3. Ante 5 boss The Mark — `14466 / 22000`, 0/4 discards used

Fresh evidence: all three losses exhausted every scoring hand while leaving all four discard resources untouched.

### D1 finding 1 — under-pace made-hand discard suppression — GREEN

Canonical owner: `LiveHandDecisionEvaluator._discard_value`.

- `cb2058cc` — semantic `d1.live.underpace_made_hand_keeps_discard_recovery`
- `820e096d` — made-hand preservation applies only when the play actually meets current survival pace
- `4ecf9bc5` — benchmark wiring

Validated locally **71/71**, `D1_SURVIVAL` 23/23. No numeric tuning.

## Baseline B — timeout still bypassed final arbiter

Session: `balatro-20260831T091211Z-8eae7b51`.

1. Ante 4 boss The Mark — `7353 / 10000`, 0/4 discards used
2. Ante 1 Big Blind — `74 / 450`, 0/5 discards used (Drunkard)
3. Ante 2 Big Blind — `939 / 1200`, 1/4 discard used

### D1 finding 2 — timeout planner ranking bypasses final arbiter — GREEN

Canonical owner: `PathAwareLiveHandActionDecisionEngine._structural_timeout_fallback`.

The timeout path reused `plans[0]` directly, turning planner ordering into a second final controller. Stopping search is legal; bypassing the canonical Play-vs-Discard arbiter is not.

- `dcdbefe4` — semantic `d1.live.timeout_preserves_final_arbiter`
- `d7ec97f3` — retained completed plan sets with authoritative public hand state flow back through `LiveHandActionPolicy`

Validated locally **72/72**, `D1_SURVIVAL` 24/24.

## Baseline C — discard-hoarding resolved; early scoring foothold defect exposed

Session: `balatro-20260831T093436Z-9a84e993`.

1. Ante 2 Small Blind — `544 / 800`, 4/4 discards used; only Joker at death Midas Mask
2. Ante 7 Big Blind — `47112 / 52500`, 5/5 discards used
3. Ante 3 boss The Needle — `300 / 2000`, 4/4 discards used

The global discard-hoarding failure was resolved in this pass: every loss spent all available discards.

### D2 finding — first-Joker bootstrap conflated structural value with scoring foothold — GREEN

Canonical owner: `JokerAcquisitionPolicy`.

The Ante-1/2 special first-Joker relaxation was intended to establish immediate scoring power but admitted any positive whole-build gain, allowing support/economy value to inherit scoring-emergency authority.

- `0f1fd70f` — bootstrap requires positive canonical `direct_scoring_gain`
- `b9a015e1` — repairs one accidental syntax typo introduced in that edit
- `9470907a` — semantic `d2.live.first_joker_bootstrap_requires_scoring_foothold`
- `6e9c563a` — completes the synthetic transition-planner fixture contract used by installed post-transaction D2 policy

Validated locally **73/73**, `SHOP_SURVIVAL` 19/19. Support/economy Jokers remain legal through normal D2 economics; they simply cannot use the scoring-foothold exception without current literal scoring power.

## Baseline D — current 73/73 stack

Session: `balatro-20260831T102028Z-6cf4214a`.

All three attempts completed normally; result **0/3 wins**.

1. attempt 1 — loss, Ante 2 boss **The Needle**, `550 / 800`, `hands_left=0`, `discards_left=4`, `discards_used=0`; owned Jokers at death: Even Steven, Misprint, Card Sharp
2. attempt 2 — loss, Ante 5 boss **The Psychic**, `17750 / 22000`, `hands_left=0`, `discards_left=0`, `discards_used=4`; five-Joker board, $70
3. attempt 3 — loss, Ante 4 boss **The Wheel**, `8270 / 10000`, `hands_left=0`, `discards_left=0`, `discards_used=4`; five-Joker board, $82

Interpretation:

- the previous **global** discard-hoarding defect remains resolved in attempts 2 and 3;
- attempt 1 is a distinct final-hand resource-geometry failure: The Needle provides one scoring hand, yet D1 spent that sole Play and died while all four discards remained available;
- this is not evidence to reopen the old made-hand/timeout fixes globally.

### D1 finding 3 — final-hand safe schedule cannot represent multiple discards before sole Play — VALIDATION PENDING

Canonical owner: `_safe_search_schedule` used by `PathAwareLiveHandActionDecisionEngine._search_schedule`.

Source inspection after Baseline D:

- production Red/White D1 currently uses `safe_pace_optimization_policy._safe_search_schedule`;
- before this correction, whenever more than one action remained, that helper returned exactly one **horizon-2** advisory pass;
- with `hands_remaining=1` and `discards_remaining=4`, a horizon-2 planner can model at most `Discard -> Play`;
- it cannot compare the legal lines `Discard -> Discard -> ... -> Play`, even though discards do not consume the sole remaining scoring hand;
- the generic adaptive planner already owns a global bounded maximum horizon of five, exactly enough for four discards plus one Play.

Correction:

- `cf17eac1` — ordinary multi-hand D1 stays horizon 2, but when exactly one scoring hand remains with spare discards, the safe schedule expands only enough to represent the remaining discard chain plus final Play, capped by the existing `LIVE_ADAPTIVE_MAX_HORIZON=5`, caller `max_horizon`, and existing 750-node safe-pass cap;
- no score weights, probability floors, pace thresholds, or hidden-state assumptions changed;
- `9d5fda58` — adds semantic `d1.live.final_hand_search_spends_remaining_discards`;
- `446f426c` — wires that semantic into the Red/White benchmark.

Expected checkpoint after local validation:

- **74/74** overall
- `D1_SURVIVAL` **25/25**
- `SHOP_SURVIVAL` **19/19**
- `BUILD_COHERENCE` **12/12**
- `RESOURCE_COHERENCE` **18/18**

# EXACT NEXT ACTION

Validate the new final-hand D1 search-scope semantic:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

If green, update this roadmap to 74/74 and run another fresh three-attempt Phase-5 baseline. Compare specifically:

- whether last-hand states with spare discards now spend them when useful;
- whether attempts 2/3-style normal discard behavior stays intact;
- boss survival depth and build/shop quality;
- runtime latency, especially whether the narrow one-hand horizon expansion stays bounded.

Do not numerically tune yet.

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
- Phase-1 expansion beyond validated batches absent fresh Phase-5 evidence
- Phase-2 expansion beyond validated batches absent fresh Phase-5 evidence
- Phase-3 build-evidence expansion absent fresh Phase-5 evidence
- Phase-4 expansion beyond six validated batches absent fresh Phase-5 evidence
- global D1 discard-hoarding defect after Baseline C, unless fresh multi-run evidence reopens it
- Mouth discard-only legality defect
- Green Joker survival-equivalent authority
- Hook/log-resilience search reserve
- historical SHOP recursive expectation roots
- BLIND_SELECT quiescence deadlock
- ROUND_EVAL checkout fast path
- D1 root pre-beam wall-clock defect
- failed-trial tuner cascading
- Phase-A Bond exploratory tuning
- D14/D11 latency blocker absent fresh timing evidence
