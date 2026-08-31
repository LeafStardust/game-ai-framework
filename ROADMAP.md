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

# Current state — 2026-09-01

> **Phase 5 live validation is COMPLETE at 74/74 semantic green. Phase 6 numerical/action-quality tuning is ACTIVE. Corrected live result remains 0 wins across the original baseline and Tunes A/B/C/D/E. Tune A remains retained provisionally. Tunes B, C, D, and E are REJECTED and reverted. Tune E's reverted configuration must now be locally revalidated before any Tune F live work.**

Validated checkpoints:

- Phase 0 authority consolidation: **COMPLETE / 24/24 semantic green**
- Full deterministic Balatro suite: **GREEN**
- Phase 1 D1 survival expansion: **COMPLETE / 33/33 green**
- Phase 2 simple shop survival: **COMPLETE / 42/42 green**
- Phase 3 coherent build evidence: **COMPLETE / 52/52 green**, `BUILD_COHERENCE` 12/12
- Phase 4 resource semantics: **COMPLETE / 70/70**, `RESOURCE_COHERENCE` 18/18
- Phase 5 live D1/D2 semantics: **COMPLETE / 74/74**, `D1_SURVIVAL` 25/25, `SHOP_SURVIVAL` 19/19
- Phase 6 Tune A first-Joker cash runway: **SEMANTIC GREEN / 74/74; RETAINED / 0 OF 10 WINS after corrected terminal bookkeeping**
- Phase 6 Tune B early paid-reroll runway: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune C ordinary Joker replacement margin: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune D booster acquisition margin: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune E contextual/B3 Joker build weight: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT VALIDATION PENDING**
- Phase 6 supervisor telemetry resilience: **LOCAL REGRESSION GREEN** after `d22f1b0a` + `cac8fd95`
- Phase 6 sticky-win GAME_OVER restart semantics: **LOCAL REGRESSION GREEN** (`28cec27b` + `6e1a2696`)

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

Final result: **52/52 GREEN**, `BUILD_COHERENCE` 12/12.

# Phase 4 — COMPLETE

Validated six resource-heavy semantic batches covering D8/D9 boundaries, pack legality, consumable slot/mode authority, voucher downside/reserve, bounded destructive/generative outcomes, and D14 cross-family normalization.

Final result: **70/70**, `RESOURCE_COHERENCE` 18/18.

Important commits:

- `84bd534c` — cross-family D14 resource semantics
- `eeb7dc52` — benchmark wiring
- `e79c941c` — synthetic Tarot fixture correction
- `c1b0888d` — prevent BUY_AND_USE structural build gain leaking into parent utility

# Phase 5 — LIVE VALIDATION — COMPLETE

Primary gate source: `docs/balatro/BALATRO_LIVE_VALIDATION_GATE.md`.

Historical runtime blockers and D1/D2 semantic findings remain closed at **74/74 semantic green**. Reopen Phase 5 only for fresh reproducible mechanics, legality, ownership, projection, hidden-information, or runtime evidence.

Key corrections:

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
- repeated medium/late losses retained large cash balances while still failing scoring requirements;
- representative evidence includes a four-Joker Ante-4 loss with about **$56**, plus prior five-Joker losses with roughly **$70–$82**.

## Tune A — first-Joker cash runway — RETAINED PROVISIONALLY

Commit: `1621b9ce`.

Change: in Ante 1–2, a first-Joker purchase must leave at least **$2**, for both ordinary D2 BUY and the first-scoring-foothold bootstrap.

Semantic result: **74/74 GREEN**.
Corrected live result: **0/10 wins**. The previously reported Crimson Heart win was actually a GAME_OVER loss at `68218 / 100000` with a sticky public `won=true` bit.

Tune A remains provisionally retained because it removed the specifically observed `$0/$1` first-Joker bankroll commitment while staying semantically clean. It has not demonstrated a win-rate improvement.

## Tune B — early paid-reroll runway — REJECTED / REVERTED

Experiment: `32457e2e` changed pre-Ante-6 D11 cash-after-reroll floor **$10 → $8**.
Live result: **0/10**.
Revert: `1ed61d29` restored `$10`; revert locally validated **74/74 GREEN**.

Do not reopen the `$8` D11 experiment absent new controlled evidence.

## Tune C — ordinary Joker replacement margin — REJECTED / REVERTED

Experiment: `47a212d0` changed ordinary D2 replacement advantage **0.75 → 0.50** while aligned replacements stayed `0.25`.
Semantic result: **74/74 GREEN**.
Live result: **0/10**.
Revert: `6261165b` restored **0.75**; revert locally validated **74/74 GREEN**.

Do not reopen the `0.50` replacement experiment absent new controlled evidence.

## Tune D — D8 booster acquisition margin — REJECTED / REVERTED

Canonical owner: D8 `BuildAwareShopBoosterPolicy`, configured by the Red/White playbook.

Experiment commit: `65cdaa23`.
Revert commit: `6bd95bcc`.

Experiment:

- `booster_acquisition.minimum_buy_advantage`: **0.35 → 0.20**;
- `minimum_pack_hit_probability` remained **0.45**;
- family-specific public useful-offer priors remained unchanged;
- money, interest, and reserve costs remained unchanged;
- D9 opened-pack visible choice semantics remained unchanged;
- no unopened pack identities were predicted;
- D2, D11, D14, and Tune A remained unchanged.

Semantic result before live sampling: **74/74 GREEN**.

### Tune-D live comparison

Session: `balatro-20260831T162752Z-a61dfb38`.

Result: **0/10 wins**. All ten attempts ended with authoritative `LOSS` / `game over (lost)`, and the supervisor exited normally at the requested ten-attempt limit.

Action counts by attempt were: **86, 95, 21, 113, 68, 116, 98, 148, 97, 70**. The sample therefore included both short and deep runs rather than failing at one uniform stage.

The uploaded JSONL attempt files were explicitly supplied, but the active Python/container sandbox did not expose the provided mounted paths when read directly, and file search indexed only the session summary rather than the JSONL trace content. Therefore no exact booster-purchase count, pack-choice sequence, or per-attempt cash/Joker claim is made from this batch.

Interpretation:

- Tune D did not improve the primary metric versus baseline or Tunes A/B/C: all remain **0/10**;
- without retrievable trace evidence showing a compensating improvement, the more permissive D8 margin does not justify retention;
- `6bd95bcc` restores `minimum_buy_advantage=0.35` while leaving Tune A intact;
- user locally revalidated the reverted configuration **74/74 GREEN**;
- do not stack Tune E on top of the rejected D8 experiment.

## Tune E — rebalance realized scoring vs contextual Joker value — REJECTED / REVERTED

Canonical owner: `JokerBuildValueEvaluator` / `JokerBuildValueWeights`, upstream of D2 admission and D14 shared-resource normalization.

Experiment commits: `e17518fc` + constructor-repair `ba93321f`.
Revert commit: `d5c3f8ce` restores the pre-Tune-E `contextual_gain=1.0` file state while preserving later branch history.

Experiment:

- `JokerBuildValueWeights.contextual_gain`: **1.0 → 0.75**;
- literal whole-build `direct_scoring_gain` weight remained **6.0**;
- literal direct-scoring cap remained **12.0**;
- D2 purchase/replacement thresholds remained unchanged;
- Tune A's Ante-1/2 first-Joker `$2` runway remained unchanged;
- D14 money, interest, reserve, slot, and cross-family normalization remained unchanged;
- no boss/Joker-specific rule and no hidden-state inference was introduced.

Semantic result before live sampling: **74/74 GREEN**.

### Tune-E live comparison

Session: `balatro-20260831T183301Z-3d72a54d`.

Result: **0/10 wins**. Death antes: **1, 4, 4, 3, 4, 5, 2, 2, 4, 3**. Furthest run reached only **Ante 5**; mean death ante was **3.2**.

Death score ratios were approximately **82.3%, 36.9%, 54.4%, 69.6%, 92.0%, 69.8%, 48.6%, 84.3%, 96.3%, 92.8%**.

Five attempts died with full five-Joker boards while retaining substantial cash:

- attempt 2: **$34**, `Misprint / Devious Joker / Crazy Joker / Abstract Joker / Square Joker`, `7376 / 20000` at Ante 4 Wall;
- attempt 3: **$37**, `Juggler / Abstract Joker / Swashbuckler / Lusty Joker / Card Sharp`, `5437 / 10000` at Ante 4 Hook;
- attempt 5: **$36**, `Crafty Joker / Mad Joker / Wrathful Joker / Blue Joker / Smiley Face`, `9202 / 10000` at Ante 4 Water;
- attempt 6: **$66**, `Jolly Joker / Sly Joker / Scholar / Blue Joker / Blackboard`, `11520 / 16500` at Ante 5 Big Blind;
- attempt 9: **$43**, `Odd Todd / Gluttonous Joker / Ice Cream / Baron / Driver's License`, `9632 / 10000` at Ante 4 Club.

The uploaded JSONL traces were directly readable in this Tune-E batch. Purchase evidence confirms active Joker acquisition rather than a generic refusal-to-spend failure: examples include full-board sequences in attempts 2, 5, 6, and 9, plus replacement/sale activity in attempts 2 and 9. Attempt 3's supplied summary independently records 14 purchases, 2 sales, five Jokers, and `$37` at death.

Interpretation:

- Tune E did not improve win rate: **0/10**, same as baseline and Tunes A/B/C/D;
- it also did not improve depth: furthest **Ante 5**, worse than the original baseline's Ante 7;
- the intended tradeoff did not solve the known large-cash/underpowered-board failure mode;
- several full boards were composed of individually scoring but weakly unified conditional effects, consistent with contextual/B3 downweighting reducing build coherence without enough compensating realized score;
- Tune E is therefore rejected and reverted rather than stacked into Tune F.

Do not reopen `contextual_gain=0.75` absent new controlled evidence.

## Runtime — sticky public `won` GAME_OVER restart — VALIDATED

Balatro's public `won` bit can remain sticky after a later Ante-8 GAME_OVER loss.

- `28cec27b` — complete `GAME_OVER` is authoritative loss evidence for restart; stale `won=true` no longer vetoes it.
- `6e1a2696` — focused regression.
- local validation: **GREEN**.

# EXACT NEXT ACTION

Validate the Tune-E revert semantically before any Tune-F work:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

Expected: **74/74 GREEN**. If green, record the restored post-Tune-E baseline and select Tune F only from a distinct evidence-backed mechanism. Do not reopen the rejected D11, D2 replacement-margin, D8 booster-margin, or contextual-weight experiments without new controlled evidence.

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
- Tune-C `0.50` ordinary Joker replacement margin absent new controlled evidence
- Tune-D `0.20` D8 booster acquisition margin absent new controlled evidence
- Tune-E `0.75` contextual/B3 Joker build weight absent new controlled evidence
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
