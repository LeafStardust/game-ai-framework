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
- two-slot shop generation preflights every possible catalogue/pricing dependency before the first type RNG draw.

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

Owned resource-sensitive acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

Owned R1 categories include:

- broad static score/rule/retrigger Joker acquisition groups;
- money-based and permanent-owned-deck scoring Jokers;
- exact `G.playing_cards` permanent-deck observation;
- strict card decode/count/modifier validation;
- strict LuaJIT authoritative-array decoding;
- private draw/discard/played-zone validation;
- exact seed/tag/container validation;
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
- generic SELL_JOKER inverse lifecycle;
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

Representative gates:

```text
33794664514  1461 passed, 1594 deselected
33797071526  1482 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
33803629167  1563 passed, 1594 deselected
33804894982  1593 passed, 1594 deselected
```

## R2.5–R2.8 — blind/Boss lifecycle — BROADLY GREEN

Exact normal Red/White ownership now covers audited start/active/disable/defeat mechanics across all 28 vanilla Bosses, including:

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

Generic training `SELECT_BLIND` remains hidden until its strategic action boundary is frozen end-to-end. Internal exact lifecycle primitives may be broader than the currently exposed training vocabulary.

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

## Base main-shop type RNG — GREEN

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
- voucher/Tag rate modifiers fail closed at this boundary.

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

Representative gate:

```text
CI 33941827707: 1973 passed, 1595 deselected
```

Generated Negative is valid shop-generation metadata. **Negative acquisition remains fail-closed** until exact slot-capacity consequences are owned.

## Tarot/Planet identity + pricing — GREEN

Owned:

- 22 Tarot and 12 Planet centers in pinned vanilla order;
- `UNAVAILABLE` source positions preserved;
- keys `Tarotsho{ante}` / `Planetsho{ante}`;
- `_resample2`, `_resample3`, ... behavior;
- all-unavailable Strength/Pluto fallback;
- immutable selected-center base cost;
- exact no-edition `Card:set_cost()` pricing;
- generic `GeneratedShopConsumableItem` metadata.

```text
CI 33943525506: 2014 passed, 1595 deselected  observer layer
CI 33944049829: 2028 passed, 1595 deselected  explicit record materialization
```

## Canonical Tarot/Planet generation-state wiring — GREEN

Canonical path now exists:

```text
live runtime observer
    -> strict snapshot payload
    -> DefaultBalatroStateTranslator
    -> BalatroState.consumable_generation_pool_observed
    -> BalatroState.consumable_generation_pools {"Tarot", "Planet"}
    -> strict headless bridge
    -> exact identity + pricing owners
```

Important defect found and fixed:

- a legacy `consumable_generation_pool_live_state_policy` translator wrapper was rewriting the strict canonical catalogue after `DefaultBalatroStateTranslator` had validated it;
- it uppercased keys to `TAROT`/`PLANET` and could silently drop malformed records;
- the wrapper now leaves the canonical catalogue untouched and owns only its auxiliary Omen Globe / Showman / Soul / Black Hole fields.

```text
963413d  fix(balatro): preserve strict consumable generation catalogue
CI 33945779690: 2057 passed, 1595 deselected
```

Canonical all-or-nothing state is now the sole Tarot/Planet generation catalogue consumed by headless shop generation.

## Two ordinary main-shop slots — GREEN FOR BASE BOUNDARY

Source audit:

- vanilla loops once per missing `G.shop_jokers` slot;
- each iteration calls `create_card_for_shop()` and emplaces its result;
- emplacement alone does not call `add_to_deck()` and therefore does not mutate `G.GAME.used_jokers`;
- slot-two eligibility is therefore unchanged by deferring publication of slot one.

Headless composition now preserves exact source RNG order while publishing atomically:

```text
preflight all possible Joker/Tarot/Planet catalogues + pricing
slot 1: cdt type -> full type-specific identity/edition/pricing
slot 2: cdt type -> full type-specific identity/edition/pricing
publish both generated metadata items into shared two-slot capacity
```

Why publication is deferred:

- existing lower-level base generation primitives deliberately require ungenerated inventory;
- generated shop metadata does not affect dynamic eligibility until purchase/add-to-deck;
- atomic publication prevents a malformed slot-two dependency from leaving a half-generated public shop;
- returned `GeneratedMainShop.items` preserves physical source slot order even though canonical public state stores Jokers and consumables in category-specific lists.

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

### Current exact boundary

The base two-slot **initial shop inventory** generation path is now owned for ordinary Joker/Tarot/Planet metadata under the currently explicit no-voucher/no-Tag modifier boundary.

This does **not** yet mean:

- generated metadata is automatically purchase-legal;
- runtime gameplay objects are constructed for every generated center;
- voucher/Tag-modified shop rates are owned;
- boosters/vouchers are generated;
- shop reroll lifecycle is owned;
- Negative acquisition is safe.

---

# Immediate next development action

## R2.10 next slice — exact shop reroll lifecycle

Do **not** jump to PPO, observation encoding, boosters, or broad voucher mechanics.

Audit and implement the normal base reroll boundary from pinned vanilla source.

Required source questions before writing:

1. exact affordability/legality predicate for reroll;
2. exact order of money deduction versus inventory dissolution/regeneration;
3. exact reroll-cost progression and whether free-reroll state is separate;
4. whether existing main-shop cards mutate any generation eligibility when removed;
5. exact reuse of the same `create_card_for_shop()` source loop and keyed RNG streams;
6. what public/private state must survive a reroll;
7. whether voucher/Tag/free-reroll modifiers can stay fail-closed initially.

Preferred first implementation boundary:

- active normal SHOP;
- exactly generated ordinary two-card main shop;
- no voucher/Tag/free-reroll modifiers;
- authoritative exact money + reroll cost;
- dissolve/clear old main-shop metadata;
- deduct exact reroll cost in source order;
- increment/update next reroll cost exactly;
- regenerate the two ordinary slots through the existing `generate_base_main_shop()` owner;
- atomic/fail-closed behavior with deterministic replay tests.

Do not duplicate shop generation logic inside reroll. Reroll must call the existing canonical two-slot generation owner after its own lifecycle mutations are exact.

After this slice is green:

1. synchronize this roadmap again;
2. audit booster/voucher generation separately;
3. expand modifier boundaries only when exact;
4. keep R3 action exposure tied to exact legality/execution ownership;
5. add R5 parity fixtures before declaring training environment authoritative.

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

- stable canonical identifier;
- exact required parameters;
- deterministic legality owner;
- exact transition owner;
- serialization representation;
- mask representation.

Do not expose an action merely because a lower-level mechanical primitive exists.

---

# R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic D1/D9/tactical owners for hand-level play while RL controls strategic boundaries. Tactical trajectories remain logged for parity/debugging.

# R5 — live/simulator parity harness — NOT STARTED

Priority fixtures:

- ordinary shop generation;
- mixed Joker/Tarot/Planet main-shop inventory;
- shop reroll;
- Joker replacement/sale;
- voucher purchase/rejection;
- pack paths;
- blind skip;
- ordinary blind start/clear;
- boss restrictions;
- Card Sharp reset;
- Throwback skip counter;
- Baron held-card state;
- owned-deck composition;
- economy/interest transitions;
- RNG/shuffle/initial-draw parity.

# R6 — environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead only after semantics are correct.

## Phase-R exit criteria

- deterministic reset/step API;
- initial strategic actions have exact legality + execution tests;
- Red/White run proceeds reset -> terminal headlessly;
- fixed-seed replay deterministic;
- representative live parity fixtures green;
- throughput supports automated training;
- environment version stored in trajectory metadata.

---

# Later phases

## O — observation/action encoding — NOT STARTED

Versioned public observation/action schemas; no hidden-information leakage; illegal actions probability zero after masking.

## B0 — RL baseline infrastructure — NOT STARTED

At minimum:

1. random legal strategic baseline;
2. deterministic symbolic/headless baseline;
3. reproducible seeded evaluation harness;
4. trajectory logging/versioning.

## PPO strategic learner — NOT STARTED

Only after environment exactness, parity, encoding, and baseline gates pass.

---

# Current checkpoint

As of this synchronization:

```text
Branch                         feat/v1.0-red-white-competence
Code head before docs          bdefc13a57ca36c66bc234570c202abe00e1cd3c
Latest deterministic CI        33946028581
Result                         2063 passed, 1595 deselected
Current primary phase          R2.10 normal shop generation
Completed current boundary     base two-slot Joker/Tarot/Planet shop generation
Next exact boundary            normal base shop reroll lifecycle
Live Balatro validation needed NO
```

Latest relevant commits:

```text
963413d  fix canonical Tarot/Planet catalogue overwrite
dce24f7  insert generated consumables into shared main shop
520f12c  compose exact two-slot main shop generation
bdefc13  test two-slot main shop composition
```

The next code written should therefore implement or classify the **normal base shop reroll lifecycle** at its canonical source boundary. It should **not** be Bond tuning, PPO, observation training, booster generation, or broad voucher support.
