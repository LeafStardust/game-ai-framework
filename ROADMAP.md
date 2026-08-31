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

> **Phase 5 live validation is COMPLETE at 74/74 semantic green. Phase 6 numerical/action-quality tuning is ACTIVE. Tune A is RETAINED at 1/10 wins versus the 0/10 baseline. Tune B was REJECTED at 0/10 and its revert to the Tune-A `$10` D11 runway is locally validated 74/74 GREEN. Tune C is ACTIVE and SEMANTIC GREEN at 74/74: ordinary D2 Joker replacement advantage is 0.50 while aligned replacements remain 0.25. The next gate is a fresh 10-attempt Tune-C live comparison with no further changes.**

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
- Phase 6 Tune A first-Joker cash runway: **SEMANTIC GREEN / 74/74; RETAINED / 1 OF 10 WINS**
- Phase 6 Tune B early paid-reroll runway: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune C ordinary Joker replacement margin: **SEMANTIC GREEN / 74/74; LIVE COMPARISON PENDING**
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

Historical Phase-5 runtime blockers and D1/D2 semantic findings remain closed at **74/74 semantic green**. Reopen Phase 5 only for fresh reproducible mechanics, legality, ownership, projection, hidden-information, or runtime evidence.

Key validated Phase-5 corrections:

- `820e096d` — under-pace made-hand discard recovery
- `d7ec97f3` — timeout retains canonical final arbiter
- `0f1fd70f` — early first-Joker bootstrap requires literal scoring foothold
- `cf17eac1` — final-hand D1 can search the remaining discard chain before the sole Play

# Phase 6 — NUMERICAL / ACTION-QUALITY TUNING — ACTIVE

Goal: improve actual Red/White win rate without changing the validated semantic ownership model.

## Phase-6 baseline — 10 unchanged attempts

Session: `balatro-20260831T112338Z-d58df919`.

Result: **0/10 wins**. Death antes: **4, 3, 5, 3, 4, 1, 1, 1, 6, 7**.

Important evidence:

- three attempts died in Ante 1;
- two attempts reached Ante 6 or later;
- attempt 9 reached `38005 / 40000` at Ante 6;
- repeated later losses retained large cash balances while still failing scoring requirements;
- representative late/medium-run evidence includes a four-Joker Ante-4 loss with **$56**, plus prior five-Joker losses with roughly **$70–$82**.

## Phase-6 Tune A — first-Joker cash runway — COMPLETE / RETAINED / 1 OF 10 WINS

Canonical owner: `JokerAcquisitionPolicy`.

Commit: `1621b9ce`.

Change: in Ante 1–2, a first-Joker purchase must leave at least **$2**. This applies to ordinary D2 BUY and the first-scoring-foothold bootstrap. Once a Joker is owned and at Ante 3+, ordinary D2 economics are unchanged.

Validation: **74/74 GREEN**.

Live result: **1/10 wins**, including an Ante-8 Crimson Heart win. Tune A remains retained.

## Phase-6 Tune B — early paid-reroll runway — REJECTED / REVERTED

Experiment commit: `32457e2e`.
Revert commit: `1ed61d29`.

Experiment: Red/White pre-Ante-6 `minimum_money_after_paid_reroll` **$10 → $8**.

Semantic result: **74/74 GREEN**.
Live result: session `balatro-20260831T135424Z-655cd5c9` finished **0/10 wins**.

Interpretation:

- Tune B did not improve the primary metric versus retained Tune A (**1/10 → 0/10**);
- the `$8` D11 runway was therefore rejected and restored to `$10`;
- user locally revalidated the reverted Tune-A state **74/74 GREEN**;
- do not reopen the `$8` D11 experiment absent new controlled evidence.

## Phase-6 Tune C — ordinary Joker replacement margin — ACTIVE / SEMANTIC GREEN

Canonical owner: D2 `JokerAcquisitionPolicy`, configured by the Red/White playbook.

Commit: `47a212d0`.

Change:

- `minimum_replacement_advantage`: **0.75 → 0.50**;
- `aligned_minimum_replacement_advantage` remains **0.25**;
- `minimum_replacement_build_delta` remains **0.0**;
- first-Joker Tune A `$2` runway remains unchanged;
- ordinary new-slot purchase threshold remains **0.35**;
- D11 and D14 resource coefficients remain unchanged.

Why this target:

- across the Phase-6 baseline and preceding live validation, multiple medium/late losses reached full or near-full Joker boards while retaining large cash balances and still failed scoring requirements;
- this points more directly at **upgrade/replacement selectivity** than at reroll starvation;
- lowering only the ordinary replacement margin permits mechanically positive upgrades to replace weak incumbents more readily without making aligned replacements, first-Joker acquisition, boosters, consumables, or rerolls more permissive;
- 0.50 is a single conservative step between the prior ordinary 0.75 threshold and the existing aligned 0.25 threshold.

Validation:

- user locally validated the full Red/White semantic benchmark **74/74 GREEN** after Tune C;
- all semantic/category ownership contracts remain unchanged.

This remains an A/B numerical hypothesis. No Joker identity is hard-coded, and no hidden future information is used.

# EXACT NEXT ACTION

Run a fresh **10-attempt Tune-C live sample** with Tune A retained and no additional changes:

```powershell
git pull
.\BalatroAgentToggle.bat --attempts 10

```

Compare Tune C against both the original 0/10 baseline and retained Tune A 1/10 on:

- win rate and furthest ante;
- death score ratio;
- cash at death;
- Joker count/composition;
- full/near-full-board replacement frequency and replacement outcomes where trace evidence is retrievable;
- realized direct scoring power;
- discard/hands consumed at death;
- whether large-cash underpowered deaths decrease.

Do not stack Tune D until this 10-run Tune-C sample is reviewed.

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
- Tune-B `$8` pre-Ante-6 paid-reroll runway absent new controlled evidence
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