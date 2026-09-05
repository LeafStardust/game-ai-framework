# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Objective

**Maximize P(clear Ante 8 | Red Deck, White Stake, normal mode).**

The project has pivoted from manually tuned Bond-value strategy to reinforcement learning in a fast deterministic Balatro environment. Existing deterministic mechanics, legality, public-state observation, tactical hand play, candidate projection, telemetry, and useful Bond-derived features remain assets. Manual Bond coefficient tuning is retired as the primary competence path.

## Non-negotiable contract

- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported or inexact transitions stay absent from the training mask.
- Prefer canonical ownership over wrappers, rescue layers, duplicated mechanics, or approximations.
- Training code must not redefine Balatro mechanics for convenience.
- Simulator shortcuts are allowed only when behaviorally equivalent at the modeled boundary and regression/parity covered.
- Model checkpoints are artifacts, not strategy source of truth.
- Do **not** start PPO or observation training before exact environment semantics and representative live/simulator parity gates.
- Work Chat runs deterministic/static validation itself. GitHub Actions is authoritative when no local clone is available.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Permanent deck truth is `G.playing_cards`; never substitute `G.deck.cards`.
- Hidden physical draw order and face-down card/Joker identity-to-position mappings are not policy-visible.
- Python `random` is not Balatro RNG.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.
- If context becomes insufficient to continue safely, **stop immediately rather than guessing**.

## Continuation procedure

For every continuation session:

1. read this file first;
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

## Current checkpoint — 2026-09-05

```text
Branch: feat/v1.0-red-white-competence
Code HEAD before this roadmap sync:
337bd9bd6c7dda98cbbca091928dadb393aff9c5
  test(balatro): pin normal voucher selection sequence

Latest verified code-head CI:
33946770946
2079 passed, 1595 deselected
```

This roadmap-sync commit is documentation-only and becomes the branch HEAD after it is pushed. The code checkpoint above remains the latest mechanics checkpoint until further code lands.

### Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**, with remaining lifecycle-specific exclusions kept fail-closed.
- R2 RNG/lifecycle/shop generation: **ACTIVE — PRIMARY WORKSTREAM**.
- Exact ordinary shop reroll: **IMPLEMENTED / GREEN**.
- Exact normal Voucher identity polling/selection: **IMPLEMENTED / GREEN**.
- Authoritative Voucher eligibility/generation-pool observation: **NEXT TASK**.
- Voucher purchase/effect lifecycle: **NOT implied by identity selection; remains separately gated**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **NOT CURRENTLY REQUIRED**.

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
- malformed Joker generation catalogues are rejected all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal;
- malformed Tarot/Planet eligibility records are rejected before shop RNG advances;
- the canonical Tarot/Planet catalogue may not be overwritten by legacy wrappers;
- two-slot shop generation preflights every possible catalogue/pricing dependency before the first type RNG draw;
- Voucher selection must not use a guessed/static eligibility catalogue.

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

L3 contract remains:

```text
BALATRO_ENV_CONTRACT_VERSION = "l3-v1"
```

The simulator is **not authoritative game truth** until representative R5 live/simulator parity passes.

---

# R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

## Exact state/resource ownership

Owned resource-sensitive acquisitions include:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

Owned deterministic state categories include:

- broad static score/rule/retrigger Joker acquisition groups;
- money-based scoring Jokers;
- permanent-owned-deck scoring Jokers;
- exact `G.playing_cards` permanent-deck observation;
- strict card decode/count/modifier validation;
- strict LuaJIT authoritative-array decoding;
- private draw/discard/played-zone validation;
- exact seed/tag/container validation;
- owned-deck-sensitive acquisitions including Steel Joker, Stone Joker, Driver's License, and Erosion;
- exact next-round hand/discard allowance observation where required.

Representative R1 gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Still fail closed where not globally owned:

- unknown/unaudited Joker acquisitions;
- Joker editions where acquisition changes capacity semantics, especially Negative;
- generic Voucher effect application;
- booster-pack opening where exact pack lifecycle is not yet owned;
- malformed/noninteger prices;
- generic SELL_JOKER inverse lifecycle where a Joker has unowned inverse effects;
- lifecycle acquisitions whose future effects remain unowned.

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
- card areas re-sort by exact retained creation order before shuffle;
- repeated keyed `random()` calls are not equivalent.

```text
246f442  exact pseudoshuffle
d9662c6  shuffle vectors + restore behavior
CI 33791916289: 1435 passed, 1594 deselected
```

## R2.3 — card/Joker creation order — GREEN FOR OWNED CASES

- playing-card creation order retained privately from exact live IDs or pristine base-deck structure;
- Joker physical/creation order retained separately where needed;
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
- first blind starts source-correctly from round 0 -> 1.

Key early blind-start slice:

```text
5e2e02a  own pristine first blind start
5e9c77a  pin pristine first blind lifecycle
CI 33796012173: 1467 passed, 1594 deselected
```

Representative later gates:

```text
33797071526  1482 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
33803629167  1563 passed, 1594 deselected
33804894982  1593 passed, 1594 deselected
```

## R2.5–R2.8 — blind/Boss lifecycle — BROADLY GREEN

Exact normal Red/White ownership covers audited start/active/disable/defeat mechanics across all 28 vanilla Bosses, including:

- Burglar `setting_blind` hands/discards;
- centralized Chicot `Blind:disable()` behavior;
- Water / Needle / Manacle resources;
- Eye / Mouth mutable hand-rule state;
- static suit/face debuffs;
- Cerulean forced selection;
- Psychic rejection;
- Flint score-base reduction;
- Tooth money loss;
- Hook forced-discard RNG;
- Ox money reset;
- Arm hand-level decrement;
- Serpent post-action draw;
- House/Mark/Wheel/Fish facing state;
- Pillar permanent play history;
- Verdant Leaf debuff + sale-disable path;
- Amber Acorn hidden Joker ordering;
- Crimson Heart Joker-debuff lifecycle;
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

Generic training `SELECT_BLIND` remains gated by end-to-end strategic-action ownership even though internal exact lifecycle primitives are substantially broader.

## R2.9 — round-end cashout + blind/Ante progression — GREEN FOR NORMAL OWNED CHAIN

Owned source ordering includes:

1. cleared-blind validation at ROUND_EVAL;
2. exact permanent-card zone repopulation;
3. blind reward payout;
4. `$1` per unused hand;
5. base interest from pre-payout money, capped at `$5` for the current economy boundary;
6. audited end-of-round Joker dollar effects;
7. active but initially ungenerated SHOP state;
8. Small/Big/Boss defeat/cashout progression;
9. exact normal Boss selection;
10. exact normal skip-tag selection;
11. next-Ante Small Tag -> Big Tag -> Boss generation order;
12. composed supported Boss round resolution to SHOP.

```text
CI 33915588784: 1924 passed, 1595 deselected
```

Cashout, shop generation, leaving shop, and blind selection remain distinct strategic boundaries unless pinned source proves otherwise.

---

# R2.10 — normal shop generation — ACTIVE / CURRENT WORKSTREAM

## Main-shop type RNG — GREEN

Unmodified rates:

```text
Joker    20
Tarot     4
Planet    4
Base      0
Spectral  0
```

- key `cdt{ante}`;
- two ordinary main-shop slots;
- unsupported Voucher/Tag rate modifiers fail closed at the relevant boundary.

## Ordinary Joker generation — GREEN THROUGH METADATA MATERIALIZATION

Owned:

- rarity key `rarity{ante}sho`;
- all 150 vanilla Joker centers in source-significant order;
- authoritative runtime eligibility from `G.P_JOKER_RARITY_POOLS`, unlocks, duplicate suppression, Showman, pool flags, bans, and immutable center cost;
- all rarity 1–4 canonical catalogue validation before RNG;
- identity key `Joker{rarity}sho` plus source-compatible resampling;
- ordinary edition key `edisho{ante}` with exact threshold ordering;
- descriptor composition rarity -> center/cost -> edition;
- exact `Card:set_cost()` pricing from authoritative inflation and discount percent;
- Foil/Holographic/Polychrome/Negative metadata surcharges;
- generic `GeneratedShopJokerItem`;
- shared two-slot capacity enforcement without fabricating a gameplay Joker object.

```text
CI 33941827707: 1973 passed, 1595 deselected
```

Generated Negative is valid shop-generation metadata. **Negative acquisition remains fail-closed** until exact slot-capacity consequences are owned.

## Tarot/Planet generation — GREEN

Owned:

- 22 Tarot and 12 Planet centers in pinned vanilla order;
- `UNAVAILABLE` source positions preserved;
- keys `Tarotsho{ante}` / `Planetsho{ante}`;
- `_resample2`, `_resample3`, ... behavior;
- all-unavailable Strength/Pluto fallback;
- immutable selected-center base cost;
- exact no-edition `Card:set_cost()` pricing;
- generic `GeneratedShopConsumableItem` metadata.

Canonical strict state path:

```text
live runtime observer
    -> strict snapshot payload
    -> DefaultBalatroStateTranslator
    -> BalatroState.consumable_generation_pool_observed
    -> BalatroState.consumable_generation_pools {"Tarot", "Planet"}
    -> strict headless bridge
    -> exact identity + pricing owners
```

Important fixed defect:

- a legacy consumable-generation wrapper previously rewrote the strict canonical catalogue after translation;
- canonical all-or-nothing state is now the sole Tarot/Planet generation catalogue consumed by headless shop generation.

```text
CI 33943525506: 2014 passed, 1595 deselected
CI 33944049829: 2028 passed, 1595 deselected
963413d  preserve strict consumable generation catalogue
CI 33945779690: 2057 passed, 1595 deselected
```

## Two ordinary main-shop slots — GREEN FOR BASE BOUNDARY

Headless composition preserves source RNG order while publishing atomically:

```text
preflight all possible Joker/Tarot/Planet catalogues + pricing
slot 1: cdt type -> full type-specific identity/edition/pricing
slot 2: cdt type -> full type-specific identity/edition/pricing
publish both generated metadata items into shared two-slot capacity
```

Added:

```text
dce24f7  insert generated consumables into shared main-shop capacity
520f12c  compose exact two-slot main shop generation
bdefc13  cover two-slot replay/preflight/isolation
CI 33946028581: 2063 passed, 1595 deselected
```

Tests prove:

- exactly two ordinary items are published;
- source input and RNG remain isolated;
- same seed/catalogues reproduce identical items and RNG state;
- malformed Tarot/Planet catalogue fails before RNG advancement;
- malformed Joker catalogue fails before RNG advancement;
- non-authoritative pricing fails before RNG advancement;
- pre-existing inventory is rejected.

## Exact shop reroll — GREEN

Implemented after the previous roadmap checkpoint:

```text
a3ac4c2  exact shop reroll transition
d914d84  shop reroll regressions
```

Owned boundary includes the normal ordinary-main-shop reroll transition under the same exact catalogue/pricing/RNG constraints as initial two-slot generation. Unsupported modifiers remain fail closed.

Reroll generation must continue to consume the same canonical Joker/Tarot/Planet state owners; it must not create a second eligibility path.

## Normal Voucher identity selection — GREEN

Implemented:

```text
b56fb87  normal Voucher selection primitive
337bd9b  pin normal Voucher selection sequence
CI 33946770946: 2079 passed, 1595 deselected
```

Current exact owner:

```text
games/balatro/env/shop_voucher_generation.py
```

Semantics:

- mirrors normal-mode `get_next_voucher_key(true)` identity polling;
- caller supplies an authoritative ordered `available_vouchers` catalogue;
- excludes `used_vouchers`;
- excludes `starting_voucher_keys`;
- uses keyed RNG `Voucher{ante}`;
- preserves bounded retry/resampling behavior;
- returns selected key plus poll count;
- fails closed when no exact eligible catalogue exists or retry is exhausted.

### Critical distinction

**Voucher identity selection is exact; Voucher eligibility observation and Voucher purchase/effect application are separate ownership problems.**

Do not infer from `b56fb87` / `337bd9b` that:

- a static Python Voucher list is authoritative;
- every profile-unlocked Voucher is available;
- Voucher purchase effects are exact;
- Voucher-modified shop rates are exact;
- Voucher generation is ready to publish into canonical shop state.

---

# Current audit — authoritative Voucher eligibility catalogue

## Existing exact precedent

The live runtime already has dedicated strict observers for ordinary generation eligibility:

```text
games/balatro/live/runtime/joker_generation_pool_observer.py
games/balatro/live/runtime/consumable_generation_pool_observer.py
```

They reconstruct eligibility from the **running game's own mechanics-critical runtime tables**, not a guessed Python unlock catalogue.

### Joker observer owns

- `G.P_JOKER_RARITY_POOLS` runtime order;
- center keys and immutable base costs;
- unlock state;
- `G.GAME.used_jokers` duplicate suppression;
- Showman exception;
- pool flags;
- banned keys;
- all-or-nothing strict LuaJIT reads.

### Tarot/Planet observer owns

- `G.P_CENTER_POOLS.Tarot` / `.Planet` runtime order;
- center keys/base costs/unlock state;
- duplicate suppression + Showman;
- pool flags and bans;
- Planet softlock hand-play prerequisites;
- all-or-nothing strict LuaJIT reads.

Any incomplete mechanics-critical read returns unobserved/`None`; headless generation does not guess missing profile/runtime state.

## Voucher gap — NEXT TASK

`BalatroState` currently has canonical generation-pool state for Joker and consumables, but **no equivalent Voucher generation-pool field/path yet**.

Next work must audit pinned vanilla Voucher selection predicates and identify the exact running-game tables needed to reproduce the catalogue supplied to `get_next_voucher_key(true)`.

Required questions:

1. What is the exact source-significant Voucher pool/order used by normal mode?
2. Which runtime/profile fields control `unlocked` / availability?
3. How do `used_vouchers`, `starting_voucher_keys`, bans, challenges, or pool flags interact?
4. Are any Voucher pair/dependency rules applied before or during `get_next_voucher_key` polling?
5. Can every required predicate be observed from running-game state without leaking information that the policy should not receive?
6. Which fields belong in public `BalatroState` versus simulator-private generation state?

### Implementation order if audit proves exact observation possible

1. add a strict runtime Voucher-generation-pool observer following the Joker/Consumable all-or-nothing pattern;
2. add a strict snapshot payload contract;
3. wire canonical translation without legacy wrapper rewriting;
4. add `BalatroState` observed/catalogue fields only if they are appropriate public-state facts; otherwise retain them in simulator-private generation state;
5. bridge the exact catalogue into `select_normal_shop_voucher`;
6. prove malformed/incomplete catalogue rejection occurs **before RNG advances**;
7. prove same seed + same authoritative catalogue reproduces selected Voucher and RNG state;
8. only then compose Voucher metadata publication into normal shop generation.

If the audit cannot prove exact observation, **keep `shop_voucher_generation.py` caller-supplied/private and document the blocker; do not invent a static Voucher catalogue.**

### After Voucher generation catalogue

Only after identity generation is exact and canonical:

- materialize exact Voucher shop metadata/pricing;
- publish normal Voucher slot into shop state;
- audit Voucher purchase/effect semantics in small coherent groups;
- integrate only owned Voucher effects into later shop generation/rate/slot/capacity state;
- keep unsupported Vouchers purchase-ineligible.

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

Every training-visible action requires:

- stable canonical type/id;
- required parameters;
- deterministic legality;
- exact transition;
- serialization representation;
- mask representation;
- no hidden-information leakage.

Internal exact lifecycle/generation primitives may exist before the corresponding action becomes training-exposed.

Do not widen the training mask merely because a lower-level identity RNG or transition helper exists.

---

# R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic D1/D9/tactical owners for hand-level play while RL controls strategic boundaries. Tactical trajectories remain logged for parity/debugging.

# R5 — live/simulator parity harness — NOT STARTED

Priority fixtures:

- initial ordinary shop generation;
- ordinary shop reroll;
- Joker/Tarot/Planet identity and price generation;
- normal Voucher identity/slot generation once owned;
- ordinary purchase/hold/end-shop;
- Joker replacement;
- Voucher purchase/rejection;
- pack paths;
- blind skip;
- ordinary blind start/clear;
- Boss restrictions;
- Card Sharp reset;
- Throwback skip counter;
- Baron held-card state;
- The Sun path;
- owned-deck composition;
- economy/interest transitions;
- RNG/shuffle/initial-draw parity.

The environment is not authoritative for training until representative R5 fixtures pass.

# R6 — environment performance gate — NOT STARTED

Measure only after semantics are correct:

- steps/sec;
- runs/minute;
- parallel scaling;
- tactical-bridge cost;
- serialization overhead.

---

# Later phases

## O — observation/action encoding — NOT STARTED

Versioned public observation/action schemas, no hidden-information leakage, illegal actions probability zero after masking.

## B0 — RL baseline infrastructure — NOT STARTED

Required before PPO:

1. random legal strategic baseline;
2. deterministic/symbolic strategic baseline;
3. fixed-seed replay suite;
4. environment throughput benchmark;
5. trajectory/version metadata.

## PPO strategic learner — NOT STARTED

Do not begin until Phase R semantic/parity gates and baseline infrastructure are complete enough to trust the environment.

Manual Bond-value coefficient tuning remains retired as the primary competence path.

---

# Exact next action

**Do not write more shop mechanics until the Voucher eligibility catalogue audit is complete.**

Immediate order:

1. inspect pinned vanilla `get_next_voucher_key` and Voucher pool construction;
2. enumerate every eligibility predicate/runtime dependency;
3. compare them to currently observable runtime state;
4. classify the catalogue as public canonical state vs simulator-private generation state;
5. implement a strict all-or-nothing observer only if exactness/public-information rules permit it;
6. add focused regressions;
7. run the deterministic CI selector and inspect the actual pytest count;
8. synchronize this roadmap again after the green slice.

No Balatro live run is currently required.