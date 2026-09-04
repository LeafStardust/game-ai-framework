# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Non-negotiable contract

- Objective: **maximize P(clear Ante 8 | Red Deck, White Stake, normal mode)**.
- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported/inexact transitions stay absent from the training mask.
- Prefer canonical ownership over wrappers, rescue layers, or approximations.
- Manual Bond tuning is retired as the primary competence path.
- Do **not** start PPO/observation training before exactness and live/simulator parity gates.
- Work Chat runs deterministic/static validation itself. GitHub Actions is authoritative when no local clone exists.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Permanent deck truth is `G.playing_cards`; never substitute `G.deck.cards`.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.
- Hidden physical draw order and face-down card/Joker identity-to-position mapping are not policy-visible information.
- If context becomes insufficient to continue safely, **stop immediately rather than guessing**.

## Required continuation procedure

For every continuation session:

1. read this `ROADMAP.md` first;
2. verify current branch/HEAD before editing;
3. inspect canonical owner(s) for the next task;
4. check for intervening commits before writing;
5. treat chat/session summaries as navigation only; repository state is authoritative;
6. add focused fail-closed regressions for every new exactness slice;
7. push coherent completed commits;
8. inspect the actual CI pytest result, not only the workflow badge;
9. synchronize this roadmap after green slices.

Pinned vanilla source for exact audits:

```text
GladdonT/balatro-source-code
895ab3a25bc6f513fa80885eb59951bf8e76bc55
```

Authoritative deterministic workflow:

```text
.github/workflows/balatro-l3.yml
```

Current CI selector:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

## Fail-closed rule

If exactness cannot be proved:

- reject the transition/action;
- omit it from the training mask;
- retain `None`/unobserved state where applicable;
- do not silently substitute related state;
- do not invent hidden/public state merely for simulator convenience.

Examples already enforced:

- partial LuaJIT/TValue permanent-deck reads invalidate `owned_deck`;
- future draw order remains private;
- face-down identities are masked from policy observation;
- Amber Acorn hidden Joker mapping is masked while active;
- Python `random` is not Balatro RNG;
- unsupported Joker inverse sale lifecycles remain rejected.

---

# Completed foundation

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
R0 headless environment architecture COMPLETE
```

L3 contract remains `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`.

The simulator is **not authoritative game truth** until R5 live/simulator parity passes.

---

# Phase R — exact headless environment — ACTIVE

## R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

Exact resource-sensitive acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

Owned acquisition/state categories include:

- static score/rule/retrigger Jokers audited incrementally;
- exact money-based and owned-deck-based scoring Jokers;
- `G.playing_cards` all-or-nothing permanent-deck observation;
- strict permanent card decode/count/modifier validation;
- private draw/discard/played-zone type validation;
- exact headless seed/tag/container validation.

Owned-deck-sensitive acquisition gate includes Steel Joker, Stone Joker, Driver's License, and Erosion.

Representative R1 gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Still fail closed:

- unknown/unaudited Joker acquisitions;
- Joker editions, especially Negative;
- generic vouchers;
- generic packs;
- malformed/noninteger prices;
- generic `SELL_JOKER` where inverse lifecycle is not owned.

---

## R2 — RNG + round/blind/Boss lifecycle — ACTIVE / PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

- keyed pseudohash/pseudoseed semantics;
- LuaJIT combined Tausworthe generator;
- inclusive integer draws;
- independent keyed queues;
- bit-preserving snapshot/restore;
- never Python `random`.

```text
2e61cd8  RNG primitives
290ff11  pinned vectors
CI 33791671797: 1432 passed, 1594 deselected
```

### R2.2 — pseudoshuffle — GREEN

One keyed pseudoseed advance, then one LuaJIT stream drives Fisher–Yates.

```text
246f442  pseudoshuffle
d9662c6  vectors
CI 33791916289: 1435 passed, 1594 deselected
```

### R2.3 — playing-card/Joker creation order — GREEN FOR OWNED CASES

- playing-card creation order retained privately from exact live IDs or pristine base-deck structure;
- Joker creation and physical orders are separate simulator-owned state;
- simulator acquisitions/removals retain exact Joker creation order;
- duplicate/missing/noninteger live IDs fail closed;
- no fake public `sort_id`.

### R2.4 — shuffle/deal + round resources — GREEN

- exact supported-deck shuffle/deal;
- public `deck` canonicalized independently of hidden physical order;
- exact tail draw direction;
- exact hand sort for owned cases;
- one-shot hand/discard round bonuses consumed in source order;
- first blind starts from source-correct `round 0 -> 1`.

Representative gates:

```text
33795507133  1461 passed, 1594 deselected
33797071526  1482 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
33803629167  1563 passed, 1594 deselected
33804894982  1593 passed, 1594 deselected
```

### R2.5 — `setting_blind` Jokers — PARTIAL / EXACT WHERE AUDITED

Burglar lifecycle effect is exact on supported blind starts:

```text
hands_remaining += 3
discards_remaining = 0
```

Chicot lifecycle is now source-ordered through the centralized Boss-disable dispatcher for the currently owned Boss set except the pre-deal Manacle case described below.

Unknown lifecycle Jokers fail closed. **Burglar and Chicot acquisitions remain fail-closed** because purchase persists into arbitrary future lifecycle states that are not all yet owned.

### R2.6 — non-Boss starts — GREEN FOR SUPPORTED STATE

Small/Big blind setup owns:

1. `ease_round(1)` equivalent;
2. blind target/resource initialization;
3. round bonuses;
4. audited `setting_blind` effects;
5. exact shuffle/deal;
6. policy-safe public/private card zones.

### R2.7 — Boss lifecycle — ACTIVE

Owned Boss boundaries and downstream mechanics:

```text
The Wall + Violet Vessel       requirement-only                   GREEN
The Eye + The Mouth            mutable hand-rule state            GREEN
The Water + The Needle         reversible round resources         GREEN
The Manacle                    reversible hand-size mutation      GREEN; PRE-DEAL CHICOT BLOCKED
The Goad/Window/Head/Club      static suit card debuffs           GREEN
The Plant                      face-card debuffs                  GREEN
Cerulean Bell                  forced-selection lifecycle         GREEN
The Psychic                    hand rejection                     GREEN
The Flint                      base score halving                 GREEN
The Tooth                      -$1 per played card                GREEN
The Hook                       keyed forced discards              GREEN
The Ox                         target hand -> money = 0           GREEN
The Arm                        hand level decrement               GREEN
The Serpent                    post-action 3-card draw             GREEN
The House + The Mark           deterministic facing               GREEN
The Wheel                      keyed per-draw facing RNG           GREEN
The Fish                       temporal post-play facing           GREEN
The Pillar                     permanent Ante play history         GREEN
Verdant Leaf                   all-card debuff + minimum sale     GREEN
Amber Acorn                    hidden Joker order + reveal         GREEN
Crimson Heart                  Joker debuff lifecycle              GREEN
```

Representative gates:

```text
33839910429  Hook
33841056452  Ox + Arm
33843165212  Serpent
33845952545  House + Mark
33846232884  Wheel
33846610717  Fish
33850320184  Pillar
33855720629  Verdant Leaf — 1734 passed, 1595 deselected
33857249827  Amber primitive — 1755 passed, 1595 deselected
33863345344  Crimson checkpoint — 1794 passed, 1595 deselected
33865394680  Chicot/Cerulean checkpoint — 1805 passed, 1595 deselected
33869467530  Chicot Verdant/facing checkpoint — 1815 passed, 1595 deselected
```

#### Verdant Leaf — GREEN

Owned minimum exact sale lifecycle:

- Boss start debuffs all permanent playing cards;
- selling an audited static sell-safe Joker credits exact sell value;
- sale disables Verdant and clears permanent-card debuffs;
- the same centralized Verdant disable inverse is now used by Chicot;
- Eternal/edition/resource-sensitive/unsupported sale paths fail closed;
- generic `SELL_JOKER` remains `PLANNED` and is **not** training-exposed.

#### Amber Acorn — GREEN FOR CURRENT OWNED BOUNDARY

Owned source behavior:

- all owned Jokers become hidden while Amber is active;
- `G.jokers:shuffle("aajk")` is executed three times with source-exact re-sort-before-each-shuffle semantics;
- hidden physical order is retained internally;
- policy sees the Joker multiset but not identity-to-position mapping;
- Amber start is composed between common resource setup and Joker `setting_blind` effects;
- disable/reveal exposes the retained shuffled physical order without restoring pre-Amber order;
- headless Joker creation order survives simulator acquisitions/removals.

#### Crimson Heart — GREEN FOR CURRENT OWNED BOUNDARY

Owned source behavior:

- pre-deal `prepped` state;
- initial `drawn_to_hand` target selection using keyed `crimson_heart` pseudorandom selection over retained Joker creation order;
- previous target exclusion when two or more Jokers exist;
- `press_play` re-arms the next target selection;
- selected Joker receives public `debuffed` state;
- debuffed Joker scoring effects are suppressed while the Joker remains present in the projection graph;
- debuffed Jokers remain visible to cross-Joker mechanics such as Baseball Card;
- disable cleanup clears Joker debuffs and `prepped` state without consuming RNG.

#### Chicot / centralized `Blind:disable()` — GREEN EXCEPT PRE-DEAL MANACLE

Pinned vanilla trigger:

```text
Chicot: context.setting_blind -> queue G.GAME.blind:disable()
```

Owned source ordering:

1. round resources are installed;
2. Boss `set_blind` mutation occurs;
3. every Joker receives `setting_blind`;
4. Burglar/current-round outputs are installed;
5. the queued Chicot disable executes;
6. only later does `DRAW_TO_HAND` / `nr{ante}` shuffle/deal occur.

Central dispatcher currently owns exact disable consequences for:

- Wall / Violet requirement restoration;
- Water / Needle resource restoration;
- static suit debuff Bosses;
- Plant;
- Pillar;
- Verdant Leaf;
- House / Wheel / Mark / Fish facing cleanup;
- Cerulean Bell forced-selection cleanup;
- Amber Acorn reveal/disable;
- Crimson Heart debuff/prepped cleanup;
- Eye / Mouth / Psychic / Flint / Tooth / Hook / Ox / Arm / Serpent simple disable state.

Recent composition fixes:

```text
8943e36  centralize Verdant disable cleanup
034f363  admit Verdant through Boss-disable dispatcher
0540b52  Chicot/Verdant regressions
99405b7  suppress disabled House/Mark/Wheel facing effects
ab133f5  avoid Boss-disable/facing import cycle
 a22bf6a  keep disabled Fish replenishment face-up
209c68c  Chicot facing Boss regressions
CI 33869467530: 1815 passed, 1595 deselected
```

Important exactness details:

- Chicot-disabled Wheel does **not** consume the `wheel` RNG key after the ordinary `nr{ante}` deal;
- Chicot-disabled House/Mark deal face-up;
- Chicot-disabled Fish later replenishes face-up after play;
- `wheel_flipped` is vanilla flip/UI bookkeeping, not a gameplay-state dependency; headless therefore owns the mechanical face-up inverse without inventing a public marker;
- multiple Chicot disable requests remain fail-closed until repeated-disable event semantics are explicitly owned.

### R2.8 — PRE-DEAL MANACLE / PRIOR PHYSICAL DECK STATE — NEXT

This is now the concrete Chicot blocker.

Vanilla Manacle ordering:

```text
Blind:set_blind(The Manacle)
    -> G.hand:change_size(-1)
setting_blind Jokers
    -> Chicot queues Blind:disable()
Blind:disable(The Manacle)
    -> G.hand:change_size(+1)
    -> G.FUNCS.draw_from_deck_to_hand(1)
new_round later event
    -> G.STATE = DRAW_TO_HAND
    -> G.deck:shuffle("nr" .. ante)
    -> ordinary initial draw
```

The extra Manacle replacement card is therefore drawn **before** the normal new-round shuffle. Exact card identity depends on the physical deck order retained from the prior round/shop boundary.

Do not fake this by drawing from canonical public `deck`, sorting by creation order, or shuffling early.

Implement in this order:

1. audit vanilla prior-round hand/discard/deck repopulation order (`draw_from_hand_to_discard`, then `draw_from_discard_to_deck`);
2. define exact headless round-end private-zone repopulation ownership;
3. prove shop/blind-select transitions preserve that private physical deck order without leaking it publicly;
4. add a pre-shuffle one-card draw primitive that consumes the retained physical deck tail and updates public canonical deck/hand without RNG;
5. compose Manacle `Blind:disable()` at Chicot timing with hand-size restore + that pre-shuffle draw;
6. prove the later `nr{ante}` shuffle includes the remaining cards and does not redraw the pre-shuffle card;
7. add source-order, input-isolation, replay/restore, and fail-closed regressions;
8. only then remove the current pre-deal Manacle rejection.

Do **not** expose `SELECT_BLIND` merely because individual Boss starts are increasingly complete.

### Remaining R2 categories after Manacle/prior-zone ownership

- active tags;
- voucher blind-start effects;
- shop/reroll RNG;
- pack RNG/state;
- boss-selection RNG;
- any remaining Boss defeat/round cleanup not already owned.

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Important status:

```text
SELECT_BLIND  PLANNED / hidden from training mask
SELL_JOKER   PLANNED / minimum Verdant path only
```

Do not widen action exposure until complete composed transitions are exact.

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity — NOT STARTED

Priority parity fixtures:

- shop purchase/hold/end-shop;
- Joker replacement/sale;
- reroll/voucher/pack paths;
- blind skip/start/clear;
- Boss restrictions and disable/defeat cleanup;
- lifecycle-sensitive Jokers;
- permanent deck/history;
- economy;
- RNG/shuffle/draw/facing/Joker-order parity.

## R6 — performance gate — NOT STARTED

Measure throughput only after exact semantics and representative live parity are green.

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
V   simulator -> live learned-policy validation
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
R2 RNG / round / Boss lifecycle        ACTIVE / PRIMARY
R2 supported Small/Big starts          GREEN
R2 supported Boss starts/effects       GREEN THROUGH CURRENT AUDITED SET
R2 Verdant + minimum static sale       GREEN
R2 Amber hidden order + reveal         GREEN
R2 Crimson Heart lifecycle             GREEN
R2 Chicot Boss disable                 GREEN EXCEPT PRE-DEAL MANACLE
R2 facing-Boss Chicot composition      GREEN
NEXT                                   PRIOR-ROUND PRIVATE DECK ORDER -> MANACLE CHICOT
SELECT_BLIND                           NOT EXPOSED
Burglar acquisition                    FAIL-CLOSED
Chicot acquisition                     FAIL-CLOSED
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
209c68ceee7d44c66a0fbd577be8d38976eb59f2
```

The next code written should therefore be **exact prior-round private-zone/deck repopulation sufficient to support the pre-shuffle Manacle/Chicot draw**. It should **not** be Bond tuning, PPO, generic `SELL_JOKER`, or broad action exposure.