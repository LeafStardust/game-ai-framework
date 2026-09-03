# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Primary objective: **maximize P(clear Ante 8 | Red Deck, White Stake, normal mode)**.
- Work Chat runs deterministic/static tests itself where available; GitHub Actions is authoritative when no local clone exists.
- User runs only validation that genuinely requires Windows/Balatro.
- Preserve exact mechanics, legality, boss rules, economy, public-information boundaries, and reproducible RNG.
- Prefer canonical ownership over rescue wrappers or approximations.
- Unsupported/inexact transitions stay absent from the training mask.
- Manual Bond coefficient tuning is retired as the primary competence path.
- Do **not** start PPO/observation training before the exactness/parity gates.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.

---

# Completed foundation

## A–K — symbolic/mechanical foundation — COMPLETE AS BASELINE

Retain deterministic mechanics/state/legality/tactical execution, Bond features, `BuildValue` / `StrategyDelta`, telemetry, and motifs as baselines/features. Do not resume manual strategy tuning as the primary path.

## L — live stabilization — COMPLETE

L3 froze the environment contract:

```text
BALATRO_ENV_CONTRACT_VERSION = "l3-v1"
CI 33758680261: 1223 passed, 1594 deselected
```

Do not request another open-ended live batch at this stage.

## R0 — headless environment architecture — COMPLETE

Authoritative environment: `games/balatro/env/`.

- deterministic reset/step/legal-actions facade
- canonical `BalatroState`
- serialization/restore and illegal-action rejection boundary
- CI `33760179448`: `1233 passed, 1594 deselected`

Legacy `games/balatro/environment.py` is not authoritative RL environment truth.

---

# Phase R — exact headless Balatro environment — ACTIVE

The simulator is not authoritative game truth until R5 live/simulator parity passes.

## R1 — deterministic state/acquisition transitions — SUBSTANTIALLY COMPLETE; OPEN LIFECYCLES REMAIN

### Acquisition contract

Generic acquisition is not “append inventory + subtract money.” Every persistent consequence must be exact.

Current hard fail-closed surfaces:

- Joker editions, especially Negative
- unknown/unaudited Joker identities
- generic voucher acquisition
- packs until exact pack/RNG state exists
- `SELL_JOKER` until inverse lifecycle effects exist
- malformed/noninteger prices

Exact resource-sensitive Joker acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

The large audited inventory-only scoring/rule/retrigger acquisition set remains green, including Four Fingers/Pareidolia/Shortcut/Smeared/Splash, hand-shape groups, suit groups, Scary Face/Arrowhead/Onyx Agate/Flower Pot/Seeing Double, Joker Stencil/Shoot the Moon/Triboulet, Bull/Bootstraps, and Dusk/Hack/Hanging Chad/Mime/Sock and Buskin.

### Permanent owned deck — GREEN

Exact deck-dependent Jokers:

```text
Steel Joker
Stone Joker
Driver's License
Erosion
```

Authority rules:

- permanent deck truth comes from `G.playing_cards`
- **never** substitute `G.deck.cards`
- translation is all-or-nothing
- malformed/count-mismatched cards make `owned_deck = None`
- low-level LuaJIT TValue failures cannot silently shorten the authoritative deck

Key gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Private deterministic state validates exact card zones, seed type, tags, pack container shape, round-reset baselines, playing-card creation order, RNG state, one-shot round bonuses, and reversible Boss resource fields.

---

## R2 — RNG + exact round/blind lifecycle — ACTIVE / CURRENT PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

Balatro keyed pseudohash/pseudoseed over LuaJIT combined Tausworthe `math.random`; never Python `random`.

```text
2e61cd8  exact Balatro/LuaJIT RNG primitives
290ff11  pinned reference vectors
CI 33791671797: 1432 passed, 1594 deselected
```

### R2.2 — pseudoshuffle — GREEN

One keyed pseudoseed advance, then one LuaJIT RNG stream drives Fisher–Yates.

```text
246f442  exact pseudoshuffle
 d9662c6  pinned shuffle vectors
CI 33791916289: 1435 passed, 1594 deselected
```

### R2.3 — playing-card creation order + private RNG ownership — GREEN

Exact private order is reconstructable only from:

1. unique integer live `playing_card` IDs; or
2. the untouched vanilla one-of-each 52-card deck.

Unprovable order fails closed. No fake public `sort_id` is introduced.

Relevant commits: `e7b0bb0`, `2a26e79`, `34d88e9`, `7c070b2`, `2dc47eb`, `0a7f845`, `eed926e`.

```text
CI 33795507133: 1461 passed, 1594 deselected
```

### R2.4 — exact complete-deck shuffle/deal — GREEN FOR SUPPORTED COMPLETE DECKS

Pristine implementation: `61ec993`, `2d37016`.
Generalized implementation retains exact original-suit history when required and preserves hidden physical draw order privately.

`deal_supported_round_start()` requires authoritative complete deck composition, exact object identity, exact retained creation order, and exact original-suit nominal where history cannot otherwise be proved.

Pinned `TESTSEED` first hand:

```text
A Hearts, K Hearts, Q Diamonds, 9 Spades,
9 Clubs, 5 Clubs, 5 Diamonds, 4 Clubs
```

A narrow additional proof now exists for a structurally untouched base 52-card deck carrying only transient Boss `debuffed` flags. In that case original suit is still exactly inferable from current suit; enhancements/conversions/live-created cards remain on the strict historical-nominal path.

```text
1ce2662  allow exact transient-debuff base deals
8bb5ae1  pin transient-debuff deal invariants
CI 33803629167: 1563 passed, 1594 deselected
```

### R2.5 — round bonuses/resources — GREEN

Private signed one-shot fields:

```text
round_bonus_hands
round_bonus_discards
```

Vanilla baseline:

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

Bonuses are consumed only after blind setup / `setting_blind` Joker processing.

```text
CI 33796637904: 1479 passed, 1594 deselected
```

### R2.6 — `setting_blind` Joker lifecycle / Burglar — GREEN FOR AUDITED IDENTITIES

Burglar:

```text
hands += 3
discards_remaining = 0
```

Source order:

```text
round resource baseline
→ Boss set_blind mutation
→ playing-card debuff pass when applicable
→ audited Joker setting_blind pass
→ consume one-shot round bonuses
```

Unknown lifecycle identities fail closed.

```text
CI 33797436606: 1483 passed, 1594 deselected
```

### R2.7 — first-round counter parity — GREEN

Vanilla `G.GAME.round` begins at `0`; selecting the first blind queues `ease_round(1)` before `new_round()`. First start is `0 → 1`.

```text
CI 33797071526: 1482 passed, 1594 deselected
```

### R2.8 — Small/Big Blind start — GREEN

`prepare_supported_nonboss_blind_start()` owns:

```text
BLIND_SELECT
→ round += 1
→ blind requirement
→ round-resource baseline
→ audited setting_blind Jokers
→ consume bonuses
→ DRAW_TO_HAND
```

`start_supported_nonboss_blind()` composes this with exact generalized shuffle/deal.

Key gates:

```text
33797587142  1492 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
33796012173  1467 passed, 1594 deselected  # pristine first-blind regression gate
```

### R2.9 — Boss blind-start lifecycle — ACTIVE

Bosses are admitted only by exact source-audited lifecycle semantics.

#### R2.9a — requirement-only Bosses — GREEN

```text
The Wall
Violet Vessel
```

Their start-time mechanic is fully represented by the authoritative blind requirement; no additional `Blind:set_blind` state mutation is needed on the audited boundary.

```text
CI 33799746434: 1509 passed, 1594 deselected
```

#### R2.9b — mutable hand-rule Bosses — GREEN

```text
The Eye
The Mouth
```

Canonical start state:

```text
boss_blind_state_observed = True
boss_blind_hands = set()
boss_blind_only_hand = None
```

```text
CI 33800243393: 1518 passed, 1594 deselected
```

#### R2.9c — Water / Needle reversible resources — GREEN

Vanilla start behavior is represented with private reversal state:

```text
Water:
  boss_discards_sub = current post-bonus discards
  discards_remaining -= boss_discards_sub

Needle:
  boss_hands_sub = round_reset_hands - 1
  hands_remaining -= boss_hands_sub
```

`Blind:disable()` restoration is owned for both. Source ordering relative to Burglar and round bonuses is pinned.

```text
CI 33801195935: 1542 passed, 1594 deselected
```

#### R2.9d — The Manacle reversible hand-size lifecycle — GREEN

Private state:

```text
boss_hand_size_sub = 1
```

Start:

```text
hand_size -= 1
```

Exact end boundaries are intentionally distinct:

```text
Blind:disable():
  hand_size += 1
  draw one replacement card from the already-shuffled physical draw pile
  do not advance RNG again

Blind:defeat():
  hand_size += 1
  no replacement draw
```

Pre-deal Manacle disable remains fail-closed because Chicot-style disable during `setting_blind` would require an exact pre-deal draw boundary that is not yet owned.

Key commits include `88af1e4`, `c8f699b`, `899fc96`, `142c530`, `6bbbb22`, and the Manacle lifecycle regressions through `4b955e4` plus later corrections. The final static-suit head gate below includes these Manacle corrections.

#### R2.9e — static suit card-debuff Bosses — GREEN ON EXACT BASE-DECK BOUNDARY

Audited set:

```text
The Goad    → Spades
The Window  → Diamonds
The Head    → Hearts
The Club    → Clubs
```

Vanilla order reproduced:

```text
round baseline
→ Boss-specific start mutation (none for this family)
→ debuff pass over every permanent playing card
→ Joker setting_blind
→ consume bonuses
→ shuffle/deal
```

First implementation deliberately supports only the untouched one-of-each 52-card composition with no Wild/suit-changing enhancement, conversion, edition, seal, permanent bonus, live-created card, forced selection, or pre-existing unknown debuff. This makes `card:is_suit(..., true)` exactly equivalent to base suit equality without approximating modified-card suit semantics.

Disable/defeat cleanup clears the Boss-owned transient debuffs across the retained permanent-card object set without changing card zones or RNG.

```text
8af8dae  own static suit Boss card debuffs
0baef57  compose static suit Boss start lifecycle
3262dcc  pin all four Bosses, deal preservation, cleanup, isolation, fail-closed cases
CI 33803874842: 1583 passed, 1594 deselected
```

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Burglar purchase remains **FAIL-CLOSED** even though its effect is owned for the currently supported starts. A purchased Burglar persists into arbitrary future Bosses, so broader supported Boss-start coverage is still required before admitting it as run-safe.

High-priority unowned Boss/start groups:

- **The Plant**: face-card debuff; vanilla `card:is_face(true)` includes Pareidolia, so exact implementation must consult Joker inventory and cannot be reduced to J/Q/K
- **The Pillar**: requires persistent per-card `played_this_ante` history
- **Verdant Leaf**: requires all-card debuff plus Joker-sale lifecycle
- **Amber Acorn**: Joker flip + seeded Joker-order shuffle
- face-down families (Wheel/House/Mark/Fish) require exact facing/round-event ownership
- Cerulean Bell forced selection lifecycle
- Hook random discards and other action-time Boss RNG
- Chicot Boss-disable composition, including pre-deal Manacle disable

Other unowned stochastic/lifecycle surfaces:

- prior-round zone cleanup for all supported trajectories
- active tag effects
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG
- remaining modeled random effects

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Target actions include `END_SHOP`, reroll/buy/sell/use/pack actions, `SKIP_BLIND`, and `SELECT_BLIND`.

Every training-visible action needs exact legality, exact transition, stable serialization, and mask representation.

**Do not expose `SELECT_BLIND` yet.**

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity — NOT STARTED

Priority parity fixtures include shop transitions, blind skip/start/clear, Boss restrictions, lifecycle-sensitive Jokers, owned-deck composition, economy, and RNG/shuffle/initial draw.

## R6 — performance gate — NOT STARTED

Measure throughput only after correctness/parity.

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

Reference reward remains terminal-only unless validated shaping improves Ante-8 clear probability:

```text
Ante 8 cleared: +1
run lost:        0
```

---

# Deterministic CI contract

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

No local clone is assumed in Work Chat; never claim local pytest unless a real local runtime exists.

---

# Current exact checkpoint

```text
A–K symbolic/mechanical baseline                  COMPLETE
L live stabilization                             COMPLETE
R0 environment architecture                      COMPLETE
R1 deterministic state/acquisition               SUBSTANTIALLY COMPLETE
R2 exact RNG / round start                       ACTIVE
R2.1 LuaJIT RNG                                  GREEN — CI 33791671797
R2.2 pseudoshuffle                               GREEN — CI 33791916289
R2.3 creation order / private RNG                GREEN — CI 33795507133
R2.4 complete-deck exact deal                    GREEN FOR SUPPORTED DECKS
R2.5 round resources / bonuses                   GREEN — CI 33796637904
R2.6 Burglar setting_blind                       GREEN — CI 33797436606
R2.7 first round 0→1                             GREEN — CI 33797071526
R2.8 Small/Big start + deal                      GREEN — CI 33798795353
R2.9a Wall + Violet Vessel                       GREEN — CI 33799746434
R2.9b Eye + Mouth                                GREEN — CI 33800243393
R2.9c Water + Needle                             GREEN — CI 33801195935
R2.9d Manacle start/disable/defeat               GREEN UNDER FINAL HEAD GATE
R2.9e Goad/Window/Head/Club                      GREEN — CI 33803874842
Transient-debuff base-deck deal                  GREEN — CI 33803629167
SELECT_BLIND                                      NOT EXPOSED
Burglar acquisition                              FAIL-CLOSED
Generic/unknown acquisitions                     FAIL-CLOSED
Joker editions                                   FAIL-CLOSED
Generic vouchers/packs                           FAIL-CLOSED
SELL_JOKER                                       FAIL-CLOSED
R4 tactical bridge                               NOT STARTED
R5 parity                                        NOT STARTED
R6 performance                                   NOT STARTED
Observation/PPO                                  NOT STARTED
```

Current branch code head immediately before this roadmap synchronization:

```text
3262dcc9daaa1fe2b9e9193594e8ffaf016d2e0f
```

---

# Exact next development action

**Continue R2 Boss lifecycle. Do not start PPO/observation training.**

Immediate order:

1. implement **The Plant** only after reproducing vanilla `card:is_face(true)` exactly, including Pareidolia interaction, on a clearly bounded permanent-card surface;
2. pin Plant start/deal/cleanup/input-isolation and Pareidolia regressions;
3. keep Pillar blocked until persistent per-card `played_this_ante` state is owned;
4. keep Verdant Leaf blocked until Joker sale/inverse lifecycle is owned;
5. continue remaining Boss families in mechanically coherent groups rather than broad allowlists;
6. preserve the distinction among Boss `set_blind`, `disable`, `defeat`, press-play, hand-rule, and draw-time effects;
7. keep tags, vouchers, editions, packs, unknown acquisitions, sell effects, and `SELECT_BLIND` fail-closed until exact;
8. add R5 live/simulator parity before declaring the environment authoritative for training.

Controlling environment question:

> **Does the environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
