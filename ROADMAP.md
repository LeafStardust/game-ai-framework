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
- Unsupported/inexact actions stay absent from the training mask; do not assign arbitrary low value.
- Model checkpoints are artifacts, not source-of-truth strategy definitions.
- Do not reintroduce legacy multi-attempt CLI conventions such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.

---

# Primary objective

**Red Deck / White Stake, normal mode: maximize probability of clearing Ante 8.**

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

Initial RL keeps tactical hand play deterministic while RL learns strategic run development. Full tactical RL remains optional later work.

Do **not** start PPO or observation training until the headless environment reaches its exactness/parity gates.

---

# Completed foundation — Phases A–K

A–K symbolic/mechanical foundation is complete as baseline. Retain:

- canonical Bond vocabulary/features;
- mechanics/state/legality;
- deterministic tactical owners;
- `BuildValue` / `StrategyDelta` as frozen symbolic baseline;
- sparse relationships/motifs and telemetry.

Do not return to manual Bond coefficient tuning as the primary competence path.

---

# Phase L — Live correctness stabilization — COMPLETE

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

- `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`;
- unsupported training actions fail closed;
- CI `33758680261`: `1223 passed, 1594 deselected`.

Do not request another open-ended live batch at this stage.

---

# Phase R — Headless Balatro environment — ACTIVE

The headless simulator is not authoritative game truth until live/simulator parity gates pass.

## R0 — Environment architecture/ownership — COMPLETE

- authoritative environment under `games/balatro/env/`;
- version `r0-v1`;
- `reset`, `step`, `legal_actions`;
- canonical `BalatroState` observations;
- serialization/restore and illegal-action rejection;
- CI `33760179448`: `1233 passed, 1594 deselected`.

Legacy `games/balatro/environment.py` is not authoritative RL environment truth.

---

## R1 — Deterministic state/acquisition transitions — SUBSTANTIALLY COMPLETE; LIFECYCLE WORK REMAINS

### Acquisition contract

Generic acquisition is **not** merely append inventory + subtract money.

Always fail closed unless identity/state consequences are exact. Current hard boundaries:

- all Joker editions remain blocked, especially Negative;
- generic/unknown Joker identities remain blocked;
- generic voucher acquisition remains blocked;
- packs remain blocked until exact pack/RNG state;
- `SELL_JOKER` remains blocked until inverse lifecycle effects are exact.

Exact generic shop behavior:

- `END_SHOP`;
- held-consumable purchase when capacity/price/affordability are exact;
- price must be an exact integer; bool/string/float/missing/invalid/negative fail closed.

### Exact resource-sensitive Joker acquisitions

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2, requires hand_size >= 2
Drunkard     round_reset_discards += 1, observed reset baseline required
Troubadour   hand_size += 2; round_reset_hands -= 1, observed baseline required
Merry Andy   hand_size -= 1; round_reset_discards += 3, observed baseline required
```

Live `round_reset_hands` ownership CI `33781164005`: `1297 passed, 1594 deselected`.
Merry Andy CI `33781461393`: `1300 passed, 1594 deselected`.

### Exact inventory-only scoring/rule acquisition set

Current audited scoring/rule set includes:

```text
FlatMult Abstract Acrobat Banner Baron Blackboard Blue EvenSteven Fibonacci Half
MysticSummit OddTodd Photograph RaisedFist Scholar SmileyFace WalkieTalkie Juggler
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

Relevant green gates progressed through:

```text
33782526550  1310 passed
33782754111  1320 passed
33783865698  1332 passed
33784097107  1340 passed
33784381489  1348 passed
33785203157  1358 passed
33785485082  1364 passed
33786958116  1370 passed
33787354303  1380 passed
```

All above had `1594 deselected` unless otherwise noted.

### Permanent owned-deck scoring — GREEN

Exact owned-deck dependent Jokers:

```text
Steel Joker
Stone Joker
Driver's License
Erosion
```

Rules:

- authoritative live permanent deck source is `G.playing_cards`;
- **never** substitute `G.deck.cards` for permanent ownership;
- translator is all-or-nothing;
- malformed cards/count mismatch/inexact modifiers make `owned_deck = None`;
- authoritative empty deck remains `[]`.

Commits:

```text
7b7699e  fail closed on partial owned-deck translation
17176c7  gate deck-scoring acquisitions on owned deck
5062f0f  owned-deck acquisition tests
```

CI `33788603611`: `1401 passed, 1594 deselected`.

### Permanent `G.playing_cards` decode completeness — GREEN

A low-level LuaJIT TValue decode failure can no longer silently shorten the permanent owned deck. Strict all-or-nothing array reading is used only where permanent-deck authority requires it; tolerant observation elsewhere is retained.

CI `33789894797`: `1405 passed, 1594 deselected`.

### Private deterministic state hardening — GREEN

- `draw_pile`, `discard_pile`, `played_pile` are exact `list[BalatroCard]`;
- seed is `str | int`, bool rejected;
- tags are `list[str]`;
- pack choices must at least be a list pending exact pack ownership.

Card-zone gate: `1412 passed, 1594 deselected`.
Container CI `33790592775`: `1424 passed, 1594 deselected`.

---

## R2 — RNG + blind-start stochastic lifecycle — ACTIVE / CURRENT PRIMARY WORKSTREAM

### R2.1 — Exact Balatro/LuaJIT RNG — GREEN

`games/balatro/env/rng.py` owns:

- Balatro keyed pseudohash/pseudoseed progression;
- LuaJIT combined Tausworthe `math.random` semantics;
- inclusive integer draws;
- independent keyed queues;
- bit-preserving snapshot/restore.

Do **not** use Python `random` as a substitute.

Commits `2e61cd8`, `290ff11`.
CI `33791671797`: `1432 passed, 1594 deselected`.

### R2.2 — Exact pseudoshuffle — GREEN

- keyed pseudoseed advances once per shuffle;
- one LuaJIT RNG stream drives Fisher–Yates;
- not equivalent to repeated keyed random calls.

Commits `246f442`, `d9662c6`.
CI `33791916289`: `1435 passed, 1594 deselected`.

### R2.3 — Exact playing-card creation/pre-shuffle order — GREEN

Vanilla sorts cards by monotonic `sort_id` before pseudoshuffle. Public state does not expose a fake sort id.

Exact reconstruction is allowed only when:

1. every owned live playing card has a unique exact integer `playing_card` id (`BalatroCard.live_id`), whose relative creation order matches playing-card `sort_id`; or
2. the deck is the untouched one-of-each vanilla 52-card identity set, whose initial control-code creation order is known.

Duplicate/mixed/missing IDs or modified no-ID decks fail closed.

Commits:

```text
e7b0bb0  derive exact playing-card creation order
2a26e79  pin card-order tests
34d88e9  include env_r2 tests in deterministic CI selector
7c070b2  retain private card creation order in headless state
2dc47eb  test retained order
0a7f845  own exact Balatro RNG in HeadlessRunState
eed926e  test headless RNG ownership
```

Corrected CI selector includes `env_r2`.
CI `33795507133`: **1461 passed, 1594 deselected**.

### R2.4a — Exact pristine round-start shuffle/deal — GREEN

`games/balatro/env/deal.py` currently owns the exact pristine 52-card draw boundary:

- requires `DRAW_TO_HAND`;
- exact retained card creation order;
- shuffle key `nr{ante}`;
- hidden shuffled order remains private;
- public remaining deck is canonicalized;
- initial hand drawn from deck tail and nominal-sorted;
- RNG state advances reproducibly;
- phase becomes `SELECTING_HAND`.

Commits `61ec993`, `2d37016`.
CI `33794664514`: `1461 passed, 1594 deselected`.

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

Next hidden draw tail: `10 Clubs`.
`nr1` node after shuffle: `0.8232194488594`.

### R2.4b — Round-start bonus/resource lifecycle — GREEN

Private headless state now owns signed exact one-shot fields:

```text
round_bonus_hands
round_bonus_discards
```

Vanilla source ordering is preserved:

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

The bonuses are **not** consumed during baseline computation. Consumption is a separate explicit step after blind/Joker setup.

Commits:

```text
906719d  own round-start bonus state
d727221  validate signed exact bonus state
58ac3cc  own round resource baseline / bonus consumption
bd07ffe  pin round lifecycle
```

CI `33796637904`: **1479 passed, 1594 deselected**.

### R2.4c — Burglar `setting_blind` lifecycle — GREEN

Canonical project Burglar behavior on `BLIND_SELECTED`:

```text
hands_gained += 3
discards_remaining = 0
```

Source-order ownership:

```text
reset + round_bonus baseline
→ setting_blind Joker pass
→ consume round bonuses
```

The generic Joker `.apply()` interface is **not** treated as a universal event bus because some mechanical Joker implementations are trigger-agnostic and rely on their owning scoring/rule pipeline.

All currently R1-admitted acquisition identities are classified as inert at vanilla `setting_blind`; Burglar is the first owned active case. Unknown lifecycle identities fail closed.

Commits:

```text
cf56473  own Burglar blind-selected lifecycle
f0c300c  Burglar lifecycle tests
19ba181  classify admitted blind-start inert Jokers
d82e012  pin inert coexistence and unclassified rejection
```

CI `33796875616`: `1482 passed, 1594 deselected`.
CI `33797436606`: **1483 passed, 1594 deselected**.

### R2.4d — First-blind round counter parity — GREEN

Vanilla source truth:

- `G.GAME.round` initializes to `0`;
- `G.FUNCS.select_blind` queues `ease_round(1)` before `new_round()`;
- therefore fresh first `BLIND_SELECT` is round `0`, and starting it produces round `1`.

The initial project-local assumption that first BLIND_SELECT was already round 1 was corrected.

Commits:

```text
3fa6948  mirror first-blind round increment
727eb8e  pin round 0 → 1 behavior
```

CI `33797071526`: **1482 passed, 1594 deselected**.

### R2.4e — Supported Small/Big Blind pre-deal lifecycle — GREEN

`prepare_supported_nonboss_blind_start()` now composes the deterministic source-ordered **pre-deal** boundary for audited Small/Big Blind state:

```text
BLIND_SELECT
→ round += 1
→ blind requirement/public boss-state normalization
→ reset + round_bonus resources
→ audited setting_blind Joker effects
→ consume one-shot round bonuses
→ DRAW_TO_HAND
```

Current fail-closed constraints:

- Small/Big only; Boss excluded;
- no active tags;
- no vouchers;
- unclassified Joker lifecycle rejected;
- exact reset allowances required;
- transition card zones must be empty;
- this helper is not itself a training-visible action.

Commits:

```text
c327b4d  compose supported nonboss blind lifecycle
e32e3e2  pin supported nonboss lifecycle
```

CI `33797587142`: **1492 passed, 1594 deselected**.

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Burglar purchase remains **FAIL-CLOSED** even though its non-boss `setting_blind` effect is now owned, because a purchased Burglar persists into Boss blinds and the Boss blind-start lifecycle is not yet complete.

Still unowned/high-priority:

- generalized exact shuffle/deal for authoritative modified owned decks;
- prior-round card-zone cleanup sufficient to reach a complete next-round deck;
- Boss blind setup/debuff/restriction lifecycle;
- active tag effects at blind start;
- voucher effects at blind start;
- shop generation/reroll RNG;
- pack RNG/state;
- boss selection RNG;
- other random effects.

---

## R3 — Typed action vocabulary — PARTIAL / TIED TO EXACTNESS

Target strategic actions:

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

Do not expose `SELECT_BLIND` yet.

---

## R4 — Deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — Live/simulator parity harness — NOT STARTED

Priority fixtures include:

- shop purchase/end-shop;
- reroll/voucher/pack paths;
- blind skip/start/clear;
- boss restrictions;
- owned-deck composition;
- economy/interest;
- RNG/shuffle/initial draw;
- lifecycle-sensitive Jokers.

## R6 — Performance gate — NOT STARTED

Measure only after semantics are correct.

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

Reference reward remains terminal-only unless an explicitly validated shaping experiment improves Ante-8 clear probability:

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
R1 deterministic state/acquisition work           SUBSTANTIALLY COMPLETE / OPEN LIFECYCLES
R2 RNG determinism                                ACTIVE
R2.1 Balatro/LuaJIT RNG                           GREEN — CI 33791671797
R2.2 pseudoshuffle                                GREEN — CI 33791916289
R2.3 card creation order + headless RNG           GREEN — CI 33795507133
R2.4 pristine shuffle/deal                        GREEN — CI 33794664514
R2.4 round bonus/resource lifecycle               GREEN — CI 33796637904
R2.4 Burglar setting_blind lifecycle              GREEN — CI 33796875616
R2.4 admitted inert-Joker classification          GREEN — CI 33797436606
R2.4 first round 0→1 source parity                GREEN — CI 33797071526
R2.4 supported Small/Big pre-deal lifecycle       GREEN — CI 33797587142
SELECT_BLIND training action                      NOT EXPOSED
Burglar acquisition                               FAIL-CLOSED UNTIL BOSS LIFECYCLE OWNED
Boss blind-start lifecycle                        NOT YET OWNED
General modified-deck shuffle/deal                NEXT
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

Current code head immediately before this roadmap synchronization:

```text
e32e3e21aaf02f1efb33149d64c81501778716a0
```

---

# Exact next development action

**Continue R2 exact environment work. Do not start PPO/observation training.**

Immediate order:

1. generalize round-start shuffle/deal beyond pristine 52 cards only when permanent owned deck, current complete deck composition, and retained playing-card creation order prove the same card set;
2. reproduce vanilla short-deck draw semantics (`min(deck size, hand capacity)`), still keeping shuffled order private;
3. retain fail-closed behavior when deck completeness/order cannot be proved;
4. then implement exact Boss blind-start setup/debuff/restriction lifecycle in small audited slices;
5. only after Boss + non-Boss blind-start transitions are exact should Burglar purchase and/or `SELECT_BLIND` be reconsidered;
6. keep tags, vouchers, editions, packs, unknown acquisitions, sell/inverse effects, and unowned RNG paths blocked;
7. add R5 live/simulator parity before declaring the environment authoritative for training.

The next code should therefore be **generalized exact owned-deck round-start shuffle/deal**, followed by **Boss blind-start lifecycle ownership**. It should **not** be Bond tuning and **not** PPO.

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
  ├─ creation order                                ✓
  ├─ pristine deal                                 ✓
  ├─ round bonus lifecycle                         ✓
  ├─ Burglar setting_blind                         ✓
  ├─ Small/Big pre-deal lifecycle                  ✓
  ├─ generalized modified-deck deal                ← NEXT
  └─ Boss blind-start lifecycle                    ← AFTER
        ↓
R3 ACTION COMPLETION
        ↓
R4 TACTICAL BRIDGE
        ↓
R5 PARITY + R6 PERFORMANCE
        ↓
OBSERVATION/ACTION ENCODING
        ↓
BASELINES
        ↓
PPO
        ↓
EVALUATION / TRANSFER / COMPETENCE GATE
```

Controlling implementation question:

> **Does the headless environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does the eventual learned policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
