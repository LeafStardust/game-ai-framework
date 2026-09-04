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
- Face-down card identity is **not public information**. Headless simulation may retain true identity internally for exact mechanics, but policy observations must mask it.

---

# Required development procedure

## Start from repository truth

For every continuation session:

1. read the current `ROADMAP.md` first;
2. verify current branch/head before editing;
3. inspect the canonical owner(s) for the next roadmap task;
4. check for intervening commits before writing;
5. treat chat/session summaries as navigation aids only — repository state is authoritative.

Target branch:

```text
feat/v1.0-red-white-competence
```

`ROADMAP.md` is the single source of truth for phase status, blockers, next work, and validation state. Update it after green checkpoints that materially change those.

## Small exact slices

For each mechanics/state/lifecycle slice:

1. audit vanilla/source behavior and existing production owners;
2. classify the exact missing ownership boundary;
3. patch the canonical owner rather than adding a rescue wrapper;
4. add focused deterministic regressions, including rejection/fail-closed behavior where relevant;
5. keep unsupported composition unavailable rather than approximating it;
6. run the deterministic CI gate;
7. inspect the actual pytest result and selection count;
8. only then mark the slice GREEN and synchronize this roadmap.

Do not bulk-admit Jokers/actions merely because nearby classes are supported. Audit counters, RNG, economy, card mutation, sell/destruction behavior, lifecycle state, and persistent consequences individually.

## Source-audit rule

When exact Balatro behavior is unclear, trace the pinned vanilla implementation or an already-validated canonical repository owner before coding. Do not infer exact mechanics from UI behavior, names, memory, wiki prose, or Python convenience semantics when source-exact behavior is available.

Current vanilla source pin used for audits:

```text
GladdonT/balatro-source-code
895ab3a25bc6f513fa80885eb59951bf8e76bc55
```

If that source reference changes, record the new pin before depending on it for deterministic parity work.

## Fail-closed rule

If exactness cannot be proved at the modeled boundary:

- reject the transition/action;
- omit it from the training mask;
- preserve `None`/unobserved state where applicable;
- do not silently substitute a related public field;
- do not add synthetic state merely to make a transition convenient unless source-justified and lifecycle-owned.

Examples already enforced:

- permanent owned deck is `G.playing_cards`, never `G.deck.cards`;
- partial LuaJIT array reads make owned-deck observation unavailable rather than shorter;
- future physical draw order remains private;
- face-down identity remains masked from policy observations;
- Python `random` is not a substitute for Balatro/LuaJIT RNG.

## Deterministic pytest procedure — GitHub Actions is the Work Chat gate

Work Chat does **not** ask the user to pull and run deterministic pytest when GitHub Actions can run it.

Authoritative workflow:

```text
.github/workflows/balatro-l3.yml
```

Current command:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

Required procedure after a relevant push:

1. locate the workflow run for the exact pushed commit/head;
2. wait for `balatro-deterministic-tests` to complete;
3. require workflow/job conclusion `success`;
4. inspect the job log's final pytest line;
5. record exact `passed` and `deselected` counts when reporting a gate;
6. confirm the intended new test family was actually selected by the `-k` expression;
7. if new tests were deselected, fix CI selection and rerun before calling the slice GREEN.

A green workflow badge alone is **not sufficient evidence**. Historical example: the first R2 card-order workflow succeeded while six `env_r2` tests were deselected; the selector was corrected to include `env_r2`, and only the corrected run counted.

Do not claim local pytest ran unless a real local repository/runtime exists in the current environment.

## Commit/push procedure

The user has authorized pushing completed commits to the remote branch.

- Push coherent completed implementation/test/doc slices without repeatedly asking permission.
- Prefer separate implementation and focused regression commits when useful for auditability.
- Do not claim a commit/push exists without GitHub evidence.
- Do not stack large unrelated mechanics changes behind an unverified gate.
- Synchronize this roadmap after green checkpoints so another session can resume exactly.

## Live Balatro validation procedure

Do **not** ask the user to run Balatro for deterministic/static questions CI can answer.

Request a Windows/live Balatro run only when uncertainty genuinely depends on live game integration, memory observation, runtime parity, UI/execution behavior, or another condition that source + deterministic tests cannot establish. When one is required, state exactly what run/evidence is needed rather than asking for an open-ended batch.

Standing instruction: **no open-ended live batch** unless a later roadmap gate explicitly requires one.

## Scope/context discipline

- Follow the roadmap's current primary workstream; do not pivot back to Bond coefficient tuning.
- Do not start PPO/observation training before the roadmap gates permit it.
- Do not reintroduce retired legacy attempt flags; use the canonical attempt-count interface.
- If context becomes insufficient to continue safely, stop rather than guessing or making an ungrounded large change. Resume from repository + roadmap truth in the next session.

---

# Completed foundation

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
R0 headless environment architecture COMPLETE
```

L3 contract: `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`.

Historical gates:

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
Tooth                           -$1 per played card           GREEN  CI 33839102154
Hook                            keyed forced discards         GREEN  CI 33839910429
Ox                              matching hand -> money = 0   GREEN  CI 33841056452
Arm                             level > 1 -> level - 1       GREEN  CI 33841056452
Serpent                         post-action 3-card draw       GREEN  CI 33843165212
House + Mark                    deterministic card facing    GREEN  CI 33845952545
Wheel                           keyed per-draw card facing    GREEN  CI 33846232884
Fish                            temporal post-play facing     GREEN  CI 33846610717
Pillar                          permanent Ante card history  GREEN  CI 33850320184
```

### Start-inert Boss family — GREEN

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

### Selected owned Boss semantics

#### Hook

At `Blind:press_play`:

1. player-selected cards are excluded from candidates;
2. choose up to two remaining hand cards using keyed `pseudorandom_element(..., "hook")`;
3. remove first candidate before second selection;
4. move forced cards to discard;
5. do not decrement discard allowance;
6. do not draw replacements;
7. preserve exact RNG state.

#### Ox

- authoritative target is `G.GAME.current_round.most_played_poker_hand`;
- observer exposes it and translator canonicalizes names;
- headless owner uses `BalatroState.round_most_played_hand` and never recomputes it;
- a match sets money exactly to `0`, including from negative money;
- missing/invalid target fails closed.

#### Arm

Vanilla `Blind:debuff_hand` decrements the classified hand level only when level > 1. Canonical scoring derives base Chips/Mult from `BalatroState.hand_levels`; no duplicate Chips/Mult state is used.

#### Serpent

After at least one play or discard:

```text
draw_count = min(#remaining_deck, 3)
```

Uses authoritative action history and private physical draw order, may grow the hand above nominal capacity, consumes no RNG, and fails closed on unknown history/private-public mismatch.

```text
CI 33843165212: 1675 passed, 1594 deselected
```

### R2.10 — face-down/facing state — GREEN FOR HOUSE/WHEEL/MARK/FISH

Canonical card state includes:

```text
BalatroCard.face_down
BalatroCard.facing_observed
```

Live observer/translator preserves authoritative facing. Policy observations mask face-down rank/suit/hidden modifiers and `live_id`; internal simulation retains true identity for exact mechanics. Future physical draw order remains private.

#### House + Mark

```text
CI 33845952545: 1686 passed, 1595 deselected
```

#### Wheel

Per physical drawn card:

```text
face_down = pseudorandom(pseudoseed("wheel")) < probabilities.normal / 7
```

One keyed `wheel` RNG advance per physical draw. Current exact boundary requires normal probability state; unsupported probability-modifying composition fails closed.

```text
CI 33846232884: 1692 passed, 1595 deselected
```

#### Fish

Temporal behavior is owned atomically rather than inventing a persistent simulator flag:

```text
initial draw     face up
post-play draw   new cards face down
post-discard     new cards face up
```

```text
CI 33846610717: 1700 passed, 1595 deselected
```

### R2.11 — Pillar / permanent `played_this_ante` history — GREEN

Vanilla Pillar depends on each permanent playing card's persistent:

```text
card.ability.played_this_ante
```

Owned state/lifecycle:

- canonical card fields track both value and observation exactness;
- `G.playing_cards` process-memory observation exposes permanent-card history;
- translator carries that history fail-closed into `BalatroCard`;
- accepted `PLAY_CARDS` marking sets selected permanent cards `played_this_ante = True` without pretending to own the entire play transition;
- new-Ante cleanup clears the flag across the permanent deck;
- pristine fresh Red/White initialization establishes authoritative `False` history only for the exact untouched 52-card base run;
- live snapshots never replace observed history with pristine defaults;
- Pillar debuffs exactly the cards marked as played earlier in the current Ante;
- Pillar cleanup clears transient debuff state while retaining Ante history until the actual new-Ante reset;
- any missing permanent-card history observation causes Pillar start/mutation to fail closed;
- public-policy safety remains unchanged: persistent play history does not grant hidden card identity.

Relevant commits:

```text
caf0e08  track permanent played-this-ante state
4c27da8  exact Pillar history debuff
5e946d4  integrate exact Pillar blind start
28a500c  Pillar history debuff regressions
e158a25  observe permanent played-this-ante state
0ee5195  translate permanent played-this-ante state
2ece03c  live Pillar history observation regressions
182bd77  permanent played-this-ante lifecycle
d51ba14  permanent Ante history lifecycle regressions
d87701b  enforce Pillar live history in R2 gate
2bc4c98  remove ungated Pillar history test path
48f58eb  initialize fresh-run Ante card history
```

Final pre-documentation Pillar/card-history gate:

```text
CI 33850320184: 1724 passed, 1595 deselected
```

### NEXT R2 WORK — VERDANT LEAF / JOKER-SALE LIFECYCLE

The next structural Boss blocker is **Verdant Leaf**.

Vanilla behavior requires ownership of its all-card debuff state and the lifecycle where selling a Joker disables the Boss restriction. This crosses the currently fail-closed `SELL_JOKER` boundary, so it must not be approximated as a static card debuff.

Next implementation order:

1. audit vanilla Verdant Leaf `set_blind`, card debuff, Joker-sale disable, cleanup/defeat, and Chicot interactions;
2. audit the canonical live `SELL_JOKER` legality/execution path and every persistent inverse effect that can make selling exact or unsafe;
3. define the minimum headless Joker-sale transition boundary needed by Verdant Leaf;
4. retain generic `SELL_JOKER` as unavailable until inverse acquisition/lifecycle effects are exact for the sold Joker class;
5. implement Verdant's all-card debuff only at states where its disable/sale lifecycle is fully owned;
6. add focused regressions for pre-sale debuff, exact disable-on-sale, cleanup, rejected unsupported sales, copy/isolation, and live parity fields if new observation is required;
7. keep `SELECT_BLIND` non-training-exposed until the composed strategic boundary is broad enough.

### Current hard blockers / later Boss categories

- Verdant Leaf — **NEXT**, all-card debuff + Joker-sale lifecycle
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

Priority fixtures: shop paths, blind skip/start/clear, Boss restrictions, lifecycle-sensitive Jokers, owned deck, economy, RNG/shuffle/draw/facing/permanent-card-history parity.

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

# Current exact checkpoint

```text
R1 deterministic state/acquisition     SUBSTANTIALLY COMPLETE
R2 RNG / round / Boss lifecycle        ACTIVE
R2 start-inert family                  GREEN THROUGH SERPENT
R2 Hook downstream                     GREEN — CI 33839910429
R2 Ox downstream + live target         GREEN — CI 33841056452
R2 Arm downstream                      GREEN — CI 33841056452
R2 Serpent downstream + composition    GREEN — CI 33843165212
R2 public facing schema/live wiring    GREEN
R2 House + Mark facing                 GREEN — CI 33845952545
R2 Wheel facing RNG                    GREEN — CI 33846232884
R2 Fish temporal facing                GREEN — CI 33846610717
R2 Pillar + permanent Ante history     GREEN — CI 33850320184
NEXT                                   VERDANT LEAF / SELL_JOKER LIFECYCLE
SELECT_BLIND                           NOT EXPOSED
Burglar acquisition                    FAIL-CLOSED
Generic/unknown acquisitions           FAIL-CLOSED
Joker editions                         FAIL-CLOSED
Generic vouchers/packs                 FAIL-CLOSED
SELL_JOKER                             FAIL-CLOSED / NEXT STRUCTURAL DEPENDENCY
R4 tactical bridge                     NOT STARTED
R5 parity                              NOT STARTED
R6 performance                         NOT STARTED
Observation/PPO                        NOT STARTED
```

Current branch code head immediately before this documentation work:

```text
48f58eba1a30149ee40455e3de4fefb7f0b63fe4
```

Documentation commits may sit above that code head without changing mechanics.

The next code written should therefore be **the exact Verdant Leaf / Joker-sale lifecycle audit and minimum canonical ownership needed to support it**. It should **not** be Bond tuning, PPO, or a static approximation that ignores sale/inverse lifecycle effects.
