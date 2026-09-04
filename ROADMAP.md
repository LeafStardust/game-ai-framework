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

Generic acquisition is not “append inventory + subtract money.” Every persistent consequence must be exact.

Hard fail-closed surfaces include:

- Joker editions, especially Negative
- unknown/unaudited Joker identities
- generic voucher acquisition
- packs until exact pack/RNG state exists
- `SELL_JOKER` until inverse lifecycle effects exist
- malformed/noninteger prices

Exact resource-sensitive acquisitions currently include:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

The exact inventory-only score/rule/retrigger acquisition set is implemented incrementally and includes the audited passive-rule, hand-shape, suit, static conditional, money-scoring, owned-deck-scoring, and retrigger groups already present in `ShopTransitionEngine`.

### Permanent owned deck — GREEN

Exact deck-dependent Jokers include Steel Joker, Stone Joker, Driver's License, and Erosion.

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

Exact private order is reconstructable only from unique integer live `playing_card` IDs or the untouched vanilla one-of-each 52-card deck. Unprovable order fails closed. No fake public `sort_id` is introduced.

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

Transient Boss debuffs are supported on an otherwise exact base deck without leaking physical draw order.

```text
1ce2662  allow exact transient-debuff base deals
8bb5ae1  pin transient-debuff deal invariants
CI 33803629167: 1563 passed, 1594 deselected
```

`draw_one_supported_card_to_hand()` may draw only from an already-authoritative private physical draw pile. Never reconstruct future physical draw order from the public canonical deck.

### R2.5 — round resources / one-shot bonuses — GREEN

Vanilla baseline:

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

Canonical source order is: compute current-round allowances, immediately clear one-shot bonus fields, then execute `Blind:set_blind` and Joker `setting_blind` effects.

```text
2462a9f  match vanilla round-bonus consumption order
af80d5a  pin source-order regressions
CI 33804894982: 1593 passed, 1594 deselected
```

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

Unknown lifecycle identities fail closed. Burglar acquisition itself remains fail-closed because a purchased Burglar persists into arbitrary future unsupported lifecycle states.

### R2.7 — first-round counter parity — GREEN

Vanilla `G.GAME.round` begins at `0`; selecting the first blind increments it before `new_round()`. First start is `0 → 1`.

```text
CI 33797071526: 1482 passed, 1594 deselected
```

### R2.8 — Small/Big Blind start — GREEN

`prepare_supported_nonboss_blind_start()` owns exact pre-deal lifecycle; `start_supported_nonboss_blind()` composes it with exact generalized shuffle/deal.

```text
CI 33798795353: 1497 passed, 1594 deselected
CI 33796012173: 1467 passed, 1594 deselected
```

### R2.9 — Boss blind lifecycle — ACTIVE

Bosses are admitted only by source-audited exact semantics.

#### R2.9a — requirement-only Bosses — GREEN

```text
The Wall
Violet Vessel
CI 33799746434: 1509 passed, 1594 deselected
```

#### R2.9b — mutable hand-rule Bosses — GREEN

```text
The Eye
The Mouth
CI 33800243393: 1518 passed, 1594 deselected
```

Start initializes the canonical empty mutable Boss hand restriction/history state.

#### R2.9c — Water / Needle reversible resources — GREEN

Water removes current post-baseline discards and stores the exact reversal amount. Needle removes `round_reset_hands - 1`, preserving one-shot hand-bonus semantics. `Blind:disable()` restoration is owned.

```text
CI 33801195935: 1542 passed, 1594 deselected
```

#### R2.9d — The Manacle — GREEN ON OWNED POST-DEAL BOUNDARY

```text
start:          hand_size -= 1
Blind:disable: hand_size += 1; draw one replacement from authoritative physical draw pile
Blind:defeat:  hand_size += 1; no replacement draw
```

Pre-deal Chicot + Manacle remains fail-closed because the replacement draw occurs before the normal round-start shuffle and depends on the actual carried physical deck order from the previous round.

#### R2.9e — static suit card-debuff Bosses — GREEN

```text
The Goad    → Spades
The Window  → Diamonds
The Head    → Hearts
The Club    → Clubs
```

```text
8af8dae  own static suit Boss card debuffs
0baef57  compose static suit Boss start lifecycle
3262dcc  regressions
CI 33803874842: 1583 passed, 1594 deselected
```

#### R2.9f — The Plant — GREEN

Uses exact vanilla `card:is_face(true)` semantics; Pareidolia therefore makes every playing card a face card. Cleanup removes only Plant-owned transient debuffs.

```text
CI 33804343818: 1593 passed, 1594 deselected
```

#### R2.9g — exact `pseudorandom_element` — GREEN

Source-correct semantics:

```lua
math.randomseed(seed)
collect candidates
sort by value.sort_id when present, otherwise key
choose exactly one math.random(#keys)
```

No Fisher–Yates shuffle occurs inside `pseudorandom_element`.

```text
08153fc  match vanilla pseudorandom_element selection
5bb7ee6  corrected vectors
CI 33805699954: 1598 passed, 1594 deselected
```

Superseded exploratory commits `cf87867` / `8a6a351` are not authoritative.

#### R2.9h — Cerulean Bell start/drawn_to_hand/cleanup — GREEN

Exact ownership:

```text
ordinary Boss pre-deal lifecycle
→ exact shuffle/deal
→ sort current hand candidates by retained playing-card creation/sort_id order
→ pseudorandom_element("cerulean_bell")
→ set exactly one card.forced_selection
```

One existing forced card consumes no RNG; multiple pre-existing forced cards fail closed. `Blind:disable()` / `Blind:defeat()` cleanup clears forced selection across the authoritative permanent deck.

```text
07662ee  own drawn_to_hand selection
0da847b  standalone regressions
9a9b125  compose full start
9f5872a  full-start regressions
ffb804c  own cleanup
aea440d  cleanup regressions
CI 33806003643: 1604 passed, 1594 deselected
CI 33806391869: 1610 passed, 1594 deselected
CI 33806527436: 1614 passed, 1594 deselected
```

#### R2.9i — Psychic / Flint / Tooth start-inert Boss start — GREEN

Vanilla confirms these Bosses add no extra state during `Blind:set_blind` or `Blind:drawn_to_hand`.

```text
7e85cf0  classify start-inert Boss starts
fa329ff  pin classification
CI 33809819965: 1622 passed, 1594 deselected
```

#### R2.9j — The Psychic downstream play/scoring semantics — GREEN

**Semantic correction:** “Must play 5 cards” is not an action-legality ban in vanilla Balatro. Plays of 1–4 cards are accepted, then `Blind:debuff_hand` rejects the hand for scoring. Those plays can therefore deliberately burn/cycle a hand.

Canonical ownership is reused rather than duplicated:

- `boss_play_action_is_legal()` keeps the play admissible;
- `boss_hand_is_debuffed()` triggers for fewer than five played cards;
- `LiveFinalJokerScoreOutcomeModel` / `BossBaseScoreScorerMixin` project the accepted play as exactly zero score;
- five-card plays follow ordinary scoring.

```text
89ffd84  pin Psychic downstream scoring semantics
CI 33838722781: 1625 passed, 1594 deselected
```

#### R2.9k — The Flint downstream scoring semantics — GREEN

Vanilla `Blind:modify_hand` rounds each current base component to half:

```text
base Mult  = max(floor(mult * 0.5 + 0.5), 1)
base Chips = max(floor(chips * 0.5 + 0.5), 0)
```

For positive integral base values this is exact ceil-halving. Existing `BossBaseScoreScorerMixin` already applies the transform at the correct boundary **before ordinary scoring-card/Joker additions**; no duplicate mechanics owner was added.

```text
df4537b  pin Flint downstream scoring semantics
CI 33838934769: 1628 passed, 1594 deselected
```

#### R2.9l — The Tooth downstream press-play economy — GREEN

Vanilla `Blind:press_play` charges exactly `$1` for each played card. There was no existing exact Python owner, so `games/balatro/env/boss_play.py` now owns only that narrow source boundary.

Exact contract:

- active only for The Tooth at `SELECTING_HAND`;
- requires canonical `PLAY_CARDS` with 1–5 unique authoritative current-hand card objects;
- `money -= number_of_played_cards`;
- negative money is allowed, matching vanilla `ease_dollars` behavior;
- no RNG or card-zone mutation;
- wrong boss/action/phase or copied/non-authoritative cards fail closed.

```text
6e13894  own Tooth press-play economy
27956b0  pin Tooth downstream economy semantics
CI 33839102154: 1635 passed, 1594 deselected
```

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Known hard blockers include:

- **The Pillar** — persistent per-card `played_this_ante` history
- **Verdant Leaf** — all-card debuff plus Joker-sale lifecycle
- **Amber Acorn** — Joker flip + seeded Joker-order shuffle
- face-down families (Wheel/House/Mark/Fish) — exact facing and round-event ownership
- The Hook and other action-time/random Boss effects not yet owned by the headless transition boundary
- Chicot Boss-disable composition, especially pre-deal Manacle
- prior-round zone cleanup for arbitrary trajectories
- active tag effects
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG
- remaining modeled random effects

### NEXT R2 WORK — ACTION-TIME BOSS EFFECTS

The start-inert Psychic / Flint / Tooth downstream audit is complete and green. The next coherent R2 work is the **action-time Boss family**, starting with **The Hook** because exact `pseudorandom_element` is already owned.

Before admitting The Hook, source-audit and own the complete press-play consequence in vanilla order:

1. determine the exact candidate set from the current hand after the player's chosen play is committed/highlighted;
2. use keyed `pseudorandom_element(..., pseudoseed("hook"))` for each forced discard with correct candidate removal between selections;
3. reproduce the exact forced-discard zone transition and confirm whether replacement draw is suppressed on this Boss-forced path;
4. preserve RNG snapshot/replay equivalence;
5. fail closed if private physical-zone ownership is insufficient.

Only after that slice is green should the next action-time Boss be admitted. Do not skip to face-down/Pillar/Verdant/Amber/Chicot paths by approximation.

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
R2 exact RNG / round & Boss lifecycle            ACTIVE
R2.1 LuaJIT RNG                                  GREEN — CI 33791671797
R2.2 pseudoshuffle                               GREEN — CI 33791916289
R2.3 creation order / private RNG                GREEN — CI 33795507133
R2.4 complete-deck exact deal                    GREEN FOR SUPPORTED DECKS
R2.5 round resources / bonus order               GREEN — CI 33804894982
R2.6 Burglar setting_blind                       GREEN FOR AUDITED STARTS
R2.7 first round 0→1                             GREEN — CI 33797071526
R2.8 Small/Big start + deal                      GREEN — CI 33798795353
R2.9a Wall + Violet Vessel                       GREEN — CI 33799746434
R2.9b Eye + Mouth                                GREEN — CI 33800243393
R2.9c Water + Needle                             GREEN — CI 33801195935
R2.9d Manacle                                    GREEN ON OWNED BOUNDARIES
R2.9e Goad/Window/Head/Club                      GREEN — CI 33803874842
R2.9f Plant                                      GREEN — CI 33804343818
R2.9g pseudorandom_element                       GREEN — CI 33805699954
R2.9h Cerulean Bell                              GREEN — CI 33806527436
R2.9i Psychic/Flint/Tooth blind start            GREEN — CI 33809819965
R2.9j Psychic downstream                         GREEN — CI 33838722781
R2.9k Flint downstream                           GREEN — CI 33838934769
R2.9l Tooth downstream                           GREEN — CI 33839102154
The Hook action-time lifecycle                    NEXT / NOT YET OWNED
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
27956b0dc4af8df5c6b05094b9e04e39685ba594
```

The next code written should therefore be the **source-audited The Hook action-time transition**, or a prerequisite exact card-zone owner discovered by that audit. It should **not** be Bond tuning, PPO, or an approximation of another blocked Boss lifecycle.
