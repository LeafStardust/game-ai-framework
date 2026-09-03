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
- Model checkpoints are artifacts, not source-of-truth strategy definitions.
- Unsupported or inexact actions stay absent from the training mask; do not assign them arbitrary low value.
- Do not reintroduce legacy multi-attempt CLI conventions such as `--one`, `--three`, or `--five`; the canonical attempt-count interface is the newer attempt-count form.

---

# Primary objective

**Red Deck / White Stake, normal mode: maximize probability of clearing Ante 8.**

Controlling metric:

```text
P(clear Ante 8 | Red Deck, White Stake, normal mode)
```

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

Training:

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

# Bond-system authority

Retain as deterministic baseline / optional features:

- canonical 46-Bond vocabulary;
- mechanics-to-Bond contributions;
- realization semantics;
- sparse relationships/motifs;
- deterministic feature tests and telemetry;
- frozen `BuildValue` / `StrategyDelta` baseline.

Do **not** return to manual Bond coefficient tuning, persistent named strategy FSMs, prescription plumbing, or one-off live-loss thresholds as the primary competence path.

Planned later observation ablation:

```text
RAW
RAW+BOND
BOND-HEAVY diagnostic only if useful
```

---

# Completed foundation — Phases A–K

- **A** Bond vocabulary — COMPLETE.
- **B** mechanical descriptors — COMPLETE; `games/balatro/mechanics.py` canonical.
- **C** mechanics→Bond contributions — COMPLETE.
- **D** Bond strategic value — COMPLETE AS BASELINE.
- **E** sparse relationships/motifs — COMPLETE AS BASELINE/FEATURES.
- **F** `BuildValue(state)` — COMPLETE AS BASELINE.
- **G** projected-state `StrategyDelta(candidate)` — COMPLETE AS BASELINE.
- **H** canonical strategic decision-owner integration — COMPLETE.
- **I** tactical exploitation proofs — COMPLETE: Burnt Joker, Hanged Man/thinning, Steel/Baron/Mime.
- **J** deterministic end-to-end proofs — COMPLETE.
- **K** legacy strategic migration cleanup — COMPLETE.

Retained semantic corrections include Midas→Vampire trigger order, persistent enhancement feed, renewable future-feed distinction, debuffed Gold cards, Midas scoring-face requirements, Stone-card rank identity, and Planet observed/exotic-hand evidence semantics.

---

# Phase L — Live correctness stabilization — COMPLETE

## L1 — September 2 baseline

Batch `balatro-20260902T200815Z-dba5db6f`:

- attempt 001 lost Ante 7 boss The House: `49,834 / 70,000`;
- attempt 002 lost Ante 3 boss The Needle: `770 / 2,000`;
- attempt 003 lost Ante 2 boss The Club: `1,404 / 1,600`.

## L2 — September 3 post-repair batch

Batch `balatro-20260903T094415Z-87fd8720`:

- attempt 001 lost Ante 1 boss The Club: `272 / 600`;
- attempt 002 lost Ante 3 boss The Water: `2,512 / 4,000`;
- attempt 003 lost Ante 7 Big Blind: `21,908 / 52,500`.

## L3 — environment freeze gate

- `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`;
- training actions fail closed unless legality/execution ownership is declared;
- boss reroll unsupported/unavailable;
- translator phase-boundary regressions cover stale-round reset / active-round preservation;
- Linux `APPDATA` construction issues repaired without skips;
- CI `33758680261`: `1223 passed, 1594 deselected`.

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
- explicit single-agent turn ownership, Ante-8 terminal semantics, serialization/restore, illegal-action rejection;
- CI `33760179448`: `1233 passed, 1594 deselected`.

Legacy `games/balatro/environment.py` remains toy/stub code and is not authoritative RL environment truth.

---

## R1 — State transition engine — SUBSTANTIALLY COMPLETE / OPEN LIFECYCLE WORK REMAINS

### Core acquisition rule

Generic acquisition is **not** `append inventory + subtract money`.

`BalatroState` owns mutable capacities/resources and public gameplay state. Some Jokers/vouchers mutate those immediately or later. Therefore:

- `BUY_JOKER` is identity/state gated;
- generic `BUY_VOUCHER` remains fail-closed;
- unsupported/inexact actions are absent from `legal_actions()` and reject on direct execution;
- all Joker editions remain fail-closed, especially Negative because it changes Joker capacity;
- `SELL_JOKER` remains outside the frozen training surface until inverse lifecycle effects are exact;
- packs remain blocked until exact pack state + R2 RNG ownership exist.

### Exact generic shop behavior

Always supported in active shop when otherwise legal:

- `END_SHOP`;
- held-consumable purchase when capacity, price, and affordability are exact.

Price semantics fail closed:

- exact integer only;
- bool/string/float/missing/invalid mapping/negative rejected;
- legality and direct transition execution share the same boundary.

### Exact resource/capacity-sensitive acquisitions

- **Juggler**: `hand_size += 1` once.
- **Stuntman**: `hand_size -= 2`; blocked if current authoritative hand size < 2.
- **Drunkard**: `round_reset_discards += 1`; requires observed reset-discard baseline.
- **Troubadour**: `hand_size += 2`, `round_reset_hands -= 1`; requires observed reset-hands baseline and >=1.
- **Merry Andy**: `hand_size -= 1`, `round_reset_discards += 3`; requires observed reset-discards and hand size >=1.

Live next-round hand ownership:

- `BalatroState` owns/copies `round_reset_hands_observed` / `round_reset_hands`;
- `LiveMemoryBalatroObserver` reads public `G.GAME.round_resets.hands`;
- translator accepts only valid exact nonnegative integer values;
- CI `33781164005`: `1297 passed, 1594 deselected`.

Merry Andy CI `33781461393`: `1300 passed, 1594 deselected`.

### Exact inventory-only scoring/rule acquisitions

Audited and admitted groups:

```text
FlatMultJoker AbstractJoker AcrobatJoker BannerJoker BaronJoker
BlackboardJoker BlueJoker EvenStevenJoker FibonacciJoker HalfJoker
MysticSummitJoker OddToddJoker PhotographJoker RaisedFistJoker
ScholarJoker SmileyFaceJoker WalkieTalkieJoker JugglerJoker

FourFingersJoker PareidoliaJoker ShortcutJoker SmearedJoker SplashJoker
JollyJoker SlyJoker ZanyJoker WilyJoker TheDuoJoker
CrazyJoker DeviousJoker DrollJoker CraftyJoker MadJoker CleverJoker
TheTrioJoker TheFamilyJoker TheOrderJoker TheTribeJoker
GreedyJoker LustyJoker WrathfulJoker GluttonousJoker
ScaryFaceJoker ArrowheadJoker OnyxAgateJoker FlowerPotJoker SeeingDoubleJoker
JokerStencil ShootTheMoonJoker TribouletJoker
BullJoker BootstrapsJoker
DuskJoker HackJoker HangingChadJoker MimeJoker SockAndBuskinJoker
```

Relevant green gates:

```text
33782526550  1310 passed, 1594 deselected
33782754111  1320 passed, 1594 deselected
33783865698  1332 passed, 1594 deselected
33784097107  1340 passed, 1594 deselected
33784381489  1348 passed, 1594 deselected
33785203157  1358 passed, 1594 deselected
33785485082  1364 passed, 1594 deselected
33786958116  1370 passed, 1594 deselected
33787354303  1380 passed, 1594 deselected
```

### Permanent owned-deck scoring expansion — GREEN

Affected Jokers:

```text
SteelJoker
StoneJoker
DriversLicenseJoker
ErosionJoker
```

Authoritative semantics:

- `G.playing_cards` is the live public permanent owned-card collection;
- `G.deck.cards` is **not** a substitute because it represents currently drawable composition/future physical deck order;
- `BalatroState.owned_deck` remains `None` when permanent ownership is unobserved/inexact;
- translator performs all-or-nothing owned-card translation;
- malformed records, invalid rank/suit/modifier values, or count mismatch make `owned_deck` unavailable rather than silently shortening it;
- observed authoritative empty collection remains `[]`;
- the four acquisitions are legal only when `owned_deck` is authoritative; Erosion additionally requires a recognized starting-deck size;
- editions remain rejected.

Commits:

```text
7b7699e  fix(balatro): fail closed on partial owned deck translation
17176c7  feat(balatro): gate deck scoring acquisitions on owned deck
5062f0f  test(balatro): cover exact owned deck R1 acquisitions
```

CI `33788603611`: **1401 passed, 1594 deselected**.

### `G.playing_cards` decode-completeness hardening — COMPLETE / GREEN

Problem resolved:

- general LuaJIT array decoding may tolerate an unreadable TValue by skipping it;
- permanent owned-deck truth cannot tolerate that because a partial 51/52-card read can look like a legitimately thinned deck;
- authoritative `G.playing_cards` reads now use a strict all-or-nothing path;
- ordinary tolerant array reads elsewhere remain unchanged;
- an unreadable owned-card entry now makes the permanent deck observation unavailable rather than shortened;
- no fallback to `G.deck.cards` is permitted.

Functional checkpoint:

```text
fc124f0  strict permanent-deck observer completeness
```

CI `33789894797`: **1405 passed, 1594 deselected**.

### Private headless card-zone hardening — COMPLETE / GREEN

`HeadlessRunState` now validates private simulator card zones rather than trusting arbitrary caller values:

```text
draw_pile
discard_pile
played_pile
```

Each must be an exact `list[BalatroCard]`.

Commits:

```text
b63f091  validate private headless card zones
6425478  cover private headless card-zone validation
```

Deterministic branch gate after this slice: **1412 passed, 1594 deselected**.

### Remaining deterministic container validation — COMPLETE / GREEN

Without inventing future R2 schemas:

- seed is restricted to `str | int`, bool rejected;
- tags are `list[str]`;
- pack choices must at least be a list until exact pack semantics are owned.

Commit:

```text
a9593a0  tighten deterministic headless containers
```

CI `33790592775`: **1424 passed, 1594 deselected**.

### Burglar / blind-start boundary — RESOLVED AS R2 DEPENDENCY

**Burglar remains fail-closed until exact blind-start lifecycle is owned.**

Vanilla boundary:

1. bridge executes `G.FUNCS.select_blind` from `BLIND_SELECT`;
2. vanilla selection immediately invokes `new_round()`;
3. `new_round()` sets the blind and fires `setting_blind` Joker effects;
4. it then enters `DRAW_TO_HAND`, calls `G.deck:shuffle(...)`, and draws the initial hand.

There is no canonical live post-selection/pre-RNG action boundary. Do not invent one merely to admit Burglar.

CI `33786662421`: `1366 passed, 1594 deselected`.

### Current R1 fail-closed boundary

Still blocked unless/until exact lifecycle owners are implemented:

- unknown/generic Joker identities;
- all Joker editions;
- generic voucher acquisition;
- booster-pack opening;
- stochastic acquisition/generation requiring R2 RNG;
- unaudited persistent/lifecycle consequences;
- `SELL_JOKER` inverse lifecycle effects;
- lifecycle/economy/RNG Jokers such as Chaos the Clown, Credit Card, Egg, Gros Michel/Cavendish, Ice Cream/Popcorn/Ramen, and persistent-counter Jokers.

R1 should no longer be treated as the sole active phase: deterministic state hardening has reached the point where exact stochastic evolution is the blocking dependency, so **R2 is now active in parallel with remaining lifecycle-specific R1 work**.

---

## R2 — RNG determinism — ACTIVE

### R2.1 — Balatro/LuaJIT RNG primitive — IMPLEMENTED / GREEN

Do **not** use Python `random` semantics.

Audited runtime stack:

```text
Balatro pseudohash / pseudoseed / pseudorandom helpers
        ↓
LuaJIT math.randomseed / math.random
        ↓
combined Tausworthe generator
```

Implemented:

- vanilla keyed pseudoseed node progression;
- LuaJIT combined Tausworthe draws;
- inclusive integer draw semantics;
- independent keyed queues;
- exact serializable RNG node state;
- bit-preserving snapshot/restore;
- pinned deterministic reference vectors.

Commits:

```text
2e61cd8  exact Balatro/LuaJIT RNG primitives
290ff11  pinned RNG reference vectors
```

CI `33791671797`: **1432 passed, 1594 deselected**.

### R2.2 — Balatro pseudoshuffle — IMPLEMENTED / GREEN

Vanilla semantics reproduced:

- `pseudoshuffle(cards, pseudoseed(key))` advances the keyed pseudoseed **once**;
- one LuaJIT RNG stream then drives all Fisher–Yates swaps;
- this is **not** equivalent to repeated keyed `random()` calls;
- RNG snapshot/restore preserves the next shuffle result.

Commits:

```text
246f442  implement exact Balatro pseudoshuffle semantics
d9662c6  pin shuffle vectors and restore behavior
```

CI `33791916289`: **1435 passed, 1594 deselected**.

### R2.3 — Playing-card creation / pre-shuffle sort order — IMPLEMENTED, CI SELECTION FIX REQUIRED

Why this exists:

Vanilla `CardArea:shuffle` sorts the card array by each card's monotonic `sort_id` before calling `pseudoshuffle`. Public `BalatroCard` intentionally does not expose a synthetic engine `sort_id`.

Audited exact reconstruction cases:

1. **Live modified decks**: every permanent playing card has a unique exact integer `playing_card` id (`BalatroCard.live_id`). Both `sort_id` and `playing_card` increase with playing-card creation, so relative playing-card order can be recovered by unique integer `live_id`.
2. **Fresh vanilla base deck**: exact initial creation order is recoverable from the source game's sorted playing-card control codes when the deck is exactly the untouched one-of-each 52-card rank/suit identity set.

Fail closed for:

- duplicate live ids;
- mixed missing/noninteger live ids;
- modified card identity sets without authoritative live creation ids;
- any state where exact relative creation order cannot be proved.

The order is simulator-private. Do **not** add a fake public `sort_id` field merely for headless convenience.

Commits:

```text
e7b0bb0  feat(balatro): derive exact playing-card creation order
2a26e79  test(balatro): pin exact R2 card creation order
```

Important CI truth:

- workflow run `33792852889` succeeded with `1435 passed, 1600 deselected`;
- the six new `env_r2` card-order regressions were **deselected** because `.github/workflows/balatro-l3.yml` currently selects `env_r1` and `rng` but not `env_r2`;
- therefore this card-order slice is **implemented but not yet CI-gated**;
- do not mark R2.3 green until the workflow/test selection is repaired and the tests actually execute.

### R2.4 — Exact `SELECT_BLIND` / blind-start lifecycle — NEXT AFTER R2.3 GATE

Before exposing `SELECT_BLIND` to training, reproduce vanilla ordering as one exact action boundary:

1. blind selection/setup;
2. current-round resource reset;
3. boss/blind setup and restrictions;
4. Joker `setting_blind` effects, including Burglar;
5. canonical pre-shuffle playing-card sort;
6. `G.deck:shuffle("nr" .. ante)` equivalent via exact pseudoseed/pseudoshuffle;
7. initial draw into hand;
8. resulting public/private zone state and RNG state.

Do not create an artificial pre-RNG sub-action that does not exist in live Balatro.

### Remaining R2 requirements

- `reset(seed)` owns all environment RNG needed by modeled transitions;
- deterministic shop generation;
- deterministic pack contents/choices;
- boss selection;
- modeled random Joker/consumable effects;
- no unrelated global RNG in transitions;
- replay metadata records seed/action sequence;
- identical environment version + seed + actions produce identical trajectories;
- serialization/restoration preserves the next RNG result.

---

## R3 — Typed action vocabulary — PARTIAL / TIED TO EXACTNESS

Target strategic actions as exact ownership becomes available:

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

Every training-visible action requires stable type/id, required parameters, deterministic legality, exact transition, serialization representation, and mask representation.

`SELECT_BLIND` remains **planned/non-training-exposed** until R2.3 is CI-gated and R2.4 exact blind-start lifecycle is implemented.

---

## R4 — Deterministic tactical bridge — NOT STARTED

Reuse existing deterministic D1/D9/tactical owners for hand-level play while RL controls strategic boundaries. Tactical trajectories remain logged for parity/debugging.

## R5 — Live/simulator parity harness — NOT STARTED

Priority fixtures:

- ordinary shop purchase/hold/end-shop;
- Joker replacement;
- reroll;
- voucher purchase/rejection;
- pack paths;
- blind skip;
- ordinary blind start/clear;
- boss restrictions;
- Card Sharp reset;
- Throwback skip counter;
- Baron held-card state;
- The Sun path;
- owned-deck composition;
- economy/interest transitions;
- RNG/shuffle/initial-draw parity.

## R6 — Environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead only after semantics are correct.

### Phase R exit criteria

- deterministic reset/step API;
- all initial strategic actions have exact legality + execution tests;
- Red/White run proceeds reset→terminal entirely headlessly;
- fixed-seed replay deterministic;
- representative live parity fixtures green;
- throughput supports automated training;
- environment version stored in trajectory metadata.

---

# Later phases

## O — Observation/action encoding — NOT STARTED

Versioned public observation/action schemas, no hidden-information leakage, illegal actions probability zero after masking.

## B0 — RL baseline infrastructure — NOT STARTED

1. random legal strategic baseline;
2. frozen symbolic/Bond baseline in the same environment;
3. stable versioned trajectory format.

## P — PPO strategic learner — NOT STARTED

Initial reward reference:

```text
Ante 8 cleared: +1
run lost:        0
```

Any shaping must be explicitly configured and validated against Ante-8 success.

## C0 — Curriculum/sample efficiency — NOT STARTED

Strategic shop/build/economy control first; expand action ownership only after exact environment transitions exist.

## E0 — Evaluation framework — NOT STARTED

Separate train/dev/final held-out seeds. Mandatory comparisons:

```text
Random legal policy
Frozen symbolic/Bond baseline
Learned RAW
Learned RAW+BOND
```

Report clear rate, confidence interval, run count, ante/failure distribution, invalid actions, runtime, diagnostics.

## A0 — Bond observation ablation — NOT STARTED

Retain Bonds only if they improve sample efficiency, competence, stability, or useful interpretability.

## F0 — Reward validation — NOT STARTED

Terminal-only remains reference. Reject shaping that raises shaped return without improving Ante-8 success.

## T — Training scale-up — NOT STARTED

Record source commit, environment/schema versions, config, workers, seeds, steps, evaluation protocol.

## V — Simulator→live learned-policy validation — NOT STARTED

Freeze promoted checkpoints; same encoder/decoder live and headlessly; canonical live legality remains safety boundary.

## Q — Red/White competence gate — NOT STARTED

Required evidence: large held-out simulated evaluation, confidence intervals, baselines, multiple training seeds, live validation of frozen checkpoint, no unresolved high-impact parity defect.

## X — Optional full tactical RL — NOT REQUIRED FOR INITIAL GATE

Only if strategic-only RL plateaus for reasons attributable to hand/discard decisions.

## M — Post-RL symbolic cleanup — NOT STARTED

Do not delete symbolic/Bond baseline before Q. After learned authority is proven, retain one canonical learned strategic owner and one deterministic mechanics/legality boundary.

## N — Broader competence — NOT STARTED

Only after Red/White success: additional decks, higher stakes, broader actions, endless objectives, optional tactical RL, wider framework integration.

---

# Testing and reproducibility contract

Use deterministic tests for mechanics, transitions, legality, phase boundaries, RNG, serialization, encodings, masks, parity, checkpoint loading, deterministic inference.

Use statistical rollout evaluation for win rate, learning curves, model comparisons, ablations, reward validation, hyperparameter comparison.

Current deterministic CI command:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1"
```

**Known immediate defect:** this selection does not include generic `env_r2` test names. Fix the CI/test-selection boundary before relying on R2.3 regressions.

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

Failure classification before code changes:

1. mechanics bug;
2. state bug;
3. legality/action bug;
4. simulator/live parity bug;
5. training bug;
6. reward bug;
7. representation limitation;
8. capacity/optimization issue;
9. ordinary learned-policy error.

A single bad run is not sufficient evidence for a new hand-coded exception.

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

R1 state transition engine                        SUBSTANTIALLY COMPLETE; lifecycle work remains
R1 acquisition semantics audit                    SUBSTANTIALLY COMPLETE / fail-closed boundary retained
Exact resource-sensitive acquisitions             Juggler/Stuntman/Drunkard/Troubadour/Merry Andy
Passive/scoring/retrigger acquisitions            GREEN
Owned-deck scoring expansion                      GREEN — CI 33788603611
Owned-deck translator fail-closed semantics       GREEN
G.playing_cards decode-completeness hardening     GREEN — CI 33789894797
Private headless card-zone validation             GREEN — 1412 passed
Deterministic seed/tag/pack container checks      GREEN — CI 33790592775
Burglar acquisition                               FAIL-CLOSED UNTIL EXACT BLIND-START LIFECYCLE

R2 RNG determinism                                ACTIVE
Balatro/LuaJIT RNG primitive                      GREEN — CI 33791671797
Balatro pseudoshuffle                             GREEN — CI 33791916289
Playing-card creation-order derivation            IMPLEMENTED — CI SELECTION FIX REQUIRED
R2 card-order dedicated tests                     PRESENT BUT DESELECTED IN CI 33792852889
SELECT_BLIND training action                      PLANNED — NEXT STRUCTURAL TRANSITION AFTER R2.3 GATE

Generic/unknown Joker acquisition                 FAIL-CLOSED
Joker editions                                    FAIL-CLOSED
Generic voucher acquisition                       FAIL-CLOSED
Booster-pack opening                              FAIL-CLOSED UNTIL RNG/PACK STATE EXACT
SELL_JOKER lifecycle/inverse modifiers            NOT YET IN TRAINING SURFACE
R3 action vocabulary                              PARTIAL / TIED TO R1/R2 EXACTNESS
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
2a26e7989583b6f0160d425cf56c75be2eb7a516
```

Latest functional R1/R2 commits after the previous roadmap checkpoint:

```text
fc124f0  harden permanent G.playing_cards completeness
b63f091  validate private headless card zones
6425478  test private card-zone validation
a9593a0  tighten deterministic headless containers
2e61cd8  implement Balatro/LuaJIT RNG primitives
290ff11  pin RNG reference vectors
246f442  implement Balatro pseudoshuffle
d9662c6  pin pseudoshuffle vectors / restore behavior
e7b0bb0  derive exact playing-card creation order
2a26e79  pin R2 playing-card creation-order regressions
```

---

# Exact next development action

**Continue R2 correctness work. Do not move to PPO/observation training yet.**

Immediate order:

1. repair deterministic CI selection so `env_r2` card-order regressions actually run;
2. rerun the Balatro deterministic suite and require the R2.3 card-order tests to be selected/green;
3. store/validate exact simulator-private playing-card creation order in `HeadlessRunState` only after the derivation gate is green;
4. implement exact `SELECT_BLIND` as the real vanilla action boundary, not an invented pre-RNG split;
5. reproduce source ordering: blind setup → resource reset/restrictions → `setting_blind` Joker effects → pre-shuffle card sort → keyed pseudoshuffle → initial draw;
6. admit Burglar only when that lifecycle transition is exact;
7. keep editions, generic vouchers, packs, unknown acquisitions, sell/inverse semantics, and other lifecycle-dependent effects fail-closed until their owners exist;
8. continue R2 RNG ownership for shop generation, packs, bosses, and modeled stochastic effects;
9. complete R3 actions only as their exact transitions become available;
10. add R5 parity before treating the environment as authoritative for training.

The next code is therefore **R2 CI-gate repair followed by exact blind-start transition ownership**. It is **not** Bond tuning and **not** PPO.

---

# Progress criterion

```text
mechanical/state/action foundation                 ✓
Bond symbolic baseline                             ✓
legacy strategic-controller cleanup                ✓
live correctness stabilization                     ✓
R0 HEADLESS ENVIRONMENT ARCHITECTURE               ✓
        ↓
R1 EXACT STATE TRANSITIONS                         ✓ substantial deterministic foundation
  ├─ acquisition/state semantics                   ✓ broad exact allowlist + fail-closed remainder
  ├─ permanent owned-deck truth                    ✓
  ├─ LuaJIT owned-deck completeness                ✓
  └─ private card-zone/container validation        ✓
        ↓
R2 RNG DETERMINISM                                 ← ACTIVE
  ├─ LuaJIT/Balatro keyed RNG                      ✓
  ├─ pseudoshuffle                                 ✓
  ├─ playing-card creation order                   implemented; CI gate repair ← NEXT
  └─ exact SELECT_BLIND + initial draw             ← NEXT AFTER GATE
        ↓
R3 ACTION COMPLETION
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
```

Controlling implementation question:

> **Does the environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
