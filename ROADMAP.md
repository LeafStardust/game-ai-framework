# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

The project has pivoted from hand-authored Bond-value strategy toward reinforcement learning (RL) in a fast deterministic Balatro environment. Existing deterministic mechanics, state translation, legality, tactical execution, candidate projection, telemetry, and Bond features remain foundations/baselines. Manual Bond-weight tuning is retired as the primary competence path.

---

# Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Work Chat runs deterministic/static tests itself where available; GitHub Actions is the current authoritative test runner.
- The user runs only validation that genuinely requires the Windows/Balatro game environment.
- Preserve exact mechanics, legality, boss rules, affordability, survival, public-information boundaries, and reproducible RNG semantics.
- Prefer canonical ownership over wrappers/rescue layers.
- Training code must never silently redefine Balatro mechanics to make learning easier.
- Simulator shortcuts are allowed only when behaviorally equivalent at the modeled boundary and covered by parity tests.
- Unsupported/inexact actions stay absent from the training mask.
- Model checkpoints are artifacts, not source-of-truth strategy definitions.
- Do not reintroduce legacy multi-attempt CLI conventions such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.

Primary objective:

> **Red Deck / White Stake, normal mode: maximize probability of clearing Ante 8.**

Do **not** start PPO, observation training, or resume manual Bond tuning until the exact headless environment reaches its parity/performance gates.

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

Initial RL keeps tactical hand play deterministic while RL learns strategic run development. Full tactical RL remains optional later work.

---

# Completed foundation

## A–K — symbolic/mechanical foundation — COMPLETE AS BASELINE

Retain canonical Bond features, mechanics/state/legality, deterministic tactical owners, `BuildValue` / `StrategyDelta`, sparse relationships/motifs, and telemetry. Do not return to manual coefficient tuning as the primary competence path.

## L — live correctness stabilization — COMPLETE

Historical live batches:

```text
2026-09-02  balatro-20260902T200815Z-dba5db6f
attempt 001  Ante 7 The House   49,834 / 70,000
attempt 002  Ante 3 The Needle     770 / 2,000
attempt 003  Ante 2 The Club     1,404 / 1,600

2026-09-03  balatro-20260903T094415Z-87fd8720
attempt 001  Ante 1 The Club       272 / 600
attempt 002  Ante 3 The Water    2,512 / 4,000
attempt 003  Ante 7 Big Blind   21,908 / 52,500
```

L3 environment freeze:
- `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`
- unsupported training actions fail closed
- CI `33758680261`: `1223 passed, 1594 deselected`

Do not request another open-ended live batch at this stage.

## R0 — environment architecture/ownership — COMPLETE

- authoritative environment under `games/balatro/env/`
- version `r0-v1`
- deterministic `reset`, `step`, `legal_actions`
- canonical `BalatroState` observations
- serialization/restore and illegal-action rejection
- CI `33760179448`: `1233 passed, 1594 deselected`

Legacy `games/balatro/environment.py` is not authoritative RL environment truth.

---

# Phase R — headless Balatro environment — ACTIVE

The headless simulator is not authoritative game truth until live/simulator parity gates pass.

## R1 — deterministic state/acquisition transitions — SUBSTANTIALLY COMPLETE; OPEN LIFECYCLES REMAIN

### Acquisition contract

Generic acquisition is **not** merely append inventory + subtract money. Always fail closed unless identity/state consequences are exact.

Hard boundaries:
- all Joker editions blocked, especially Negative
- generic/unknown Joker identities blocked
- generic voucher acquisition blocked
- packs blocked until exact pack/RNG state
- `SELL_JOKER` blocked until inverse lifecycle effects are exact
- price must be an exact nonnegative integer; bool/string/float/missing/invalid fail closed

Always-supported exact shop actions currently include `END_SHOP` and exact held-consumable purchase when capacity/price/affordability are known.

### Exact resource-sensitive Joker acquisitions

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2, requires hand_size >= 2
Drunkard     round_reset_discards += 1, observed reset baseline required
Troubadour   hand_size += 2; round_reset_hands -= 1, observed baseline required
Merry Andy   hand_size -= 1; round_reset_discards += 3, observed baseline required
```

### Exact inventory-only scoring/rule acquisition families

Audited exact acquisition set includes the established flat/scoring/rule Jokers plus:

```text
FourFingers Pareidolia Shortcut Smeared Splash
Jolly Sly Zany Wily TheDuo
Crazy Devious Droll Crafty Mad Clever
TheTrio TheFamily TheOrder TheTribe
Greedy Lusty Wrathful Gluttonous
ScaryFace Arrowhead OnyxAgate FlowerPot SeeingDouble
JokerStencil ShootTheMoon Triboulet
Bull Bootstraps
Dusk Hack HangingChad Mime SockAndBuskin
```

### Permanent owned-deck scoring — GREEN

Exact deck-dependent acquisition support:

```text
Steel Joker
Stone Joker
Driver's License
Erosion
```

Authority rules:
- permanent owned deck source is `G.playing_cards`
- **never** substitute `G.deck.cards`
- translator is all-or-nothing
- malformed/count-mismatched/inexact permanent card records yield `owned_deck = None`
- low-level LuaJIT TValue failures cannot silently shorten an authoritative permanent deck

Key gates:
- CI `33788603611`: `1401 passed, 1594 deselected`
- strict `G.playing_cards` completeness CI `33789894797`: `1405 passed, 1594 deselected`

### Private deterministic state hardening — GREEN

- private `draw_pile`, `discard_pile`, `played_pile` contain only `BalatroCard`
- seed is `str | int`, bool rejected
- tags are `list[str]`
- pack choices are at least list-shaped pending exact pack ownership
- round-reset hand/discard baselines fail closed when unobserved

Card-zone gate: `1412 passed, 1594 deselected`.
Container CI `33790592775`: `1424 passed, 1594 deselected`.

---

## R2 — exact RNG + round/blind lifecycle — ACTIVE / CURRENT PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

`games/balatro/env/rng.py` owns:
- Balatro keyed pseudohash/pseudoseed progression
- LuaJIT combined Tausworthe `math.random`
- inclusive integer draws
- independent keyed queues
- bit-preserving snapshot/restore

Do not use Python `random` as a substitute.

Commits `2e61cd8`, `290ff11`.
CI `33791671797`: `1432 passed, 1594 deselected`.

### R2.2 — pseudoshuffle — GREEN

- keyed pseudoseed advances once per shuffle
- one LuaJIT RNG stream drives Fisher–Yates
- not equivalent to repeated keyed random calls

Commits `246f442`, `d9662c6`.
CI `33791916289`: `1435 passed, 1594 deselected`.

### R2.3 — playing-card creation/pre-shuffle order + headless RNG ownership — GREEN

Vanilla sorts playing cards by monotonic `sort_id` before pseudoshuffle. Public state does not expose a fake `sort_id`.

Exact reconstruction is allowed only when:
1. every owned live playing card has a unique exact integer `playing_card` id (`BalatroCard.live_id`), preserving relative playing-card creation order; or
2. the deck is the untouched one-of-each vanilla 52-card identity set with known initial creation order.

Duplicate/mixed/missing IDs or unprovable modified no-ID decks fail closed.

Key commits:

```text
e7b0bb0  derive exact playing-card creation order
2a26e79  pin card-order tests
34d88e9  include env_r2 tests in deterministic CI
7c070b2  retain private card creation order
2dc47eb  test retained order
0a7f845  own exact RNG state in HeadlessRunState
eed926e  test headless RNG ownership
```

CI `33795507133`: **1461 passed, 1594 deselected**.

### R2.4 — exact round-start shuffle/deal — GREEN FOR SUPPORTED COMPLETE DECKS

Initial pristine implementation:
- commits `61ec993`, `2d37016`
- CI `33794664514`: `1461 passed, 1594 deselected`

Pinned `TESTSEED` first hand:

```text
A Hearts
K Hearts
Q Diamonds
9 Spades
9 Clubs
5 Clubs
5 Diamonds
4 Clubs
```

Next hidden draw tail: `10 Clubs`; `nr1` node after shuffle: `0.8232194488594`.

Generalized exact owned-deck support is now implemented:

```text
fa6c40e  retain original suit nominal required by vanilla Card:get_nominal()
1f35a5c  generalize exact owned-deck round-start deal
```

`deal_supported_round_start()` supports pristine or modified complete authoritative decks only when:
- `owned_deck` is authoritative
- current deck is the complete permanent-card collection
- current deck references the same exact card objects
- retained playing-card creation order is exact
- modified cards retain exact original-suit nominal

Short exact decks use vanilla `min(deck size, hand capacity)` draw semantics. Hidden physical draw order remains private; public remaining deck is canonicalized.

### R2.5 — round-start bonus/resource lifecycle — GREEN

Private headless state owns signed exact one-shot:

```text
round_bonus_hands
round_bonus_discards
```

Source semantics:

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

Bonuses are consumed only after blind/Joker setup.

Commits `906719d`, `d727221`, `58ac3cc`, `bd07ffe`.
CI `33796637904`: **1479 passed, 1594 deselected**.

### R2.6 — `setting_blind` Joker lifecycle / Burglar — GREEN FOR AUDITED IDENTITIES

Burglar source effect:

```text
hands += 3
discards_remaining = 0
```

Owned source order:

```text
reset + round_bonus baseline
→ audited setting_blind Joker pass
→ consume one-shot round bonuses
```

All currently R1-admitted scoring/rule acquisition identities are explicitly classified as inert at `setting_blind`; Burglar is the first active case. Unknown lifecycle identities fail closed.

Commits `cf56473`, `f0c300c`, `19ba181`, `d82e012`.
CI `33797436606`: **1483 passed, 1594 deselected**.

### R2.7 — first-round counter parity — GREEN

Vanilla source truth:
- `G.GAME.round` initializes to `0`
- `select_blind` queues `ease_round(1)` before `new_round()`
- fresh first `BLIND_SELECT` therefore transitions `0 → 1`

Commits `3fa6948`, `727eb8e`.
CI `33797071526`: **1482 passed, 1594 deselected**.

### R2.8 — Small/Big Blind start lifecycle — GREEN

`prepare_supported_nonboss_blind_start()` owns:

```text
BLIND_SELECT
→ round += 1
→ authoritative blind requirement
→ reset + round_bonus resources
→ audited setting_blind Jokers
→ consume bonuses
→ DRAW_TO_HAND
```

`start_supported_nonboss_blind()` composes that lifecycle with generalized exact `deal_supported_round_start()`.

Current fail-closed constraints:
- Small/Big only
- no active tags
- no vouchers
- unclassified Joker lifecycle rejected
- exact reset allowances required
- transition card zones empty
- helper is not itself training-visible `SELECT_BLIND`

Original lifecycle commits `c327b4d`, `e32e3e2`; CI `33797587142`: **1492 passed, 1594 deselected**.

Additional composed Burglar/non-boss integration:

```text
09ae7a2  compose supported nonboss blind start
d95d342  cover nonboss Burglar + bonus ordering + exact deal
```

CI `33798795353`: **1497 passed, 1594 deselected**.

### R2.9 — Boss blind-start lifecycle — ACTIVE

Boss start logic must be expanded in **small source-audited groups**, not by assuming all bosses share ordinary blind setup.

Vanilla `Blind:set_blind` has explicit start-time cases for at least:
- The Eye
- The Mouth
- The Fish
- The Water
- The Needle
- The Manacle
- Amber Acorn

and then runs the generic card/Joker debuff pass. Bosses with RNG, resource overrides, hand-size changes, card debuffs, mutable blind-owned state, or Joker shuffling stay blocked until their specific start semantics are owned.

#### First boss slice — The Wall — GREEN

The Wall has no start-time card/resource/mutable-state consequence beyond the authoritative enlarged blind requirement. The exact Boss boundary now owns:
- Boss identity and requirement validation
- round increment
- round resource baseline
- audited `setting_blind` Jokers, including Burglar
- one-shot bonus consumption
- clearing nonapplicable Eye/Mouth mutable state
- transition to `DRAW_TO_HAND`
- optional generalized exact shuffle/deal composition

Commits:

```text
4f5b476  own first Wall boss-start slice
e3f1bd5  pin Wall lifecycle and Burglar/deal composition
7c27802  preserve established blind-start validation contracts
```

The first Wall test run exposed only an error-message regression (`1 failed, 1501 passed, 1594 deselected`); successful transition semantics were unaffected. The validation contract was restored.

CI `33799302675`: **1502 passed, 1594 deselected**.

Next audited requirement-only candidate: **Violet Vessel**. Vanilla source definition uses only its enlarged requirement (`mult = 6`) with an empty debuff table and it is not one of the explicit `Blind:set_blind` start-time special cases. Verify this again in code/tests before admitting it.

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Burglar purchase remains **FAIL-CLOSED**. Its ordinary Small/Big and Wall `setting_blind` behavior is now owned, but a purchased Burglar persists into every possible Boss blind; the full Boss-start surface is not yet exact.

Still unowned/high-priority:
- remaining Boss blind-start groups
- prior-round card-zone cleanup sufficient to reconstruct the complete next-round deck in all supported trajectories
- active tag effects at blind start
- voucher effects at blind start
- shop generation/reroll RNG
- pack RNG/state
- boss selection RNG
- other modeled random effects

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Target actions include:

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

Every training-visible action requires stable type/id, exact parameters, deterministic legality, exact transition, serialization representation, and mask representation.

Do **not** expose `SELECT_BLIND` yet.

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity harness — NOT STARTED

Priority fixtures:
- shop purchase/end-shop/reroll
- voucher/pack paths
- blind skip/start/clear
- boss restrictions
- owned-deck composition
- economy/interest
- RNG/shuffle/initial draw
- lifecycle-sensitive Jokers

## R6 — environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead only after semantics are correct.

---

# Later RL phases — NOT STARTED

```text
O   observation/action encoding
B0  random + frozen symbolic baselines
P   PPO strategic learner
C0  curriculum/sample efficiency
E0  statistical evaluation
A0  Bond feature ablation
F0  reward validation
T   training scale-up
V   simulator→live learned-policy validation
Q   Red/White competence gate
X   optional full tactical RL
M   post-RL symbolic cleanup
N   broader decks/stakes/objectives
```

Reference reward remains terminal-only unless a validated shaping experiment improves Ante-8 clear probability:

```text
Ante 8 cleared: +1
run lost:        0
```

---

# Testing/reproducibility contract

Current deterministic CI selector:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

Use deterministic tests for mechanics, transitions, legality, phase boundaries, RNG, serialization, masks, and parity fixtures. Use statistical rollout evaluation later for learned competence.

No local clone is assumed in Work Chat; do not claim local pytest unless a real local runtime exists.

---

# Current checkpoint — EXACT PROJECT STATE

```text
Historical symbolic/Bond architecture             COMPLETE AS BASELINE
Mechanics/state/action deterministic foundation   SUBSTANTIALLY COMPLETE
Phase K cleanup                                   COMPLETE
Phase L live stabilization                        COMPLETE
L3 environment freeze                             COMPLETE
R0 environment architecture                       COMPLETE
R1 deterministic state/acquisition                SUBSTANTIALLY COMPLETE / OPEN LIFECYCLES
R2 RNG determinism                                ACTIVE
R2.1 Balatro/LuaJIT RNG                           GREEN — CI 33791671797
R2.2 pseudoshuffle                                GREEN — CI 33791916289
R2.3 card creation order + headless RNG           GREEN — CI 33795507133
R2.4 generalized complete-deck shuffle/deal       IMPLEMENTED / GREEN AT CURRENT HEAD
R2.5 round bonus/resource lifecycle               GREEN — CI 33796637904
R2.6 Burglar setting_blind lifecycle              GREEN — CI 33797436606
R2.7 first round 0→1 source parity                GREEN — CI 33797071526
R2.8 supported Small/Big start + exact deal       GREEN — CI 33798795353
R2.9 The Wall Boss start                          GREEN — CI 33799302675
R2.9 remaining Boss start groups                  ACTIVE — CURRENT NEXT WORK
SELECT_BLIND training action                      NOT EXPOSED
Burglar acquisition                               FAIL-CLOSED UNTIL FULL BOSS START OWNED
Generic/unknown Joker acquisition                 FAIL-CLOSED
Joker editions                                    FAIL-CLOSED
Generic voucher acquisition                       FAIL-CLOSED
Booster-pack opening                              FAIL-CLOSED
SELL_JOKER                                        FAIL-CLOSED
R4 tactical bridge                                NOT STARTED
R5 parity harness                                 NOT STARTED
R6 performance                                    NOT STARTED
Observation/action encoding                       NOT STARTED
PPO                                               NOT STARTED
```

Current branch code head immediately before this roadmap synchronization:

```text
7c278020c46601efdefafb1049e8249d460a5b53
```

---

# Exact next development action

**Continue R2 Boss blind-start lifecycle. Do not start PPO/observation training.**

Immediate order:

1. verify and admit **Violet Vessel** as the next requirement-only Boss start if source/tests confirm no additional start mutation or debuff;
2. classify remaining Bosses by vanilla `Blind:set_blind` and `debuff_card` behavior rather than by display description alone;
3. implement start-inert/requirement-only Bosses in a small coherent group;
4. separately implement resource-mutating Bosses such as Water/Needle/Manacle with exact source ordering;
5. separately implement mutable-state Bosses such as Eye/Mouth;
6. separately implement card/Joker debuff or RNG-sensitive Bosses; keep Amber Acorn and other stochastic starts blocked until exact RNG/order ownership exists for their effect;
7. only after the full supported Boss-start surface is exact should Burglar purchase and `SELECT_BLIND` exposure be reconsidered;
8. retain fail-closed tags, vouchers, editions, packs, unknown acquisitions, and sell/inverse effects;
9. add R5 live/simulator parity before declaring the environment authoritative for training.

The next code should therefore be **Violet Vessel / requirement-only Boss start auditing and exact Boss lifecycle expansion**. It should **not** be Bond tuning and **not** PPO.

---

# Progress criterion

```text
mechanical/state/action foundation                 ✓
Bond symbolic baseline                             ✓
live correctness stabilization                     ✓
R0 HEADLESS ARCHITECTURE                           ✓
R1 DETERMINISTIC STATE/ACQUISITION                 ✓ substantial
        ↓
R2 EXACT RNG / ROUND START                         ← ACTIVE
  ├─ LuaJIT RNG                                    ✓
  ├─ pseudoshuffle                                 ✓
  ├─ creation order / private RNG                  ✓
  ├─ complete-deck exact shuffle/deal              ✓
  ├─ round resources / bonuses                     ✓
  ├─ Burglar setting_blind                         ✓
  ├─ Small/Big start                               ✓
  ├─ The Wall Boss start                           ✓
  └─ remaining Boss start groups                   ← NEXT
        ↓
R3 ACTION COMPLETION
        ↓
R4 DETERMINISTIC TACTICAL BRIDGE
        ↓
R5 LIVE/SIMULATOR PARITY
        ↓
R6 PERFORMANCE
        ↓
OBSERVATION + ACTION ENCODING
        ↓
HEADLESS BASELINES
        ↓
PPO STRATEGIC LEARNER
        ↓
CURRICULUM / EVALUATION / ABLATION
        ↓
TRAINING SCALE-UP
        ↓
SIMULATOR↔LIVE VALIDATION
        ↓
RED/WHITE COMPETENCE GATE
```

Controlling environment question:

> **Does the environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
