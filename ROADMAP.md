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

---

# Current checkpoint — 2026-09-05

```text
Branch: feat/v1.0-red-white-competence
Code HEAD before this roadmap sync:
1a785c4b79d8ec01eab3382d9b474028ff55b7a3
  test(balatro): make shop-entry voucher state authoritative

Latest verified code-head CI:
33962480568
2209 passed, 1595 deselected
```

The previous code head `ab94bd4` correctly widened ordinary cash-out to preserve already-supported Voucher consequences into the next shop, but exposed stale test fixtures that represented an empty Voucher table / zero discount without marking those observations authoritative. CI `33962013858` therefore failed with 19 fixture-level exactness errors. Production fail-closed semantics were **not** weakened. The fixtures were corrected to explicitly model authoritative empty Voucher state and a dedicated regression now proves supported Voucher state survives cash-out exactly.

Recent closure commits include:

```text
34d88e9  ci(balatro): include R2 deterministic coverage
7c070b2  feat(balatro): retain exact playing-card order in headless state
0a7f845  feat(balatro): own exact RNG state in headless runs
61ec993  feat(balatro): own exact pristine round-start deal
2d37016  test(balatro): pin pristine R2 shuffle and deal

# later R2/Voucher work
314ebfd  feat(balatro): own exact generated shop repricing
c226882  feat(balatro): own exact discount voucher redemption
cc4bf73  feat(balatro): expose exact discount voucher shop transitions
b072fb3  fix(balatro): require exact current shop prices before discount redemption
75fec9b  test(balatro): pin exact current prices for discount transitions

# shop type-rate and reroll families
[intervening commits]  exact Tarot/Planet Merchant/Tycoon state, live translation,
                       redemption, shop weighting and transition coverage
ceeacec  feat(balatro): retain persistent reroll cost state
fd9f052  feat(balatro): compose paid rerolls with exact voucher costs
57954d7  test(balatro): pin exact reroll voucher lifecycle
ab94bd4  feat(balatro): preserve exact vouchers through cash out
9a657cc  test(balatro): make cashout voucher fixtures authoritative
5d9a2ef  test(balatro): mark resource cashout voucher state exact
1a785c4  test(balatro): make shop-entry voucher state authoritative
```

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop generation: **ACTIVE — PRIMARY WORKSTREAM**.
- Exact Balatro/LuaJIT RNG + pseudoshuffle: **GREEN**.
- Exact playing-card/Joker private ordering for owned cases: **GREEN**.
- Exact normal round/blind/Boss lifecycle across audited Red/White paths: **BROADLY GREEN**.
- Exact round-end cashout + normal blind/Ante progression: **GREEN**.
- Exact normal shop main slots + paid reroll: **GREEN**.
- Exact Joker/Tarot/Planet normal shop generation owned slices: **GREEN**.
- Exact Voucher runtime eligibility, identity polling, metadata/pricing, and separate Voucher slot publication: **GREEN**.
- Complete 32-Voucher redemption-effect classification: **COMPLETE**.
- Exact resource/capacity Voucher redemption group: **GREEN — 8 VOUCHERS**.
- Exact Joker edition-rate Voucher family: **GREEN — Hone / Glow Up**.
- Exact discount Voucher family: **GREEN — Clearance Sale / Liquidation**.
- Exact shop type-rate Voucher family: **GREEN — Tarot Merchant/Tycoon + Planet Merchant/Tycoon**.
- Exact reroll-cost Voucher family: **GREEN — Reroll Surplus / Reroll Glut**.
- Supported Voucher state through ordinary cash-out/new-shop entry: **GREEN — CI 33962480568**.
- Remaining Voucher effect families: **FAIL CLOSED UNTIL THEIR DOWNSTREAM EFFECTS ARE OWNED**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **NOT CURRENTLY REQUIRED**.

## Exact currently supported Voucher families

### Resource / capacity

```text
v_crystal_ball
v_grabber
v_nacho_tong
v_wasteful
v_recyclomancy
v_antimatter
v_paint_brush
v_palette
```

### Joker edition rate

```text
v_hone
v_glow_up
```

### Shop discount

```text
v_clearance_sale
v_liquidation
```

### Shop type rate

```text
v_tarot_merchant
v_tarot_tycoon
v_planet_merchant
v_planet_tycoon
```

### Persistent reroll cost

```text
v_reroll_surplus
v_reroll_glut
```

`games/balatro/env/voucher_capabilities.py` is the canonical per-boundary capability owner. Exact generation capability is distinct from exact redemption/cash-out capability; never replace these checks with a blanket `if state.vouchers` rule.

Current invariant set:

- Voucher ownership must be structurally valid and duplicate-free;
- nonempty ownership must be authoritative (`vouchers_observed is True`);
- only explicitly audited Vouchers may cross each generation/redemption/cash-out boundary;
- unsupported modifiers reject before RNG is consumed;
- upgrade Vouchers never infer hidden base ownership from numeric state;
- observed ownership and the canonical numeric modifier it implies must agree exactly;
- every downstream consumer of an exact Voucher effect must read the same canonical state owner;
- an authoritative empty Voucher table is distinct from an unobserved Voucher table;
- an authoritative zero discount is distinct from an unobserved discount field.

## Canonical exact Voucher state

```text
joker_generation_edition_rate
shop_discount_percent
shop_discount_percent_observed
tarot_rate
planet_rate
HeadlessRunState.base_reroll_cost
HeadlessRunState.reroll_cost
```

Owned upgrade progression:

```text
Glow Up       requires Hone
Liquidation   requires Clearance Sale
Tarot Tycoon  requires Tarot Merchant
Planet Tycoon requires Planet Merchant
Reroll Glut   requires Reroll Surplus
```

### Hone / Glow Up

- base edition rate = 1.0;
- Hone = 2.0;
- Glow Up after Hone = 4.0;
- exact Joker edition generation consumes this canonical rate;
- ownership/rate mismatch fails closed;
- live observer/translator preserve the rate.

### Clearance Sale / Liquidation

- base discount = 0%;
- Clearance Sale = 25%;
- Liquidation after Clearance = 50%;
- pricing uses centralized `vanilla_card_cost` semantics;
- generated Joker/Tarot/Planet/Voucher records retain immutable base cost;
- redemption pays the old visible Voucher price, records ownership, then reprices supported generated inventory;
- current visible generated prices must match the authoritative pre-redemption discount;
- active unsupported price modifiers, Booster pricing, or legacy inventory block redemption.

### Tarot / Planet Merchant and Tycoon

Canonical rates:

```text
Tarot base      4.0
Tarot Merchant  9.6
Tarot Tycoon   32.0
Planet base     4.0
Planet Merchant 9.6
Planet Tycoon  32.0
```

Owned behavior:

- live `G.GAME.tarot_rate` / `planet_rate` translate into canonical state;
- normal main-shop type polling consumes those canonical rates;
- changing a rate affects future shop type selection, not already-visible inventory;
- ownership↔rate mismatches fail closed;
- upgrade progression is explicit;
- supported type-rate Vouchers compose with resource, edition-rate, discount, and reroll-cost families.

### Reroll Surplus / Reroll Glut

Persistent Red/White base reroll costs:

```text
none                     $5
Reroll Surplus            $3
Reroll Surplus + Glut     $1
```

Owned behavior:

- persistent base and current reroll prices are separate state;
- paid rerolls use the current price then advance it exactly;
- Voucher redemption reduces both appropriate cost owners without consuming RNG;
- new-shop entry resets current cost to persistent Voucher-derived base when temporary/free modifiers are absent;
- temporary/free reroll states remain fail closed;
- supported Voucher state survives ordinary cash-out into the next shop exactly.

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
- malformed Joker/Tarot/Planet/Voucher catalogues are rejected all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal;
- canonical generation catalogues may not be overwritten by legacy wrappers;
- two-slot main-shop generation preflights dependencies before first type RNG;
- Voucher selection never falls back to a guessed/static Python catalogue;
- unsupported Voucher centers never become legal merely because identity/price/slot are known;
- duplicate, malformed, or unobserved nonempty Voucher ownership is rejected;
- unsupported Voucher modifiers remain rejected even alongside supported Vouchers;
- Voucher upgrade ownership/state mismatches are rejected rather than repaired by inference;
- discount redemption is hidden when current generated prices are stale or pricing paths are unowned;
- ordinary cash-out rejects unsupported Voucher generation/pricing/economy state rather than erasing it;
- tests must mark authoritative empty/zero observations explicitly instead of relying on defaults.

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

The simulator is **not authoritative game truth** until representative R5 live/simulator parity passes.

---

# R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

Owned resource-sensitive Joker acquisitions include Juggler, Stuntman, Drunkard, Troubadour, and Merry Andy. Broad static score/rule/retrigger Joker groups, money-based scoring, owned-deck scoring, permanent `G.playing_cards` observation, strict card decoding, authoritative array completeness, private card zones, and next-round hand/discard allowances are owned where current transitions require them.

Still fail closed where not globally owned:

- unknown/unaudited Joker acquisitions;
- Joker editions whose acquisition changes capacity semantics, especially Negative;
- unsupported Voucher effects;
- pack lifecycle paths not yet exact;
- malformed/noninteger prices;
- generic SELL_JOKER inverse lifecycle where inverse effects are unowned.

Representative R1 gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

---

# R2 — RNG + lifecycle + shop generation — ACTIVE

## RNG / shuffle / ordering — GREEN

```text
33791671797  1432 passed, 1594 deselected   exact LuaJIT/Balatro RNG
33791916289  1435 passed, 1594 deselected   exact pseudoshuffle
33795507133  1461 passed, 1594 deselected   env_r2/card order
```

Owned:

- keyed Balatro pseudoseed progression;
- LuaJIT combined Tausworthe draws;
- bit-preserving RNG snapshot/restore;
- vanilla pseudoshuffle semantics;
- private playing-card creation order / physical deck order where provable;
- private Joker order where lifecycle parity requires it.

## Round/blind/Boss lifecycle — BROADLY GREEN

The environment owns audited Red/White blind start, draw, resource modification, Boss active effects, disable/defeat restoration, and round resolution across all 28 vanilla Bosses. Hidden-information behavior remains masked correctly.

Representative gates:

```text
33796012173  1467 passed, 1594 deselected   first blind lifecycle
33855720629  1734 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
33915588784  1924 passed, 1595 deselected   round-end/progression
```

Generic training `SELECT_BLIND` remains tied to end-to-end strategic-action ownership even though internal lifecycle primitives are substantially broader.

## Normal shop / Voucher generation — GREEN FOR OWNED PATHS

Owned slices include:

- normal main-shop slot type polling;
- ordinary Joker rarity/center/edition generation for authoritative catalogues;
- Tarot/Planet normal generation;
- paid shop reroll;
- centralized Card:set_cost-compatible pricing;
- generated visible-shop repricing from immutable base metadata;
- Voucher eligibility/identity polling;
- Voucher runtime metadata + exact price;
- separate normal Voucher slot publication;
- supported Voucher state carried through ordinary shop generation;
- edition-rate, discount, type-rate and reroll-cost Voucher effects at all currently owned downstream consumers;
- exact supported Voucher state across ordinary cash-out/new-shop entry.

Representative later gates:

```text
33941827707  1973 passed, 1595 deselected
33943525506  2014 passed, 1595 deselected
33945779690  2057 passed, 1595 deselected
33952322285  2110 passed, 1595 deselected
33956063668  2117 passed, 1595 deselected
33956949501  2133 passed, 1595 deselected   Hone / Glow Up
33959454017  2155 passed, 1595 deselected   discount pricing / repricing
33960365203  2165 passed, 1595 deselected   discount redemption
33961839253  2208 passed, 1595 deselected   reroll Voucher lifecycle
33962013858  19 failed, 2189 passed          stale cashout fixtures exposed
33962480568  2209 passed, 1595 deselected   Voucher-preserving cashout closure
```

---

# Next work — interest-cap Voucher family audit

The next coherent family is:

```text
v_seed_money
v_money_tree
```

Pinned vanilla evidence:

- Seed Money and Money Tree modify `G.GAME.interest_cap`;
- Voucher redemption assigns `G.GAME.interest_cap = center_table.extra`;
- Money Tree requires Seed Money;
- round evaluation computes interest as
  `interest_amount * min(floor(dollars / 5), interest_cap / 5)` when interest is enabled.

This family is attractive now because ordinary cash-out already owns baseline interest and supported Voucher state preservation. It is **not yet exact** because the current cash-out helper still hard-codes the base `$25` interest cap.

Immediate audit/implementation order:

1. inspect pinned center configs and exact redemption values for Seed Money / Money Tree;
2. establish one canonical public/headless `interest_cap` state and live observation path from `G.GAME.interest_cap`;
3. distinguish authoritative base cap from an unavailable live read;
4. replace hard-coded cash-out cap with canonical exact state;
5. enforce ownership progression and ownership↔cap consistency;
6. confirm no-interest/challenge modifiers remain outside Red/White normal-mode support and fail closed if encountered;
7. make supported interest Vouchers compose with resource, edition-rate, discount, type-rate, and reroll-cost Vouchers;
8. preserve the canonical cap through cash-out/shop boundaries without consuming RNG;
9. expose BUY_VOUCHER only after every interest consumer uses the canonical state;
10. add base/Seed/Money Tree boundary tests, affordability/debit tests, mismatch rejection, and same-round interest semantics;
11. run full deterministic CI and synchronize this roadmap after green.

Do **not** infer interest-cap ownership from money or observed payout rows. Ownership and canonical numeric state must agree explicitly.

## Subsequent R2 family selection

After the interest-cap family, re-audit remaining unsupported Vouchers against actual downstream ownership. Prefer families whose full consequences are already modeled. Pack-size/pack-generation, shop-slot-count, playing-card shop, special/economy, or other modifiers stay blocked until their entire downstream lifecycle is exact.

---

# R3 — typed strategic action vocabulary — PARTIAL

Target actions include:

```text
END_SHOP
REROLL_SHOP
BUY_JOKER
SELL_JOKER
BUY_VOUCHER
BUY_CONSUMABLE
OPEN_PACK
CHOOSE_PACK_OPTION
SKIP_PACK
USE_CONSUMABLE
SKIP_BLIND
SELECT_BLIND
```

Only actions with exact legality, transition, serialization, and mask ownership may become training-visible.

---

# R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic tactical/hand-play owners while RL controls strategic boundaries. Do not rewrite tactical mechanics in the learner.

# R5 — live/simulator parity harness — NOT STARTED

Required before treating the simulator as authoritative training truth. Priority fixtures include shop generation/purchase/reroll, Voucher redemption, blind start/clear, representative Bosses, RNG/shuffle/draw, owned-deck composition, and economy transitions.

# R6 — environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead only after semantics are correct.

# Later phases

## O — observation/action encoding — NOT STARTED

Versioned public observation/action schemas; no hidden-information leakage; illegal action probability zero after masking.

## B0 — RL baseline infrastructure — NOT STARTED

Random legal and deterministic symbolic/headless baselines before learned policy work.

## PPO — NOT STARTED

Do not begin until R-phase exactness, representative parity, and performance gates are satisfied.
