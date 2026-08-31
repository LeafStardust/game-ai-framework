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

> **Phase 5 live validation is COMPLETE at 74/74 semantic green. Phase 6 numerical/action-quality tuning is ACTIVE. Corrected primary live result remains 0 wins across the original baseline and Tunes A/B/C. Tune A remains retained provisionally because it removed the specific observed `$0/$1` first-Joker commitment while staying semantically clean. Tune B is REJECTED and reverted. Tune C is now also REJECTED at 0/10 and reverted in `6261165b`, restoring ordinary D2 Joker replacement advantage to 0.75. Sticky-`won` GAME_OVER restart semantics are fixed and locally validated GREEN. The exact next action is semantic revalidation of the Tune-C revert before selecting a distinct Tune D.**

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
- Phase 6 Tune C ordinary Joker replacement margin: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT PENDING LOCAL SEMANTIC VALIDATION**
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

Final Phase-3 result: **52/52 GREEN**, `BUILD_COHERENCE` 12/12.

# Phase 4 — COMPLETE

Validated six resource-heavy semantic batches:

1. D8 unopened-booster transaction cost vs D9 opened-pack sunk-cost boundary;
2. opened-pack target legality and unsupported stochastic effects failing closed;
3. consumable inventory/slot pressure and BUY vs BUY_AND_USE authority;
4. voucher purchase value vs permanent downside/current-run reserve;
5. destructive/generative Spectral/Tarot choices through explicit bounded outcome models;
6. cross-family D14 arbitration after child resource semantics.

Final result: **70/70**, `RESOURCE_COHERENCE` 18/18.

Important Batch-6 commits:

- `84bd534c` — cross-family D14 resource semantics
- `eeb7dc52` — benchmark wiring
- `e79c941c` — synthetic Tarot fixture correction
- `c1b0888d` — prevent BUY_AND_USE structural build gain leaking into parent utility

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

## Phase-6 Tune A — first-Joker cash runway — COMPLETE / RETAINED / CORRECTED 0 OF 10 WINS

Canonical owner: `JokerAcquisitionPolicy`.

Commit: `1621b9ce`.

Change: in Ante 1–2, a first-Joker purchase must leave at least **$2**. This applies to ordinary D2 BUY and the first-scoring-foothold bootstrap. Once a Joker is owned and at Ante 3+, ordinary D2 economics are unchanged.

Validation: **74/74 GREEN**.

The previously reported 1/10 result was incorrect. Session `balatro-20260831T123756Z-62a20e03` attempt 7 reached Ante 8 boss Crimson Heart but ended at `68218 / 100000`, `hands_left=0`, phase `GAME_OVER`. The public `won` bit remained sticky. Corrected result: **0/10 wins**.

Tune A remains retained provisionally because it removed the specific observed `$0/$1` first-Joker bankroll commitment while remaining semantically clean. It has not demonstrated a win-rate improvement over the original baseline.

## Phase-6 Tune B — early paid-reroll runway — REJECTED / REVERTED

Experiment commit: `32457e2e`.
Revert commit: `1ed61d29`.

Experiment: Red/White pre-Ante-6 `minimum_money_after_paid_reroll` **$10 → $8**.

Semantic result: **74/74 GREEN**.
Live result: session `balatro-20260831T135424Z-655cd5c9` finished **0/10 wins**.

The experiment failed to establish a primary or trace-grounded compensating benefit, so the `$8` D11 runway was rejected and restored to `$10`. The restored state was locally revalidated **74/74 GREEN**.

## Phase-6 Tune C — ordinary Joker replacement margin — REJECTED / REVERTED

Canonical owner: D2 `JokerAcquisitionPolicy`, configured by the Red/White playbook.

Experiment commit: `47a212d0`.
Revert commit: `6261165b`.

Experiment:

- `minimum_replacement_advantage`: **0.75 → 0.50**;
- aligned replacement margin remained **0.25**;
- first-Joker Tune A `$2` runway remained unchanged;
- ordinary new-slot purchase threshold remained **0.35**;
- D11 and D14 coefficients remained unchanged.

Semantic result before live sampling: **74/74 GREEN**.

### Tune-C live comparison

The first session `balatro-20260831T145541Z-6d7821ed` produced nine valid completed gameplay attempts, all authoritative **LOSS** outcomes. Attempt 9 reached Ante 8 boss **Violet Vessel**, required `300000`, ended around `88815 / 300000`, and then exposed the sticky-`won` restart bug. The gameplay result itself remained valid.

After the runtime repair was validated, session `balatro-20260831T155937Z-39d11c7e` supplied the required tenth attempt. The authoritative session summary records:

- attempt count: 1;
- actions: 96;
- outcome: **LOSS**;
- stop reason: `game over (lost)`;
- session stop: normal `attempt limit reached (1); auto-off before next run`;
- session `won=false`.

Combined Tune-C result: **0/10 wins**.

Interpretation:

- Tune C did not improve the primary metric versus baseline or retained Tune A; all remain **0/10**;
- the experiment therefore does not justify retaining the more permissive ordinary replacement threshold;
- no additional numerical parameter is stacked on top of it;
- `6261165b` restores `minimum_replacement_advantage=0.75` while leaving Tune A intact.

The uploaded tenth-attempt JSONL was not exposed through the active file-search/container path during this audit, so no exact replacement-count or decision-sequence claim is made from attempt 10. Rejection is based on the complete controlled 10-run outcome sample, not invented trace details.

## Runtime finding — sticky public `won` must not veto authoritative GAME_OVER loss restart — VALIDATED

Canonical runtime source: `games/balatro/live/runtime/live_memory_restart_run_injected.py`.

Balatro's public `won` bit can remain sticky after a later Ante-8 GAME_OVER loss. Production autonomous-loop semantics already treated complete `GAME_OVER` as authoritative loss evidence, but the restart validator contradicted that contract.

Fix:

- `28cec27b` — complete `GAME_OVER` remains mandatory, but stale `won=true` no longer vetoes loss restart;
- non-GAME_OVER and incomplete GAME_OVER snapshots still fail closed;
- deck/stake identity and post-restart BLIND_SELECT verification remain unchanged;
- `6e1a2696` — focused regression.

Validation: **LOCAL REGRESSION GREEN**.

# EXACT NEXT ACTION

Validate the Tune-C revert back to the retained Tune-A configuration:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark

```

Expected result: **74/74 GREEN**.

If green, select Tune D only from a **distinct evidence-backed problem**. Do not reopen Tune B's `$8` D11 runway or Tune C's `0.50` ordinary replacement margin without new controlled evidence. Prioritize a problem that can explain why the stack can reach Ante 6–8 yet repeatedly remains underpowered, while preserving canonical ownership and changing only one numerical preference at a time.

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