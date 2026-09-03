# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

The project has pivoted from hand-authored Bond-value strategy toward reinforcement learning (RL) in a fast deterministic Balatro environment. Existing deterministic mechanics, state translation, legality, tactical execution, candidate projection, telemetry, and Bond feature work remain foundations. Manual Bond-weight tuning is retired as the primary competence path.

---

# Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Work Chat runs deterministic/static tests itself where the environment permits.
- The user runs only validation that genuinely requires the Windows/Balatro game environment.
- Preserve exact mechanics, legality, boss rules, affordability, survival, public-information boundaries, and reproducible RNG semantics.
- Prefer canonical ownership over wrappers/rescue layers.
- Training code must never silently redefine Balatro mechanics to make learning easier.
- Simulator shortcuts are allowed only when behaviorally equivalent at the modeled state/action boundary and covered by parity tests.
- Model checkpoints are artifacts, not source-of-truth strategy definitions. Promoted checkpoints require reproducible configs, seeds, environment/schema versions, and evaluation results.

---

# Primary objective

**Red Deck / White Stake, normal mode: maximize probability of clearing Ante 8.**

The terminal objective is run success, not score maximization, Joker collection, money maximization, Bond completion, or build aesthetics.

---

# Target architecture

```text
LIVE BALATRO OR HEADLESS ENVIRONMENT
        ↓
CANONICAL PUBLIC GAME STATE
        ↓
EXACT MECHANICS + LEGAL ACTION GENERATION
        ↓
OBSERVATION ENCODER
   ├─ raw/public state features
   └─ optional Bond/mechanical derived features
        ↓
LEARNED POLICY / VALUE MODEL
        ↓
LEGAL-ACTION MASK
        ↓
CANONICAL ACTION
        ↓
EXISTING EXECUTION OWNER / HEADLESS step(action)
        ↓
REWARD + NEXT STATE
```

Training loop:

```text
parallel deterministic environments
→ trajectories
→ returns / advantages
→ PPO update
→ checkpoint
→ fixed-seed evaluation
→ regression comparison
→ repeat
```

Initial RL keeps tactical hand play deterministic while RL learns strategic run development. Full tactical RL remains optional later work.

---

# Bond-system status

Preserve:

- canonical Bond vocabulary;
- mechanics-to-Bond contributions;
- realization semantics;
- sparse relationship/motif descriptors that encode real public-state structure;
- deterministic feature tests;
- Bond telemetry.

Authority change:

- Bonds are no longer the final strategic authority.
- `BuildValue` / `StrategyDelta` remain frozen deterministic baselines and optional diagnostic features.
- Do not resume manual Bond coefficient optimization as the primary path.

Planned observation ablations after training is stable:

```text
A. RAW
B. RAW+BOND
C. BOND-HEAVY diagnostic only if useful
```

Production selection is based on held-out win rate and stability.

---

# Explicitly obsolete development path

Do not return to:

- manual Optuna tuning of Bond coefficients as primary strategy learning;
- endless live batches for discovering one-off strategic thresholds;
- named strategy-state / identity FSM expansion;
- rebuilding persistent `StrategyPlan` / FORMING / PINNED controllers;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- prescription plumbing such as `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, or `commit_*`;
- rescue wrappers that override canonical legality/admission owners;
- treating symbolic `BuildValue` as win-probability proof;
- Joker-specific thresholds inferred only from suspicious live losses rather than exact mechanics/public-state truth.

---

# Completed foundation — Phases A–K

## A — Bond vocabulary — COMPLETE

46 canonical Bonds; deterministic vocabulary frozen.

## B — Mechanical descriptors — COMPLETE

`games/balatro/mechanics.py` is the canonical public mechanics surface.

## C — Mechanics → Bond contributions — COMPLETE

`games/balatro/bonds/contributions.py` owns keyed contribution normalization.

## D — Bond strategic value — COMPLETE AS BASELINE

`games/balatro/bonds/strategic_value.py` remains the frozen symbolic baseline.

## E — Sparse relationships / motifs — COMPLETE AS BASELINE/FEATURES

Relationships and motifs remain deliberately sparse; unlisted pairs are neutral.

## F — `BuildValue(state)` — COMPLETE AS BASELINE

Deterministic whole-build baseline retained.

## G — Projected-state `StrategyDelta(candidate)` — COMPLETE AS BASELINE

Retained for deterministic projection/comparison tests, not as final learned-policy authority.

## H — Canonical strategic decision-owner integration — COMPLETE

Canonical acquisition, replacement, pack, consumable, voucher, shop-arbitration, and execution ownership remains the action-interface foundation for RL.

## I — Tactical exploitation — COMPLETE

Representative deterministic proofs cover:

1. Burnt Joker first-discard hand leveling.
2. Hanged Man / permanent deck thinning.
3. Steel / Baron / Mime held-card preservation and exploitation.

## J — Deterministic end-to-end proofs — COMPLETE

Representative hand-leveling, thinning, and held-card paths are green and become simulator parity assets.

## K — Legacy strategic migration cleanup — COMPLETE

Rejected persistent strategy-controller architecture removed while preserving canonical mechanics/economics/health/D1/D2/D9/D14/boss/runtime ownership.

Important retained semantic corrections include Midas→Vampire trigger order, persistent enhancement feed, renewable future-feed distinction, debuffed Gold cards, Midas scoring-face requirements, Stone-card rank identity, and Planet observed/exotic-hand evidence semantics.

---

# Phase L — Live correctness stabilization before RL environment freeze — COMPLETE

## L1 — September 2 baseline — COMPLETE

Batch `balatro-20260902T200815Z-dba5db6f`:

- attempt 001 lost Ante 7 boss The House: `49,834 / 70,000`;
- attempt 002 lost Ante 3 boss The Needle: `770 / 2,000`;
- attempt 003 lost Ante 2 boss The Club: `1,404 / 1,600`.

Repairs included Baron motif false positive, Flash Card D2 authority, Throwback realization, Card Sharp stale history, D14 attribution, and unsupported Director's Cut/Retcon boss-reroll fail-closed behavior.

## L2 — September 3 post-repair batch — COMPLETE / INSPECTED

Batch `balatro-20260903T094415Z-87fd8720`:

- attempt 001 lost Ante 1 boss The Club: `272 / 600`;
- attempt 002 lost Ante 3 boss The Water: `2,512 / 4,000`;
- attempt 003 lost Ante 7 Big Blind: `21,908 / 52,500`.

Repairs included the D14 deterministic-policy timing blind spot and The Sun optional-proof/D1 budget starvation.

## L3 — RL environment freeze gate — COMPLETE

- `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`;
- training-exposed actions fail closed unless canonical legality/execution ownership is declared;
- unsupported boss reroll is unavailable;
- translator phase-boundary regression covers stale-round reset and active-round preservation;
- CI `33758680261`: `1223 passed, 1594 deselected`;
- 7 Linux-only `APPDATA` construction issues repaired without test skips.

Do not request another open-ended live batch and do not resume symbolic strategy tuning.

---

# Phase R — Headless Balatro environment — ACTIVE

Purpose: build a fast deterministic training environment reproducing the canonical modeled Red Deck / White Stake surface without the live Windows/Balatro UI. It is not authoritative game truth until parity gates pass.

## R0 — Environment architecture and ownership — COMPLETE

- authoritative environment under `games/balatro/env/`;
- versioned `r0-v1` boundary;
- `reset`, `step`, `legal_actions`;
- observations wrap/copy canonical `BalatroState`;
- strategic actions alias frozen `l3-v1` contract;
- explicit single-agent turn ownership, Ante-8 terminal semantics, serialization/restore, and illegal-action rejection;
- CI `33760179448`: `1233 passed, 1594 deselected`.

Legacy `games/balatro/environment.py` remains toy/stub code and is not authoritative RL environment truth.

## R1 — State transition engine — ACTIVE

### Core acquisition rule

Generic acquisition is not `append inventory + subtract money`.

Canonical `BalatroState` owns mutable capacities/resources including hand size, next-round hand/discard allowances, Joker slots, and consumable slots. Some Jokers/vouchers mutate these immediately or at later lifecycle boundaries. Therefore:

- `BUY_JOKER` is identity-gated;
- generic `BUY_VOUCHER` remains fail-closed;
- unsupported/inexact actions are absent from `legal_actions()` and reject on direct execution;
- all Joker editions remain fail-closed, especially Negative because it changes Joker-capacity semantics;
- `SELL_JOKER` remains outside the frozen training surface until inverse lifecycle effects are audited;
- packs remain blocked until exact pack state and R2 RNG ownership exist.

### Exact shop behavior currently owned

Always supported in active shop when otherwise legal:

- `END_SHOP`;
- exact held-consumable purchase when capacity, price, and affordability are exact.

Price semantics fail closed:

- price must be an exact integer;
- bool/string/float/missing/invalid mapping/negative values are rejected as exact purchases;
- legality and direct transition execution share the same price/slot boundary.

### Exact resource/capacity-sensitive Joker acquisitions

- **Juggler**: `hand_size += 1` once.
- **Stuntman**: `hand_size -= 2`; fail-closed when authoritative hand size is below 2.
- **Drunkard**: `round_reset_discards += 1`; requires authoritative observed next-round discard allowance.
- **Troubadour**: `hand_size += 2`, `round_reset_hands -= 1`; requires authoritative observed next-round hand allowance and at least 1 hand.
- **Merry Andy**: `hand_size -= 1`, `round_reset_discards += 3`; requires authoritative observed reset-discard baseline and hand size at least 1.

Canonical/live next-round hand ownership is complete:

- `BalatroState` owns/copies `round_reset_hands_observed` / `round_reset_hands`;
- `LiveMemoryBalatroObserver` reads `G.GAME.round_resets.hands` fail-closed;
- `DefaultBalatroStateTranslator` maps only valid exact nonnegative integer values;
- observer/translator tests cover observed, zero, missing, and invalid behavior;
- CI `33781164005`: `1297 passed, 1594 deselected`.

Merry Andy exactness:

- `tests/balatro/test_balatro_env_r1_merry_andy.py` covers gates, isolation, affordability/inventory transfer, and exact one-time modifiers;
- CI `33781461393`: `1300 passed, 1594 deselected`.

### Exact inventory-only scoring/rule acquisitions

These Jokers have no acquisition-time capacity/resource mutation and their gameplay rule/scoring semantics are already owned by the canonical hand-rule or validated live score-projector path. Their non-edition purchases are exact inventory/economy transitions.

Previously admitted scoring/state-safe set:

- `FlatMultJoker`
- `AbstractJoker`
- `AcrobatJoker`
- `BannerJoker`
- `BaronJoker`
- `BlackboardJoker`
- `BlueJoker`
- `EvenStevenJoker`
- `FibonacciJoker`
- `HalfJoker`
- `MysticSummitJoker`
- `OddToddJoker`
- `PhotographJoker`
- `RaisedFistJoker`
- `ScholarJoker`
- `SmileyFaceJoker`
- `WalkieTalkieJoker`
- `JugglerJoker`

Passive hand-rule group:

- `FourFingersJoker`
- `PareidoliaJoker`
- `ShortcutJoker`
- `SmearedJoker`
- `SplashJoker`

Semantics are already canonical: Four Fingers changes straight/flush size, Pareidolia face identity, Shortcut straight gaps, Smeared suit equivalence, Splash scoring-card membership.

CI `33782526550`: `1310 passed, 1594 deselected`.

Initial hand-shape score-only group:

- `JollyJoker`
- `SlyJoker`
- `ZanyJoker`
- `WilyJoker`
- `TheDuoJoker`

CI `33782754111`: `1320 passed, 1594 deselected`.

Pair / Straight / Flush score-only expansion:

- `CrazyJoker`
- `DeviousJoker`
- `DrollJoker`
- `CraftyJoker`
- `MadJoker`
- `CleverJoker`

All six only mutate score during hand evaluation. Parameterized tests prove exact money/inventory transfer, input isolation, unchanged resources, projector support, edition rejection, and direct-transition rejection.

CI `33783865698`: `1332 passed, 1594 deselected`.

Hand-shape xMult expansion:

- `TheTrioJoker`
- `TheFamilyJoker`
- `TheOrderJoker`
- `TheTribeJoker`

All four are pure hand-shape xMult predicates with no acquisition/lifecycle mutation.

CI `33784097107`: `1340 passed, 1594 deselected`.

Suit-scoring expansion:

- `GreedyJoker`
- `LustyJoker`
- `WrathfulJoker`
- `GluttonousJoker`

All four only add score contribution based on canonical suit matching. `tests/balatro/test_balatro_env_r1_suit_scoring_acquisition.py` separately proves inventory/economy exactness, unchanged resources, projector ownership, edition rejection, and direct-transition rejection.

CI `33784381489`: `1348 passed, 1594 deselected`.

### Current R1 fail-closed boundary

Still fail-closed:

- unknown/generic Joker identities;
- all Joker editions;
- generic voucher acquisition;
- booster-pack opening;
- stochastic acquisition/generation requiring R2 RNG;
- any acquisition whose immediate persistent or later lifecycle consequences have not been audited;
- `SELL_JOKER` and inverse capacity/resource semantics.

Important retained audit finding:

- **Burglar is not acquisition-only.** Its modeled effect fires at `BLIND_SELECTED`, gaining hands and setting discards to zero. Keep it blocked until R1 owns that blind-selection lifecycle transition exactly.

### Latest functional R1 commits

```text
c816aa8  feat(balatro): translate next-round hand allowance
d58436c  feat(balatro): observe next-round hand allowance
8bf4c07  test(balatro): cover live next-round hand ownership
f3fe9f2  test(balatro): keep R1 live ownership in CI
91d66ef  feat(balatro): enable exact Merry Andy acquisition
00363a7  test(balatro): cover exact Merry Andy R1 acquisition
bccddd7  feat(balatro): admit exact passive hand-rule acquisitions
b29bfb3  test(balatro): cover passive hand-rule R1 acquisitions
0d075e4  feat(balatro): admit exact hand-shape scoring acquisitions
e1276c0  test(balatro): cover hand-shape scoring R1 acquisitions
1ac746c  feat(balatro): admit exact pair straight flush scoring acquisitions
c0ab092  test(balatro): cover pair straight flush R1 acquisitions
6cf10bb  feat(balatro): admit exact hand-shape xmult acquisitions
4940a79  test(balatro): cover hand-shape xmult R1 acquisitions
3146473  feat(balatro): admit exact suit scoring acquisitions
06c2430  test(balatro): cover suit scoring R1 acquisitions
```

### R1 immediate objective

Continue the acquisition/lifecycle semantics inventory from the green suit-scoring checkpoint.

For each next candidate:

1. classify the lifecycle point where its consequences occur;
2. admit it only if immediate and persistent consequences are exactly represented by canonical/headless state and existing owned scoring/rule semantics;
3. preserve affordability and slot legality;
4. preserve input-state isolation;
5. retain edition rejection;
6. retain legality + direct-transition rejection tests;
7. if a candidate depends on an unowned lifecycle transition, keep it blocked and implement that lifecycle category before admission;
8. do not broaden generic Joker/voucher/pack surfaces merely because the live UI can click them.

After the remaining R1 transition categories are exact, continue R2/R3. Do not move to PPO or observation training yet.

### Remaining R1 state categories

- seed / RNG state;
- ante, blind, boss, blind requirement;
- current score and round progress;
- money/economy state;
- hands/discards remaining and next-round allowances;
- exact deck/card zones and public card properties;
- current hand;
- Jokers/editions/counters and slot capacity;
- consumables and slot capacity;
- vouchers/shop modifiers;
- hand levels;
- tags/skips;
- shop inventory and reroll state;
- pack state/choices;
- boss restrictions;
- run-wide and round-local Joker counters.

Do not substitute averages for exact deterministic state where training parity requires exactness.

## R2 — RNG determinism — NOT STARTED AS A COMPLETE PHASE

Requirements:

- `reset(seed)` owns environment RNG;
- deterministic shop generation, draws, packs, boss selection, and modeled random effects;
- no unrelated global RNG in transitions;
- replay metadata records seed/action sequence;
- identical environment version + seed + actions produce identical trajectories;
- serialization/restoration preserves the next RNG result.

## R3 — Typed action vocabulary — PARTIAL / TIED TO R1 EXACTNESS

Initial strategic action classes as applicable:

```text
END_SHOP
REROLL_SHOP
BUY_JOKER(slot)
SELL_JOKER(slot)
BUY_VOUCHER(slot)
BUY_CONSUMABLE(slot)
BUY_CARD(slot)
OPEN_PACK(slot/type)
CHOOSE_PACK_OPTION(index)
SKIP_PACK
USE_CONSUMABLE(targets...)
SKIP_BLIND
SELECT_BLIND / START_BLIND
```

Every training-visible action requires stable type/id, required parameters, deterministic legality, deterministic exact transition, serialization representation, and training-mask representation. Unsupported actions are absent, not given arbitrary low value.

## R4 — Deterministic tactical bridge — NOT STARTED

Initial curriculum reuses existing deterministic D1/D9/tactical owners for hand-level play while RL controls strategic boundaries. Tactical trajectories remain logged for parity/debugging.

## R5 — Live/simulator parity harness — NOT STARTED

Priority fixtures include ordinary shop purchase/hold/end-shop, Joker replacement, reroll, voucher purchase/rejection, pack paths, blind skip, ordinary blind clear, boss restrictions, Card Sharp reset, Throwback skip counter, Baron held-card state, The Sun path, and economy/interest transitions.

## R6 — Environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead after semantics are correct. Do not trade correctness for speed without an explicit parity record.

### Phase R exit criteria

- deterministic reset/step API;
- all initial strategic actions have exact legality + execution tests;
- Red/White run proceeds reset→terminal entirely headlessly;
- fixed-seed replay deterministic;
- representative live parity fixtures green;
- throughput supports automated training experiments;
- environment version stored in trajectory metadata.

---

# Phase O — Observation and action encoding — NOT STARTED

Create versioned observation/action schemas with no hidden-information leakage. Encode public run context, Jokers, deck structure, visible offers, capacities, counters, and optional Bond/mechanics features. Illegal actions must have zero probability after masking.

---

# Phase B0 — RL baseline infrastructure — NOT STARTED

1. random legal strategic baseline;
2. frozen symbolic/Bond baseline in the same headless environment;
3. stable trajectory format containing environment/schema versions, seed, step, phase, mask, selected action, reward, termination, and useful diagnostics.

---

# Phase P — PPO strategic learner — NOT STARTED

Build a modest masked policy/value network, parallel rollout collector, GAE/returns, PPO update, reproducible checkpointing, and terminal-win reward baseline.

```text
Ante 8 cleared: +1
run lost:        0
```

Any shaping must be explicitly configured and validated against actual Ante-8 success.

---

# Phase C0 — Curriculum and sample efficiency — NOT STARTED

Initial RL controls strategic shop/build/economy decisions while deterministic tactical owners resolve hand play. Curriculum may expand through packs, vouchers, rerolls, skips, consumable timing, and later optional tactical RL. Fresh Ante-1 evaluation remains authoritative.

---

# Phase E0 — Evaluation framework — NOT STARTED

Maintain separate training, development-evaluation, and final held-out seed sets.

Mandatory comparisons:

```text
Random legal policy
Frozen symbolic/Bond baseline
Learned RAW model
Learned RAW+BOND model
```

Report Ante-8 clear rate, confidence interval, run count, ante/failure distributions, invalid actions, runtime, and useful policy diagnostics.

---

# Phase A0 — Observation/Bond ablation — NOT STARTED

Compare RAW vs RAW+BOND under equal training budgets and multiple training seeds. Retain Bond features only if they improve sample efficiency, final competence, stability, or useful interpretability at acceptable cost.

---

# Phase F0 — Reward/objective validation — NOT STARTED

Always retain terminal-only reward as reference. Reject shaping that increases shaped return without increasing Ante-8 success.

---

# Phase T — Training scale-up — NOT STARTED

Scale parallel rollout collection only after environment/training stability. Record source commit, environment/schema versions, model/reward/PPO config, workers, seeds, steps, and evaluation protocol for meaningful runs.

---

# Phase V — Simulator-to-live learned-policy validation — NOT STARTED

Freeze a promoted checkpoint and use the same observation encoder/action decoder live and headlessly. Canonical live legality remains the safety boundary. Classify simulator/live mismatches before changing policy behavior.

---

# Phase Q — Red/White learned competence gate — NOT STARTED

Controlling metric:

```text
P(clear Ante 8 | Red Deck, White Stake, normal mode)
```

Required evidence: large held-out simulated evaluation, confidence intervals, random/symbolic baselines, multiple training seeds, live validation on a frozen checkpoint, and no unresolved high-impact parity defect.

---

# Phase X — Optional full tactical RL — NOT REQUIRED FOR INITIAL GATE

Begin only if strategic-only RL with deterministic tactical execution plateaus for reasons attributable to hand/discard decisions.

---

# Phase M — Post-RL symbolic cleanup — NOT STARTED

Do not delete symbolic/Bond baseline before Phase Q. After learned authority is proven, retain one canonical learned strategic owner, one deterministic mechanics/legality boundary, and only optional Bond diagnostics/features.

---

# Phase N — Broader competence — NOT STARTED

Only after Red/White success: additional decks, higher stakes, broader actions such as boss reroll if desired, endless objectives, tactical RL, and wider framework integration.

---

# Testing and reproducibility contract

Use deterministic tests for mechanics, transitions, legality, phase boundaries, RNG, serialization, encodings, masks, parity, checkpoint loading, and deterministic inference.

Use statistical rollout evaluation for win rate, learning curves, model comparisons, ablations, reward validation, and hyperparameter comparison.

Every promoted model records:

```text
source commit
model checkpoint hash/path
environment version
observation schema version
action schema version
reward configuration
training configuration
training seed(s)
training step count
evaluation seed set id
evaluation results
```

---

# Failure-classification contract

Classify bad decisions before changing code:

1. mechanics bug;
2. state bug;
3. legality/action bug;
4. simulator/live parity bug;
5. training bug;
6. reward bug;
7. representation limitation;
8. capacity/optimization issue;
9. ordinary learned-policy error.

A single bad run is not sufficient evidence for a new hand-coded strategic exception.

---

# Current checkpoint — EXACT PROJECT STATE

```text
Historical symbolic/Bond architecture             COMPLETE AS BASELINE
Mechanics/state/action deterministic foundation   SUBSTANTIALLY COMPLETE
Phase K legacy-controller cleanup                 COMPLETE
September 2 live baseline                         INSPECTED
September 3 post-repair batch                     INSPECTED
Manual Bond numerical tuning                      RETIRED AS PRIMARY PATH
RL pivot                                           APPROVED / ROADMAP ACTIVE
L3 environment-freeze correctness gate            COMPLETE
R0 environment architecture/ownership             COMPLETE
R1 state transition engine                        ACTIVE
R1 acquisition semantics audit                    ACTIVE — CURRENT WORKSTREAM
Exact resource-sensitive acquisitions             Juggler/Stuntman/Drunkard/Troubadour/Merry Andy
Passive hand-rule acquisitions                    GREEN
Hand-shape score-only acquisitions                GREEN
Pair/Straight/Flush score-only expansion          GREEN — CI 33783865698
Hand-shape xMult expansion                        GREEN — CI 33784097107
Suit-scoring expansion                            GREEN — CI 33784381489
Burglar acquisition                               FAIL-CLOSED PENDING BLIND_SELECTED OWNERSHIP
Generic/unknown Joker acquisition                 FAIL-CLOSED
Joker editions                                    FAIL-CLOSED
Generic voucher acquisition                       FAIL-CLOSED
Booster-pack opening                              FAIL-CLOSED UNTIL RNG/PACK STATE EXACT
SELL_JOKER lifecycle/inverse modifiers            NOT YET IN TRAINING SURFACE
R2 RNG determinism                                NOT STARTED AS COMPLETE PHASE
R3 action vocabulary                              PARTIAL / TIED TO R1 EXACTNESS
R4 deterministic tactical bridge                  NOT STARTED
R5 live/simulator parity harness                  NOT STARTED
R6 performance gate                               NOT STARTED
Observation/action encoding                       NOT STARTED
Random/symbolic headless baselines                 NOT STARTED
PPO strategic learner                             NOT STARTED
RL curriculum                                     NOT STARTED
Statistical evaluation framework                  NOT STARTED
Bond feature ablation                             NOT STARTED
Training scale-up                                 NOT STARTED
Simulator-to-live learned-policy validation        NOT STARTED
Red/White learned competence gate                 NOT STARTED
Full tactical RL                                  OPTIONAL / NOT STARTED
Post-RL symbolic cleanup                          NOT STARTED
```

Current branch code head immediately before this roadmap synchronization:

```text
06c2430b71a9535f4c584007bead79d308bc4cdb
```

---

# Exact next development action

**Continue R1. Do not move to PPO/observation training work yet.**

Immediate order:

1. continue the small scoring/rule acquisition audit and classify each candidate by lifecycle point;
2. admit the next exact acquisition only where purchase plus all persistent consequences are already owned;
3. keep lifecycle-dependent Jokers blocked until the required lifecycle transition exists;
4. keep generic Joker/voucher buys, editions, packs, and unknown acquisitions fail-closed;
5. preserve deterministic legality, isolation, edition-rejection, and direct-transition rejection tests;
6. when score-only inventory expansion stops being the limiting surface, implement the next blocked lifecycle transition category rather than weakening the exactness gate;
7. finish R1 transition categories, then R2/R3;
8. add R5 parity fixtures before treating the environment as authoritative for training.

The next code should therefore be **continued exact R1 acquisition/lifecycle transition work from the green suit-scoring checkpoint**. It should **not** be Bond tuning and **not** PPO.

---

# Progress criterion

```text
mechanical/state/action foundation                 ✓
Bond symbolic baseline                             ✓
legacy strategic-controller cleanup                ✓
live correctness stabilization                     ✓
R0 HEADLESS ENVIRONMENT ARCHITECTURE               ✓
        ↓
R1 EXACT STATE TRANSITIONS                         ← ACTIVE
  └─ acquisition semantics audit                   ← ACTIVE
      ├─ resource-sensitive capacity ownership      ✓ incremental
      ├─ passive hand-rule acquisitions             ✓
      ├─ score-only inventory acquisitions          ✓ expanding incrementally
      └─ lifecycle-dependent acquisitions           ← KEEP FAIL-CLOSED UNTIL OWNED
        ↓
R2 RNG + R3 ACTION COMPLETION
        ↓
R4 DETERMINISTIC TACTICAL BRIDGE
        ↓
R5 PARITY + R6 PERFORMANCE
        ↓
OBSERVATION + ACTION ENCODING
        ↓
RANDOM + SYMBOLIC HEADLESS BASELINES
        ↓
PPO STRATEGIC LEARNER
        ↓
CURRICULUM + REWARD VALIDATION
        ↓
STATISTICAL EVALUATION + BOND ABLATION
        ↓
TRAINING SCALE-UP
        ↓
SIMULATOR ↔ LIVE TRANSFER VALIDATION
        ↓
RED/WHITE RL COMPETENCE GATE
        ↓
POST-RL SYMBOLIC CLEANUP
        ↓
OPTIONAL FULL TACTICAL RL / BROADER COMPETENCE
```

Controlling implementation question:

> **Does the environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
