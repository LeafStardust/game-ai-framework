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

Exact resource-sensitive acquisitions include:

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

Vanilla `G.GAME.round` begins at `0`; `G.FUNCS.select_blind` queues `ease_round(1)` before `new_round()`. First start is exactly `0 → 1`.

```text
CI 33797071526: 1482 passed, 1594 deselected
CI 33796012173: 1467 passed, 1594 deselected
```

### R2.8 — Small/Big Blind start — GREEN

`prepare_supported_nonboss_blind_start()` owns exact pre-deal lifecycle; `start_supported_nonboss_blind()` composes it with exact generalized shuffle/deal.

```text
CI 33798795353: 1497 passed, 1594 deselected
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
CI 33803874842: 1583 passed, 1594 deselected
```

#### R2.9f — The Plant — GREEN

Uses exact vanilla `card:is_face(true)` semantics; Pareidolia therefore makes every playing card a face card. Cleanup removes only Plant-owned transient debuffs.

```text
CI 33804343818: 1593 passed, 1594 deselected
```

#### R2.9g — exact `pseudorandom_element` — GREEN

Source-correct semantics: seed once, sort candidates by `sort_id`/key, choose one LuaJIT random index. No Fisher–Yates shuffle occurs inside `pseudorandom_element`.

```text
08153fc  match vanilla pseudorandom_element selection
5bb7ee6  corrected vectors
CI 33805699954: 1598 passed, 1594 deselected
```

#### R2.9h — Cerulean Bell — GREEN

Exact start/deal, creation-order-sorted hand candidates, `pseudorandom_element("cerulean_bell")`, forced-selection state, and disable/defeat cleanup are owned.

```text
CI 33806527436: 1614 passed, 1594 deselected
```

#### R2.9i — start-inert Boss start family — GREEN FOR AUDITED MEMBERS

Current audited members:

```text
The Psychic
The Flint
The Tooth
The Hook
```

They add no extra mutation during `Blind:set_blind` / initial `Blind:drawn_to_hand`; downstream mechanics are owned separately.

```text
7e85cf0  initial classification
fa329ff  initial regressions
efc54b0  classify Hook as start-inert
503ed85  include Hook in start-inert regression set
CI 33839910429: 1643 passed, 1594 deselected
```

#### R2.9j — The Psychic downstream — GREEN

1–4 card plays remain legal but are rejected by `Blind:debuff_hand` for scoring; five-card plays score normally.

```text
89ffd84
CI 33838722781: 1625 passed, 1594 deselected
```

#### R2.9k — The Flint downstream — GREEN

```text
base Mult  = max(floor(mult * 0.5 + 0.5), 1)
base Chips = max(floor(chips * 0.5 + 0.5), 0)
```

Existing canonical scoring ownership applies this before ordinary card/Joker additions.

```text
df4537b
CI 33838934769: 1628 passed, 1594 deselected
```

#### R2.9l — The Tooth downstream — GREEN

At `Blind:press_play`, money decreases exactly `$1` per played card; negative money is allowed.

```text
6e13894  exact Tooth press-play owner
27956b0  regressions
CI 33839102154: 1635 passed, 1594 deselected
```

#### R2.9m — The Hook downstream forced discards — GREEN

Exact `Blind:press_play` ownership:

1. player's chosen play cards are excluded from Hook candidates because vanilla has already moved them to `G.play`;
2. select up to two remaining hand cards with keyed `pseudorandom_element(..., pseudoseed("hook"))`;
3. remove the first selected candidate before the second draw;
4. move forced cards to discard in visible-hand order;
5. do **not** decrement `discards_remaining`;
6. do **not** draw replacements or change phase;
7. preserve exact RNG snapshot/replay state.

Current narrow implementation fails closed when Joker/seal discard triggers would need additional lifecycle ownership.

```text
80c0136  own Hook forced-discard boundary
0f94698  pin Hook press-play forced discards
efc54b0  classify Hook as start-inert
503ed85  corrected start-inert regression
CI 33839910429: 1643 passed, 1594 deselected
```

#### R2.9n — The Ox downstream economy — HEADLESS GREEN; LIVE TARGET WIRING ACTIVE

Vanilla `Blind:debuff_hand` compares the classified hand against the fixed public `G.GAME.current_round.most_played_poker_hand`. On a match it executes `ease_dollars(-G.GAME.dollars, true)`, making money exactly `0` even from a negative balance.

Headless exact owner:

- `games/balatro/env/boss_hand.py::apply_ox_debuff_hand_economy`
- uses canonical `BalatroState.round_most_played_hand` only;
- **does not recompute** the target from mutable aggregate hand counters;
- missing/invalid target fails closed;
- disabled Boss is inert.

```text
0940a54  own Ox debuff-hand economy
5eb7964  pin Ox economy regressions
CI 33840439252: 1649 passed, 1594 deselected
```

Remaining work before Ox is fully classified:

1. expose authoritative `G.GAME.current_round.most_played_poker_hand` from the process-memory observer into the existing translator path;
2. add observer/translator regressions proving live `"Pair"` → canonical `PAIR` and missing/invalid values remain unknown;
3. classify The Ox as start-inert only after that live/public field path is green.

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Known hard blockers include:

- **The Pillar** — persistent per-card `played_this_ante` history
- **Verdant Leaf** — all-card debuff plus Joker-sale lifecycle
- **Amber Acorn** — Joker flip + seeded Joker-order shuffle
- face-down families (Wheel/House/Mark/Fish) — exact facing and round-event ownership
- Crimson Heart — per-hand random Joker debuff lifecycle
- The Arm — poker-hand level decrement lifecycle not yet audited into R2 owner
- Chicot Boss-disable composition, especially pre-deal Manacle
- prior-round zone cleanup for arbitrary trajectories
- active tag effects
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG
- remaining modeled random effects

### NEXT R2 WORK — COMPLETE OX PUBLIC-STATE PATH, THEN THE ARM

Immediate order:

1. wire `current_round.most_played_poker_hand` through live process-memory observation;
2. gate Ox observer/translator parity tests;
3. add Ox to the exact start-inert Boss set;
4. sync this roadmap with the resulting CI;
5. then source-audit **The Arm**, whose downstream effect is deterministic hand-level decrement when the played hand level is above 1.

Do not skip to face-down/Pillar/Verdant/Amber/Chicot paths by approximation.

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
R2.9i start-inert Boss family                    GREEN THROUGH HOOK — CI 33839910429
R2.9j Psychic downstream                         GREEN — CI 33838722781
R2.9k Flint downstream                           GREEN — CI 33838934769
R2.9l Tooth downstream                           GREEN — CI 33839102154
R2.9m Hook downstream                            GREEN — CI 33839910429
R2.9n Ox downstream                              HEADLESS GREEN — CI 33840439252; LIVE TARGET WIRING ACTIVE
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
5eb7964967871522b09ddf11694ec2d6b60e47fa
```

The next code written should therefore be the **exact live/public Ox target wiring and regression gate**, followed by **The Arm** only after Ox is fully green. It should **not** be Bond tuning, PPO, or an approximation of another blocked Boss lifecycle.
