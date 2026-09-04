# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Non-negotiable contract

- Objective: **maximize P(clear Ante 8 | Red Deck, White Stake, normal mode)**.
- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported/inexact transitions stay absent from the training mask.
- Prefer canonical ownership over rescue wrappers or approximations.
- Manual Bond tuning is retired as the primary competence path.
- Do **not** start PPO/observation training before exactness + parity gates.
- Work Chat runs deterministic/static validation itself; GitHub Actions is authoritative when no local clone exists.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Never substitute `G.deck.cards` for permanent owned-deck truth; permanent deck source is `G.playing_cards`.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, `--five`; retain the canonical attempt-count interface.

---

# Completed foundation

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
R0 headless environment architecture COMPLETE
```

L3 contract: `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`.

Key historical gates:

```text
33758680261  1223 passed, 1594 deselected
33760179448  1233 passed, 1594 deselected
```

Do not request another open-ended live batch at this stage.

---

# Phase R — exact headless Balatro environment — ACTIVE

The simulator is not authoritative game truth until R5 live/simulator parity passes.

## R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

Generic acquisition is not “append inventory + subtract money.” Persistent consequences must be exact.

Exact resource-sensitive acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

The audited inventory-only score/rule/retrigger Joker set is owned incrementally in `ShopTransitionEngine`, including passive-rule, hand-shape, suit, conditional, money, owned-deck, and retrigger groups.

Permanent-deck authority:

- `G.playing_cards` only;
- all-or-nothing observation/translation;
- partial LuaJIT/TValue reads fail closed;
- malformed/count-mismatched cards make `owned_deck = None`;
- Steel Joker, Stone Joker, Driver's License, and Erosion are exact-gated on permanent owned deck.

Key R1 hardening gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Still fail closed:

- unknown/unaudited Joker acquisitions;
- Joker editions, especially Negative;
- generic voucher acquisition;
- packs until exact RNG/pack state exists;
- `SELL_JOKER` until inverse lifecycle effects exist;
- malformed/noninteger prices.

---

## R2 — RNG + round/blind/Boss lifecycle — ACTIVE / CURRENT PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

Keyed pseudohash/pseudoseed over LuaJIT combined Tausworthe RNG; never Python `random`.

```text
2e61cd8  RNG primitives
290ff11  pinned vectors
CI 33791671797: 1432 passed, 1594 deselected
```

### R2.2 — pseudoshuffle — GREEN

One keyed pseudoseed advance, then one LuaJIT RNG stream drives Fisher–Yates.

```text
246f442  pseudoshuffle
d9662c6  vectors
CI 33791916289: 1435 passed, 1594 deselected
```

### R2.3 — playing-card creation order/private RNG — GREEN

Exact order only from unique integer live `playing_card` IDs or untouched vanilla one-of-each 52-card structure. Otherwise fail closed. No fake public `sort_id`.

```text
CI 33795507133: 1461 passed, 1594 deselected
```

### R2.4 — complete-deck exact shuffle/deal — GREEN FOR SUPPORTED DECKS

`deal_supported_round_start()` owns exact physical shuffle/deal while public `deck` remains canonicalized and does not reveal future order. `draw_one_supported_card_to_hand()` uses only an already-owned private physical draw pile.

```text
CI 33803629167: 1563 passed, 1594 deselected
```

### R2.5 — round resources/one-shot bonuses — GREEN

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

Bonuses are consumed before Boss `set_blind` and Joker `setting_blind` effects.

```text
CI 33804894982: 1593 passed, 1594 deselected
```

### R2.6 — Burglar `setting_blind` — GREEN FOR AUDITED STARTS

```text
hands += 3
discards_remaining = 0
```

Unknown lifecycle Jokers fail closed. Burglar acquisition remains fail-closed because a bought Burglar persists into future arbitrary lifecycle states.

### R2.7 — first-round parity — GREEN

Vanilla `G.GAME.round` initializes at 0 and first select-blind queues `ease_round(1)` before `new_round()`.

```text
CI 33797071526: 1482 passed, 1594 deselected
```

### R2.8 — Small/Big Blind start — GREEN

```text
CI 33798795353: 1497 passed, 1594 deselected
```

### R2.9 — Boss lifecycle — ACTIVE

Owned Boss slices:

```text
Wall + Violet Vessel            requirement-only             GREEN  CI 33799746434
Eye + Mouth                     mutable hand-rule             GREEN  CI 33800243393
Water + Needle                  reversible resources         GREEN  CI 33801195935
Manacle                         reversible hand size         GREEN  on owned boundaries
Goad/Window/Head/Club           static suit card debuffs     GREEN  CI 33803874842
Plant                           face-card debuffs             GREEN  CI 33804343818
pseudorandom_element            source-exact selection       GREEN  CI 33805699954
Cerulean Bell                   forced-selection lifecycle   GREEN  CI 33806527436
Psychic                         downstream hand rejection    GREEN  CI 33838722781
Flint                           downstream base-score halve  GREEN  CI 33838934769
Tooth                           -$1 per played card          GREEN  CI 33839102154
Hook                            keyed forced discards        GREEN  CI 33839910429
Ox                              matching hand -> money = 0   GREEN  CI 33841056452
Arm                             level > 1 -> level - 1       GREEN  CI 33841056452
Serpent                         post-action 3-card draw       GREEN  CI 33843165212
```

#### Start-inert Boss family — GREEN

Current audited members:

```text
The Psychic
The Flint
The Tooth
The Hook
The Ox
The Arm
The Serpent
```

They have no additional `Blind:set_blind` / initial `Blind:drawn_to_hand` mutation; downstream effects are owned separately.

#### Hook exact semantics

At `Blind:press_play`:

1. player-selected play cards are already excluded from candidates;
2. choose up to two remaining hand cards using keyed `pseudorandom_element(..., "hook")` semantics;
3. remove first candidate before second selection;
4. move forced cards to discard;
5. do not decrement discard allowance;
6. do not draw replacements;
7. preserve exact RNG state.

Current narrow Hook implementation fails closed when unowned Joker/seal discard triggers would fire.

#### Ox exact semantics

- authoritative fixed target is `G.GAME.current_round.most_played_poker_hand`;
- process-memory observer now exposes that public field;
- existing translator canonicalizes live names, e.g. `"Pair"` → `PAIR`;
- headless owner uses `BalatroState.round_most_played_hand` and **never recomputes** from mutable counts;
- match sets money exactly to `0`, including from negative money;
- missing/invalid target fails closed.

Relevant commits:

```text
0940a54  Ox headless economy
5eb7964  Ox regressions
226f148  observe live Ox round target
e11ac21  live observer/translator regressions
5169f7f  classify Ox start-inert
6a4a726  Ox start-inert tests
```

#### Arm exact semantics

Vanilla `Blind:debuff_hand` decrements the classified hand level only when level > 1. Canonical scoring already derives base Chips/Mult from `BalatroState.hand_levels`, so no duplicate Chips/Mult state is required.

Relevant commits:

```text
706173b  Arm hand-level decrement
6ab2683  Arm downstream regressions
735c181  classify Arm start-inert
a62b53a  Arm start-inert regressions
```

#### Serpent exact semantics

Vanilla `draw_from_deck_to_hand` overrides ordinary free-hand-capacity draw after at least one play or discard while The Serpent is enabled:

```text
draw_count = min(#remaining_deck, 3)
```

The dedicated headless owner:

- uses authoritative current-round play/discard history;
- uses the private physical draw pile and never leaks future order;
- may grow the hand above nominal hand capacity, as vanilla does;
- re-sorts the resulting hand using the exact owned-card sort boundary;
- consumes no RNG;
- fails closed for unknown history, private/public deck mismatch, wrong phase, wrong Boss, or disabled Serpent;
- composes with the audited start-inert Boss start and exact initial shuffle/deal.

Relevant commits:

```text
3a72e25  Serpent post-action draw owner
dbe52d8  Serpent downstream regressions
592081d  classify Serpent start-inert
fca90dc  start-inert family regression
723c8a5  composed start -> play-history -> Serpent draw regression
```

Current Serpent-composed gate:

```text
CI 33843165212: 1675 passed, 1594 deselected
```

### NEXT R2 WORK — FACE-DOWN / FACING STATE OWNERSHIP

Source audit identifies a mechanically related Boss family whose semantics depend on card-facing state:

```text
The House
The Wheel
The Mark
The Fish
```

Do **not** classify these as start-inert yet. `BalatroCard` currently has no authoritative facing/face-down field, so exact headless transitions cannot represent their visible hidden-card state.

Next implementation order:

1. audit exact vanilla `Blind:set_blind`, `Blind:drawn_to_hand`, `Blind:press_play`, disable/defeat flip behavior for all four;
2. add the minimum canonical **public** facing state needed to represent what the player can see, without leaking rank/suit information through observations when a card is face down;
3. wire live observer + translator exactness for facing state;
4. add deterministic draw/flip lifecycle owners per mechanically coherent Boss subgroup;
5. keep public future draw order private;
6. add source-pinned regressions and fail-closed tests;
7. only then widen Boss-start ownership.

The current audit already confirms vanilla flips any remaining face-down hand cards back face-up when these Bosses are disabled/defeated; that inverse lifecycle must be owned too.

### Current hard blockers / later Boss categories

- Pillar — persistent per-card `played_this_ante` history
- Verdant Leaf — all-card debuff + Joker-sale lifecycle
- Amber Acorn — Joker flip + seeded Joker-order shuffle
- Crimson Heart — per-hand random Joker debuff lifecycle
- Chicot composition, especially pre-deal Manacle
- prior-round arbitrary zone cleanup
- active tags
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Every training-visible action requires exact legality, transition, serialization, and mask representation. `SELECT_BLIND` remains hidden until R2/R3 exact ownership is broad enough.

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity — NOT STARTED

Priority fixtures: shop paths, blind skip/start/clear, Boss restrictions, lifecycle-sensitive Jokers, owned deck, economy, RNG/shuffle/draw parity.

## R6 — performance gate — NOT STARTED

Measure throughput only after semantics/parity are correct.

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
R1 deterministic state/acquisition     SUBSTANTIALLY COMPLETE
R2 RNG / round / Boss lifecycle        ACTIVE
R2 start-inert family                  GREEN THROUGH SERPENT
R2 Hook downstream                     GREEN — CI 33839910429
R2 Ox downstream + live target         GREEN — CI 33841056452
R2 Arm downstream                      GREEN — CI 33841056452
R2 Serpent downstream + composition    GREEN — CI 33843165212
NEXT                                   FACE-DOWN / FACING STATE OWNERSHIP
SELECT_BLIND                           NOT EXPOSED
Burglar acquisition                    FAIL-CLOSED
Generic/unknown acquisitions           FAIL-CLOSED
Joker editions                         FAIL-CLOSED
Generic vouchers/packs                 FAIL-CLOSED
SELL_JOKER                             FAIL-CLOSED
R4 tactical bridge                     NOT STARTED
R5 parity                              NOT STARTED
R6 performance                         NOT STARTED
Observation/PPO                        NOT STARTED
```

Current branch code head immediately before this roadmap synchronization:

```text
723c8a56ba536589df508c1c4c5a2e113ffbae0c
```

The next code written should therefore be **exact public facing-state ownership and the source-audited House/Wheel/Mark/Fish lifecycle**, beginning with observer/translator/schema exactness. It should **not** be Bond tuning, PPO, or an approximation that exposes hidden card information.
