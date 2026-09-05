# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Objective

**Maximize P(clear Ante 8 | Red Deck, White Stake, normal mode).**

The project has pivoted from manually tuned Bond-value strategy to reinforcement learning in a fast deterministic Balatro environment. Existing deterministic mechanics, legality, state observation, tactical hand play, candidate projection, telemetry, and useful Bond-derived features remain assets; manual Bond coefficient tuning is retired as the primary competence path.

## Non-negotiable contract

- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported or inexact transitions stay absent from the training mask.
- Prefer canonical ownership over wrappers, rescue layers, approximations, or duplicated mechanics.
- Training code must not redefine Balatro mechanics for convenience.
- Simulator shortcuts are allowed only when behaviorally equivalent at the modeled boundary and covered by parity/regression tests.
- Model checkpoints are artifacts, not strategy source of truth.
- Do **not** start PPO/observation training before exact environment semantics and representative live/simulator parity gates.
- Work Chat runs deterministic/static validation itself. GitHub Actions is authoritative when no local clone exists.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Permanent deck truth is `G.playing_cards`; never substitute `G.deck.cards`.
- Hidden physical draw order and face-down card/Joker identity-to-position mappings are not policy-visible information.
- Python `random` is not Balatro RNG.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.
- If context becomes insufficient to continue safely, **stop immediately rather than guessing**.

## Continuation procedure

For every continuation session:

1. read this `ROADMAP.md` first;
2. verify current branch/HEAD before editing;
3. inspect canonical owners and pinned vanilla source for the next task;
4. check for intervening commits before writing;
5. treat chat/session summaries as navigation only; repository state is authoritative;
6. add focused fail-closed regressions for every new exactness slice;
7. push coherent completed commits;
8. inspect the actual CI pytest result, not only the workflow badge;
9. synchronize this roadmap after green slices.

Pinned vanilla source:

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
- Amber Acorn hidden Joker mapping is masked while active;
- unsupported Joker inverse sale lifecycles remain rejected;
- pre-deal Manacle/Chicot requires authoritative retained physical deck order;
- shop Joker generation requires authoritative dynamic eligibility;
- malformed Joker generation catalogues are rejected all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal.

---

# Foundation status

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
L3 environment freeze                COMPLETE
R0 headless environment architecture COMPLETE
R1 deterministic state/acquisition   SUBSTANTIALLY COMPLETE
R2 RNG/lifecycle/shop generation     ACTIVE — PRIMARY WORKSTREAM
R3 typed action vocabulary           PARTIAL / TIED TO EXACTNESS
R4 deterministic tactical bridge     NOT STARTED
R5 live/simulator parity harness      NOT STARTED
R6 environment performance gate      NOT STARTED
O observation/action encoding        NOT STARTED
B0 RL baseline infrastructure        NOT STARTED
PPO strategic learner                NOT STARTED
```

L3 contract remains `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`.

The simulator is **not authoritative game truth** until R5 representative live/simulator parity passes.

---

# R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

Owned resource-sensitive acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

Owned categories include:

- broad static score/rule/retrigger Joker acquisition groups;
- money-based and owned-deck-based scoring Jokers;
- exact `G.playing_cards` permanent-deck observation;
- strict card decode/count/modifier validation;
- strict LuaJIT authoritative-array path;
- private draw/discard/played-zone validation;
- exact headless seed/tag/container validation;
- owned-deck-sensitive acquisitions including Steel Joker, Stone Joker, Driver's License, and Erosion.

Representative gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Still fail closed where not globally owned:

- unknown/unaudited Joker acquisitions;
- Joker editions, especially Negative slot-capacity consequences;
- generic voucher/pack acquisition;
- malformed/noninteger prices;
- generic `SELL_JOKER` inverse lifecycle;
- arbitrary lifecycle acquisitions whose future effects are not yet exact.

---

# R2 — RNG + round/blind/Boss/shop lifecycle — ACTIVE

## R2.1 — Balatro/LuaJIT RNG — GREEN

Owned:

- keyed pseudohash/pseudoseed progression;
- LuaJIT combined Tausworthe generator;
- inclusive integer draws;
- independent keyed queues;
- exact serializable node state;
- bit-preserving snapshot/restore.

```text
2e61cd8  exact Balatro/LuaJIT RNG primitives
290ff11  pinned RNG reference vectors
CI 33791671797: 1432 passed, 1594 deselected
```

## R2.2 — pseudoshuffle — GREEN

- one keyed pseudoseed advance per shuffle;
- one LuaJIT stream drives Fisher–Yates;
- CardArea re-sorts by creation/`sort_id` order before shuffle;
- repeated keyed `random()` calls are not equivalent.

```text
246f442  exact pseudoshuffle
d9662c6  shuffle vectors + restore behavior
CI 33791916289: 1435 passed, 1594 deselected
```

## R2.3 — card/Joker creation order — GREEN FOR OWNED CASES

- playing-card creation order retained privately from exact live IDs or pristine base-deck structure;
- Joker creation and physical order are separate simulator-owned state;
- simulator acquisitions/removals retain exact Joker creation order;
- duplicate/missing/noninteger live IDs fail closed;
- no fake public `sort_id`.

```text
e7b0bb0  derive exact playing-card creation order
2a26e79  pin creation-order regressions
34d88e9  include env_r2 in CI
7c070b2  retain playing-card order in headless state
2dc47eb  retained-order regressions
CI 33795507133: 1461 passed, 1594 deselected
```

## R2.4 — shuffle/deal + round resources — GREEN

Owned:

- exact supported-deck shuffle/deal;
- hidden physical draw order remains private;
- exact deck-tail draw direction;
- exact hand sorting for owned card-history cases;
- exact RNG replay state;
- one-shot hand/discard bonuses consumed in source order;
- first blind starts source-correctly from `round 0 -> 1`.

Representative gates:

```text
33794664514  1461 passed, 1594 deselected
33797071526  1482 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
33803629167  1563 passed, 1594 deselected
33804894982  1593 passed, 1594 deselected
```

## R2.5–R2.8 — blind/Boss lifecycle — BROADLY GREEN

Exact ownership now covers the normal Red/White lifecycle for all 28 vanilla Bosses across their audited start/active/disable/defeat mechanics, including:

- Burglar `setting_blind` hands/discards;
- centralized Chicot `Blind:disable()` behavior;
- The Water / Needle / Manacle resources;
- Eye / Mouth mutable hand-rule state;
- static suit/face debuffs;
- Cerulean forced selection;
- Psychic rejection;
- Flint score base reduction;
- Tooth money loss;
- Hook forced discard RNG;
- Ox money reset;
- Arm hand-level decrement;
- Serpent post-action draw;
- House/Mark/Wheel/Fish facing state;
- Pillar permanent play history;
- Verdant Leaf debuff + sale disable path;
- Amber Acorn hidden Joker ordering;
- Crimson Heart Joker debuff lifecycle;
- retained prior physical deck order for pre-deal Manacle/Chicot.

Representative gates:

```text
33855720629  1734 passed, 1595 deselected
33857249827  1755 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33865394680  1805 passed, 1595 deselected
33869467530  1815 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
```

Generic training `SELECT_BLIND` remains hidden until the strategic action boundary is frozen end-to-end; exact internal lifecycle primitives may be broader than the currently exposed training vocabulary.

## R2.9 — round-end cashout + blind/Ante progression — GREEN FOR NORMAL OWNED CHAIN

Owned source ordering includes:

1. cleared-blind validation at `ROUND_EVAL`;
2. exact permanent-card zone repopulation;
3. blind reward payout;
4. `$1` per unused hand;
5. base interest from pre-payout money, capped at `$5` for the current economy boundary;
6. audited end-of-round Joker dollar effects;
7. active but initially ungenerated `SHOP` state;
8. Small/Big/Boss defeat/cashout progression;
9. exact normal Boss selection;
10. exact normal skip-tag selection;
11. next-Ante Small Tag -> Big Tag -> Boss generation order;
12. composed supported Boss round resolution to SHOP.

```text
CI 33915588784: 1924 passed, 1595 deselected
```

Do not fold asynchronous vanilla events into the wrong strategic action. Cashout, shop generation, leaving shop, and blind selection remain distinct unless source proves otherwise.

---

# R2.10 — normal shop generation — ACTIVE / CURRENT WORKSTREAM

## Base main-shop type RNG — GREEN

Unmodified rates:

```text
Joker    20
Tarot     4
Planet    4
Base      0
Spectral  0
```

- key: `cdt{ante}`;
- two ordinary main-shop slots;
- voucher/Tag rate modifiers and already-generated inventory fail closed.

## Ordinary Joker rarity RNG — GREEN

Key:

```text
rarity{ante}sho
```

Thresholds:

```text
Common    <= 0.70
Uncommon  >  0.70
Rare      >  0.95
```

Legendary is not reachable through this ordinary path.

## Frozen vanilla Joker centre order — GREEN

- all 150 vanilla Joker centers pinned in mechanically significant global order;
- Common 61 / Uncommon 64 / Rare 20 / Legendary 5;
- source spellings retained exactly;
- rarity pools preserve global center order.

Key commits:

```text
f85364a  base shop Joker rarity RNG
f8712ae  rarity regressions
ff011d2  freeze vanilla Joker pool order
41f26f1  pin vanilla Joker catalogue
```

## Dynamic Joker eligibility observation — GREEN

Live authoritative owner:

```text
games/balatro/live/runtime/joker_generation_pool_observer.py
```

It reads and applies the runtime predicates required by vanilla pool construction:

- rarity-pool order from `G.P_JOKER_RARITY_POOLS`;
- unlock state;
- `G.GAME.used_jokers` duplicate suppression;
- Showman override;
- `no_pool_flag` / `yes_pool_flag` against `G.GAME.pool_flags`;
- `G.GAME.banned_keys`.

Critical reads are all-or-nothing. Incomplete runtime state yields no authoritative pool.

Canonical state schema uses string rarity keys:

```text
"1", "2", "3", "4"
```

Recent schema defect and repair:

```text
4997f52  fix canonical string rarity lookup
ad31609  fix observer→translator regression expectation
b13fadd  pin canonical state→shop bridge
CI 33941331764: 1962 passed, 1595 deselected
```

The headless bridge now validates the **entire** rarity 1–4 catalogue before using any selected rarity, including record rarity/key/metadata types and duplicate keys:

```text
fdcb329  validate observed Joker pools all-or-nothing
12c4724  regress malformed unrelated rarities/metadata/duplicates
CI 33941827707: 1973 passed, 1595 deselected
```

## Concrete Joker center identity / resampling — GREEN

Given authoritative eligible keys:

- unavailable rarity-pool positions stay literal `UNAVAILABLE`;
- initial key: `Joker{rarity}sho`;
- resamples: `Joker{rarity}sho_resample2`, `...3`, etc.;
- all-unavailable fallback remains vanilla `j_joker`.

Center selection does not guess profile state.

## Ordinary Joker edition RNG — GREEN FOR BASE RATE

Vanilla ordinary shop Joker creation occurs inside:

```text
create_card(..., key_append='sho')
```

Edition key:

```text
edisho{ante}
```

Non-guaranteed `_mod=1`, Negative-allowed thresholds use one draw in this source order:

```text
Negative      roll > 1 - 0.003              (not scaled by edition_rate)
Polychrome    roll > 1 - 0.006*edition_rate
Holographic   roll > 1 - 0.020*edition_rate
Foil          roll > 1 - 0.040*edition_rate
None          otherwise
```

The current base boundary rejects vouchers and active Tags and therefore requires exact `edition_rate == 1.0`.

```text
05ffd67  own base shop Joker edition RNG
3339309  pin threshold/order/RNG regressions
CI 33941586989: 1967 passed, 1595 deselected
```

Generated Negative editions are valid generation state. **Negative acquisition remains fail-closed** until its slot-capacity consequence is owned.

## Ordinary Joker descriptor composition — GREEN

`games/balatro/env/shop_joker_generation.py` now composes the Joker-specific part of vanilla `create_card(..., 'sho')`:

1. rarity;
2. authoritative eligible center + exact resampling;
3. edition.

It returns a deterministic descriptor containing:

```text
center_key
rarity
edition
resamples
post-generation RNG state
```

It intentionally does **not** yet instantiate a Python Joker, set a shop price, place inventory, or imply purchase legality.

```text
fbc8aad  compose ordinary shop Joker descriptor
015daa4  pin descriptor source-order/RNG regression
CI 33941690306: 1970 passed, 1595 deselected
```

## Current R2.10 blocker — PRICE + INVENTORY MATERIALIZATION

A descriptor is not yet an actual shop card. Before ordinary Joker slots become generated public inventory, own source-exact pricing and safe materialization.

Pinned vanilla `Card:set_cost()` formula:

```text
extra_cost = inflation
+ 3 if Holographic
+ 2 if Foil
+ 5 if Polychrome
+ 5 if Negative

cost = max(
    1,
    floor((base_cost + extra_cost + 0.5) * (100 - discount_percent) / 100)
)
```

Immediate next work:

1. audit/freeze authoritative base costs for all ordinary Joker centers, or provide an equally exact canonical owner;
2. own inflation and discount-percent state needed by `Card:set_cost()`;
3. add exact price regressions for unedited/Foil/Holographic/Polychrome/Negative cases;
4. define a generated shop-item representation that can carry center identity, rarity, edition, and exact price without requiring every center to be constructible as a strategy Joker object;
5. insert generated Joker items into `shop_jokers` only after identity + edition + price are exact;
6. keep purchase legality independently fail-closed for unsupported identities/editions;
7. then compose both ordinary main-shop slots in source order;
8. after Joker slots, own Tarot/Planet identity generation before declaring base main-shop generation complete.

Do **not** skip directly from descriptor to a generic fabricated Joker object. Some Jokers require dynamic constructor/lifecycle state and must remain unsupported until that state is owned.

---

# R3 — typed action vocabulary — PARTIAL / TIED TO EXACTNESS

Target strategic actions as exact ownership becomes available:

```text
END_SHOP
REROLL_SHOP
BUY_JOKER(slot)
SELL_JOKER(slot)
BUY_VOUCHER(slot)
BUY_CONSUMABLE(slot)
BUY_CARD(slot)
OPEN_PACK(slot/type)
CHOOSE_PACK_OPTION(index)
SKIP_PACK
USE_CONSUMABLE(targets...)
SKIP_BLIND
SELECT_BLIND / START_BLIND
```

Every training-visible action requires stable type/id, parameters, deterministic legality, exact transition, serialization representation, and mask representation.

Do not expose an action merely because an internal transition primitive exists.

# R4 — deterministic tactical bridge — NOT STARTED

Reuse the validated deterministic hand-play stack while RL initially controls strategic run development. Tactical trajectories remain logged for parity/debugging.

# R5 — live/simulator parity harness — NOT STARTED

Priority fixtures:

- ordinary shop generation/purchase/hold/end-shop;
- Joker replacement/sale;
- reroll;
- voucher purchase/rejection;
- pack paths;
- blind skip/start/clear;
- boss restrictions;
- Card Sharp reset;
- Throwback skip counter;
- Baron held-card state;
- owned-deck composition;
- economy/interest transitions;
- RNG/shuffle/initial-draw parity.

# R6 — environment performance gate — NOT STARTED

Only after semantic correctness: measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead.

# Later RL phases — NOT STARTED

## O — observation/action encoding

Versioned public observation/action schemas; no hidden-information leakage; illegal-action probability zero after masking.

## B0 — baseline infrastructure

- random legal strategic baseline;
- existing symbolic policy as deterministic baseline where compatible;
- fixed evaluation seed banks;
- run-level metrics and reproducible trajectory logging.

## PPO — strategic learner

Start only after Phase-R exactness/parity/performance and O/B0 prerequisites are satisfied.

---

# Current checkpoint — 2026-09-05

```text
Historical symbolic/Bond architecture        COMPLETE AS BASELINE
Manual Bond numerical tuning                 RETIRED AS PRIMARY PATH
R0 environment architecture                  COMPLETE
R1 deterministic transition/acquisition      SUBSTANTIALLY COMPLETE
R2 RNG/pseudoshuffle                         GREEN
R2 card/Joker ordering                       GREEN FOR OWNED CASES
R2 deal/round resources                      GREEN
R2 Boss lifecycle                            BROADLY GREEN — 28 VANILLA BOSSES OWNED
R2 cashout/blind/Ante progression            GREEN FOR NORMAL OWNED CHAIN
R2.10 shop type RNG                          GREEN
R2.10 Joker rarity RNG                       GREEN
R2.10 150-center order                       GREEN
R2.10 dynamic eligibility observer           GREEN
R2.10 canonical pool bridge                  GREEN
R2.10 all-rarity fail-closed validation      GREEN — CI 33941827707
R2.10 center identity/resampling             GREEN
R2.10 base edition RNG                       GREEN — CI 33941586989
R2.10 ordinary Joker descriptor              GREEN — CI 33941690306
R2.10 Joker price/materialization            NEXT
R3 training vocabulary                       PARTIAL
R4 tactical bridge                           NOT STARTED
R5 parity harness                             NOT STARTED
R6 performance gate                          NOT STARTED
Observation/action encoding                  NOT STARTED
RL baselines                                 NOT STARTED
PPO                                          NOT STARTED
```

Current code head before this documentation commit:

```text
12c472464b830e9ddab78d235a226c4c4db5d0c6
```

Latest authoritative green deterministic gate:

```text
CI 33941827707
1973 passed, 1595 deselected
```

No live Balatro run is required at this checkpoint.

## Exact next development action

Continue **R2.10 normal shop generation** at the pricing/materialization boundary:

1. pin exact ordinary Joker base-cost ownership;
2. pin/validate inflation and discount-percent inputs;
3. implement exact `Card:set_cost()` equivalent for generated Joker descriptors;
4. test edition surcharges and fail-closed modifiers;
5. create a generic exact generated-shop-item representation rather than forcing every selected center through `LiveJokerFactory`;
6. only then populate `shop_jokers` and compose both ordinary main-shop slots.

Do **not** start PPO, observation encoding, Bond tuning, or an open-ended live run.