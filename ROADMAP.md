# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Work Chat runs all deterministic/static tests itself in its isolated repository environment and keeps output quiet (`.venv/bin/python -m pytest -q` plus focused failure inspection).
- The user runs only actual Balatro gameplay and validation that genuinely requires the user's Windows/game environment.
- Do not ask the user to pull and run pytest when Work Chat can execute the test. If a test genuinely cannot run in Work Chat because it depends on the Windows/game environment, state that limitation explicitly.
- Commands genuinely requiring the user's environment must begin with `git pull` and be PowerShell-compatible.
- Preserve exact mechanics, legality, boss rules, affordability, survival, and hidden-information boundaries.
- Prefer canonical ownership over wrappers/rescue layers.
- Cleanup is part of migration completion.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical architecture:

```text
PUBLIC GAME STATE
→ MECHANICAL DESCRIPTORS
→ WEIGHTED BOND CONTRIBUTIONS
→ BOND DEVELOPMENT + REALIZATION
→ SPARSE RELATIONSHIPS + EXCEPTIONAL MOTIFS
→ BuildValue(state)
→ PROJECTED STATE AFTER CANDIDATE
→ StrategyDelta(candidate)
→ EXISTING CANONICAL DECISION OWNER
```

Bonds provide strategic value/guidance only. Tactical/gameplay owners remain authoritative for mechanics and hard constraints.

## Canonical formulas

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

```text
BondValue = bond_strength(points) × realization × optional calibration weight
RelationshipValue = coefficient × min(BondValueA, BondValueB)
MotifValue = completion × estimated_payoff
BuildValue(state) = Σ BondValue + Σ RelationshipValue + Σ MotifValue
StrategyDelta(candidate) = BuildValue(projected) - BuildValue(current) - transition_cost
```

Transition cost is small inertia against near-equal thrashing, not a strategy state machine.

# Explicitly obsolete architecture

Do not rebuild or preserve as production authority:

- giant persistent strategy controller/state machine;
- named strategy identity as primary action authority;
- FORMING/PINNED/etc. action states;
- persistent `StrategyPlan` propagation;
- `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, `commit_*`, or pivot-prescription plumbing;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- duplicate Bond/build evaluators.

# Required end state

```text
ONE mechanics → Bonds → BuildValue → StrategyDelta path
ONE set of production integrations
NO parallel legacy Bond planner/controller path
NO dead prescription plumbing
NO obsolete compatibility wrappers/tests/docs
```

# CURRENT DEVELOPMENT PATH

## Phase A — Freeze Bond vocabulary — COMPLETE

Validated green. 46 canonical Bonds. Canonical renames include `burnt → hand_leveling`, `gold_economy → gold_cards`, and `vampire → enhancement_consumption`.

## Phase B — Mechanical descriptors — COMPLETE

Validated green. `games/balatro/mechanics.py` is the canonical public mechanics surface.

## Phase C — Mechanics → Bond contributions — COMPLETE

Validated green across all 46 Bonds. `games/balatro/bonds/contributions.py` owns keyed contribution normalization.

## Phase D — Bond strategic value — COMPLETE

Validated green. `games/balatro/bonds/strategic_value.py` owns nonlinear per-Bond value; Bond rank is diagnostic rather than action authority.

## Phase E — Sparse relationships and exceptional motifs — COMPLETE

Validated green. Relationships and motifs remain deliberately sparse; unlisted pairs are neutral.

## Phase F — Canonical `BuildValue(state)` — COMPLETE

Validated green. `games/balatro/bonds/build_value.py` is the single whole-build evaluator.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE

Validated green. `strategy_delta_from_states(...)` is the canonical comparison boundary. No strategy identity, commitment state, pivot FSM, or prescription fields exist in `StrategyDelta`.

## Phase H — Integrate canonical strategic decision owners — COMPLETE

Validated green across Joker acquisition/replacement, pack choices, deterministic Tarot/Spectral transforms, Planet development, resource arbitration, and stateful Joker admission.

Production no longer installs retired R0/FORMING/PINNED controllers, generic pivot/resistance authority, manual prescription execution, pinned pack execution, strategy-authority correction, or Bond-rank retention vetoes.

Public mechanics/evidence remain authoritative for legitimate guards such as exotic-Planet anti-bootstrap behavior, Stateful Joker admission, affordability, resource reserve, legality, and hidden-information boundaries.

## Phase I — Verify tactical exploitation — COMPLETE

Validated green.

Representative canonical tactical proofs cover:

1. Burnt Joker first-discard hand leveling.
2. Hanged Man / permanent deck thinning.
3. Steel / Baron / Mime held-card preservation and exploitation.

Tactical owners remain subordinate to survival, clear probability, boss constraints, and legality.

## Phase J — Deterministic end-to-end proofs — COMPLETE

Validated green in representative end-to-end paths for hand leveling, deck thinning, and held-card engines.

Compatible candidates gain canonical BuildValue/StrategyDelta, destructive dependency removal loses value, materially stronger alternatives can still win, and D1/D2/D9/D14 tactical owners exploit the constructed engine.

## Phase K — Migration cleanup gate — COMPLETE

Completed repository-wide migration cleanup.

### Production cleanup

- removed the retired R0/PINNED/FORMING transition and retention controllers;
- removed generic pivot FSM/resistance and pivot calibration/telemetry;
- removed Bond-rank power-engine/tactical retention vetoes;
- removed manual prescriptions, pinned execution, strategy authority correction, and obsolete Build Health HOLD→BUY wrappers;
- removed the `StrategyPlan`, behavior-strategy, and strategy-semantics subsystems;
- collapsed `Composition` to structural Bond/motif/synergy/conflict evidence only;
- removed `evaluate_bond_composition(...)` and migrated production consumers to structural/canonical boundaries;
- migrated canonical Bond IDs/realizers from retired `vampire` / `gold_economy` identities to `enhancement_consumption` / `gold_cards`;
- migrated offline Bond tuning away from deleted pivot-resistance parameters;
- preserved valid mechanics, economics, health, D1/D2/D9/D14, boss, hidden-information, and runtime constraints.

### Semantic corrections discovered during cleanup

Full-suite classification exposed and fixed real mechanics regressions rather than masking them:

- Midas → Vampire same-hand feed respects Joker trigger order;
- persistent enhancement feed remains a run-level Vampire axis even when temporarily debuffed;
- Midas renewable future feed distinguishes current scoring order from future feed availability;
- Gold-card realization ignores debuffed immediate Gold effects;
- Midas Gold generation requires a live scoring face route;
- Stone cards hide ordinary rank identity from Midas/Vampire unless Pareidolia/all-cards-face semantics apply;
- Planet observed-hand ranking and exotic-hand public-evidence behavior remain canonical.

### Validation

- collection is green;
- focused Phase K regression groups are green;
- the complete `tests/balatro` suite is green after the final stale `strategy_candidates` / `evaluate_bond_composition` Build Health test was removed.

Phase K exit condition is satisfied: no rejected commitment/prescription architecture is required by production, and the deterministic Balatro suite is green.

## Phase L — Targeted live validation and tuning — ACTIVE

**Current project state: still in the validation/testing phase. Phase L is not complete, numerical tuning has not started, and broader competence work has not started.**

The deterministic cleanup prerequisite is green. The active loop is now:

```text
live baseline telemetry
→ classify suspicious decision
→ patch canonical semantics/runtime/authority
→ add focused regression
→ WORK CHAT DETERMINISTIC VALIDATION
→ USER LIVE VALIDATION ONLY WHEN REQUIRED
→ only after green, continue classification
```

A newly patched live defect is not considered resolved until Work Chat has run its focused deterministic validation successfully. If the behavior can only be proven in the real Balatro/Windows environment, it remains awaiting user live validation after deterministic coverage is green. Do not advance merely because the code change and regression test have been committed.

### L1 — Fresh production baseline — COMPLETE AS DATA COLLECTION

Fresh three-attempt production batch: `balatro-20260902T200815Z-dba5db6f`.

Outcomes:

- attempt 001: lost Ante 7 boss The House, 49,834 / 70,000;
- attempt 002: lost Ante 3 boss The Needle, 770 / 2,000;
- attempt 003: lost Ante 2 boss The Club, 1,404 / 1,600.

Runtime findings:

- no permanent SHOP stall;
- no SHOP decision exceeded 5 seconds in this batch;
- maximum observed SHOP decision latency was approximately 3.829 seconds;
- maximum observed D1 decision latency was approximately 2.519 seconds;
- D1's previous 20–25 second `nodes=0` failure is absent after bounded root admission;
- D14 timing contained non-trivial residual around standalone Joker evaluation; L2.3.3 subsequently exposed that work as a disjoint canonical timing stage without changing policy behavior.

Decision-quality findings:

- attempt 003 bought Baron for $8 in Ante 1 from an untouched 52-card deck and no established held-King engine;
- canonical evaluation incorrectly treated the ordinary four starting Kings as `KING_INFRASTRUCTURE`, making `baron_mime_steel` POTENTIAL from Baron + baseline deck alone and inflating StrategyDelta;
- production fix: exceptional Baron motif King infrastructure now requires increased King density (at least five Kings), while ordinary Kings and held-card Bonds remain available to value Baron normally;
- attempt 002 bought Flash Card even though canonical D2 explicitly returned HOLD (`buy advantage=0.100` versus threshold `0.350`); a later live Build Health rescue converted that rejected candidate back into BUY.

L1 being complete means the three-run baseline has been collected and is usable for diagnosis. It does **not** mean the live competence gate has passed.

### L2 — Classify and repair live failures — ACTIVE / TESTING

For every suspicious live decision, classify it before changing numbers:

1. **mechanics/model bug** — fix semantics first;
2. **runtime/latency bug** — bound or factorize computation without changing decision meaning;
3. **integration/authority bug** — repair ownership/order instead of adding a rescue wrapper;
4. **calibration issue** — only then tune contribution weights, realization, relationships, motif payoff, transition inertia, or integration weights.

#### L2.1 — Baron exceptional-motif false positive — FIXED AND VALIDATED

Classification: **mechanics/model bug**.

Observed failure:

- untouched starting deck contained the normal four Kings;
- those four Kings were incorrectly accepted as developed `KING_INFRASTRUCTURE`;
- Baron + baseline deck therefore activated exceptional `baron_mime_steel` POTENTIAL too early;
- the inflated motif value contributed to the bad Ante 1 Baron purchase.

Repair:

- exceptional Baron motif King infrastructure now requires actual developed King density: at least five Kings;
- ordinary four-King baseline evidence still contributes through normal held-card/King-relevant Bond valuation rather than exceptional motif completion.

Validation state:

- focused Baron motif fixtures/regression: **GREEN, user-confirmed**;
- associated corrected test commit: `7caf314d432f94c5874c28cf1fd273ed497204d8` (`test(balatro): update Baron motif fixtures for developed King density`).

This item is closed unless later live telemetry disproves the repaired semantics.

#### L2.2 — Flash Card D2 HOLD resurrected into BUY — FIXED AND VALIDATED

Classification: **integration/authority bug**.

Observed failure from attempt 002:

- canonical D2 evaluated Flash Card and returned HOLD;
- telemetry recorded `buy advantage=0.100` against threshold `0.350`;
- a later `live_competence_guard_policy` Build Health Joker rescue overrode that result and emitted BUY;
- this violated the architecture: D2 is the canonical Joker acquisition/admission owner and a post-D2 wrapper must not resurrect a rejected Joker purchase.

Repair:

- removed Joker acquisition rescue authority from `live_competence_guard_policy`;
- the live competence guard no longer converts canonical Joker HOLD decisions into BUY;
- D2 HOLD/BUY admission is final at that boundary;
- independent D1 liveness filtering remains;
- the bounded D14 scaling-deficit reroll guard remains because it operates on reroll behavior rather than overriding a rejected Joker candidate.

Committed repair/test state:

- production fix: `62f74053ca4976522fb4e70326859a6a643b02e4` — `fix(balatro): preserve canonical D2 Joker hold authority`;
- original focused regression: `f6c6fc7f211e221b98141f1f9481f85e0309fc76` — `test(balatro): protect canonical D2 hold authority`;
- collection correction: `d1d599a1f96560c068998da275f9634d6beddd1b` — `test(balatro): target canonical D2 authority regression`; the original regression referenced retired `PlaybookJokerAcquisitionPolicy` and was corrected to target canonical `JokerAcquisitionPolicy` after Phase K cleanup;
- focused D2 authority validation after that correction: **GREEN, user-confirmed**.

This item is now closed unless later live telemetry shows another post-D2 authority path.

#### L2.3 — Remaining baseline defects — ORIGINAL-BATCH INSPECTION COMPLETE

The D2 gate is green. Resume diagnosis from the same three-attempt baseline before any numerical tuning.

##### L2.3.1 — Attempt 001 Throwback blind-skip realization false positive — FIXED AND VALIDATED

Classification: **mechanics/model bug**.

Observed defect during Attempt 001 Joker inspection:

- the canonical `blind_skip` realizer marked the Bond ACTIVE solely because Throwback was owned;
- with `blinds_skipped == 0`, Throwback has not yet accumulated any skip-derived XMult, so ACTIVE overstated realized engine value before the first actual skip.

Repair:

- Throwback-backed `blind_skip` remains PARTIAL at zero skipped blinds;
- it becomes ACTIVE only after at least one blind has actually been skipped;
- the existing stronger-realization threshold at five skipped blinds is unchanged.

Committed repair/test state:

- production fix: `cde297bda93ac002f4c6ea78c0900a9d50530afb` — `fix(balatro): require realized Throwback skip value`;
- focused regression: `5ed53b870060d25c1feddaebcc078bbeaa29f41a` — `test(balatro): cover Throwback realization threshold`;
- focused Throwback validation: **GREEN, user-confirmed**.

This item is closed unless later live telemetry disproves the repaired semantics.

##### L2.3.2 — Attempt 001 Card Sharp shop-history leakage — FIXED AND DETERMINISTICALLY VALIDATED

Classification: **mechanics/model bug** at the live public-state translation boundary.

Observed defect during the Ante 7 shop before The House:

- Balatro's live memory still exposed the completed Big Blind's `played_this_round` values during SHOP (`Flush=2`, `Full House=2`, `Pair=1`);
- the translator copied those completed-round values into canonical `round_hand_play_counts` as if they were live for the upcoming boss;
- that stale history inflated the Odd Todd → Card Sharp replacement delta from `1.074` to `2.657`;
- after the recorded `$1.400` economic adjustment, the stale state changed the decision from canonical HOLD (`-0.326`) to BUY (`1.257`);
- the counters reset to zero only after The House began, confirming that the shop values belonged to the completed blind rather than the upcoming round.

Repair:

- live translation now preserves run-wide `hand_play_counts` in every phase;
- current-round `round_hand_play_counts` are accepted only during active `SELECTING_HAND` state and are normalized to zero in SHOP, BLIND_SELECT, pack, round-evaluation, and terminal states;
- Card Sharp's existing reachable repeated-hand projection remains intact, so the candidate still receives legitimate future value without treating a completed round as already active.

Validation state:

- focused Card Sharp/translator/competence regression slice: **GREEN in Work Chat (`17 passed`)**;
- broader affected Card Sharp/live translation/Joker projection/shop-arbiter slice: **GREEN in Work Chat (`174 passed`)**;
- exact attempt-001 snapshot replay: nonzero translated round counters `3 → 0`, Odd Todd replacement delta `2.656506 → 1.074050`, economic-adjusted result `-0.325950` (HOLD);
- complete Balatro suite check: `2,787 passed, 19 failed`; none of the failures exercise this repair, and the failures remain separately classified as pre-existing stale Throwback/D1 assertions, production-wrapper expectation mismatches, or Windows bridge construction that lacks `APPDATA` in Work Chat's Linux environment;
- no separate user pytest run is required; the next genuine live batch can confirm the repaired behavior alongside the remaining Phase L validation.

This item is closed unless later live telemetry disproves the repaired phase semantics.

##### L2.3.3 — D14 standalone-Joker timing attribution — FIXED AND DETERMINISTICALLY VALIDATED

Classification: **runtime telemetry-attribution bug** at the canonical D14 child boundary.

Observed defect in attempt-001 SHOP telemetry:

- multiple Joker buys, replacements, and rerolls reported substantial D14 `residual` time while the visible `joker` bucket remained at or near zero;
- `BuildAwareShopArbiter.decide()` evaluated every visible Joker through canonical D2 before entering the timed `_best_joker_decision()` boundary;
- the existing `joker` measurement therefore covered only selection among already-computed D2 decisions and misattributed the potentially expensive standalone evaluation work to `residual`;
- globally wrapping D2 would be incorrect because D2 also participates inside reroll/expectation paths and would double-count nested work.

Repair:

- the arbiter now exposes its existing one-pass visible-Joker evaluation as the canonical `_standalone_joker_decisions()` child without changing inputs, outputs, ordering, thresholds, or decision authority;
- compact D14 telemetry records that disjoint direct child as `joker_standalone`, while preserving `joker` for admitted-result selection;
- the durable live-tuning trace exposes the same boundary as `D14_JOKER_STANDALONE`;
- D14 continues to reuse the resulting tuple for both ordinary Joker selection and the bounded visible-pair check, so no additional D2 evaluation was introduced.

Validation state:

- focused D14 diagnostic/arbiter regression slice: **GREEN in Work Chat (`22 passed`)**;
- broader affected SHOP/Joker/replacement/voucher slice: **GREEN in Work Chat (`160 passed`)**;
- deterministic timing regression proves a `2.500s` standalone evaluation is reported wholly in `joker_standalone` with the exact policy results unchanged;
- this repair improves attribution only. It does not claim that D14 is faster, and no optimization is authorized until new telemetry identifies a genuinely expensive canonical owner.

This item is closed. Inspect the new stage in the next genuine live run; do not reopen policy semantics merely because prior residual values were large.

##### L2.3.4 — Attempt 001 unusable Director's Cut purchase — FIXED AND DETERMINISTICALLY VALIDATED

Classification: **integration/authority bug** at canonical D3 voucher admission.

Observed defect at attempt-001 sequence 366:

- the agent bought Director's Cut for `$10` at Ante 6 with `$57` available;
- D3 assigned the unknown-voucher fallback base value `5.000`, added `0.400` horizon value, and admitted the purchase with `3.400` child advantage / `1.900` D14 normalized gain;
- Director's Cut and Retcon provide value only through an explicit paid boss-blind reroll;
- the production action vocabulary, live runner, and injected dispatcher expose no boss-reroll action, so the agent could not use the purchased capability at any later blind.

Repair:

- canonical D3 now rejects Director's Cut and Retcon while boss-reroll execution is unsupported;
- the rejection has zero persistent value, no executable purchase action, and an explicit fail-closed rationale;
- passive and otherwise implemented vouchers retain their existing valuation and admission paths;
- implementing boss-reroll execution remains possible as a later bounded feature, but Phase L2 does not open that connector path merely to justify an unusable purchase.

Validation state:

- focused D3/voucher/readiness/D14/live-shop regression slice: **GREEN in Work Chat (`46 passed`)**;
- broader affected SHOP/Joker/replacement/voucher slice: **GREEN in Work Chat (`162 passed`)**;
- the exact attempt state (`$57`, Ante 6, `$10` Director's Cut) is covered by the regression and now returns HOLD with no executable action;
- no user pytest or separate Windows validation is required for this fail-closed admission repair; the next genuine live batch should simply contain no Director's Cut/Retcon purchase unless boss-reroll execution is added first.

This item is closed unless a production boss-reroll action is deliberately implemented later, at which point D3 valuation must be reintroduced together with end-to-end execution proof.

##### L2.3.5 — Residual original-batch classification — COMPLETE / NO ADDITIONAL PATCH

The remaining causally usable evidence from the September 2 batch has been inspected:

- attempt 002 contains no additional suspicious material decision before the sequence-48 Flash Card authority divergence;
- attempt 003 diverges at the already-fixed early Baron purchase, so later choices cannot validate current policy;
- attempt 001's surviving low-margin Joker swaps and public-pool rerolls are calibration evidence rather than a demonstrated mechanics/runtime/authority contradiction, so they do not authorize a semantic patch while L3 is closed;
- exact replay of the sequence-160 Saturn state confirms that D4's `4.150` child admission score becomes literal D14 value `0.000` and normalized value `-1.050` after resource cost, so END_SHOP is the correct canonical parent decision;
- terminal boss losses in all three attempts occur after an already-confirmed causal divergence and therefore cannot be used to patch current D1/boss policy merely because the old run lost.

No further code change is authorized from this original batch. This is an evidence boundary, not a claim that current live competence has passed.

#### L2.4 — Post-repair three-attempt live validation — BATCH INSPECTED / REPAIRS AWAIT LIVE VALIDATION

Fresh post-repair batch: `balatro-20260903T094415Z-87fd8720`.

Outcomes:

- attempt 001: lost Ante 1 boss The Club, `272 / 600`;
- attempt 002: lost Ante 3 boss The Water, `2,512 / 4,000`;
- attempt 003: lost Ante 7 Big Blind, `21,908 / 52,500`;
- no action-result failure occurred in the batch.

Exercise status of the previously repaired defects:

- Baron, Flash Card, Throwback, Card Sharp, Director's Cut, and Retcon were neither offered nor owned, so this batch did not directly exercise those item-specific repairs;
- every observed `BUY_JOKER` came from canonical `arbiter_source=JOKER_BUY`; no post-D2 rescue authority appeared;
- replaying every SHOP observation through the production translator produced zero upcoming-round hand counters, preserving the Card Sharp phase-boundary repair;
- `joker_standalone` correctly explained the expensive visible-Joker work, including `4.288s` of the `4.302s` D14 decision at attempt-002 sequence 119;
- numerical tuning remains closed because two new runtime/telemetry defects were demonstrated and repaired below.

##### L2.4.1 — D14 deterministic-policy timing blind spot — FIXED AND DETERMINISTICALLY VALIDATED

Classification: **runtime telemetry-attribution bug** at the canonical D14 deterministic child boundary.

Observed defect:

- attempt-002 sequence 124 reported `3.461s` D14 total with `3.369s` residual after buying Smiley Face while Supernova and Planet Merchant remained visible;
- attempt-003 voucher decisions showed the same pattern, including `2.017s` residual for Wasteful;
- compact timing wrapped only base `BalatroShopPolicy.rank_actions`, while production uses an overriding active shop policy, so canonical deterministic/Voucher work escaped the timer;
- globally wrapping a base policy method was also the wrong ownership boundary because ranking can occur inside nested reroll evaluation.

Repair:

- `BuildAwareShopArbiter` now exposes its existing active-policy call as `_rank_deterministic_actions()` without changing policy inputs, results, thresholds, or authority;
- compact and durable diagnostics time that direct D14 child;
- `deterministic` is now a disjoint top-level stage subtracted from D14 residual, while nested reroll work remains excluded from top-level subtraction.

Validation state:

- focused D14/D1 diagnostic slice: **GREEN in Work Chat (`20 passed`, shared with L2.4.2)**;
- broader affected D1/SHOP slice: **`268 passed`, with seven known unrelated failures** (five stale pre-existing D1 beam assertions and two Linux `APPDATA` bridge-construction failures);
- focused regression proves the active production override is timed as `deterministic` and returns exactly the same result.

##### L2.4.2 — The Sun starved D1 before node admission — FIXED AND DETERMINISTICALLY VALIDATED

Classification: **runtime/latency bug** at D1 root consumable admission.

Observed defect:

- attempt-003 sequences 190 and 194 both held The Sun and exhausted the adaptive search at `8.488s` / `9.163s` with `nodes=0/750`, `budget_exceeded=True`, and `best_action=NONE`;
- exact snapshot replay reproduced the cause: `_guaranteed_sun_action()` spent `8.001s` and `8.442s` attempting a full multi-target Sun proof before any ordinary Play/Discard node could be admitted;
- the legal structural fallback prevented an illegal action, but the optional consumable proof consumed the entire search budget and recreated the eliminated zero-node latency mode.

Repair:

- The Sun exact-clear proof receives a dedicated `0.75s` slice bounded by the parent deadline;
- expiration still rejects the unproved Sun candidate safely, but leaves the remaining parent budget for canonical ordinary D1 search;
- no search score, gameplay threshold, or Bond calibration changed.

Validation state:

- focused regression proves the Sun child deadline is strictly earlier than the parent D1 deadline;
- exact attempt-003 replay now returns from the Sun proof in approximately `0.984–1.180s` instead of consuming the full eight-second budget;
- an exact sequence-188 root replay then admitted `385` ordinary nodes before the parent deadline instead of reporting `nodes=0`;
- focused D14/D1 diagnostic slice: **GREEN in Work Chat (`20 passed`)**;
- broader affected D1/SHOP slice: **`268 passed`, with the same seven documented unrelated failures**.

##### L2.4.3 — Remaining batch decision classification — COMPLETE / NO ADDITIONAL PATCH

- attempt 001's Mercury purchase and subsequent Ante-1 Club loss do not demonstrate a mechanics, runtime, or authority contradiction;
- attempt 002's Handy Tag skip valued the observed tag at `$15`, included interest, shop, and boss-preparation opportunity costs, and cleared the configured skip margin before the later Water loss; the loss alone is calibration evidence, not proof that D13 violated public mechanics;
- later attempt-003 decisions after the first sequence-190 D1 runtime divergence are not valid evidence for changing current policy semantics;
- no Baron/Flash/Throwback/Card-Sharp/boss-reroll regression was observed, but absence from the offer pool is not positive live validation.

No architecture or numerical change is authorized from these remaining decisions.

### Current validation checkpoint — EXACT STATE

```text
Deterministic Phase K suite                     GREEN
Fresh 3-attempt live baseline collection       COMPLETE
Baron motif semantics patch                    GREEN
Flash Card / canonical D2 authority patch      GREEN
Throwback blind-skip realization patch         GREEN
Card Sharp shop-history translation patch      GREEN (WORK CHAT)
D14 standalone-Joker timing attribution patch  GREEN (WORK CHAT)
Director's Cut/Retcon D3 fail-closed patch      GREEN (WORK CHAT)
Original September 2 baseline classification    COMPLETE
Post-repair three-attempt batch                 INSPECTED; 2 RUNTIME REPAIRS GREEN
Post-L2.4 repair live validation                AWAITING USER BALATRO RUN
Numerical tuning / Optuna                       NOT STARTED
Phase M broader competence                      NOT STARTED
```

Therefore the repository is **still in testing/live validation**, specifically Phase L2.4 post-repair live validation. Do not mark L2 complete and do not describe the branch as having moved into numerical tuning.

### L3 — Numerical tuning gate — NOT STARTED

Do not start Optuna/numerical calibration until:

1. the remaining baseline suspicious decisions have been classified;
2. all confirmed mechanics/runtime/integration defects from that baseline are repaired and validated;
3. SHOP/D1/D14 interactive latency is acceptable or remaining residuals are demonstrated non-blocking;
4. no canonical owner is being bypassed by late rescue/compatibility authority.

When tuning begins, preserve the canonical architecture and compare against the production baseline using authoritative unseeded live runs with run provenance.

## Phase M — Broader competence — NOT STARTED

After Bond-guided Red/White competence is demonstrated, address broader gameplay failures, consistency, higher stakes, and additional decks.

# Exact next action

**Publish the L2.4 runtime repairs, then collect one unchanged-HEAD three-attempt Balatro validation batch. This remains testing/validation, not tuning.**

1. Work Chat commits and publishes the deterministically green D14 attribution and D1 Sun-budget repairs.
2. User pulls the exact published branch HEAD and runs `BalatroAgentToggle.bat --three` once with Balatro ready at a fresh Red Deck / White Stake run.
3. User returns the three JSONL artifacts and summaries; no user pytest run is requested.
4. Work Chat verifies that D14 deterministic work is attributed, The Sun cannot recreate `nodes=0` starvation, and no earlier mechanics/runtime/authority contradiction appears.
5. Work Chat patches only confirmed defects at their canonical owner and runs all focused deterministic regressions itself.
6. Keep L3 numerical tuning closed until post-repair semantic/integration/runtime validation is green.

# Progress criterion

```text
mechanical semantics
→ canonical Bond contributions
→ Bond/relationship/motif value
→ BuildValue
→ StrategyDelta
→ canonical decision-owner integration
→ legacy-path removal
→ tactical exploitation
→ deterministic E2E proof
→ cleanup gate
→ live validation/testing  ← CURRENT
→ numerical tuning
→ broader competence
```

Controlling question:

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent actually exploit that engine to win?**
