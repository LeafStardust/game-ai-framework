# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

The project has pivoted from a hand-authored Bond-value strategy toward reinforcement learning (RL) in a fast, deterministic Balatro environment. Existing deterministic mechanics, state translation, legality, tactical execution, candidate projection, telemetry, and Bond feature work remain foundations. Manual Bond-weight tuning is retired as the primary competence path.

---

# Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Work Chat runs deterministic/static tests itself where the environment permits.
- The user runs only validation that genuinely requires the Windows/Balatro game environment.
- Preserve exact mechanics, legality, boss rules, affordability, survival, public-information boundaries, and reproducible RNG semantics.
- Prefer canonical ownership over wrappers/rescue layers.
- Training code must never silently redefine Balatro mechanics to make learning easier.
- Simulator shortcuts are allowed only when behaviorally equivalent for the modeled state/action boundary and covered by parity tests.
- Model checkpoints are artifacts, not source-of-truth strategy definitions. Reproducible configs, seeds, environment versions, and evaluation results must accompany promoted checkpoints.

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
many parallel deterministic environments
→ collect trajectories
→ compute returns / advantages
→ PPO update
→ checkpoint
→ fixed-seed evaluation
→ regression comparison
→ repeat
```

Initial RL deliberately keeps tactical hand play deterministic while learning strategic run development. Full tactical RL remains optional later work.

---

# Bond-system status

Preserve:

- canonical Bond vocabulary;
- mechanics-to-Bond contributions;
- realization semantics;
- sparse relationship/motif descriptors that encode real public-state structure;
- deterministic feature tests;
- Bond telemetry.

Change of authority:

- Bonds are no longer the final strategic authority.
- `BuildValue` / `StrategyDelta` remain frozen deterministic baselines and diagnostic features.
- Do not resume manual Bond coefficient optimization as the primary path.

Planned observation ablations once training is stable:

```text
A. RAW
B. RAW+BOND
C. BOND-HEAVY diagnostic, only if useful
```

Production selection is based on held-out win rate and stability.

---

# Explicitly obsolete development path

Do not return to:

- manual Optuna tuning of Bond coefficients as the primary strategy-learning mechanism;
- endless live run batches for discovering one-off strategic thresholds;
- named strategy-state / identity FSM expansion;
- rebuilding persistent `StrategyPlan` / FORMING / PINNED controllers;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- prescription plumbing such as `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, or `commit_*`;
- rescue wrappers that override canonical legality/admission owners;
- treating symbolic `BuildValue` as win-probability proof;
- Joker-specific thresholds derived only from suspicious live losses rather than exact mechanics/public-state truth.

---

# Completed foundation — Phases A–K

## Phase A — Freeze Bond vocabulary — COMPLETE

46 canonical Bonds; deterministic vocabulary is frozen.

## Phase B — Mechanical descriptors — COMPLETE

`games/balatro/mechanics.py` is the canonical public mechanics surface.

## Phase C — Mechanics → Bond contributions — COMPLETE

`games/balatro/bonds/contributions.py` owns keyed contribution normalization.

## Phase D — Bond strategic value — COMPLETE AS BASELINE

`games/balatro/bonds/strategic_value.py` remains the frozen symbolic baseline.

## Phase E — Sparse relationships / motifs — COMPLETE AS BASELINE/FEATURES

Relationships and motifs remain deliberately sparse; unlisted pairs are neutral.

## Phase F — `BuildValue(state)` — COMPLETE AS BASELINE

Deterministic whole-build baseline retained.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE AS BASELINE

Retained for deterministic comparison/projection tests, not as final learned-policy authority.

## Phase H — Canonical strategic decision-owner integration — COMPLETE

Canonical acquisition, replacement, pack, consumable, voucher, shop-arbitration, and execution ownership remains the action interface foundation for RL.

## Phase I — Tactical exploitation — COMPLETE

Representative deterministic proofs cover:

1. Burnt Joker first-discard hand leveling.
2. Hanged Man / permanent deck thinning.
3. Steel / Baron / Mime held-card preservation and exploitation.

## Phase J — Deterministic end-to-end proofs — COMPLETE

Representative hand-leveling, thinning, and held-card paths are green and become simulator parity assets.

## Phase K — Legacy strategic migration cleanup — COMPLETE

Rejected persistent strategy-controller architecture removed while preserving canonical mechanics/economics/health/D1/D2/D9/D14/boss/runtime ownership.

Important retained semantic corrections include Midas→Vampire trigger order, persistent enhancement feed, renewable future-feed distinction, debuffed Gold cards, Midas scoring-face requirements, Stone-card rank identity, and Planet observed/exotic-hand evidence semantics.

---

# Phase L — Live correctness stabilization before RL environment freeze — COMPLETE

## L1 — September 2 baseline — COMPLETE

Batch: `balatro-20260902T200815Z-dba5db6f`

Outcomes:

- attempt 001: lost Ante 7 boss The House, `49,834 / 70,000`;
- attempt 002: lost Ante 3 boss The Needle, `770 / 2,000`;
- attempt 003: lost Ante 2 boss The Club, `1,404 / 1,600`.

Repairs included Baron motif false positive, Flash Card D2 authority, Throwback realization, Card Sharp stale history, D14 attribution, and unsupported Director's Cut/Retcon boss-reroll fail-closed behavior.

## L2 — September 3 post-repair batch — COMPLETE / INSPECTED

Batch: `balatro-20260903T094415Z-87fd8720`

Outcomes:

- attempt 001: lost Ante 1 boss The Club, `272 / 600`;
- attempt 002: lost Ante 3 boss The Water, `2,512 / 4,000`;
- attempt 003: lost Ante 7 Big Blind, `21,908 / 52,500`.

Repairs included the D14 deterministic-policy timing blind spot and The Sun optional-proof/D1 budget starvation.

## L3 — RL environment freeze gate — COMPLETE

Completion evidence (September 3, 2026):

- versioned environment contract frozen as `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`;
- training-exposed actions fail closed unless canonical legality and execution ownership are declared;
- unsupported boss reroll is explicitly unavailable;
- translator phase-boundary regression covers stale-round reset and active-round preservation;
- focused L3 CI run `33758680261`: `1223 passed, 1594 deselected`;
- 7 preceding Linux-only failures were classified as environment-only `APPDATA` construction failures and repaired without test skips.

L3 exit criteria are satisfied. Do not request another open-ended live batch and do not resume symbolic strategy tuning.

---

# Phase R — Headless Balatro environment — ACTIVE

**Purpose:** build a fast deterministic training environment reproducing the canonical modeled Red Deck / White Stake surface without the live Windows/Balatro UI.

The environment must be treated as game truth only after exactness/parity gates pass.

## R0 — Environment architecture and ownership — COMPLETE

Completion evidence (September 3, 2026):

- `games/balatro/env/` defines the versioned `r0-v1` environment boundary;
- `reset`, `step`, and `legal_actions` implement the target Gym-like API while delegating exact transitions to a deterministic backend;
- observations wrap/copy canonical `BalatroState` rather than creating a competing state model;
- strategic actions alias the frozen `l3-v1` contract and fail closed outside the training-exposed surface;
- single-agent turn ownership, Ante-8 terminal semantics, serialization/restore ownership, and illegal-action rejection are explicit;
- deterministic CI run `33760179448`: `1233 passed, 1594 deselected`.

The legacy `games/balatro/environment.py` toy/stub environment is **not** authoritative RL environment truth. The authoritative headless work lives under `games/balatro/env/`.

## R1 — State transition engine — ACTIVE

### Current progress — September 4, 2026

The first deterministic R1 transition slice is implemented. Current work remains the acquisition-semantics audit and incremental exact expansion of shop acquisitions.

The generic-acquisition finding remains authoritative:

- acquisitions cannot be modeled generically as only `inventory append + money subtraction`;
- canonical `BalatroState` owns mutable capacity/resource state such as hand size, next-round hand/discard allowances, Joker slots, and consumable slots;
- some Jokers/vouchers change those values immediately or persistently;
- generic `BUY_JOKER` / `BUY_VOUCHER` therefore remain incorrect unless the individual immediate effects are owned exactly;
- unsupported/inexact acquisition actions must be absent from `legal_actions()` and must reject on direct execution;
- Joker editions remain fail-closed because edition semantics, especially Negative slot effects, are not yet owned exactly in R1;
- `SELL_JOKER` is still outside the frozen training surface, so inverse lifecycle semantics are not yet part of the active R1 shop slice.

### Exact R1 shop behavior currently implemented

`ShopTransitionEngine` currently exposes only deterministic acquisitions whose semantics have been explicitly audited.

Always supported in an active shop when otherwise legal:

- `END_SHOP`;
- exact held-consumable purchase when capacity, price, and affordability are exact.

Joker purchase is identity-gated. The current audited scoring/state-safe set includes:

- `FlatMultJoker`;
- `AbstractJoker`;
- `AcrobatJoker`;
- `BannerJoker`;
- `BaronJoker`;
- `BlackboardJoker`;
- `BlueJoker`;
- `EvenStevenJoker`;
- `FibonacciJoker`;
- `HalfJoker`;
- `MysticSummitJoker`;
- `OddToddJoker`;
- `PhotographJoker`;
- `RaisedFistJoker`;
- `ScholarJoker`;
- `SmileyFaceJoker`;
- `WalkieTalkieJoker`;
- `JugglerJoker`.

Additional exact resource/capacity-sensitive Joker rules currently implemented:

- **Juggler**: purchase applies `hand_size += 1` once;
- **Stuntman**: purchase applies `hand_size -= 2`; acquisition remains fail-closed when current authoritative hand size is below 2 rather than inventing negative-capacity semantics;
- **Drunkard**: purchase applies `round_reset_discards += 1`, but only when the next-round discard allowance was authoritatively observed;
- **Troubadour**: purchase applies `hand_size += 2` and `round_reset_hands -= 1`, but only when the next-round hand allowance was authoritatively observed and is at least 1.

Current price semantics are fail-closed:

- price must exist as an exact integer;
- booleans, strings, floats, missing values, invalid mappings, and negative prices are not treated as affordable purchases;
- legality and direct transition execution agree on the same price/slot boundary.

Still fail-closed:

- unknown/generic Joker identities;
- all Joker editions;
- generic voucher acquisition;
- booster-pack opening;
- stochastic acquisition/generation paths that require R2 RNG ownership;
- any acquisition whose immediate persistent effect has not been audited.

### Current Troubadour / next-round-hands checkpoint

This is the exact code state at the roadmap update:

Completed and pushed:

1. `BalatroState` now canonically owns:
   - `round_reset_hands_observed: bool`;
   - `round_reset_hands: int`.
2. `BalatroState.copy()` preserves both fields.
3. `HeadlessRunState` validates the observed next-round hand allowance as an exact nonnegative integer.
4. `ShopTransitionEngine` enables Troubadour only when `round_reset_hands_observed` is true and `round_reset_hands >= 1`.
5. Troubadour purchase applies the exact immediate R1-owned pair:
   - `hand_size += 2`;
   - `round_reset_hands -= 1`.
6. Dedicated deterministic tests were added in `tests/balatro/test_balatro_env_r1_troubadour.py` covering:
   - state-copy preservation;
   - type/range validation;
   - fail-closed behavior when the reset-hand baseline is unobserved;
   - fail-closed behavior at zero next-round hands;
   - exact isolated acquisition when an authoritative baseline exists.

Latest code commits for this slice:

```text
d503f26  feat(balatro): own next-round hand allowance
f990b98  feat(balatro): enable exact Troubadour acquisition
f172334  test(balatro): cover exact Troubadour R1 acquisition
```

Not yet completed at this checkpoint:

- `DefaultBalatroStateTranslator` does **not yet** populate `round_reset_hands_observed` / `round_reset_hands` from live payloads;
- `LiveMemoryBalatroObserver` does **not yet** expose `G.GAME.round_resets.hands` into the public snapshot;
- corresponding translator/live-observer regression tests are still pending;
- therefore real live-derived SHOP states do not yet satisfy Troubadour's authoritative next-round-hand gate automatically;
- the just-pushed Troubadour slice has not yet been declared CI-green in this roadmap update.

The next-round live source has been identified and should be used rather than inferred:

```text
G.GAME.round_resets.hands
```

This is the exact analogue of the already-owned `G.GAME.round_resets.discards` path used for Drunkard.

### R1 immediate objective

Finish the live/public ownership path for the next-round hands baseline, then continue the acquisition inventory. Do not expose an acquisition merely because the live UI can click it.

Immediate sequence from this exact checkpoint:

1. wire `G.GAME.round_resets.hands` through `LiveMemoryBalatroObserver` as public snapshot fields;
2. wire those fields through `DefaultBalatroStateTranslator` into canonical `BalatroState`;
3. add observer + translator tests proving observed, missing, zero, and invalid-value behavior is fail-closed/canonical;
4. run focused deterministic R1 tests/CI and only then mark the Troubadour live-observation path green;
5. continue auditing the next acquisition identity/resource modifier;
6. keep generic vouchers, packs, editions, unknown Jokers, and unaudited acquisitions fail-closed;
7. broaden the legal R1 surface only after each transition is exact;
8. then continue remaining transition categories and R2/R3 work.

For every newly enabled Joker/voucher/consumable/card acquisition:

1. verify affordability and slot legality;
2. apply the exact inventory transition;
3. apply all immediate persistent state modifiers;
4. update capacities/resources/counters affected immediately;
5. preserve canonical ownership and public-state semantics;
6. add deterministic transition tests;
7. expose the action through `legal_actions()` only after the transition is exact.

Required R1 state categories remain:

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

- `reset(seed)` owns the environment RNG;
- deterministic shop generation, draw, packs, boss selection, and modeled random effects;
- no unrelated global RNG in transitions;
- replay metadata records seed/action sequence;
- identical environment version + seed + actions produce identical trajectories;
- serialization/restoration preserves the next RNG result.

## R3 — Typed action vocabulary — PARTIALLY FROZEN / IMPLEMENTATION CONTINUES WITH R1

Initial strategic action classes should cover only exact supported production actions, including as applicable:

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

Every training-visible action must have:

- stable type/id;
- required parameters;
- deterministic legality predicate;
- deterministic exact transition;
- serialization representation;
- training-mask representation.

Unsupported/inexact actions are absent, not assigned arbitrary low value.

## R4 — Deterministic tactical bridge — NOT STARTED

First curriculum will reuse existing deterministic D1/D9/tactical owners for hand-level play while RL controls strategic boundaries. Tactical trajectories must still be logged for parity/debugging.

## R5 — Live/simulator parity harness — NOT STARTED

Priority fixtures include ordinary shop purchase/hold/end-shop, Joker replacement, reroll, voucher purchase/rejection, pack paths, blind skip, ordinary blind clear, boss restrictions, Card Sharp reset, Throwback skip counter, Baron held-card state, The Sun path, and economy/interest transitions.

## R6 — Environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead after semantics are correct. Do not trade away correctness for speed without an explicit parity record.

### Phase R exit criteria

- deterministic reset/step API exists;
- all initial strategic actions have exact legality + execution tests;
- Red/White run can proceed reset→terminal entirely headlessly;
- fixed-seed replay is deterministic;
- representative live parity fixtures are green;
- throughput supports automated training experiments;
- environment version is stored in trajectory metadata.

---

# Phase O — Observation and action encoding — NOT STARTED

Create versioned observation/action schemas with no hidden-information leakage. Encode public run context, Jokers, deck structure, visible offers, capacities, counters, and optional Bond/mechanics features. Illegal actions must have zero probability after masking.

Exit requires deterministic encode/decode, complete legal masking, and model-ready tensors without ad-hoc training feature extraction.

---

# Phase B0 — RL baseline infrastructure — NOT STARTED

1. random legal strategic baseline;
2. frozen symbolic/Bond baseline in the same headless environment;
3. stable trajectory format including environment/schema versions, seed, step, phase, mask, selected action, reward, termination, and model diagnostics where applicable.

---

# Phase P — PPO strategic learner — NOT STARTED

Build a modest masked policy/value network, parallel rollout collector, GAE/returns, PPO update, reproducible checkpointing, and terminal-win reward baseline.

Primary terminal reward baseline:

```text
Ante 8 cleared: +1
run lost:       0
```

Any shaping must be explicitly configured and validated against actual Ante-8 success.

---

# Phase C0 — Curriculum and sample efficiency — NOT STARTED

Initial RL controls strategic shop/build/economy decisions while deterministic tactical owners resolve hand play. Curriculum may expand through packs, vouchers, rerolls, skips, consumable timing, and later optional tactical RL.

Full fresh Ante-1 evaluation remains authoritative even if intermediate-state curriculum is used.

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

Always retain terminal-only reward as reference. Reject reward shaping that produces high shaped return without corresponding Ante-8 success.

---

# Phase T — Training scale-up — NOT STARTED

Scale parallel rollout collection after the environment/training pipeline is stable. Record code commit, environment/schema versions, model/reward/PPO config, workers, seeds, steps, and evaluation protocol for every meaningful training run.

---

# Phase V — Simulator-to-live learned-policy validation — NOT STARTED

Freeze a promoted checkpoint and use the same observation encoder/action decoder live and headlessly. Canonical live legality remains the safety boundary. Classify simulator/live mismatches before changing policy behavior.

---

# Phase Q — Red/White learned competence gate — NOT STARTED

Controlling metric:

```text
P(clear Ante 8 | Red Deck, White Stake, normal mode)
```

Required evidence includes large held-out simulated evaluation, confidence intervals, random and symbolic baseline comparisons, multiple training seeds, live validation on a frozen checkpoint, and no unresolved high-impact parity defect.

---

# Phase X — Optional full tactical RL — NOT REQUIRED FOR INITIAL GATE

Only begin if strategic-only RL with deterministic tactical execution plateaus for reasons attributable to hand/discard decisions.

---

# Phase M — Post-RL symbolic cleanup — NOT STARTED

Do not delete the symbolic/Bond baseline before Phase Q. After learned authority is proven, keep one canonical learned strategic owner, one deterministic mechanics/legality boundary, and only optional Bond diagnostics/features.

---

# Phase N — Broader competence — NOT STARTED

Only after Red/White success: additional decks, higher stakes, broader actions such as boss reroll if desired, endless objectives, tactical RL, and wider framework integration.

---

# Testing and reproducibility contract

Use deterministic tests for mechanics, transitions, legality, phase boundaries, RNG, serialization, encodings, masks, parity, checkpoint loading, and deterministic inference.

Use statistical rollout evaluation for win rate, learning curves, model comparisons, ablations, reward validation, and hyperparameter comparison.

Every promoted model must record:

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
R1 first deterministic shop slice                 IMPLEMENTED
R1 acquisition semantics audit                    ACTIVE — CURRENT WORKSTREAM
Exact scoring-safe Joker allowlist                IMPLEMENTED INCREMENTALLY
Exact Juggler acquisition                         IMPLEMENTED
Exact Stuntman acquisition                        IMPLEMENTED WITH CAPACITY GUARD
Exact Drunkard acquisition                        IMPLEMENTED WITH OBSERVED RESET-DISCARD GATE
Canonical next-round hand allowance               IMPLEMENTED IN BalatroState
Exact Troubadour headless acquisition             IMPLEMENTED WITH OBSERVED RESET-HAND GATE
Troubadour deterministic tests                    ADDED
Live observer round_reset_hands path              NOT YET WIRED
Translator round_reset_hands path                 NOT YET WIRED
Troubadour slice focused CI                       NOT YET DECLARED GREEN
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
f1723345b76f972a48562bd36bcd7a373655938c
```

Latest functional R1 commits immediately before the roadmap update:

```text
d503f26  feat(balatro): own next-round hand allowance
f990b98  feat(balatro): enable exact Troubadour acquisition
f172334  test(balatro): cover exact Troubadour R1 acquisition
```

---

# Exact next development action

**Continue R1. Do not move to PPO/observation training work yet.**

Immediate order from the current checkpoint:

1. expose public `G.GAME.round_resets.hands` in `LiveMemoryBalatroObserver` using the same fail-closed pattern as `round_resets.discards`;
2. translate `round_reset_hands_observed` / `round_reset_hands` into canonical `BalatroState` in `DefaultBalatroStateTranslator`;
3. add deterministic observer/translator regressions for the next-round hand allowance;
4. run focused deterministic R1 tests and CI and verify the Troubadour slice green;
5. continue the acquisition-semantics inventory for the next unaudited training-relevant Joker/resource effect;
6. keep generic Joker/voucher buys, editions, packs, and other unsupported acquisitions fail-closed wherever immediate semantics are not exact;
7. implement exact immediate acquisition modifiers incrementally using canonical mechanics/owners;
8. retain deterministic legality + direct-transition rejection tests so unsupported acquisitions cannot leak through either path;
9. broaden the legal R1 action surface only after each transition is exact;
10. then continue remaining state-transition categories and R2/R3 work;
11. add R5 parity fixtures before declaring the environment authoritative for training.

The next code written should therefore be **live/public next-round-hands ownership for the already-implemented Troubadour R1 transition**, followed by continued exact acquisition/state-transition work. It should **not** be Bond tuning and **not** PPO.

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
      ├─ scoring-safe Joker allowlist               ✓ incremental
      ├─ Juggler / Stuntman capacity ownership      ✓
      ├─ Drunkard next-round discard ownership      ✓
      └─ Troubadour next-round hand ownership       ← HEADLESS DONE; LIVE PATH NEXT
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
