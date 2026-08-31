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
- Numerical tuning is Phase 6 work and must not mutate the validated semantic ownership model.

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

> **Phase 5 live validation is COMPLETE at 74/74 semantic green. Phase 6 numerical/action-quality tuning is ACTIVE. Tune A completed at 1/10 wins versus the 0/10 baseline. Tune B lowers only the pre-Ante-6 paid-reroll reserve from $10 to $8 and is awaiting semantic validation.**

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
- Phase 5 D1 final-hand discard-chain search semantic: **GREEN / 74/74**, `D1_SURVIVAL` 25/25
- Phase 6 Tune A first-Joker cash runway: **SEMANTIC GREEN / 74/74**, all category scores unchanged
- Phase 6 supervisor telemetry resilience: **LOCAL REGRESSION GREEN** after `d22f1b0a` + `cac8fd95`

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

# Phase 5 — LIVE VALIDATION — COMPLETE

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

## Baseline D — 73/73 stack

Session: `balatro-20260831T102028Z-6cf4214a`.

All three attempts completed normally; result **0/3 wins**.

1. attempt 1 — loss, Ante 2 boss **The Needle**, `550 / 800`, `hands_left=0`, `discards_left=4`, `discards_used=0`; owned Jokers at death: Even Steven, Misprint, Card Sharp
2. attempt 2 — loss, Ante 5 boss **The Psychic**, `17750 / 22000`, `hands_left=0`, `discards_left=0`, `discards_used=4`; five-Joker board, $70
3. attempt 3 — loss, Ante 4 boss **The Wheel**, `8270 / 10000`, `hands_left=0`, `discards_left=0`, `discards_used=4`; five-Joker board, $82

Interpretation:

- the previous **global** discard-hoarding defect remains resolved in attempts 2 and 3;
- attempt 1 is a distinct final-hand resource-geometry failure: The Needle provides one scoring hand, yet D1 spent that sole Play and died while all four discards remained available;
- this is not evidence to reopen the old made-hand/timeout fixes globally.

### D1 finding 3 — final-hand safe schedule cannot represent multiple discards before sole Play — GREEN

Canonical owner: `_safe_search_schedule` used by `PathAwareLiveHandActionDecisionEngine._search_schedule`.

Source inspection after Baseline D:

- production Red/White D1 uses `safe_pace_optimization_policy._safe_search_schedule`;
- before correction, whenever more than one action remained, that helper returned exactly one **horizon-2** advisory pass;
- with `hands_remaining=1` and `discards_remaining=4`, horizon 2 could model at most `Discard -> Play`;
- it could not compare legal lines `Discard -> Discard -> ... -> Play`, even though discards do not consume the sole scoring hand;
- the generic adaptive planner already owns a global bounded maximum horizon of five, exactly enough for four discards plus one Play.

Correction:

- `cf17eac1` — ordinary multi-hand D1 stays horizon 2, but when exactly one scoring hand remains with spare discards, the safe schedule expands only enough to represent the remaining discard chain plus final Play, capped by existing `LIVE_ADAPTIVE_MAX_HORIZON=5`, caller `max_horizon`, and the existing 750-node safe-pass cap;
- no score weights, probability floors, pace thresholds, or hidden-state assumptions changed;
- `9d5fda58` — semantic `d1.live.final_hand_search_spends_remaining_discards`;
- `446f426c` — benchmark wiring.

Validated locally **74/74**, `D1_SURVIVAL` **25/25**. This remains a bounded mechanical search-scope correction, not numerical tuning.

## Baseline E — 74/74 exit evidence

Two fresh unchanged 74/74 three-attempt sessions were reviewed after the final D1 correction. Neither exposed a reproducible new mechanics, legality, ownership, hidden-information, or runtime defect.

Session `balatro-20260831T104543Z-4b891757` — **0/3**:

1. Ante 2 Small Blind — `780 / 800`, 2/4 discards used; Odd Todd + Blackboard
2. Ante 2 boss The Wall — `2778 / 3200`, 0/4 discards used; Odd Todd + Green Joker
3. Ante 1 Big Blind — `376 / 450`, 4/4 discards used; no Jokers

Source audit confirmed Green Joker's discard mutation is already projected literally and Blackboard evaluates the actual held cards after play selection. The Wall's unused discards therefore do not establish a semantic defect by themselves; Green Joker makes discarding an actual scoring tradeoff.

Session `balatro-20260831T105634Z-5453d63e` — **0/3**:

1. Ante 6 boss **The Mouth** — `11260 / 40000`, 4/4 discards used; five-Joker board: Fibonacci, Photograph, Splash, Scary Face, Flower Pot
2. Ante 2 Small Blind — `736 / 800`, 4/4 discards used; only Joker Card Sharp
3. Ante 5 boss **The Hook** — `10776 / 22000`, 0/4 discards used; five-Joker board: Foil Abstract Joker, Ride the Bus, Burnt Joker, Fibonacci, Blackboard

Interpretation:

- the corrected stack demonstrably survives deep enough to reach Ante 6 and Ante 5 under normal production play;
- ordinary discard recovery remains active in attempts 1 and 2;
- the Hook attempt's unused discards are not enough to reopen global discard-hoarding without trace evidence of a mechanics/authority violation, especially with a build whose scoring value is materially state-dependent;
- no crashes, stale-plan supervisor failures, or new hidden-information boundary violations were observed;
- after six consecutive unchanged 74/74 attempts across the two exit sessions, remaining failures are best classified as **action-quality / build-strength / numerical preference** problems rather than unvalidated semantic authority defects.

Phase 5 is therefore closed at **74/74 semantic green**. Reopen it only for fresh reproducible evidence of a mechanics, legality, ownership, projection, hidden-information, or runtime defect.

# Phase 6 — NUMERICAL / ACTION-QUALITY TUNING — ACTIVE

Goal: improve actual Red/White win rate without changing the validated semantic ownership model.

Allowed work now includes measured tuning of existing policy thresholds/weights and action-quality preferences, provided every change remains inside the canonical owner for that decision family and preserves literal mechanics/projection contracts.

## Phase-6 baseline — 10 unchanged attempts

Session: `balatro-20260831T112338Z-d58df919`.

Result: **0/10 wins**.

Death antes: **4, 3, 5, 3, 4, 1, 1, 1, 6, 7**.

Important evidence:

- three attempts died in Ante 1;
- two attempts reached Ante 6 or later, proving the validated stack can still produce deep runs;
- attempt 9 reached Ante 6 and died at roughly 95% of the 40,000-chip boss requirement;
- attempt 10 reached Ante 7;
- discard recovery was broadly active; most losing blinds consumed all available discards;
- two of the three Ante-1 deaths ended with Baron as the only Joker and essentially no remaining cash ($0 and $1 respectively), while the third Ante-1 death had no Joker;
- this does not justify a Baron-specific rule: Baron is contextual and the observed issue is the amount of early bankroll committed to the first scoring foothold.

The first tuning target is therefore **early first-Joker cash runway**, not Joker identity and not semantic ownership.

## Phase-6 Tune A — first-Joker cash runway — COMPLETE / 1 OF 10 WINS

Canonical owner: `JokerAcquisitionPolicy`.

Commit: `1621b9ce`.

Change:

- in Ante 1–2, when the build has no Joker yet, any first-Joker purchase must leave at least **$2**;
- this applies whether the candidate would otherwise BUY through ordinary D2 advantage or through the special first-scoring-foothold bootstrap;
- once a Joker is owned, ordinary D2 economics are unchanged;
- Ante 3+ purchasing is unchanged;
- the scoring-foothold semantic requirement remains unchanged;
- no Joker names, boss names, hidden state, duplicate scorers, or rescue wrappers were introduced.

Validation:

- user locally validated the full Red/White semantic benchmark **74/74 GREEN** after Tune A;
- all category scores remain unchanged.

### Tune-A live comparison result

The first Tune-A session `balatro-20260831T123756Z-62a20e03` was interrupted after attempt 7 by the monitor-only telemetry Windows file-lock race. Those seven gameplay attempts remain valid. The key bookkeeping correction is that **attempt 7 was a real win**: it cleared Ante 8 / Crimson Heart with `won=true`; the supervisor then failed while publishing telemetry. The telemetry resilience repair (`d22f1b0a` + `cac8fd95`) was subsequently validated locally GREEN.

The final three Tune-A attempts came from session `balatro-20260831T132736Z-d53e9777` and all lost:

1. Ante 4 boss **The Pillar** — `7446 / 10000`, five Jokers (Raised Fist, Misprint, Photograph, Hiker, Flower Pot), $71, 0/4 manual discards used;
2. Ante 1 boss **The Hook** — `396 / 600`, no Jokers, $8, 0/4 manual discards used; The Hook itself forcibly discards after played hands, so the manual-discard counter alone is not evidence to reopen the old global D1 defect;
3. Ante 2 Big Blind — `980 / 1200`, no Jokers, $11, 4/4 discards used; the run summary records two purchases, but the exact purchase identities are not available from the retrievable trace evidence and must not be guessed.

Combined Tune-A result versus baseline:

- win rate: **0/10 → 1/10**;
- furthest result: baseline Ante 7 loss → Tune A **Ante 8 win**;
- Ante-1 deaths: **3/10 → 3/10**, so Tune A did not reduce the raw early-death count;
- the early-failure shape changed: one Tune-A Ante-1 death occurred before the first shop, while other early losses can still reach a shop/boss with no scoring Joker established;
- Tune A is therefore retained rather than reverted: it produced the first observed Red/White win and removed the specific $0/$1 first-Joker commitment behavior without a semantic regression.

The next target is not a lower ordinary D2 buy threshold. A cash-safe Ante-1/2 first Joker with positive literal `direct_scoring_gain` already uses the validated first-engine bootstrap even when it misses the ordinary `0.35` purchase-advantage threshold. The remaining no-Joker deaths instead justify testing whether early D11 paid-reroll runway is too conservative when visible shop offers fail to establish scoring.

## Phase-6 Tune B — early paid-reroll runway — SEMANTIC VALIDATION PENDING

Canonical owner: D11 `BuildAwareShopRerollPolicy`, configured by the Red/White playbook.

Commit: `32457e2e`.

Change:

- Red/White `minimum_money_after_paid_reroll`: **$10 → $8** before Ante 6;
- `minimum_margin=0.25` is unchanged, so a reroll must still beat the already-normalized best visible-shop option by the existing EV margin;
- `maximum_paid_reroll_cost=$8` is unchanged;
- Ante 6+ reserve remains **$20**;
- Tune A's first-Joker post-purchase floor remains **$2**;
- no hidden future identities or RNG are used: D11 still values rerolls only through its public/static future-shop offer prior and canonical public pool model.

Why $8:

- it is the smallest two-dollar relaxation from the existing $10 stop-loss floor;
- a normal $5 reroll still requires at least $13 cash and leaves $8, preserving meaningful runway for a subsequent scoring purchase;
- it can expose additional shop search opportunities for underbuilt early runs without making paid rerolls unconditional or weakening late-run reserves;
- the Tune-A summaries provide evidence of early no-Joker failures, but do **not** expose exact reroll decisions at those shop checkpoints; Tune B is therefore explicitly an A/B numerical hypothesis, not a claimed reconstruction of those decisions.

Do not stack another numerical tune until Tune B is semantically green and its live sample is reviewed.

# EXACT NEXT ACTION

Validate Tune B against the unchanged 74 semantic contracts before running another live sample:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

Expected semantic result: **74/74 GREEN**, with all category counts unchanged. If green, run a fresh 10-attempt Tune-B comparison with Tune A retained and no other changes.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — COMPLETE
7. Phase 6 — numerical/action-quality tuning — ACTIVE

Future stake/deck progression remains blocked until Red/White competence passes.

# Closed / do not reopen without fresh evidence

- Phase-0 ownership migrations and installer retirements
- Phase-1 expansion beyond validated batches absent fresh Phase-5 evidence
- Phase-2 expansion beyond validated batches absent fresh Phase-5 evidence
- Phase-3 build-evidence expansion absent fresh Phase-5 evidence
- Phase-4 expansion beyond six validated batches absent fresh Phase-5 evidence
- Phase-5 semantic expansion absent fresh reproducible mechanics/authority/runtime evidence
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