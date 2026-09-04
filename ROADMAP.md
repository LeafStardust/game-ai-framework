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
- Face-down card/Joker identity-to-position mapping is **not public information**. Headless simulation may retain hidden truth internally for exact mechanics, but policy observations must mask it.
- If context becomes insufficient to continue safely, **stop immediately rather than guessing**.

---

# Required development procedure

For every continuation session:

1. read current `ROADMAP.md` first;
2. verify current branch/head before editing;
3. inspect the canonical owner(s) for the next roadmap task;
4. check for intervening commits before writing;
5. treat chat/session summaries as navigation aids only — repository state is authoritative.

Target branch:

```text
feat/v1.0-red-white-competence
```

For each mechanics/state/lifecycle slice:

1. audit pinned vanilla/source behavior and existing production owners;
2. classify the exact missing ownership boundary;
3. patch the canonical owner rather than adding a rescue approximation;
4. add focused deterministic regressions, including fail-closed behavior;
5. keep unsupported composition unavailable;
6. run deterministic CI;
7. inspect the actual pytest result and selection count;
8. only then mark the slice GREEN and synchronize this roadmap.

Do not bulk-admit Jokers/actions merely because nearby classes are supported. Audit counters, RNG, economy, card mutation, sale/destruction, lifecycle state, persistent consequences, and information visibility individually.

Pinned vanilla source used for exact audits:

```text
GladdonT/balatro-source-code
895ab3a25bc6f513fa80885eb59951bf8e76bc55
```

## Fail-closed rule

If exactness cannot be proved:

- reject the transition/action;
- omit it from the training mask;
- preserve `None`/unobserved state where applicable;
- do not silently substitute related state;
- do not invent synthetic state unless source-justified and lifecycle-owned.

Already enforced examples:

- permanent owned deck = `G.playing_cards`, never `G.deck.cards`;
- partial LuaJIT/TValue reads invalidate owned-deck observation;
- future physical draw order stays private;
- face-down card identity stays masked;
- Amber Acorn hidden Joker identity-to-position mapping stays masked;
- Python `random` is not Balatro RNG;
- unsupported Joker sale inverse lifecycles stay rejected.

## Deterministic CI procedure

Authoritative workflow:

```text
.github/workflows/balatro-l3.yml
```

Current command:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

After each relevant push:

1. locate the workflow run for the exact commit;
2. require `balatro-deterministic-tests` conclusion `success`;
3. inspect the final pytest line;
4. record exact passed/deselected counts;
5. confirm the intended test family was selected.

A green workflow badge alone is not sufficient. Historical R2 card-order tests were once accidentally deselected; `env_r2` was then added to the CI selector before that slice was called green.

The user has authorized pushing coherent completed commits to the remote branch. Do not ask the user to run deterministic pytest when CI can do it. Do not request another open-ended live Balatro batch unless a later parity gate specifically requires one.

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

---

# Phase R — exact headless Balatro environment — ACTIVE

The simulator is not authoritative game truth until R5 live/simulator parity passes.

## R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

Exact resource-sensitive acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

The exact inventory-only score/rule/retrigger Joker set is owned incrementally in `ShopTransitionEngine`, including passive-rule, hand-shape, suit, conditional, money, owned-deck, and retrigger groups.

Permanent-deck authority:

- `G.playing_cards` only;
- all-or-nothing observation/translation;
- partial LuaJIT/TValue reads fail closed;
- malformed/count-mismatched cards make `owned_deck = None`;
- Steel Joker, Stone Joker, Driver's License, and Erosion are exact-gated on permanent owned deck.

Key R1 gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Still fail closed:

- unknown/unaudited Joker acquisitions;
- Joker editions, especially Negative;
- generic voucher acquisition;
- generic packs until RNG/state is exact;
- malformed/noninteger prices;
- generic `SELL_JOKER` for classes whose inverse lifecycle is not owned.

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

Exact playing-card creation order is retained privately only when provable from unique integer live `playing_card` IDs or the untouched vanilla one-of-each 52-card structure. No fake public `sort_id`.

```text
CI 33795507133: 1461 passed, 1594 deselected
```

### R2.4 — complete-deck shuffle/deal — GREEN FOR SUPPORTED DECKS

`deal_supported_round_start()` owns physical shuffle/deal. Public `deck` remains canonicalized and never exposes future order. Private draw/discard/played zones are validated exact card lists.

```text
CI 33803629167: 1563 passed, 1594 deselected
```

### R2.5 — round resources / one-shot bonuses — GREEN

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

Unknown lifecycle Jokers fail closed. Burglar acquisition remains fail-closed because purchase persists into future arbitrary lifecycle states.

### R2.7 — round/Small/Big start — GREEN

Vanilla `G.GAME.round` starts at 0; first select-blind queues `ease_round(1)` before `new_round()`.

```text
CI 33797071526: 1482 passed, 1594 deselected
CI 33798795353: 1497 passed, 1594 deselected
```

### R2.8 — Boss lifecycle — ACTIVE

Owned Boss slices:

```text
Wall + Violet Vessel            requirement-only             GREEN  CI 33799746434
Eye + Mouth                     mutable hand-rule             GREEN  CI 33800243393
Water + Needle                  reversible resources         GREEN  CI 33801195935
Manacle                         reversible hand size         GREEN
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
Verdant Leaf                    all-card debuff + sale       GREEN  CI 33855720629
Amber Acorn                     hidden Joker ordering        PARTIAL / ACTIVE
```

### Start-inert Boss family — GREEN

```text
The Psychic
The Flint
The Tooth
The Hook
The Ox
The Arm
The Serpent
```

Their start boundary is exact; downstream effects are separately owned/tested.

### Selected semantics already frozen

#### Hook

At `Blind:press_play`, choose up to two non-selected hand cards via keyed `pseudorandom_element(..., "hook")`, removing the first candidate before second selection. Forced discards do not consume discard allowance or draw replacements.

#### Ox

Uses authoritative `G.GAME.current_round.most_played_poker_hand`; matching hand sets money exactly to `0`, including from negative money. Missing target fails closed.

#### Arm

Decrements the classified hand level only when level > 1; scoring derives Chips/Mult from canonical `hand_levels`.

#### Serpent

After at least one play or discard:

```text
draw_count = min(#remaining_deck, 3)
```

May grow hand above nominal capacity, consumes no RNG, and requires authoritative private/public zone state.

#### House / Mark / Wheel / Fish

`BalatroCard.face_down` + `facing_observed` are canonical. Policy observations mask face-down identity and modifiers while internal simulation retains identity.

Wheel consumes one keyed `wheel` RNG advance per physical draw. Fish is temporal: initial draw face up, post-play draws face down, post-discard draws face up.

#### Pillar

Permanent cards carry exact `played_this_ante` + observation state from `G.playing_cards`. Accepted play marking sets selected permanent cards true; new-Ante reset clears them; missing history fails closed.

### R2.9 — Verdant Leaf / minimum Joker-sale lifecycle — GREEN

Owned source boundary:

1. Boss start applies Verdant's all-playing-card debuff before the Joker `setting_blind` pass;
2. exact shuffle/deal preserves permanent-card debuffs into active hand/draw pile;
3. selling an audited inventory-only/static sell-safe Joker removes it, credits exact nonnegative `sell_cost`, disables Verdant Leaf, and clears permanent-card debuffs;
4. Eternal Jokers, editions, invalid prices/indexes, resource-sensitive inverse lifecycles, and unsupported Joker classes remain rejected;
5. `Blind.disabled` is retained across copies/replay state;
6. generic `SELL_JOKER` remains `PLANNED` and is not training-exposed merely because this minimum path is owned.

Relevant commits:

```text
ee7e5a5  retain blind disabled state
a96a8e1  own minimum exact Verdant Joker sale
0a390e9  pin minimum Verdant sale lifecycle
1130edb  compose exact Verdant Leaf start
9d99eb8  pin exact Verdant start composition
```

Final Verdant gate:

```text
CI 33855720629: 1734 passed, 1595 deselected
```

### R2.10 — Amber Acorn hidden Joker ordering — PARTIAL / CURRENT

Pinned vanilla `Blind:set_blind` behavior:

```text
if Amber Acorn and Jokers > 0:
    flip every Joker
    if Jokers > 1:
        G.jokers:shuffle("aajk")
        G.jokers:shuffle("aajk")
        G.jokers:shuffle("aajk")
```

Pinned cleanup behavior:

- `Blind:defeat()` flips every Joker whose facing is `back` to the front;
- `Blind:disable()` does the same;
- neither path restores the pre-Amber order — the shuffled physical order remains when identities become visible again.

Implemented and green:

1. `games/balatro/env/joker_order.py`
   - derives exact Joker creation/sort order for empty/single areas or multi-Joker states with unique exact integer `live_id` values;
   - duplicate/missing/noninteger ids fail closed;
   - retains separate creation and physical orders;
   - supports exact acquire/remove/set-permutation bookkeeping primitives.
2. `games/balatro/env/amber_acorn.py`
   - implements three keyed `aajk` shuffle advances;
   - each pass restarts from creation/sort order, matching `CardArea:shuffle` → `pseudoshuffle` re-sort semantics;
   - final physical permutation is the third shuffle result;
   - RNG input state is isolated and exact.
3. `games/balatro/env/public_observation.py`
   - while active Amber is hiding Jokers, policy sees the owned Joker multiset but not identity-to-position mapping;
   - strips private `live_id`/area index from masked clones;
   - canonicalizes masked Joker presentation independently of hidden physical order;
   - source state is never mutated.
4. headless Amber order effect
   - exact physical Joker permutation is applied internally for mechanics/order-sensitive evaluation;
   - policy-facing observation remains masked while Amber is active.

Relevant commits:

```text
ad1a057  feat(balatro): mask Amber Acorn Joker order
7bfae6c  test(balatro): prevent Amber Joker-order leakage
c605b3e  feat(balatro): apply exact Amber order to headless state
808e0f2  test(balatro): cover Amber headless order effect
```

Authoritative gate:

```text
CI 33857249827: 1755 passed, 1595 deselected
```

Amber is **not yet complete**. Current implementation owns the hidden permutation/masking primitive but still requires exact lifecycle composition.

## NEXT R2 WORK — AMBER BLIND-START + REVEAL/CLEANUP COMPOSITION

Implement in this order:

1. compose Amber's order effect into `blind_start.py` **between** `_begin_predeal_lifecycle()` and `_finish_predeal_lifecycle()`, matching vanilla `Blind:set_blind` before Joker `setting_blind` effects;
2. own Joker-facing state explicitly enough to represent Amber's flip-to-back condition without exposing hidden mapping;
3. implement source-exact reveal on Boss disable and defeat: flip hidden Jokers front while retaining the shuffled physical order;
4. ensure post-reveal policy observation returns the now-visible physical order;
5. retain exact Joker creation order through simulator-owned shop acquisitions/removals so headless runs do not require live `sort_id` values merely because the Jokers were created by the simulator itself;
6. add regressions for zero/one/multiple Jokers, duplicate/missing ids, RNG snapshot/restore, input isolation, Burglar + Amber source ordering, disable/defeat reveal, post-reveal order visibility, and policy no-leak behavior;
7. only then mark Amber Boss start GREEN.

### Remaining hard Boss/lifecycle categories after Amber

- Crimson Heart — per-hand random Joker debuff lifecycle;
- Chicot composition, especially pre-deal Manacle/resource reversal;
- prior-round arbitrary zone cleanup;
- active tags;
- voucher blind-start effects;
- shop/reroll RNG;
- pack RNG/state;
- boss-selection RNG.

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Every training-visible action requires exact legality, transition, serialization, and mask representation.

Current important status:

```text
SELECT_BLIND  PLANNED / hidden from mask
SELL_JOKER   PLANNED; minimum Verdant static-sale path exists only
```

Do not widen action exposure until the composed exact lifecycle is broad enough.

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity — NOT STARTED

Priority fixtures:

- shop purchase/hold/end-shop;
- Joker replacement/sale;
- reroll/voucher/pack paths;
- blind skip/start/clear;
- Boss restrictions and cleanup;
- lifecycle-sensitive Jokers;
- owned deck/permanent card history;
- economy;
- RNG/shuffle/draw/facing/Joker-order parity.

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
R2 Ox + Arm downstream                 GREEN — CI 33841056452
R2 Serpent downstream                  GREEN — CI 33843165212
R2 House + Mark facing                 GREEN — CI 33845952545
R2 Wheel facing RNG                    GREEN — CI 33846232884
R2 Fish temporal facing                GREEN — CI 33846610717
R2 Pillar + permanent Ante history     GREEN — CI 33850320184
R2 Verdant + minimum static sale       GREEN — CI 33855720629
R2 Amber hidden order + masking        GREEN PRIMITIVE — CI 33857249827
NEXT                                   AMBER START + REVEAL/CLEANUP COMPOSITION
SELECT_BLIND                           NOT EXPOSED
Burglar acquisition                    FAIL-CLOSED
Generic/unknown acquisitions           FAIL-CLOSED
Joker editions                         FAIL-CLOSED
Generic vouchers/packs                 FAIL-CLOSED
SELL_JOKER                             PLANNED / MINIMUM VERDANT PATH ONLY
R4 tactical bridge                     NOT STARTED
R5 parity                              NOT STARTED
R6 performance                         NOT STARTED
Observation/PPO                        NOT STARTED
```

Current code head before this documentation commit:

```text
808e0f21cc0377285f0534160b7bee567633f7e0
```

The next code written should therefore be **Amber Acorn blind-start + reveal/cleanup composition**, including retained headless Joker creation order where required. It should **not** be Bond tuning, PPO, generic `SELL_JOKER`, or another public-list shuffle approximation.
