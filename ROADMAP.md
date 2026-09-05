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
cacff79e399ae9aca6176ea1d237f8f1c89cc898
  feat(balatro): observe live joker edition rates

Voucher edition-rate family:
a92185a  feat(balatro): add joker edition rate capability
af05c6d  feat(balatro): redeem exact joker edition rate vouchers
b3f02a0  test(balatro): pin exact joker edition rates
52156b9  test(balatro): pin edition upgrade thresholds
a2d5c9e  fix(balatro): fail closed on edition rate mismatch
2d63733  test(balatro): cover edition rate mismatch guards
bcae2f0  test(balatro): cover live edition rate translation
cacff79  feat(balatro): observe live joker edition rates

Latest verified code-head CI:
33956949501
2133 passed, 1595 deselected
```

Hone / Glow Up is now a closed exact Voucher family. The environment owns the persistent Joker-edition-rate state, redemption semantics, stacking, generation thresholds, replay/RNG behavior, mismatch guards, translation, and live observation required to preserve that state across live/headless boundaries.

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop generation: **ACTIVE — PRIMARY WORKSTREAM**.
- Exact Balatro/LuaJIT RNG + pseudoshuffle: **GREEN**.
- Exact playing-card/Joker private ordering for owned cases: **GREEN**.
- Exact normal round/blind/Boss lifecycle across audited Red/White paths: **BROADLY GREEN**.
- Exact round-end cashout + normal blind/Ante progression: **GREEN**.
- Exact normal shop main slots + reroll: **GREEN**.
- Exact Joker/Tarot/Planet normal shop generation owned slices: **GREEN**.
- Exact Voucher runtime eligibility, identity polling, metadata/pricing, and separate Voucher slot publication: **GREEN**.
- Complete 32-Voucher redemption-effect classification: **COMPLETE**.
- Exact resource/capacity Voucher redemption group: **GREEN — 8 VOUCHERS**.
- Owned-Voucher generation integration for the supported resource group: **GREEN**.
- Exact Joker edition-rate Voucher family (Hone / Glow Up): **GREEN — 2 VOUCHERS**.
- Remaining Voucher effect families: **FAIL CLOSED UNTIL THEIR DOWNSTREAM EFFECTS ARE OWNED**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **NOT CURRENTLY REQUIRED**.

## Exact currently supported Voucher families

### Resource / capacity group

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

### Joker edition-rate group

```text
v_hone
v_glow_up
```

`games/balatro/env/voucher_capabilities.py` remains the canonical capability boundary. Exact generation capability is distinct from exact redemption capability; do not replace per-boundary capability checks with a blanket `if state.vouchers` bypass.

Current rules:

- Voucher ownership must be structurally valid and duplicate-free;
- nonempty ownership must be authoritative (`vouchers_observed is True`);
- only explicitly audited Vouchers may cross a generation/redemption boundary;
- unsupported Voucher modifiers reject before RNG is consumed;
- upgrade Vouchers do not infer hidden base ownership from a numeric state value;
- observed ownership and the numeric modifier it implies must be mutually consistent;
- all downstream consumers of an exact Voucher effect must use the same canonical state field.

## Hone / Glow Up exactness contract

Canonical state:

```text
joker_generation_edition_rate
```

Owned behavior:

- Hone doubles the current exact Joker edition generation rate;
- Glow Up doubles it again;
- exact generation thresholds consume that canonical rate;
- zero edition rate suppresses the edition roll and does not advance its RNG node;
- stacked Hone → Glow Up progression is deterministic and replay-safe;
- ownership/rate mismatches fail closed;
- live observer + translator preserve the rate exactly;
- no hidden Voucher ownership is inferred from the observed rate alone.

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
- malformed Joker/Tarot/Planet/Voucher generation catalogues are rejected all-or-nothing;
- generated Negative Jokers do not imply Negative acquisition is legal;
- canonical generation catalogues may not be overwritten by legacy wrappers;
- two-slot main-shop generation preflights all catalogue/pricing dependencies before first type RNG;
- Voucher selection never falls back to a guessed/static Python catalogue;
- unsupported Voucher centers never become legal merely because identity, price, and shop slot are known;
- duplicate/malformed/unobserved nonempty Voucher ownership is rejected;
- unsupported Voucher modifiers remain rejected even when other owned Vouchers are supported;
- Voucher upgrade ownership/state mismatches are rejected rather than repaired by inference.

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
- unsupported Voucher redemption/effect application;
- pack lifecycle paths not yet exact;
- malformed/noninteger prices;
- generic SELL_JOKER inverse lifecycle where the Joker has unowned inverse effects.

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

Key ownership:

- keyed Balatro pseudoseed progression;
- LuaJIT combined Tausworthe draws;
- bit-preserving RNG snapshot/restore;
- vanilla pseudoshuffle semantics;
- private playing-card creation order and retained physical deck order where provable;
- private Joker order where lifecycle parity requires it.

## Round/blind/Boss lifecycle — BROADLY GREEN

The environment owns audited Red/White blind start, draw, resource modification, Boss active effects, disable/defeat restoration, and round resolution across all 28 vanilla Bosses. Special hidden-information behavior remains masked correctly.

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

## Normal shop generation — GREEN FOR OWNED BASE PATHS

Owned slices include:

- normal main-shop slot type polling;
- ordinary Joker rarity/center/edition generation for authoritative eligibility catalogues;
- Tarot/Planet normal generation;
- shop reroll for owned generation boundaries;
- strict pricing preflight;
- Voucher eligibility/identity polling;
- Voucher runtime metadata + exact price;
- separate one-normal-Voucher shop slot publication;
- supported owned-Voucher state carried through future ordinary shop generation;
- canonical Joker-edition-rate state consumed by Joker edition generation.

Representative later gates:

```text
33941827707  1973 passed, 1595 deselected
33943525506  2014 passed, 1595 deselected
33945779690  2057 passed, 1595 deselected
33952322285  2110 passed, 1595 deselected
33956063668  2117 passed, 1595 deselected
33956949501  2133 passed, 1595 deselected   Hone / Glow Up + live edition rate
```

---

# Next work — pricing/discount Voucher family audit

Hone / Glow Up is closed. The next family to audit is **Clearance Sale / Liquidation**, because it is mechanically coherent but only safe if a single exact discount state drives every affected price/affordability/execution boundary.

Do **not** implement a cosmetic/display-only discount.

Immediate audit order:

1. inspect pinned vanilla `Clearance Sale` / `Liquidation` redemption semantics;
2. identify the canonical headless/public state for the current shop price multiplier;
3. inspect every affected price path:
   - Joker shop items;
   - Tarot/Planet/playing-card shop items;
   - Voucher price publication;
   - booster-pack price publication;
   - legality/affordability checks;
   - purchase execution/debit;
   - reroll/shop regeneration persistence;
4. confirm live observer/translator can preserve the multiplier exactly;
5. if pricing is fragmented, centralize the pricing owner **before** admitting the Vouchers;
6. implement exact redemption only after all downstream consumers agree;
7. enforce Clearance Sale = `min(current_multiplier, 0.75)` and Liquidation = `min(current_multiplier, 0.5)` exactly as vanilla does;
8. add ownership/multiplier mismatch guards analogous to Hone / Glow Up where required;
9. add focused redemption, future-generation, affordability/execution, replay/RNG-isolation, and fail-closed tests;
10. run full deterministic CI and synchronize this roadmap after green.

If Clearance/Liquidation exposes missing price ownership that is too broad for one safe slice, close that canonical pricing dependency first rather than approximating the Voucher family.

## Subsequent Voucher families after pricing audit

Likely order, subject to source audit:

1. **Clearance Sale / Liquidation** — discount pricing;
2. **Tarot Merchant / Tarot Tycoon** and **Planet Merchant / Planet Tycoon** — shop type-rate modifiers;
3. **Reroll Surplus / Reroll Glut** — persistent reroll cost;
4. remaining economy/pack/special families only after their downstream lifecycle is exact.

The next family is selected by exact downstream ownership, not convenience.

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
