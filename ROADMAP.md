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
e46ee5526a88ae5c76fee118b69f396a425e5749
  test(balatro): align reroll capacity rejection wording

Latest verified code-head CI:
33964693188
2224 passed, 1595 deselected
```

The previous feature head `4821e7b` completed exact Overstock shop transition ownership but CI `33964088221` exposed two stale regressions: one still treated Overstock as unsupported at cash-out, and one hard-coded the old two-card reroll error wording after main-shop capacity became variable. Production semantics were not weakened. The fixtures were corrected in `ad333bc` and `e46ee55`; the full deterministic suite is green again.

## Recent closure commits

```text
# interest-cap Voucher family
b465f85  feat(balatro): add canonical interest cap state
f0d57a0  feat(balatro): define exact interest cap voucher boundary
12e18ac  feat(balatro): consume exact voucher interest cap at cashout
28c9f33  feat(balatro): own exact interest cap voucher redemption
0eece8a  test(balatro): pin exact interest cap voucher mechanics
e8698ad  refactor(balatro): derive exact interest cap from voucher history
1cf970c  test(balatro): derive interest cap from exact voucher history
2749b4a  feat(balatro): expose exact interest cap voucher transitions
7d4bc1e  test(balatro): cover interest cap voucher shop transitions

# shop-size Voucher family
3922b97  feat(balatro): own Overstock shop-size capability
e943bae  feat(balatro): derive main shop slots from vouchers
d162f55  feat(balatro): generate variable main shop capacity
d6f80c1  feat(balatro): reroll exact Overstock shop capacity
8a94dd6  feat(balatro): own exact Overstock redemption
4821e7b  feat(balatro): expose exact Overstock shop transition

# closure after stale integration fixtures
ad333bc  test(balatro): keep cashout unsupported voucher fixture exact
e46ee55  test(balatro): align reroll capacity rejection wording
```

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop generation: **ACTIVE — PRIMARY WORKSTREAM**.
- Exact Balatro/LuaJIT RNG + pseudoshuffle: **GREEN**.
- Exact playing-card/Joker private ordering for owned cases: **GREEN**.
- Exact normal round/blind/Boss lifecycle across audited Red/White paths: **BROADLY GREEN**.
- Exact round-end cashout + normal blind/Ante progression: **GREEN**.
- Exact normal main-shop generation + paid reroll with variable supported capacity: **GREEN**.
- Exact Joker/Tarot/Planet normal shop generation owned slices: **GREEN**.
- Exact Voucher runtime eligibility, identity polling, metadata/pricing, and separate Voucher slot publication: **GREEN**.
- Complete 32-Voucher redemption-effect classification: **COMPLETE**.
- Exact resource/capacity Voucher group: **GREEN — 8 VOUCHERS**.
- Exact Joker edition-rate family: **GREEN — Hone / Glow Up**.
- Exact discount family: **GREEN — Clearance Sale / Liquidation**.
- Exact shop type-rate family: **GREEN — Tarot Merchant/Tycoon + Planet Merchant/Tycoon**.
- Exact reroll-cost family: **GREEN — Reroll Surplus / Reroll Glut**.
- Exact interest-cap family: **GREEN — Seed Money / Money Tree**.
- Exact main-shop-size family: **GREEN — Overstock / Overstock Plus**.
- Supported Voucher state through ordinary cash-out/new-shop entry: **GREEN**.
- Remaining 10 Voucher centers: **FAIL CLOSED UNTIL THEIR DOWNSTREAM EFFECTS ARE OWNED**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **NOT CURRENTLY REQUIRED**.

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

`games/balatro/env/voucher_capabilities.py` is the canonical per-boundary capability owner. Exact generation capability is distinct from exact redemption/cash-out capability; never replace these checks with a blanket `if state.vouchers` rule.

### Remaining unsupported Voucher centers

```text
v_omen_globe
v_telescope
v_observatory
v_blank
v_magic_trick
v_illusion
v_hieroglyph
v_petroglyph
v_directors_cut
v_retcon
```

Their current blockers are real mechanics boundaries, not missing allowlist entries:

- Omen Globe depends on Spectral generation inside Arcana packs;
- Telescope / Observatory depend on Celestial pack/Planet lifecycle and Observatory held-Planet scoring;
- Blank has progression/unlock semantics rather than an ordinary immediate gameplay modifier;
- Magic Trick / Illusion require exact playing-card shop generation, purchase, and modifier generation;
- Hieroglyph / Petroglyph alter Ante plus persistent round hand/discard allowances and therefore require full downstream progression audit;
- Director's Cut / Retcon require exact Boss-reroll action/state ownership.

---

# Canonical Voucher invariants

Voucher ownership must be structurally valid, duplicate-free, and authoritative when nonempty (`vouchers_observed is True`). Upgrade Vouchers never infer hidden base ownership from numeric state. Observed ownership and every canonical numeric modifier it implies must agree exactly. Unsupported modifiers reject before RNG is consumed.

Canonical state currently consumed by exact Voucher families includes:

```text
joker_generation_edition_rate
shop_discount_percent
shop_discount_percent_observed
tarot_rate
planet_rate
interest_cap
interest_cap_observed
HeadlessRunState.base_reroll_cost
HeadlessRunState.reroll_cost
```

Main-shop capacity is reconstructed exactly from authoritative Voucher ownership rather than exposed as a redundant public field:

```text
no Overstock                     2 slots
Overstock                        3 slots
Overstock + Overstock Plus       4 slots
```

Owned upgrade progression:

```text
Glow Up         requires Hone
Liquidation     requires Clearance Sale
Tarot Tycoon    requires Tarot Merchant
Planet Tycoon   requires Planet Merchant
Reroll Glut     requires Reroll Surplus
Money Tree      requires Seed Money
Overstock Plus  requires Overstock
```

### Seed Money / Money Tree

```text
base interest cap                $25
Seed Money                       $50
Seed Money + Money Tree         $100
```

The authoritative cap is reconstructed from complete Voucher history, with explicit observed numeric state required to agree when present. Ordinary round cash-out consumes the same canonical cap. Unsupported interest/challenge modifiers remain fail closed.

### Overstock / Overstock Plus

Pinned vanilla redemption calls `change_shop_size(1)` for each Voucher. Exact headless behavior therefore derives 2/3/4 main-shop slots from authoritative Voucher history, uses that capacity for initial generation and paid rerolls, and preserves the family across cash-out/new-shop entry. Incomplete current-capacity shops fail closed before reroll RNG is consumed.

### Existing exact families

- Hone / Glow Up: edition generation rate 1.0 → 2.0 → 4.0.
- Clearance Sale / Liquidation: 0% → 25% → 50%; supported visible inventory is repriced from immutable base cost.
- Tarot / Planet Merchant/Tycoon: canonical type rates feed future main-shop type polling.
- Reroll Surplus / Glut: persistent base reroll cost $5 → $3 → $1, with current paid reroll cost tracked separately.
- Resource/capacity families update canonical slots/round allowances where their full downstream use is already owned.

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
- malformed Joker/Tarot/Planet/Voucher catalogues are rejected all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal;
- canonical generation catalogues may not be overwritten by legacy wrappers;
- shop generation preflights dependencies before first type RNG;
- Voucher selection never falls back to a guessed/static Python catalogue;
- unsupported Voucher centers never become legal merely because identity/price/slot are known;
- duplicate, malformed, or unobserved nonempty Voucher ownership is rejected;
- Voucher upgrade ownership/state mismatches are rejected rather than repaired by inference;
- discount redemption is hidden when current generated prices are stale or pricing paths are unowned;
- ordinary cash-out rejects unsupported Voucher generation/pricing/economy state rather than erasing it;
- Magic Trick remains a regression fixture for unsupported playing-card-shop effects now that Overstock is exact;
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
33796012173  1467 passed, 1594 deselected
33855720629  1734 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
33915588784  1924 passed, 1595 deselected
```

Generic training `SELECT_BLIND` remains tied to end-to-end strategic-action ownership even though internal lifecycle primitives are substantially broader.

## Normal shop / Voucher generation — GREEN FOR OWNED PATHS

Owned slices include:

- normal main-shop slot type polling;
- ordinary Joker rarity/center/edition generation for authoritative catalogues;
- Tarot/Planet normal generation;
- variable 2/3/4-card supported main-shop capacity;
- paid shop reroll at the current exact capacity;
- centralized `Card:set_cost`-compatible pricing;
- generated visible-shop repricing from immutable base metadata;
- Voucher eligibility/identity polling;
- Voucher runtime metadata + exact price;
- separate normal Voucher slot publication;
- supported Voucher state carried through ordinary shop generation and cash-out;
- all currently-supported Voucher effects consumed by their canonical downstream owners.

Representative later gates:

```text
33941827707  1973 passed, 1595 deselected
33943525506  2014 passed, 1595 deselected
33945779690  2057 passed, 1595 deselected
33952322285  2110 passed, 1595 deselected
33956949501  2133 passed, 1595 deselected   Hone / Glow Up
33959454017  2155 passed, 1595 deselected   discount pricing
33960365203  2165 passed, 1595 deselected   discount redemption
33961839253  2208 passed, 1595 deselected   reroll Voucher lifecycle
33962480568  2209 passed, 1595 deselected   Voucher-preserving cashout
33964088221  2 failed, 2222 passed          stale Overstock-era fixtures
33964693188  2224 passed, 1595 deselected   interest-cap + Overstock closure
```

---

# Next work — Hieroglyph / Petroglyph downstream audit

The next coherent unsupported family to inspect is:

```text
v_hieroglyph
v_petroglyph
```

Pinned vanilla direct effects are known:

- both call `ease_ante(-1)`;
- Hieroglyph reduces `G.GAME.round_resets.hands` by 1 and updates current hands;
- Petroglyph requires Hieroglyph and reduces `G.GAME.round_resets.discards` by 1 and updates current discards.

This family is **not supported yet**. It is the preferred next audit because canonical `ante`, next-round hand allowance, and next-round discard allowance already exist, but redemption cannot be exposed until every downstream consequence of lowering Ante and allowances is exact.

Immediate audit/implementation order:

1. inspect pinned `ease_ante` semantics and all state it updates;
2. trace how lower Ante affects blind requirements, Boss progression/selection, shop/Voucher eligibility, seeded keys, and current run progression;
3. confirm whether redemption occurs in SHOP with current hands/discards values that must also change immediately;
4. verify canonical `ante`, `round_reset_hands`, `round_reset_discards`, and their observed/exactness flags can represent the mutation without a duplicate state owner;
5. define strict upgrade ownership (`Petroglyph` requires `Hieroglyph`);
6. reject any state where downstream Ante progression cannot be reconstructed exactly;
7. add focused redemption + lifecycle tests only after the full consequence graph is owned;
8. expose BUY_VOUCHER only after every affected consumer reads canonical state;
9. run full deterministic CI;
10. synchronize this roadmap after green.

Do **not** implement Hieroglyph/Petroglyph as a simple numeric redemption patch. Lowering Ante changes future game progression and seeded behavior; the family stays fail closed unless that entire modeled boundary is exact.

If the audit proves the family is blocked, record the blocker and move to the next mechanically complete family rather than approximating it.

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
