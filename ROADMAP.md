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
d903106a28a43bcfa985339c4ca6a8c5bd874e09
  test(balatro): pin exact ante voucher redemption

Latest verified code-head CI:
33966224227
2239 passed, 1595 deselected
```

The Hieroglyph/Petroglyph downstream audit has now materially advanced beyond the previous Overstock checkpoint. Exact pre-Ante Boss/tag progression and Red/White base blind requirements now preserve literal Ante zero/negative semantics, and an internal exact Hieroglyph/Petroglyph redemption primitive is green. The family is **still not training-visible** because vanilla redemption also mutates private `round_resets.blind_ante`; the existing `BlindProgressionState` owner is not yet installed in the generic `HeadlessRunState` consumed by `ShopTransitionEngine`.

## Recent closure commits

```text
# previous interest-cap / shop-size closure
7d4bc1e  test(balatro): cover interest cap voucher shop transitions
3922b97  feat(balatro): own Overstock shop-size capability
4821e7b  feat(balatro): expose exact Overstock shop transition
ad333bc  test(balatro): keep cashout unsupported voucher fixture exact
e46ee55  test(balatro): align reroll capacity rejection wording

# Hieroglyph / Petroglyph downstream progression audit
4f44c2e  test(balatro): correct pre-Ante boss vector
2344224  test(balatro): compose pre-Ante boss cashout progression
197ae83  feat(balatro): own exact Red White base blind amount
6f7be4a  test(balatro): pin Red White pre-Ante blind amounts

# exact internal Ante-Voucher redemption boundary
49bb5c7  feat(balatro): own exact ante voucher redemption primitive
d903106  test(balatro): pin exact ante voucher redemption
```

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop generation: **ACTIVE — PRIMARY WORKSTREAM**.
- Exact Balatro/LuaJIT RNG + pseudoshuffle: **GREEN**.
- Exact playing-card/Joker private ordering for owned cases: **GREEN**.
- Exact normal round/blind/Boss lifecycle across audited Red/White paths: **BROADLY GREEN**.
- Exact round-end cashout + normal blind/Ante progression: **GREEN**.
- Exact literal Ante <= 0 Boss/tag/blind-requirement handling: **GREEN**.
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
- Hieroglyph/Petroglyph direct redemption primitive: **GREEN INTERNALLY, NOT TRAINING-EXPOSED**.
- Supported Voucher state through ordinary cash-out/new-shop entry: **GREEN FOR CURRENT TRAINING-SUPPORTED FAMILIES**.
- Remaining 10 Voucher centers: **FAIL CLOSED AT TRAINING BOUNDARY UNTIL THEIR FULL EFFECTS ARE OWNED**.
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

### Remaining training-unsupported Voucher centers

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
- Hieroglyph / Petroglyph now have exact direct redemption and downstream nonpositive-Ante primitives, but training purchase still requires private `BlindProgressionState` / `round_resets.blind_ante` ownership inside the generic run container;
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
Petroglyph      requires Hieroglyph   # internal exact primitive only so far
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

### Hieroglyph / Petroglyph — internal boundary now exact

Pinned vanilla redemption does all of the following:

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

`games/balatro/env/ante_voucher_redemption.py` now owns those direct mutations with strict observed/reducible allowance checks and exact private `BlindProgressionState` input. It supports literal Ante 0 -> -1 and consumes no RNG. It deliberately remains an **internal primitive** until progression state is installed into the generic run container and `BUY_VOUCHER` can update it atomically.

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
- Ante Voucher redemption rejects stale private `blind_ante` instead of deriving it from public Ante;
- Ante Voucher redemption rejects unobserved or irreducible current/persistent hand/discard allowances;
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

The Hieroglyph/Petroglyph downstream audit additionally owns literal nonpositive Ante behavior in:

- normal Boss selection (`max(1, ante)` only where vanilla clamps the minimum-Ante eligibility test; showdown logic uses literal Ante);
- normal Tag selection and its seeded `Tag{ante}` keys;
- pre-Ante Boss cash-out tag/Boss regeneration;
- Red/White base blind amount (`Ante < 1 -> 100`, Ante 1–8 exact table, endless >8 fail closed);
- blind progression state where `blind_ante` may be zero or negative.

Representative gates:

```text
33796012173  1467 passed, 1594 deselected
33855720629  1734 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
33915588784  1924 passed, 1595 deselected
33965599236  2233 passed, 1595 deselected   pre-Ante + Red/White blind amount closure
33966224227  2239 passed, 1595 deselected   exact internal Ante-Voucher redemption
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
33965599236  2233 passed, 1595 deselected   Hieroglyph/Petroglyph downstream progression audit
33966224227  2239 passed, 1595 deselected   internal exact Ante-Voucher redemption
```

---

# Next work — install private blind progression into the run container

The immediate blocker to training-visible Hieroglyph/Petroglyph is now structural, not mechanical.

Vanilla redemption mutates:

```text
public/canonical:
  ante
  round_resets.hands or round_resets.discards
  current hands_left or discards_left
  voucher ownership
  money/shop Voucher slot

private progression:
  round_resets.blind_ante
```

`BlindProgressionState` already owns the private blind statuses / `blind_on_deck` / `blind_ante` / Boss identity semantics, but it is currently passed explicitly through progression helpers rather than stored in `HeadlessRunState`. `ShopTransitionEngine.step(run, BUY_VOUCHER)` therefore cannot yet update public + private progression atomically.

Immediate implementation order:

1. install an optional exact `BlindProgressionState` owner in `HeadlessRunState` (or otherwise integrate the existing owner canonically; do **not** create a duplicate progression model);
2. legacy/manually-constructed run states with no authoritative progression must remain valid but fail closed for actions that require it;
3. validate retained progression against public state only at boundaries where a source invariant actually exists; do not invent a universal `blind_ante == ante` rule across Boss `end_round` intermediate states;
4. update Boss cash-out/tag/Boss progression compositions to preserve/use the same retained progression owner rather than parallel copies;
5. wire `v_hieroglyph` / `v_petroglyph` into `voucher_capabilities.py` only at the exact boundaries whose downstream consequences are now owned;
6. route `ShopTransitionEngine` Ante Voucher legality/execution through `ante_voucher_redemption.py` and atomically replace retained progression;
7. keep Petroglyph upgrade ownership strict (`v_hieroglyph` required);
8. add focused tests proving legal mask visibility only when progression + allowance observations are authoritative, plus nonpositive-Ante persistence through next blind/tag/Boss generation;
9. run the full deterministic CI and inspect the pytest count;
10. synchronize this roadmap after green.

Do **not** expose Hieroglyph/Petroglyph by adding them to a blanket Voucher allowlist before the generic run container can retain the private `blind_ante` mutation.

If progression integration reveals a conflicting owner or missing serialization boundary, stop at that exact blocker rather than adding a wrapper/rescue layer.

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
