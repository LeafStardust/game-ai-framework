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

The audited inventory-only scoring/rule/retrigger set remains green, including Four Fingers/Pareidolia/Shortcut/Smeared/Splash, hand-shape groups, suit groups, Scary Face/Arrowhead/Onyx Agate/Flower Pot/Seeing Double, Joker Stencil/Shoot the Moon/Triboulet, Bull/Bootstraps, Dusk/Hack/Hanging Chad/Mime/Sock and Buskin, and the later exact score-only groups already admitted by `ShopTransitionEngine`.

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

`deal_supported_round_start()` requires authoritative complete deck composition, exact object identity, exact retained creation order, and exact original-suit nominal where history cannot otherwise be proved.

Pinned `TESTSEED` first hand:

```text
A Hearts, K Hearts, Q Diamonds, 9 Spades,
9 Clubs, 5 Clubs, 5 Diamonds, 4 Clubs
```

Transient Boss `debuffed` flags are supported on an otherwise exact base 52-card deck without leaking physical draw order.

```text
1ce2662  allow exact transient-debuff base deals
8bb5ae1  pin transient-debuff deal invariants
CI 33803629167: 1563 passed, 1594 deselected
```

`draw_one_supported_card_to_hand()` owns deterministic post-shuffle one-card draws only when the private physical draw pile is already authoritative. Never reconstruct a physical draw order from the public canonical deck.

### R2.5 — round resources / one-shot bonuses — GREEN; SOURCE ORDER CORRECTED

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

**Canonical vanilla order:** compute the current-round allowances, then immediately clear the one-shot bonus fields **before** `Blind:set_blind` and Joker `setting_blind` processing.

```text
2462a9f  match vanilla round-bonus consumption order
af80d5a  pin source-order regressions
CI 33804894982: 1593 passed, 1594 deselected
```

`consume_round_bonuses()` remains an idempotent compatibility helper; canonical ownership is now in `apply_round_resource_baseline()`.

### R2.6 — `setting_blind` Joker lifecycle / Burglar — GREEN FOR AUDITED IDENTITIES

Burglar:

```text
hands += 3
discards_remaining = 0
```

Current exact source order:

```text
round += 1 / blind target install
→ round resource baseline from reset + bonus
→ clear one-shot bonuses
→ Boss set_blind mutation
→ Boss permanent-card debuff pass when applicable
→ audited Joker setting_blind pass
→ DRAW_TO_HAND
→ shuffle/deal
→ Boss drawn_to_hand effect when applicable
```

Unknown lifecycle identities fail closed.

### R2.7 — first-round counter parity — GREEN

Vanilla `G.GAME.round` begins at `0`; selecting the first blind queues `ease_round(1)` before `new_round()`. First start is `0 → 1`.

```text
CI 33797071526: 1482 passed, 1594 deselected
```

### R2.8 — Small/Big Blind start — GREEN

`prepare_supported_nonboss_blind_start()` owns exact pre-deal lifecycle; `start_supported_nonboss_blind()` composes it with exact generalized shuffle/deal.

```text
CI 33798795353: 1497 passed, 1594 deselected
CI 33796012173: 1467 passed, 1594 deselected  # pristine first-blind regression gate
```

### R2.9 — Boss blind-start lifecycle — ACTIVE

Bosses are admitted only by exact source-audited lifecycle semantics.

#### R2.9a — requirement-only Bosses — GREEN

```text
The Wall
Violet Vessel
```

CI `33799746434`: **1509 passed, 1594 deselected**.

#### R2.9b — mutable hand-rule Bosses — GREEN

```text
The Eye
The Mouth
```

Canonical start state initializes empty mutable Boss hand restrictions/history.

CI `33800243393`: **1518 passed, 1594 deselected**.

#### R2.9c — Water / Needle reversible resources — GREEN

Water removes current post-baseline discards and stores the exact reversal amount. Needle removes `round_reset_hands - 1`, preserving one-shot hand-bonus semantics. `Blind:disable()` restoration is owned.

CI `33801195935`: **1542 passed, 1594 deselected**.

#### R2.9d — The Manacle reversible hand-size lifecycle — GREEN ON OWNED POST-DEAL BOUNDARY

Start:

```text
boss_hand_size_sub = 1
hand_size -= 1
```

Disable/defeat are distinct:

```text
Blind:disable(): hand_size += 1; draw one replacement card from authoritative physical draw pile
Blind:defeat():  hand_size += 1; no replacement draw
```

**Pre-deal Chicot + Manacle remains fail-closed.** Chicot disables the Manacle during `setting_blind`, causing a replacement draw before the normal round-start shuffle. The exact result depends on the actual carried physical deck order from the previous round. Do not substitute creation order or public canonical deck order.

#### R2.9e — static suit card-debuff Bosses — GREEN ON EXACT BASE-DECK BOUNDARY

```text
The Goad    → Spades
The Window  → Diamonds
The Head    → Hearts
The Club    → Clubs
```

Disable/defeat cleanup clears only the Boss-owned transient debuffs.

```text
8af8dae  own static suit Boss card debuffs
0baef57  compose static suit Boss start lifecycle
3262dcc  regressions
CI 33803874842: 1583 passed, 1594 deselected
```

#### R2.9f — The Plant — GREEN ON EXACT BASE-DECK BOUNDARY

The Plant uses vanilla `card:is_face(true)`, not a hardcoded J/Q/K check. Pareidolia therefore makes every playing card a face card and is included in exact start/debuff semantics. Cleanup removes only Plant-owned transient debuffs.

CI `33804343818`: **1593 passed, 1594 deselected**.

#### R2.9g — exact `pseudorandom_element` primitive — GREEN

Vanilla semantics were source-audited and corrected before acceptance:

```lua
math.randomseed(seed)
collect candidates
sort candidates by value.sort_id when present, otherwise key
choose exactly one math.random(#keys)
```

There is **no Fisher–Yates shuffle inside `pseudorandom_element`**.

For dense numeric-key arrays, `BalatroRNG.pseudorandom_element_index()` performs one inclusive LuaJIT integer draw after one keyed pseudoseed advance. Card callers must map that selected sorted position through exact card `sort_id`/creation order.

```text
08153fc  match vanilla pseudorandom_element selection
5bb7ee6  corrected reference vectors
CI 33805699954: 1598 passed, 1594 deselected
```

Superseded exploratory commits `cf87867` / `8a6a351` encoded the wrong interpretation and are **not** authoritative semantics.

#### R2.9h — Cerulean Bell `drawn_to_hand`, full start, and cleanup — GREEN

Vanilla Cerulean Bell applies forced selection after a hand exists in `Blind:drawn_to_hand()`.

Exact ownership:

```text
ordinary Boss pre-deal lifecycle
→ exact shuffle/deal
→ sort current hand candidates by retained playing-card creation/sort_id order
→ pseudorandom_element using key "cerulean_bell"
→ set exactly one card.forced_selection
```

If one forced card already exists, no RNG is consumed. Multiple pre-existing forced cards fail closed.

Pinned `TESTSEED` behavior on the standard first dealt hand forces **4 of Clubs**. It is last in visible hand sort order but earliest among those dealt cards in retained creation/`sort_id` order, proving candidate ordering is not visible-hand order.

Cleanup mirrors both `Blind:disable()` and `Blind:defeat()` by clearing `forced_selection` across the authoritative permanent `G.playing_cards` object set with no RNG consumption, including a forced card outside the current hand.

```text
07662ee  own Cerulean Bell drawn_to_hand selection
0da847b  pin standalone drawn_to_hand behavior
9a9b125  compose Cerulean Bell blind start
9f5872a  pin full start composition
ffb804c  own forced-selection cleanup
aea440d  cleanup regressions
CI 33806003643: 1604 passed, 1594 deselected
CI 33806391869: 1610 passed, 1594 deselected
CI 33806527436: 1614 passed, 1594 deselected
```

#### R2.9i — Psychic / Flint / Tooth start-inert Boss boundary — GREEN FOR BLIND START ONLY

Vanilla source audit confirms these Bosses do not introduce additional state in `Blind:set_blind` or `Blind:drawn_to_hand`:

```text
The Psychic  → play-time hand legality: must play 5 cards
The Flint    → hand-scoring mutation: base Chips and Mult are halved
The Tooth    → play-time economy mutation: lose $1 per played card
```

They are intentionally classified separately from requirement-only Bosses. `prepare_supported_start_inert_boss_start()` owns only the ordinary Boss pre-deal lifecycle; `start_supported_start_inert_boss()` composes that boundary with exact shuffle/deal.

**This does not claim their downstream mechanics are headless-owned.** Psychic legality, Flint scoring, and Tooth economy remain explicit follow-up ownership work before a full trajectory through these Bosses can be considered run-safe.

```text
7e85cf0  classify start-inert Boss starts
fa329ff  pin start-inert Boss classification
CI 33809819965: 1622 passed, 1594 deselected
```

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Burglar purchase remains **FAIL-CLOSED** even though its `setting_blind` effect is owned for currently supported starts. A purchased Burglar persists across arbitrary future Bosses, so broader run-safe lifecycle coverage is still required before admitting it.

Known hard blockers:

- **The Pillar**: requires persistent per-card `played_this_ante` history
- **Verdant Leaf**: requires all-card debuff plus Joker-sale lifecycle
- **Amber Acorn**: Joker flip + seeded Joker-order shuffle
- face-down families (Wheel/House/Mark/Fish): require exact facing/round-event ownership
- Hook/random action-time branches and other Boss RNG not yet owned by the headless environment boundary
- Chicot Boss-disable composition, especially pre-deal Manacle disable requiring prior physical deck order
- prior-round zone cleanup for arbitrary trajectories
- active tag effects
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG
- remaining modeled random effects

### NEXT R2 WORK — DOWNSTREAM START-INERT BOSS MECHANICS

The blind-start audit for Psychic / Flint / Tooth is complete. The next code should audit and connect their **downstream** mechanics to the headless trajectory without duplicating canonical logic:

1. **The Psychic** — exact hand-play legality for “must play 5 cards”.
2. **The Flint** — exact base Chips/Mult halving at the canonical scoring boundary.
3. **The Tooth** — exact `$1 per played card` economy mutation at the canonical play boundary.

Take these as separate mechanically coherent slices. Reuse existing deterministic owners if they are exact; otherwise add the minimum canonical state/transition owner needed. Keep full `SELECT_BLIND` non-training-exposed until the resulting trajectories are run-safe.

Do **not** bypass Pillar/Verdant/Amber/face-down/Chicot blockers with approximations.

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
R2.5 round resources / bonus source order        GREEN — CI 33804894982
R2.6 Burglar setting_blind                       GREEN FOR AUDITED STARTS
R2.7 first round 0→1                             GREEN — CI 33797071526
R2.8 Small/Big start + deal                      GREEN — CI 33798795353
R2.9a Wall + Violet Vessel                       GREEN — CI 33799746434
R2.9b Eye + Mouth                                GREEN — CI 33800243393
R2.9c Water + Needle                             GREEN — CI 33801195935
R2.9d Manacle start/disable/defeat               GREEN ON OWNED BOUNDARIES
R2.9e Goad/Window/Head/Club                      GREEN — CI 33803874842
R2.9f Plant                                      GREEN — CI 33804343818
R2.9g pseudorandom_element                       GREEN — CI 33805699954
R2.9h Cerulean Bell start/draw/cleanup           GREEN — CI 33806527436
R2.9i Psychic/Flint/Tooth start only             GREEN — CI 33809819965
Psychic downstream legality                      NOT YET OWNED
Flint downstream scoring                         NOT YET OWNED
Tooth downstream economy                         NOT YET OWNED
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
fa329ff0eaf2019057037d5c9c9f185c4856c071
```

The next code written should therefore be the **downstream Psychic legality audit**, followed by Flint scoring and Tooth economy in separate exact slices, or a prerequisite exact owner discovered by those audits. It should **not** be Bond tuning, PPO, or an approximation of a blocked Boss lifecycle.