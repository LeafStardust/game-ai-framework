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

Repairs included Baron motif false positive, Flash Card D2 authority, Throwback realization, Card Sharp stale history, D14 attribution, and unsupported Director's Cut/Retcon boss-reroll fail-closed behavior.

## L2 — September 3 post-repair batch

Batch `balatro-20260903T094415Z-87fd8720`:

- attempt 001 lost Ante 1 boss The Club: `272 / 600`;
- attempt 002 lost Ante 3 boss The Water: `2,512 / 4,000`;
- attempt 003 lost Ante 7 Big Blind: `21,908 / 52,500`.

Repairs included D14 deterministic-policy timing and The Sun optional-proof/D1 budget starvation.

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

## R1 — State transition engine — ACTIVE

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

Previously admitted scoring/state-safe set:

```text
FlatMultJoker AbstractJoker AcrobatJoker BannerJoker BaronJoker
BlackboardJoker BlueJoker EvenStevenJoker FibonacciJoker HalfJoker
MysticSummitJoker OddToddJoker PhotographJoker RaisedFistJoker
ScholarJoker SmileyFaceJoker WalkieTalkieJoker JugglerJoker
```

Passive hand-rule group:

```text
FourFingersJoker PareidoliaJoker ShortcutJoker SmearedJoker SplashJoker
```

CI `33782526550`: `1310 passed, 1594 deselected`.

Initial hand-shape score-only group:

```text
JollyJoker SlyJoker ZanyJoker WilyJoker TheDuoJoker
```

CI `33782754111`: `1320 passed, 1594 deselected`.

Pair/Straight/Flush score-only expansion:

```text
CrazyJoker DeviousJoker DrollJoker CraftyJoker MadJoker CleverJoker
```

CI `33783865698`: `1332 passed, 1594 deselected`.

Hand-shape xMult expansion:

```text
TheTrioJoker TheFamilyJoker TheOrderJoker TheTribeJoker
```

CI `33784097107`: `1340 passed, 1594 deselected`.

Suit-scoring expansion:

```text
GreedyJoker LustyJoker WrathfulJoker GluttonousJoker
```

CI `33784381489`: `1348 passed, 1594 deselected`.

Conditional-scoring expansion:

```text
ScaryFaceJoker ArrowheadJoker OnyxAgateJoker FlowerPotJoker SeeingDoubleJoker
```

CI `33785203157`: `1358 passed, 1594 deselected`.

Static public-state scoring expansion:

```text
JokerStencil ShootTheMoonJoker TribouletJoker
```

CI `33785485082`: `1364 passed, 1594 deselected`.

Money-scoring expansion:

```text
BullJoker BootstrapsJoker
```

CI `33786958116`: `1370 passed, 1594 deselected`.

Retrigger-only scoring expansion:

```text
DuskJoker HackJoker HangingChadJoker MimeJoker SockAndBuskinJoker
```

These effects are contained within the validated hand-scoring projection and introduce no acquisition-time persistent mutation.

- implementation `3abedb428add794d2d16f4232e43f386ddb272c3`;
- tests `0b4a681dbd4c83231d2d1432975a2cf89de2e107`;
- CI `33787354303`: `1380 passed, 1594 deselected`.

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
- live observer canonical-sorts `G.playing_cards` before exposure and never exposes draw order;
- `BalatroState.owned_deck` remains `None` when permanent ownership is unobserved/inexact;
- `DefaultBalatroStateTranslator` now translates owned cards all-or-nothing: malformed records, invalid rank/suit/modifier values, or count mismatch make the whole `owned_deck` unavailable rather than silently shortening it;
- observed authoritative empty collection remains `[]`;
- `HeadlessRunState` rejects non-list/non-`BalatroCard` owned-deck values;
- the four acquisitions are legal only when `owned_deck` is authoritative; Erosion additionally requires a recognized starting-deck size;
- editions remain rejected;
- no acquisition-time capacity/resource mutation is introduced.

Commits:

```text
7b7699e  fix(balatro): fail closed on partial owned deck translation
17176c7  feat(balatro): gate deck scoring acquisitions on owned deck
5062f0f  test(balatro): cover exact owned deck R1 acquisitions
```

CI `33788603611`: **1401 passed, 1594 deselected**.

Observer robustness note:

- the valid live source is already `G.playing_cards`;
- lower-level `LuaJITNonGC64Decoder.array_items()` intentionally skips TValue decode failures as a general resilience behavior;
- R1 must harden completeness detection for the permanent-owned-card snapshot so a transient unreadable array element cannot masquerade as a shorter authoritative owned deck;
- until that is hardened, **never** compensate by substituting `G.deck.cards` or inferred deck averages.

### Burglar / blind-start RNG boundary — RESOLVED

**Burglar remains fail-closed through R1 and is explicitly blocked on R2 RNG ownership.**

Vanilla boundary:

1. bridge executes `G.FUNCS.select_blind` from `BLIND_SELECT`;
2. vanilla selection immediately invokes `new_round()`;
3. `new_round()` sets the blind and fires `setting_blind` Joker effects;
4. it then enters `DRAW_TO_HAND`, calls `G.deck:shuffle(...)`, and draws the initial hand.

There is no canonical live post-selection/pre-RNG action boundary. Do not invent one merely to admit Burglar.

`SELECT_BLIND` remains planned/non-training-exposed until R2 owns the entire shuffle/deal transition.

CI `33786662421`: `1366 passed, 1594 deselected`.

### Current R1 fail-closed boundary

Still blocked:

- unknown/generic Joker identities;
- all Joker editions;
- generic voucher acquisition;
- booster-pack opening;
- stochastic acquisition/generation requiring R2 RNG;
- acquisitions with unaudited persistent/lifecycle consequences;
- `SELL_JOKER` inverse lifecycle effects;
- `SELECT_BLIND` until R2 exact shuffle/deal;
- lifecycle/economy/RNG Jokers such as Chaos the Clown, Credit Card, Egg, Gros Michel/Cavendish, Ice Cream/Popcorn/Ramen, and persistent-counter Jokers until their owners exist.

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
d0ca348  feat(balatro): admit exact conditional scoring acquisitions
534c571  test(balatro): cover conditional scoring R1 acquisitions
645c0db  feat(balatro): admit exact static scoring acquisitions
b333ea2  test(balatro): cover static scoring R1 acquisitions
39ff54d  test(balatro): lock Burglar behind blind-start RNG
3a5069e  feat(balatro): admit exact money scoring acquisitions
c25940b  test(balatro): cover money scoring R1 acquisitions
3abedb4  feat(balatro): admit exact retrigger scoring acquisitions
0b4a681  test(balatro): cover retrigger scoring R1 acquisitions
7b7699e  fix(balatro): fail closed on partial owned deck translation
17176c7  feat(balatro): gate deck scoring acquisitions on owned deck
5062f0f  test(balatro): cover exact owned deck R1 acquisitions
```

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

Do not substitute averages for exact deterministic state where parity requires exactness.

---

## R2 — RNG determinism — NOT STARTED AS A COMPLETE PHASE

Requirements:

- `reset(seed)` owns environment RNG;
- deterministic shop generation, draws, packs, boss selection, modeled random effects;
- no unrelated global RNG in transitions;
- replay metadata records seed/action sequence;
- identical environment version + seed + actions produce identical trajectories;
- serialization/restoration preserves the next RNG result;
- blind-start `SELECT_BLIND` reproduces vanilla ordering: blind setup / `setting_blind` effects → deterministic shuffle → initial draw.

## R3 — Typed action vocabulary — PARTIAL / TIED TO R1 EXACTNESS

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

## R4 — Deterministic tactical bridge — NOT STARTED

Reuse existing deterministic D1/D9/tactical owners for hand-level play while RL controls strategic boundaries. Tactical trajectories remain logged for parity/debugging.

## R5 — Live/simulator parity harness — NOT STARTED

Priority fixtures: ordinary shop purchase/hold/end-shop, Joker replacement, reroll, voucher purchase/rejection, pack paths, blind skip, ordinary blind clear, boss restrictions, Card Sharp reset, Throwback skip counter, Baron held-card state, The Sun path, owned-deck composition, and economy/interest transitions.

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
R1 state transition engine                        ACTIVE
R1 acquisition semantics audit                    ACTIVE — CURRENT WORKSTREAM
Exact resource-sensitive acquisitions             Juggler/Stuntman/Drunkard/Troubadour/Merry Andy
Passive hand-rule acquisitions                    GREEN
Hand-shape score-only acquisitions                GREEN
Pair/Straight/Flush score-only expansion          GREEN — CI 33783865698
Hand-shape xMult expansion                        GREEN — CI 33784097107
Suit-scoring expansion                            GREEN — CI 33784381489
Conditional-scoring expansion                     GREEN — CI 33785203157
Static public-state scoring expansion             GREEN — CI 33785485082
Money-scoring expansion                           GREEN — CI 33786958116
Retrigger-only scoring expansion                  GREEN — CI 33787354303
Owned-deck scoring expansion                      GREEN — CI 33788603611
Owned-deck translator fail-closed semantics       GREEN
G.playing_cards decode-completeness hardening     NEXT R1 ROBUSTNESS TASK
Burglar acquisition                               FAIL-CLOSED UNTIL R2 BLIND-START RNG
SELECT_BLIND training action                      PLANNED — BLOCKED UNTIL R2 EXACT SHUFFLE/DRAW
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
5062f0f910ff4aba24646630e4dec78ea8259eb3
```

---

# Exact next development action

**Continue R1. Do not move to PPO/observation training work yet.**

Immediate order:

1. harden permanent `G.playing_cards` array completeness so a low-level unreadable TValue cannot silently become a shorter authoritative `owned_deck`;
2. keep `G.deck.cards` strictly separate from permanent owned-deck truth;
3. retain translator all-or-nothing owned-card validation and its malformed/count-mismatch regressions;
4. continue exact deck/card-zone ownership and inventory/lifecycle auditing after that robustness gate;
5. admit acquisitions only when purchase plus every persistent consequence is owned;
6. keep lifecycle-dependent Jokers blocked until their lifecycle transitions exist;
7. keep Burglar/`SELECT_BLIND` blocked until R2 owns vanilla blind-start shuffle/draw RNG;
8. keep generic Joker/voucher buys, editions, packs, and unknown acquisitions fail-closed;
9. finish deterministic R1 categories, then R2/R3;
10. add R5 parity before treating the environment as authoritative for training.

The next code is therefore **R1 live-owned-deck completeness hardening followed by exact remaining state-transition work**. It is **not** Bond tuning and **not** PPO.

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
  └─ acquisition/state semantics audit             ← ACTIVE
      ├─ resource-sensitive capacity ownership      ✓ incremental
      ├─ passive/scoring/retrigger acquisitions     ✓ expanding
      ├─ permanent owned-deck scoring               ✓
      ├─ live owned-deck completeness hardening     ← NEXT
      ├─ Burglar / blind-start boundary             ✓ classified → R2 dependency
      └─ lifecycle-dependent acquisitions           ← FAIL-CLOSED UNTIL OWNED
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
```

Controlling implementation question:

> **Does the environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
