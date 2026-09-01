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

> **Phase 5 live validation is COMPLETE at 74/74 semantic green. Phase 6 action-quality work is ACTIVE. The original Phase-6 baseline and Tunes A–F all produced 0/10 wins. Tune A remains retained provisionally; Tunes B–F are rejected/reverted. The Bond-utilization audit found and fixed one genuine cross-owner defect in D9 Buffoon handling (`c1f8422`), and the full deterministic Balatro suite was user-confirmed GREEN after the related stale-test cleanup. A controlled 10-attempt live comparison of that structural correction (`balatro-20260901T094854Z-cc1ed501`) still produced 0/10 wins. The correction remains semantically valid, but it did not change the primary live metric. The new evidence, together with repeated cash-rich/full-board but underpowered losses, raises a more fundamental possibility: the Bond model itself may correctly recognize local mechanical relationships while still defining strategy commitment/completion/coherence in a way that does not reliably represent a sufficiently strong run-winning engine. Phase 6 therefore pivots to a FULL BOND MODEL AUDIT before any further Tune G, D4/D14 integration, Build Health pressure wiring, or live comparison. Audit the Bond catalogue in semantically related batches of three, then audit relationships, motifs, strategy formation, StrategyPlan, composer, Build Health boundary, and canonical consumers. Bond remains evidence/planning only and must not become a second action authority.**

Validated checkpoints:

- Phase 0 authority consolidation: **COMPLETE / 24/24 semantic green**
- Full deterministic Balatro suite: **GREEN after D9 structural correction and stale-contract cleanup**
- Phase 1 D1 survival expansion: **COMPLETE / 33/33 green**
- Phase 2 simple shop survival: **COMPLETE / 42/42 green**
- Phase 3 coherent build evidence: **COMPLETE / 52/52 green**, `BUILD_COHERENCE` 12/12
- Phase 4 resource semantics: **COMPLETE / 70/70**, `RESOURCE_COHERENCE` 18/18
- Phase 5 live D1/D2 semantics: **COMPLETE / 74/74**, `D1_SURVIVAL` 25/25, `SHOP_SURVIVAL` 19/19
- Phase 6 Tune A first-Joker cash runway: **SEMANTIC GREEN / 74/74; RETAINED / 0 OF 10 WINS after corrected terminal bookkeeping**
- Phase 6 Tune B early paid-reroll runway: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune C ordinary Joker replacement margin: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune D booster acquisition margin: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune E contextual/B3 Joker build weight: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 Tune F observed-hand scoring prior: **SEMANTIC GREEN / 74/74; REJECTED / 0 OF 10 WINS; REVERT GREEN / 74/74**
- Phase 6 D9 Bond-utilization structural correction: **SEMANTIC GREEN / LIVE 0 OF 10 WINS / RETAINED AS CORRECT OWNERSHIP FIX**
- Phase 6 full Bond model audit: **ACTIVE / CATALOGUE FIRST / THREE SEMANTICALLY RELATED BONDS PER BATCH**
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
Effective branch-attached revert commit: `eecd0b40`, restoring pre-Tune-E `contextual_gain=1.0`. The earlier `d5c3f8ce` was an intermediate unattached revert object and is not the branch checkpoint.

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

Reverted configuration locally revalidated: **74/74 GREEN**.

Do not reopen `contextual_gain=0.75` absent new controlled evidence.

## Tune F — observed-hand scoring prior — REJECTED / REVERTED

Canonical owner: `JokerBuildValueEvaluator`, specifically the public hand-history weighting inside whole-build literal Joker scoring.

Experiment commit: `ab118a33`.
Revert commit: `bd45379d`.

Experiment:

- `_OBSERVED_HAND_PRIOR_WEIGHT`: **0.25 → 0.10**.

Semantic result before live sampling: **74/74 GREEN**.

### Tune-F live comparison

Session: `balatro-20260901T055941Z-f2447e67`.

Result: **0/10 wins**. All ten attempts ended with authoritative `LOSS`, and the supervisor stopped normally at the ten-attempt limit.

Representative deep-run evidence:

- attempt 6 reached **Ante 7 The Needle** at `18880 / 35000`;
- it had a full five-Joker board: `Blue Joker / Raised Fist / Swashbuckler / Green Joker (+34 Mult) / Ramen (x2)`;
- it retained **$103** at death;
- public hand history was already concentrated toward Two Pair/Pair (`Two Pair=15`, `Pair=12`) while advanced hand classes remained largely unplayed, so Tune F's lower off-plan prior was materially active.

Interpretation:

- Tune F did not improve the primary metric: **0/10**, like baseline and Tunes A–E;
- furthest depth was **Ante 7**, only matching the original baseline rather than exceeding it;
- stronger hand-history concentration alone did not solve the cash-rich/underpowered-build pattern;
- `bd45379d` restores `_OBSERVED_HAND_PRIOR_WEIGHT=0.25`;
- user locally revalidated the restored configuration **74/74 GREEN**.

Do not reopen `_OBSERVED_HAND_PRIOR_WEIGHT=0.10` absent new controlled evidence.

## Phase-6 D9 Bond-utilization correction — SEMANTICALLY VALID / LIVE 0 OF 10

The earlier Bond-utilization audit found one concrete cross-owner defect:

- opened Buffoon Jokers did not all pass through canonical D2;
- the live Buffoon generator suppressed `SKIP_BOOSTER` when a Joker slot was free;
- therefore a visible Joker could be forced even when D2 would HOLD because of weak value or conflict.

Commit `c1f8422` repaired this by routing every visible Buffoon Joker through canonical `PlaybookJokerAcquisitionPolicy` at already-paid opened-pack cost `$0`, preserving replacement as SELL → reobserve → SELECT and retaining Skip as a real D9 candidate.

Semantic validation:

- focused D9 regression: **GREEN**;
- full deterministic Balatro suite: **GREEN** after stale-contract/test-isolation cleanup in `aaa01d8f`, `97049e62`, `f099b0ba`, and `b8ef51b9`.

Controlled live comparison:

- session: `balatro-20260901T094854Z-cc1ed501`;
- result: **0/10 wins**;
- all ten attempts ended with authoritative losses;
- the structural correction remains correct ownership/legality behavior, but the primary metric did not improve.

This does not justify reverting `c1f8422`. It does justify moving the investigation one layer deeper: the remaining failure may be in how Bond defines and ranks strategy quality rather than only in whether canonical owners consume Bond evidence.

# Phase 6 — FULL BOND MODEL AUDIT — ACTIVE

## Why this audit now

Current evidence supports a design-level question:

> The Bond system may be good at recognizing that pieces are mechanically related while still being too weak at distinguishing a coherent but underpowered package from a genuinely run-winning engine.

Known design risks already visible in the current implementation and live evidence include:

- `PINNED` is reconstructed from the current state rather than persisted as a temporal commitment;
- strategy candidate ordering gives commitment precedence over strength;
- `StrategyPlan.completion` measures Bond/component construction, not engine sufficiency against run-stage scoring demands;
- `Composition.coherence_score` measures structural development/synergy/motif/conflict evidence, not whether the engine projects enough realized/scaling power;
- explicit motif coverage is narrow, so much of the catalogue relies on generic local mechanical-role links;
- D2 correctly rewards Bond/strategy progress, so a bad strategy-quality definition can reinforce itself even when D2 wiring is technically correct.

These are hypotheses to audit systematically, not assumptions to patch immediately.

## Audit method — three semantically related Bonds per batch

Do **not** audit alphabetically and do **not** mix unrelated Bonds merely to fill a batch. Use groups of three that share a meaningful mechanical engine or infrastructure concept.

For every Bond in a batch, audit the complete vertical slice:

1. **Definition / intended Balatro mechanic** — what strategic concept the Bond is supposed to represent and whether that abstraction makes sense.
2. **Contributors** — every Joker/card/voucher/consumable/state feature that contributes, contribution magnitude, unlock/realization conditions, and whether any relevant contributor is missing or unrelated contributor is included.
3. **Ranks R0–R5** — thresholds, whether progression is too easy/hard, and whether rank meaning corresponds to actual build development.
4. **Mechanical roles and targets** — correctness of role ontology, targets, and whether flat scoring/scaling/XMult/retrigger/economy/infrastructure distinctions are preserved.
5. **Relationships** — all declared synergy/conflict/neutral relationships to the rest of the Bond catalogue, including false positives and false negatives.
6. **Strategy effects** — how the Bond participates in semantic/behavior candidates, commitment, motif recognition, StrategyPlan goals, completion, and D2 transition bonuses.
7. **Failure cases** — concrete public states where the Bond should matter, should not matter, should be forming/established, or should lose to a stronger alternative.
8. **Tests** — whether existing tests prove those semantics or merely exercise code paths.

Classify each audited Bond as exactly one of:

- **GOOD** — semantics and coverage are adequate;
- **NEEDS MINOR FIX** — local factual/threshold/role/relationship issue without conceptual redesign;
- **DESIGN PROBLEM** — abstraction or downstream meaning is materially wrong;
- **MISSING COVERAGE** — semantics look plausible but are not adequately proven.

### Audit discipline

- Default to **audit first, redesign second**.
- Do not introduce cross-cutting strategy/composer redesign while the Bond catalogue is only partially audited.
- A narrowly isolated factual catalogue correction may be staged early only when it is unambiguous and cannot conceal a broader design issue; otherwise record it in the defect map and continue.
- Do not tune numeric weights merely to make an audited Bond “look better.”
- Do not run another live batch during the catalogue audit.
- Preserve literal Balatro mechanics and public-information boundaries.

## Catalogue audit order

Batches are chosen by semantic cohesion. Reorder only if repo inspection proves a different grouping is materially cleaner.

### Batch 1 — held-card engine core — NEXT

1. `held_cards`
2. `held_retrigger`
3. `kings`

Reason: these three sit at the core of the Baron/Mime/held-card strategy family and therefore exercise contribution semantics, retrigger amplification, rank-specific payoff/infrastructure, motif participation, and relationship quality together.

### Later catalogue batches

Determine subsequent trios from the actual catalogue after Batch 1 so they remain semantically coherent. Likely families include:

- face-card / played-retrigger packages;
- low-rank / played-retrigger packages;
- enhancement feed/payoff packages;
- hand-level / hand-payoff packages;
- suit infrastructure/payoff packages;
- economy engine/payoff packages;
- deck-thinning / deck-growth infrastructure and payoff packages;
- copy/scaler packages;
- remaining hand-shape and generic scoring Bonds.

Do not lock exact later trio membership until the catalogue files and relationship graph are inspected.

## Higher-layer audit after the Bond catalogue

Only after all Bond batches are classified, audit these layers in order:

1. **global relationship graph** — systemic false-positive/false-negative synergy/conflict patterns;
2. **mechanical-role ontology** — whether the available roles can express Balatro engines without collapsing support, flat power, scaling, and multiplicative power;
3. **motifs** — completeness, activation, maturity, prescriptions, and whether named motifs duplicate or repair generic semantics;
4. **strategy formation** — `FORMING / PINNED / ESTABLISHED / DOMINANT`, candidate ranking, confidence/strength, and pivot semantics;
5. **StrategyPlan** — package completion versus engine power/scaling trajectory and missing-goal representation;
6. **composer** — coherence, conflicts, pivot resistance, temporal persistence, observed-hand fallback, and whether a pinned strategy is actually a durable run-level thesis;
7. **Build Health boundary** — determine whether engine sufficiency/stalled-underpowered state belongs there rather than duplicating score authority inside Bond;
8. **canonical consumers** — D2, D4, D9, D14, and D1 strategy evidence consume the corrected model consistently without creating a second arbiter.

The key target distinction is:

- **structural coherence** — do these pieces mechanically reinforce each other?
- **engine sufficiency / power trajectory** — is the coherent engine realized/scaling enough for the current run stage?

Do not collapse those into one score unless the completed audit proves that is semantically sound.

## Runtime — sticky public `won` GAME_OVER restart — VALIDATED

Balatro's public `won` bit can remain sticky after a later Ante-8 GAME_OVER loss.

- `28cec27b` — complete `GAME_OVER` is authoritative loss evidence for restart; stale `won=true` no longer vetoes it.
- `6e1a2696` — focused regression.
- local validation: **GREEN**.

# EXACT NEXT ACTION

Start **Full Bond Model Audit — Batch 1** with:

1. `held_cards`
2. `held_retrigger`
3. `kings`

For this batch:

1. locate their canonical definitions across the Bond catalogue and any calibration/realization helpers;
2. enumerate every contributor and threshold for each Bond;
3. trace mechanical roles/targets and every relationship involving these Bonds;
4. trace their motif/strategy/StrategyPlan/composer effects, especially Baron/Mime/Steel;
5. inspect semantic tests and identify missing failure cases;
6. classify each Bond as **GOOD / NEEDS MINOR FIX / DESIGN PROBLEM / MISSING COVERAGE**;
7. record a concrete defect map before changing production behavior.

Do **not** run another live batch or stage Tune G during this audit. Do **not** perform a cross-cutting Bond redesign until the catalogue audit is complete unless an isolated factual defect must be corrected to continue the audit accurately.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — COMPLETE
7. Phase 6 — numerical/action-quality tuning and full Bond-model audit — ACTIVE

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
- Tune-F `_OBSERVED_HAND_PRIOR_WEIGHT=0.10` absent new controlled evidence
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
