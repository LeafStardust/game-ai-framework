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
Verified code HEAD before this roadmap sync:
83a900efff0dc81b984a93df6710324ae125bbaa
  fix(balatro): construct generated ante voucher fixtures

Latest verified code-head CI:
33967536736
2257 passed, 1595 deselected
```

The Hieroglyph/Petroglyph integration is now closed through the canonical shop action path. `HeadlessRunState` retains the existing canonical `BlindProgressionState`; Ante-Voucher redemption updates public Ante/allowances and private `blind_ante` atomically; valid ownership is neutral for unrelated shop-generation capability checks; and `ShopTransitionEngine.legal_actions()` exposes `BUY_VOUCHER` only when progression, allowance observations, price, upgrade prerequisites, and affordability are exact.

## Latest closure commits

```text
# retained blind progression + internal redemption integration
31aca80  test(balatro): cover retained ante voucher progression

# Ante-Voucher capability / canonical BUY_VOUCHER path
4a3a4e4  feat(balatro): classify exact ante voucher capability
b5ffda2  refactor(balatro): centralize ante voucher capability
d7618ff  feat(balatro): expose exact ante voucher shop transition
6a7c5ef  test(balatro): cover ante voucher shop transition
83a900e  fix(balatro): construct generated ante voucher fixtures
```

The failed collection run `33967491685` was test-fixture-only: it referenced a nonexistent helper. Production semantics were unchanged; `83a900e` corrected the test to construct the repository's real immutable `GeneratedShopVoucherItem`. Full CI then passed.

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop generation: **BROADLY GREEN; REMAINING GAPS ARE SPECIFIC**.
- R3 typed strategic action vocabulary: **PARTIAL — NEXT PRIMARY WORKSTREAM**.
- Exact Balatro/LuaJIT RNG + pseudoshuffle: **GREEN**.
- Exact playing-card/Joker private ordering for owned cases: **GREEN**.
- Exact normal round/blind/Boss lifecycle across audited Red/White paths: **BROADLY GREEN**.
- Exact round-end cashout + normal blind/Ante progression: **GREEN**.
- Exact literal Ante <= 0 Boss/tag/blind-requirement handling: **GREEN**.
- Exact normal main-shop generation + paid reroll with variable supported capacity: **GREEN**.
- Exact Joker/Tarot/Planet normal shop generation owned slices: **GREEN**.
- Exact Voucher runtime eligibility, identity polling, metadata/pricing, and separate Voucher slot publication: **GREEN**.
- Exact Hieroglyph/Petroglyph canonical training purchase: **GREEN**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **NOT CURRENTLY REQUIRED**.

---

# Foundation status

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
L3 environment freeze                COMPLETE
R0 headless environment architecture COMPLETE
R1 deterministic state/acquisition   SUBSTANTIALLY COMPLETE
R2 RNG/lifecycle/shop generation     BROADLY GREEN / SPECIFIC GAPS REMAIN
R3 typed action vocabulary           PARTIAL — NEXT PRIMARY WORKSTREAM
R4 deterministic tactical bridge     NOT STARTED
R5 live/simulator parity harness      NOT STARTED
R6 environment performance gate      NOT STARTED
O observation/action encoding        NOT STARTED
B0 RL baseline infrastructure        NOT STARTED
PPO strategic learner                NOT STARTED
```

The simulator is **not authoritative game truth** until representative R5 live/simulator parity passes.

---

# R1 — deterministic state/acquisition

## Owned

- Red Deck / White Stake canonical state validation.
- Strict public/private card-zone ownership.
- Permanent owned-deck truth from `G.playing_cards` with all-or-nothing LuaJIT/TValue decoding.
- Next-round hand/discard allowances where required.
- Exact resource-sensitive Joker acquisition effects for the currently admitted group.
- Broad static score/rule/retrigger Joker acquisition groups whose acquisition is inventory-only.
- Owned-deck-dependent scoring Jokers only when permanent deck state is authoritative.
- Exact supported Voucher acquisition effects listed below.
- Fail-closed malformed/noninteger prices.

## Still fail closed

- unknown/unaudited Joker acquisitions;
- Joker editions whose acquisition changes capacity semantics, especially Negative;
- generic `SELL_JOKER` inverse lifecycle where inverse effects are unowned;
- unsupported pack/card-shop/Voucher mechanics described below.

Representative gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

---

# Exact currently supported Voucher families

## Resource / capacity

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

## Joker edition rate

```text
v_hone
v_glow_up
```

## Shop discount

```text
v_clearance_sale
v_liquidation
```

## Shop type rate

```text
v_tarot_merchant
v_tarot_tycoon
v_planet_merchant
v_planet_tycoon
```

## Persistent reroll cost

```text
v_reroll_surplus
v_reroll_glut
```

## Interest cap

```text
v_seed_money
v_money_tree
```

## Main-shop size

```text
v_overstock_norm
v_overstock_plus
```

## Ante / round allowance

```text
v_hieroglyph
v_petroglyph
```

`games/balatro/env/voucher_capabilities.py` is the canonical per-boundary capability owner. Exact generation capability is distinct from exact redemption/cash-out capability; never replace these checks with a blanket `if state.vouchers` rule.

### Canonical upgrade progression

```text
Glow Up         requires Hone
Liquidation     requires Clearance Sale
Tarot Tycoon    requires Tarot Merchant
Planet Tycoon   requires Planet Merchant
Reroll Glut     requires Reroll Surplus
Money Tree      requires Seed Money
Overstock Plus  requires Overstock
Petroglyph      requires Hieroglyph
```

Voucher ownership remains an ordered list because redemption order is observable/replay-relevant. Membership/prerequisite checks may be set-like, but transitions append in canonical redemption order and never normalize the list into a set.

### Hieroglyph / Petroglyph — canonical shop path exact

Pinned vanilla redemption:

```text
both:
  ease_ante(-1)
  round_resets.blind_ante -= 1

Hieroglyph:
  round_resets.hands -= 1
  current hands_left -= 1

Petroglyph:
  requires Hieroglyph
  round_resets.discards -= 1
  current discards_left -= 1
```

Canonical ownership now is:

```text
HeadlessRunState.blind_progression_state
        ↓
ante_voucher_redemption.py
        ↓
ShopTransitionEngine legal mask + BUY_VOUCHER execution
```

The path fails closed when retained progression is absent/stale, the required current/persistent allowance is unobserved or irreducible, price is malformed/unaffordable, or Petroglyph lacks Hieroglyph. Successful redemption consumes no RNG and atomically updates public and private state.

Valid Hieroglyph/Petroglyph ownership is neutral for unrelated shop generation rates/capacity/pricing. Impossible `Petroglyph without Hieroglyph` ownership invalidates the Voucher capability boundary.

### Remaining training-unsupported Voucher centers

```text
v_omen_globe
v_telescope
v_observatory
v_blank
v_magic_trick
v_illusion
v_directors_cut
v_retcon
```

These are blocked by real mechanics:

- Omen Globe: Spectral generation inside Arcana packs.
- Telescope / Observatory: Celestial pack/Planet lifecycle and Observatory held-Planet scoring.
- Blank: progression/unlock semantics rather than an ordinary immediate gameplay modifier.
- Magic Trick / Illusion: exact playing-card shop generation, purchase, and modifier generation.
- Director's Cut / Retcon: exact Boss-reroll action/state ownership.

Do not promote any of these through a blanket allowlist.

---

# R2 — RNG + lifecycle + shop generation

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

Literal nonpositive Ante behavior is owned in:

- normal Boss selection (`max(1, ante)` only where vanilla actually clamps minimum-Ante eligibility);
- normal Tag selection and seeded `Tag{ante}` keys;
- pre-Ante Boss cash-out tag/Boss regeneration;
- Red/White base blind amount (`Ante < 1 -> 100`, Ante 1–8 exact table; unsupported endless states fail closed);
- retained blind progression state.

Representative gates:

```text
33796012173  1467 passed, 1594 deselected
33855720629  1734 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
33915588784  1924 passed, 1595 deselected
33965599236  2233 passed, 1595 deselected   pre-Ante + base blind closure
33966224227  2239 passed, 1595 deselected   internal Ante-Voucher redemption
33967536736  2257 passed, 1595 deselected   canonical Ante-Voucher shop integration
```

Generic training `SELECT_BLIND` remains tied to end-to-end strategic-action ownership even though internal lifecycle primitives are substantially broader.

## Normal shop / Voucher generation — GREEN FOR OWNED PATHS

Owned slices include:

- normal main-shop slot type polling;
- ordinary Joker rarity/center/edition generation for authoritative catalogues;
- Tarot/Planet normal generation;
- variable 2/3/4-card supported main-shop capacity;
- paid shop reroll at current exact capacity;
- centralized `Card:set_cost`-compatible pricing;
- generated visible-shop repricing from immutable base metadata;
- Voucher eligibility/identity polling;
- Voucher runtime metadata + exact price;
- separate normal Voucher slot publication;
- supported Voucher state through shop generation and ordinary cash-out;
- all supported Voucher effects consumed by their canonical downstream owners.

Representative later gates:

```text
33956949501  2133 passed, 1595 deselected   Hone / Glow Up
33959454017  2155 passed, 1595 deselected   discount pricing
33960365203  2165 passed, 1595 deselected   discount redemption
33961839253  2208 passed, 1595 deselected   reroll Voucher lifecycle
33962480568  2209 passed, 1595 deselected   Voucher-preserving cashout
33964693188  2224 passed, 1595 deselected   interest-cap + Overstock closure
33965599236  2233 passed, 1595 deselected   Hieroglyph/Petroglyph downstream audit
33967536736  2257 passed, 1595 deselected   Hieroglyph/Petroglyph canonical purchase
```

---

# Fail-closed rule

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
- malformed Joker/Tarot/Planet/Voucher catalogues reject all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal;
- shop generation preflights dependencies before first type RNG;
- Voucher selection never falls back to a guessed/static Python catalogue;
- unsupported Voucher centers never become legal merely because identity/price/slot are known;
- duplicate, malformed, or unobserved nonempty Voucher ownership is rejected;
- Voucher upgrade ownership/state mismatches are rejected rather than repaired by inference;
- ordinary cash-out rejects unsupported Voucher generation/pricing/economy state rather than erasing it;
- Ante Voucher redemption rejects stale/missing private `blind_ante` ownership;
- Ante Voucher redemption rejects unobserved or irreducible current/persistent allowances;
- tests must mark authoritative empty/zero observations explicitly instead of relying on defaults.

---

# R3 — typed strategic action vocabulary — PARTIAL / NEXT PRIMARY WORKSTREAM

Target strategic actions:

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

Every training-visible action requires:

1. canonical production action identifier;
2. frozen legality owner;
3. exact headless transition owner;
4. deterministic serialization/replay representation;
5. mask representation;
6. focused live/simulator parity fixture before the simulator becomes training truth.

## Current exposure posture

- `END_SHOP`: supported/frozen.
- exact owned `BUY_JOKER` subset: supported through shop engine.
- exact owned `BUY_VOUCHER` subset, now including Hieroglyph/Petroglyph: supported through shop engine.
- exact held-consumable purchase subset: supported through shop engine.
- `REROLL_SHOP`: internal deterministic mechanics are broadly implemented, but contract/training exposure still requires canonical legality/execution ownership audit.
- `SELECT_BLIND`: internal lifecycle is broadly implemented, but contract/training exposure still requires end-to-end composition/legality audit.
- `SKIP_BLIND`: internal skip/Tag paths exist for audited cases; contract/training exposure remains to be frozen.
- `SELL_JOKER`, pack actions, and generic consumable use remain incomplete at their exact lifecycle boundaries.

## Immediate next work — strategic-action exposure audit

Proceed in this order unless repository inspection reveals a concrete blocker:

1. audit **REROLL_SHOP** first because exact paid reroll mechanics, capacity, Voucher-modified base cost, generation, and RNG are already broadly owned;
2. locate and freeze the canonical production legality owner and execution owner; do not invent a parallel RL action;
3. prove the headless transition and live action use the same affordability/cost/capacity semantics;
4. expose it in `env_contract.py` only after those owners are exact;
5. add focused contract/action-mask/replay regressions and full deterministic CI;
6. then audit **SELECT_BLIND** end-to-end, composing the existing exact blind progression/start/Boss/draw owners rather than adding a synthetic pre-RNG action;
7. then audit **SKIP_BLIND** for the same contract-level ownership;
8. synchronize this roadmap after every green action exposure.

If REROLL_SHOP inspection finds a missing authoritative state or semantic mismatch, stop at that exact blocker and repair the canonical owner before exposing the action.

---

# R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic tactical/hand-play owners while RL controls strategic boundaries. Do not rewrite tactical mechanics in the learner.

# R5 — live/simulator parity harness — NOT STARTED

Required before treating the simulator as authoritative training truth. Priority fixtures:

- shop generation/purchase/reroll;
- Voucher redemption;
- blind start/clear;
- blind skip/Tag flow;
- representative Bosses;
- RNG/shuffle/draw;
- owned-deck composition;
- economy transitions.

# R6 — environment performance gate — NOT STARTED

Measure steps/sec, runs/minute, parallel scaling, tactical-bridge cost, and serialization overhead only after semantics are correct.

# Later phases

## O — observation/action encoding — NOT STARTED

Versioned public observation/action schemas; no hidden-information leakage; illegal action probability zero after masking.

## B0 — RL baseline infrastructure — NOT STARTED

Random legal and deterministic symbolic/headless baselines before learned policy work.

## PPO — NOT STARTED

Do not begin until R-phase exactness, representative parity, and performance gates are satisfied.
