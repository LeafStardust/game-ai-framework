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
3. inspect canonical owner(s) and pinned vanilla source for the next task;
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
- pre-deal Manacle/Chicot requires authoritative retained physical deck order and never reconstructs it from canonical public `deck`.

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

Owned R1 categories include:

- static score/rule/retrigger Jokers audited incrementally;
- exact money-based and owned-deck-based scoring Jokers;
- `G.playing_cards` all-or-nothing permanent-deck observation;
- strict permanent-card decode/count/modifier validation;
- strict LuaJIT authoritative-array path for `G.playing_cards`;
- private draw/discard/played-zone validation;
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
- generic vouchers/packs;
- malformed/noninteger prices;
- generic `SELL_JOKER` where inverse lifecycle is not owned;
- lifecycle acquisitions whose consequences are not owned across arbitrary reachable states.

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

- one keyed pseudoseed advance per shuffle;
- one LuaJIT stream drives Fisher–Yates;
- CardArea shuffle re-sorts by creation/`sort_id` order before RNG;
- repeated keyed `random()` calls are not equivalent.

```text
246f442  exact pseudoshuffle
d9662c6  shuffle vectors + restore behavior
CI 33791916289: 1435 passed, 1594 deselected
```

### R2.3 — playing-card/Joker creation order — GREEN FOR OWNED CASES

- playing-card creation order retained privately from exact live IDs or pristine base-deck structure;
- Joker creation and physical order are separate simulator-owned state;
- simulator acquisitions/removals retain exact Joker creation order;
- duplicate/missing/noninteger live IDs fail closed;
- no fake public `sort_id` field.

```text
e7b0bb0  derive exact playing-card creation order
2a26e79  pin creation-order regressions
34d88e9  include env_r2 coverage in CI
7c070b2  retain exact playing-card order in headless state
2dc47eb  retained-order regressions
CI 33795507133: 1461 passed, 1594 deselected
```

### R2.4 — shuffle/deal + round resources — GREEN

Owned:

- exact supported-deck shuffle/deal;
- hidden physical order kept private while public `deck` is canonicalized;
- exact deck-tail draw direction;
- exact hand sorting for owned card-history cases;
- exact headless RNG ownership/replay state;
- one-shot hand/discard round bonuses consumed in source order;
- first blind starts from source-correct `round 0 -> 1`.

Representative gates:

```text
33794664514  1461 passed, 1594 deselected
33797071526  1482 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
33803629167  1563 passed, 1594 deselected
33804894982  1593 passed, 1594 deselected
```

### R2.5 — `setting_blind` Jokers — PARTIAL / EXACT WHERE AUDITED

Burglar lifecycle effect is exact on supported starts:

```text
hands_remaining += 3
discards_remaining = 0
```

Chicot `setting_blind` behavior is source-ordered through centralized `Blind:disable()` ownership for the supported Boss set, including retained-deck pre-deal Manacle.

**Burglar and Chicot acquisitions remain fail-closed** because purchase persists into arbitrary future lifecycle states not yet all owned.

### R2.6 — non-Boss starts — GREEN FOR SUPPORTED STATE

Small/Big setup owns:

1. `ease_round(1)` equivalent;
2. blind target/resource initialization;
3. round bonuses;
4. audited `setting_blind` effects;
5. exact shuffle/deal;
6. policy-safe public/private card zones.

### R2.7 — Boss lifecycle — BROADLY GREEN FOR ALL 28 VANILLA BOSSES

Owned active/start/disable/defeat mechanics cover the full vanilla Boss roster:

```text
The Wall + Violet Vessel       requirement-only
The Eye + The Mouth            mutable hand-rule state
The Water + The Needle         reversible round resources
The Manacle                    hand-size mutation + retained Chicot paths
The Goad/Window/Head/Club      static suit card debuffs
The Plant                      face-card debuffs
Cerulean Bell                  forced-selection lifecycle
The Psychic                    hand rejection
The Flint                      base score halving
The Tooth                      -$1 per played card
The Hook                       keyed forced discards
The Ox                         target hand -> money = 0
The Arm                        hand-level decrement
The Serpent                    post-action 3-card draw
The House + The Mark           deterministic facing
The Wheel                      keyed per-draw facing RNG
The Fish                       temporal post-play facing
The Pillar                     permanent Ante play history
Verdant Leaf                   all-card debuff + minimum sale
Amber Acorn                    hidden Joker order + reveal
Crimson Heart                  Joker debuff lifecycle
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

#### Verdant Leaf

- start debuffs all permanent playing cards;
- minimum audited static Joker sale credits exact sell value;
- sale disables Verdant and clears permanent-card debuffs;
- Chicot uses the same inverse;
- unsupported/Eternal/resource-sensitive sale paths fail closed;
- generic training `SELL_JOKER` remains hidden.

#### Amber Acorn

- all owned Jokers hidden while active;
- `G.jokers:shuffle("aajk")` runs three times with source-exact re-sort-before-each-shuffle;
- hidden physical order retained internally;
- policy sees multiset but not identity-to-position mapping;
- defeat/disable reveals retained physical order without restoring pre-Amber order.

#### Crimson Heart

- pre-deal `prepped` state;
- keyed target selection over retained Joker creation order;
- previous-target exclusion when possible;
- `press_play` re-arms selection;
- selected Joker receives public `debuffed` state;
- debuffed scoring is suppressed while Joker remains present for cross-Joker mechanics;
- disable clears debuff/prepped without RNG;
- normal defeat's blank-blind pass clears selected Joker debuff and installs `prepped=true` without extra RNG.

Crimson normal-defeat/cash-out correction:

```text
8e2fdb3  own Crimson Heart normal defeat
0ea44f7  direct normal-defeat regression
3714484  composed cash-out regression
CI 33905449910: 1876 passed, 1595 deselected
```

#### Chicot / centralized `Blind:disable()`

Pinned ordering:

1. round resources installed;
2. Boss `set_blind` mutation;
3. supported Jokers receive `setting_blind`;
4. Burglar outputs installed;
5. queued Chicot disable executes;
6. only later does `DRAW_TO_HAND` / `nr{ante}` shuffle/deal occur.

Central dispatcher owns disable consequences for the current full Boss mechanics surface, including retained pre-deal Manacle, static debuffs, facing cleanup, Cerulean, Amber, Crimson, Verdant and simple Boss disable state.

Multiple Chicot disable requests remain fail-closed until repeated-disable event semantics are explicitly owned.

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

Exact ownership:

- retained prior-round private deck order;
- pre-shuffle tail draw at Chicot timing;
- later shuffle only of remaining cards;
- no duplicate/redrawn pre-drawn card;
- fail closed without authoritative retained deck.

```text
CI 33870571411: 1821 passed, 1595 deselected
CI 33871756000: 1824 passed, 1595 deselected
CI 33872332123: 1828 passed, 1595 deselected
CI 33872735051: 1833 passed, 1595 deselected
CI 33873017991: 1838 passed, 1595 deselected
```

Generic training `SELECT_BLIND` remains hidden.

### R2.9 — ROUND-END CASHOUT + BLIND/ANTE PROGRESSION — GREEN FOR NORMAL OWNED CHAIN

Owned source-ordered cash-out pieces:

1. cleared-blind validation at `ROUND_EVAL`;
2. exact permanent-card hand/discard/deck repopulation with retained private physical order;
3. blind reward payout;
4. `$1` per unused hand;
5. base interest from pre-payout money, `$1` per `$5`, capped at `$5` for current economy boundary;
6. audited end-of-round Joker dollar effects with unsupported identities fail-closed;
7. exact money mutation/input isolation;
8. active but intentionally ungenerated `SHOP` state;
9. no premature shop RNG consumption;
10. Small/Big cash-out;
11. Boss cash-out across all 28 vanilla Bosses through the normal-defeat owner.

Normal-defeat source correction:

```text
Blind:set_blind(nil, nil, true)
```

Arguments are `(blind=nil, reset=nil, silent=true)`: the third `true` is **silent**, not `reset=true`. Normal defeat installs a blank active blind and executes ordinary permanent-card/Joker debuff passes.

Facing-state normal-defeat audit is closed:

- `Blind:defeat()` does **not** run `Blind:disable()`'s explicit House/Wheel/Mark/Fish hand-card flip cleanup;
- back-facing cards may physically remain back-facing through hand -> discard -> deck repopulation;
- `new_round()` clears `wheel_flipped` on all permanent playing cards;
- `CardArea:emplace` flips a back-facing card when entering a normal hand unless the **current** Blind asks it to stay flipped;
- therefore old House/Wheel/Mark/Fish orientation is not a cross-round gameplay dependency and no synthetic public/private facing field is required solely for normal defeat/cash-out;
- normal defeat intentionally performs no synthetic face-up mutation.

Facing closure commits/gate:

```text
2da4ac4  own facing-state Boss normal defeat
be352a5  direct facing-state defeat regressions
a55cb2a  composed facing-state cash-out regressions
db64bab  compare copied cash-out cards by stable semantic content
CI 33906956546: 1884 passed, 1595 deselected
```

The normal-defeat owner accounts for **all 28 vanilla Boss names**.

The normal progression chain is now also owned for the current exact boundary:

1. `finalize_won_round_progression()` marks the current Small/Big/Boss defeated;
2. Boss `end_round` advances Ante and clears one-shot round bonuses before cash-out;
3. cash-out remains a separate lifecycle boundary and enters active, ungenerated `SHOP`;
4. `enter_blind_select_progression()` chooses the next available Small -> Big -> Boss in source order;
5. `reset_blinds_after_boss_cashout()` restores next-Ante Small/Big/Boss Upcoming state;
6. normal Boss selection uses exact keyed RNG and usage-count filtering;
7. normal Small/Big skip-tag selection uses exact keyed RNG/profile gating;
8. after a Boss cash-out, next-Ante choices are generated in source order: **Small Tag -> Big Tag -> Boss**;
9. `resolve_supported_boss_round()` composes the owned Boss end-round -> cash-out -> next-Ante generation chain while stopping at the ungenerated SHOP boundary.

Progression/generation commits:

```text
4cc2683  own blind progression end-round state
59fb3e9  isolate blind progression primitive
de192be  pin end-round blind progression
082641f  own deterministic BLIND_SELECT progression
db69e28  pin deterministic BLIND_SELECT progression
44efee3  own deterministic Boss blind reset
b9b3e0e  pin deterministic Boss reset_blinds state
f5496db  own exact normal Boss selection
257491d  pin exact normal Boss selection
5a49122  own exact normal skip-tag selection
89a7207  pin exact normal skip-tag selection
4db12ac  compose post-Boss blind generation
2951267  pin post-Boss blind generation order
db2fe5b  compose exact Boss round resolution
8fff3b6  cover composed Boss round resolution
```

Latest composition gate:

```text
CI 33915588784: 1924 passed, 1595 deselected
```

R2.9 is therefore closed for the current normal owned progression chain. Unsupported end-of-round Joker/economy modifiers and active Tag effects remain fail-closed; they are not implied by this closure.

Do not fold asynchronous vanilla events into the wrong strategic action merely for convenience. Cash-out, shop generation, leaving the shop, and blind selection remain separate lifecycle/action boundaries unless pinned source proves otherwise.

### Remaining R2 categories after R2.9 progression closure

- **shop inventory generation RNG** — next structural blocker for general multi-round traversal;
- reroll RNG and reroll-cost/economy modifiers;
- booster/pack contents, choice RNG, and pack state;
- voucher availability/lifecycle and voucher-driven shop/economy modifiers;
- active Tag application/cash-out effects beyond exact normal tag selection/generation;
- remaining unsupported end-of-round Joker/economy modifiers;
- fixed-seed replay across representative multi-round trajectories.

Normal Boss-selection RNG/progression and normal skip-tag generation are no longer listed as unfinished: those deterministic owners are green.

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

```text
END_SHOP      supported only where exact transition exists
BUY_*         only exact audited subsets become legal
SELECT_BLIND  PLANNED / HIDDEN
SELL_JOKER    PLANNED / minimum Verdant path only
SKIP_BLIND    PLANNED
REROLL_SHOP   PLANNED
PACK actions  PARTIAL/PLANNED
```

Every training-visible action requires stable canonical ID, deterministic legality, exact transition, serialization representation, and mask representation.

Do not widen `SELECT_BLIND` merely because individual start helpers are green.

---

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development. Tactical trajectories remain logged for parity/debugging.

## R5 — live/simulator parity — NOT STARTED

Priority fixtures:

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
- fixed-seed replay deterministic;
- representative live parity fixtures green;
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
R2 all 28 Boss mechanics surface        BROADLY GREEN
R2 Chicot Boss disable                  GREEN FOR OWNED BOUNDARY
R2 retained Manacle+Chicot source order GREEN — CI 33873017991
R2 round-end private deck retention     GREEN
R2 ordinary Small/Big cash-out -> SHOP  GREEN
R2 all-Boss normal defeat/cash-out      GREEN — CI 33906956546
R2.9 Boss teardown                      CLOSED FOR 28 VANILLA BOSSES
R2.9 normal blind/Ante progression      GREEN
R2.9 normal Boss selection              GREEN
R2.9 normal skip-tag generation         GREEN
R2.9 Boss -> next-Ante generation       GREEN
R2.9 composed Boss round resolution     GREEN — CI 33915588784
Shop inventory generation RNG           NEXT STRUCTURAL BLOCKER
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
8fff3b61114957ecdc4b4ffc3597833a7007f938
```

Latest authoritative green deterministic gate:

```text
CI 33915588784: 1924 passed, 1595 deselected
```

The next code written should therefore be **an exact source audit of normal shop inventory generation followed by the narrowest coherent R2 shop-generation RNG slice that can be proved exact**. Start from pinned vanilla shop creation/item-pool/RNG ordering and explicitly identify required profile/unlock, voucher, Tag, edition, rarity, booster, and slot-state dependencies before admitting generation. Keep unsupported dependencies fail-closed. It should **not** be Bond tuning, PPO, broad action exposure, generic shop approximations, or Python-RNG shortcuts.
