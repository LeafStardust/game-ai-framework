# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Non-negotiable contract

- Objective: **maximize P(clear Ante 8 | Red Deck, White Stake, normal mode)**.
- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported or inexact transitions stay absent from the training mask.
- Prefer canonical ownership over wrappers, rescue layers, or approximations.
- Manual Bond coefficient tuning is retired as the primary competence path.
- Do **not** start PPO/observation training before exactness and representative live/simulator parity gates.
- Work Chat runs deterministic/static validation itself. GitHub Actions is authoritative when no local clone exists.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Permanent deck truth is `G.playing_cards`; never substitute `G.deck.cards`.
- Hidden physical draw order and face-down card/Joker identity-to-position mapping are not policy-visible information.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.
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
- unsupported Joker inverse sale lifecycles remain rejected;
- pre-deal Manacle/Chicot requires an authoritative retained physical deck and never reconstructs from canonical public `deck`.

---

# Completed foundation

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
L3 environment freeze                COMPLETE
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
- strict permanent-card decode/count/modifier validation;
- strict LuaJIT authoritative-array path for `G.playing_cards`;
- private draw/discard/played-zone type validation;
- exact headless seed/tag/container validation;
- owned-deck-sensitive scoring acquisitions including Steel Joker, Stone Joker, Driver's License, and Erosion.

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
- generic `SELL_JOKER` where inverse lifecycle is not owned;
- lifecycle acquisitions whose future consequences are not owned across arbitrary reachable states.

---

## R2 — RNG + round/blind/Boss lifecycle — ACTIVE / PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

Owned:

- keyed pseudohash/pseudoseed progression;
- LuaJIT combined Tausworthe generator;
- inclusive integer draws;
- independent keyed queues;
- exact serializable node state;
- bit-preserving snapshot/restore;
- never Python `random`.

```text
2e61cd8  exact Balatro/LuaJIT RNG primitives
290ff11  pinned RNG reference vectors
CI 33791671797: 1432 passed, 1594 deselected
```

### R2.2 — pseudoshuffle — GREEN

Source semantics:

- one keyed pseudoseed advance per shuffle;
- one LuaJIT stream drives Fisher–Yates;
- CardArea shuffle re-sorts by creation/`sort_id` order before RNG;
- repeated keyed `random()` calls are not a valid substitute.

```text
246f442  exact pseudoshuffle
d9662c6  shuffle vectors + restore behavior
CI 33791916289: 1435 passed, 1594 deselected
```

### R2.3 — playing-card/Joker creation order — GREEN FOR OWNED CASES

- playing-card creation order retained privately from exact live IDs or pristine base-deck structure;
- Joker creation and physical orders are separate simulator-owned state;
- simulator acquisitions/removals retain exact Joker creation order;
- duplicate/missing/noninteger live IDs fail closed;
- no fake public `sort_id` field.

Important commits:

```text
e7b0bb0  derive exact playing-card creation order
2a26e79  pin creation-order regressions
34d88e9  include env_r2 coverage in CI
7c070b2  retain exact playing-card order in headless state
2dc47eb  retained-order regressions
```

Corrected full gate:

```text
CI 33795507133: 1461 passed, 1594 deselected
```

### R2.4 — shuffle/deal + round resources — GREEN

Owned:

- exact supported-deck shuffle/deal;
- hidden physical order kept private while public `deck` is canonicalized;
- exact deck-tail draw direction;
- exact hand sorting for currently owned card-history cases;
- exact headless RNG ownership and replay state;
- one-shot hand/discard round bonuses consumed in source order;
- first blind starts from source-correct `round 0 -> 1`.

Important commits:

```text
0a7f845  exact RNG state in headless runs
eed926e  headless RNG ownership regressions
61ec993  exact pristine round-start deal
2d37016  pristine shuffle/deal regressions
```

Representative gates:

```text
33794664514  1461 passed, 1594 deselected
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

Chicot `setting_blind` behavior is source-ordered through centralized `Blind:disable()` ownership for the currently supported Boss set, including the retained-deck pre-deal Manacle case described in R2.8.

Unknown lifecycle Jokers fail closed. **Burglar and Chicot acquisitions remain fail-closed** because purchase persists into arbitrary future lifecycle states that are not all yet owned.

### R2.6 — non-Boss starts — GREEN FOR SUPPORTED STATE

Small/Big blind setup owns:

1. `ease_round(1)` equivalent;
2. blind target/resource initialization;
3. round bonuses;
4. audited `setting_blind` effects;
5. exact shuffle/deal;
6. policy-safe public/private card zones.

### R2.7 — Boss lifecycle — ACTIVE / BROAD OWNED SET

Owned Boss boundaries/downstream mechanics:

```text
The Wall + Violet Vessel       requirement-only                   GREEN
The Eye + The Mouth            mutable hand-rule state            GREEN
The Water + The Needle         reversible round resources         GREEN
The Manacle                    hand-size mutation + disable paths GREEN INCLUDING RETAINED PRE-DEAL CHICOT
The Goad/Window/Head/Club      static suit card debuffs           GREEN
The Plant                      face-card debuffs                  GREEN
Cerulean Bell                  forced-selection lifecycle         GREEN
The Psychic                    hand rejection                     GREEN
The Flint                      base score halving                 GREEN
The Tooth                      -$1 per played card                GREEN
The Hook                       keyed forced discards              GREEN
The Ox                         target hand -> money = 0           GREEN
The Arm                        hand-level decrement               GREEN
The Serpent                    post-action 3-card draw             GREEN
The House + The Mark           deterministic facing               GREEN
The Wheel                      keyed per-draw facing RNG           GREEN
The Fish                       temporal post-play facing           GREEN
The Pillar                     permanent Ante play history         GREEN
Verdant Leaf                   all-card debuff + minimum sale     GREEN
Amber Acorn                    hidden Joker order + reveal         GREEN
Crimson Heart                  Joker debuff lifecycle              GREEN
```

Representative later gates:

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
- the same centralized Verdant inverse is used by Chicot;
- Eternal/edition/resource-sensitive/unsupported sale paths fail closed;
- generic `SELL_JOKER` remains `PLANNED` and is not training-exposed.

#### Amber Acorn — GREEN FOR CURRENT OWNED BOUNDARY

- all owned Jokers become hidden while Amber is active;
- `G.jokers:shuffle("aajk")` runs three times with source-exact re-sort-before-each-shuffle semantics;
- hidden physical order is retained internally;
- policy sees the Joker multiset but not identity-to-position mapping;
- disable/reveal exposes retained shuffled physical order without restoring pre-Amber order.

#### Crimson Heart — GREEN FOR CURRENT OWNED BOUNDARY

- pre-deal `prepped` state;
- initial `drawn_to_hand` keyed target selection over retained Joker creation order;
- previous-target exclusion when two or more Jokers exist;
- `press_play` re-arms selection;
- selected Joker receives public `debuffed` state;
- debuffed Joker scoring is suppressed but the Joker remains present for cross-Joker mechanics;
- disable cleanup clears Joker debuffs and `prepped` without consuming RNG.

#### Chicot / centralized `Blind:disable()` — GREEN FOR CURRENT OWNED BOUNDARY

Pinned vanilla trigger:

```text
Chicot: context.setting_blind -> queue G.GAME.blind:disable()
```

Owned source ordering:

1. round resources installed;
2. Boss `set_blind` mutation occurs;
3. every supported Joker receives `setting_blind`;
4. Burglar/current-round outputs are installed;
5. queued Chicot disable executes;
6. only later does `DRAW_TO_HAND` / normal `nr{ante}` shuffle/deal occur.

Central dispatcher owns exact disable consequences for the currently audited set, including:

- Wall / Violet target restoration;
- Water / Needle resource restoration;
- Manacle hand-size restoration and post-deal draw;
- retained pre-deal Manacle restoration + physical-tail draw when the prior deck order is authoritative;
- static suit debuff Bosses;
- Plant;
- Pillar;
- Verdant Leaf;
- House / Wheel / Mark / Fish facing cleanup;
- Cerulean Bell forced-selection cleanup;
- Amber Acorn reveal/disable;
- Crimson Heart cleanup;
- Eye / Mouth / Psychic / Flint / Tooth / Hook / Ox / Arm / Serpent simple disable state.

Important exactness details:

- Chicot-disabled Wheel does not consume the `wheel` RNG key after ordinary `nr{ante}` deal;
- Chicot-disabled House/Mark deal face-up;
- Chicot-disabled Fish replenishes face-up;
- multiple Chicot disable requests remain fail-closed until repeated-disable event semantics are explicitly owned.

### R2.8 — PRE-DEAL MANACLE / PRIOR PHYSICAL DECK STATE — GREEN

Pinned vanilla ordering:

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

The replacement card is drawn **before** the normal new-round shuffle. Exact identity therefore depends on the physical deck order retained from the prior round.

Completed ownership sequence:

1. vanilla prior-round hand/discard/deck repopulation order audited;
2. exact headless round-end private-zone repopulation implemented;
3. complete retained pre-blind deck partition proved against authoritative `owned_deck`;
4. pre-shuffle single-card draw consumes retained physical deck tail with no RNG;
5. centralized Manacle `Blind:disable()` restores hand size and performs that retained tail draw at Chicot timing;
6. later `nr{ante}` shuffle re-sorts and shuffles **only the remaining cards**;
7. pre-drawn card remains outside the shuffle, appears exactly once in the final hand, and cannot be redrawn;
8. deterministic/input-isolation/fail-closed partition regressions are green.

Important commits/gates:

```text
088a545 / 7939fa0 / 3569b58 / e4c386e  retained round-end/private-deck ownership
CI 33870571411: 1821 passed, 1595 deselected

4c2365b  retained pre-blind physical-tail draw
973cda3  retained pre-blind draw regressions
CI 33871756000: 1824 passed, 1595 deselected

5d05eba  pre-deal Manacle resource inverse
915da68  central Boss-disable admission
dee9e58  pre-deal Manacle disable regressions
6981ecc  preserve explicit missing-retained-deck rejection
CI 33872332123: 1828 passed, 1595 deselected

accf6ed  post-Manacle `nr{ante}` continuation
a3d6e71  no-redraw/partition/determinism regressions
CI 33872735051: 1833 passed, 1595 deselected

656bcbc  full retained Manacle+Chicot blind-start mechanics owner
17bd938  end-to-end retained Manacle+Chicot regressions
CI 33873017991: 1838 passed, 1595 deselected
```

This closes the concrete pre-deal Manacle blocker. The generic training `SELECT_BLIND` action is **still hidden**; completion of one difficult Boss path is not permission to expose an incomplete full-run action graph.

### R2.9 — BLIND CLEAR / ROUND-END ECONOMY -> SHOP — NEXT

This is now the primary structural blocker for a continuous headless run.

Current exact owners cover large parts of blind start, play/Boss mechanics, Boss defeat cleanup, card-zone repopulation, and shop-local transitions, but there is no single exact environment owner yet for the source-ordered transition from a cleared blind through cash-out into the next shop/blind-select state.

Audit vanilla source and implement incrementally in source order. At minimum classify/own:

1. blind clear detection and `Blind:defeat()` consequences;
2. Boss-specific defeat cleanup already modeled by specialized owners and any missing cleanup;
3. played/hand/discard card return and retained physical deck state;
4. blind reward payout;
5. remaining-hand cash value;
6. interest calculation/cap and exact money mutation;
7. relevant end-of-round Joker effects and fail-closed gating for unsupported identities;
8. ante/blind-state progression and Boss-clear consequences;
9. shop-entry phase/state initialization;
10. preservation of deterministic RNG/private state without generating shop contents early;
11. focused replay/input-isolation/fail-closed regressions.

Do **not** approximate economy or collapse vanilla event ordering merely to reach SHOP.

After the deterministic round-clear/shop boundary is green, continue with the RNG surfaces required to populate and act in that shop.

### Remaining R2 categories after R2.9

- shop generation RNG;
- reroll RNG;
- pack contents/choice RNG and pack state;
- voucher lifecycle where needed;
- active-tag generation/application where needed;
- Boss-selection RNG/progression;
- any remaining Boss defeat/end-round cleanup discovered by R2.9;
- fixed-seed replay across multi-round trajectories.

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Current important status:

```text
END_SHOP      supported where exact shop transition exists
BUY_*         only exact audited subsets become legal
SELECT_BLIND  PLANNED / HIDDEN
SELL_JOKER    PLANNED / minimum Verdant path only
SKIP_BLIND    PLANNED
REROLL_SHOP   PLANNED
PACK actions  PARTIAL/PLANNED
```

Every training-visible action requires stable canonical ID, deterministic legality, exact transition, serialization representation, and mask representation.

Do not widen `SELECT_BLIND` merely because many individual start helpers are green.

---

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development. Tactical trajectories remain logged for parity/debugging.

## R5 — live/simulator parity — NOT STARTED

Priority parity fixtures:

- shop purchase/hold/end-shop;
- Joker replacement/sale;
- reroll/voucher/pack paths;
- blind skip/start/clear;
- Boss restrictions and disable/defeat cleanup;
- lifecycle-sensitive Jokers;
- permanent deck/history;
- economy/interest/cash-out;
- RNG/shuffle/draw/facing/Joker-order parity;
- retained pre-deal Manacle+Chicot order.

The simulator does not become authoritative training truth until representative parity fixtures are green.

## R6 — performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead only after semantic correctness and representative parity.

### Phase R exit criteria

- deterministic reset/step API;
- all initial strategic actions have exact legality + execution tests;
- Red/White run proceeds reset -> terminal entirely headlessly;
- fixed-seed replay is deterministic;
- representative live parity fixtures are green;
- throughput supports automated training;
- environment version stored in trajectory metadata.

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
R1 deterministic state/acquisition      SUBSTANTIALLY COMPLETE
R2 RNG / round / Boss lifecycle         ACTIVE / PRIMARY
R2 supported Small/Big starts           GREEN
R2 supported Boss starts/effects        GREEN THROUGH CURRENT AUDITED SET
R2 Verdant + minimum static sale        GREEN
R2 Amber hidden order + reveal          GREEN
R2 Crimson Heart lifecycle              GREEN
R2 Chicot Boss disable                  GREEN FOR CURRENT OWNED BOUNDARY
R2 retained Manacle+Chicot source order GREEN — CI 33873017991
R2 round-end private deck retention     GREEN
NEXT                                    EXACT BLIND CLEAR/CASH-OUT -> SHOP BOUNDARY
SELECT_BLIND                            NOT EXPOSED
Burglar acquisition                     FAIL-CLOSED
Chicot acquisition                      FAIL-CLOSED
Generic/unknown acquisitions            FAIL-CLOSED
Joker editions                          FAIL-CLOSED
Generic vouchers/packs                  FAIL-CLOSED
SELL_JOKER                              PLANNED / MINIMUM VERDANT PATH ONLY
R4 tactical bridge                      NOT STARTED
R5 parity                               NOT STARTED
R6 performance                          NOT STARTED
Observation/PPO                         NOT STARTED
```

Current code head before this documentation commit:

```text
17bd938792142582221dd2581c25e1cf2774a712
```

Latest authoritative green deterministic gate:

```text
CI 33873017991: 1838 passed, 1595 deselected
```

The next code written should therefore be **the exact source-ordered blind-clear / round-end economy / shop-entry boundary, starting with an audit of vanilla defeat/cash-out ordering and existing specialized cleanup owners**. It should **not** be Bond tuning, PPO, broad `SELL_JOKER`, generic action exposure, or a shortcut that approximates economy.