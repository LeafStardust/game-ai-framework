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
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, `--five`, or plural `--attempts`; the sole canonical attempt-count interface is `--attempt N`.
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
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2 or env_r3 or env_r4 or env_r5"
```

---

# Current checkpoint — 2026-09-08

```text
Branch: feat/v1.0-red-white-competence

R3 closure verification commit:
2e8daa4b64694cc22862f99ea16adea3c61c00f2
  docs(balatro): sync roadmap through R3 closure
GitHub Actions run 33982517717
2331 passed, 1595 deselected

R4 exact discard bridge:
c117ab054e8cebb8a402711cca46ed48fb076172
  feat(balatro): bridge public tactical discard
GitHub Actions run 33982555046
2335 passed, 1595 deselected

R4 production decision-engine wiring:
5d8565b6910eb9c77b8342465dc404bd6a902840
  refactor(balatro): wire R4 tactical decision engine
GitHub Actions run 33995495867
2336 passed, 1595 deselected

R4 ordinary Play lifecycle:
652b32624ae2feaad9e768baac9f505b386bb271
  feat(balatro): own ordinary R4 play lifecycle
GitHub Actions run 33999099418
GitHub Actions job 101394654137
2350 passed, 1595 deselected

R4 representative Boss tactical coverage:
98ab566071f0af94305ffaba5b9fa0482e25b4ad
  feat(balatro): admit exact Tooth tactical play
f8bc7aabafcd766fd9bcada15e8bef489977d7a5
  feat(balatro): admit exact Hook tactical play

e9408fa943bbc2609f3ee96e53318ba2ff2c874c
  feat(balatro): record public tactical trajectory evidence
0603f420ee7f7d1f235c21b0ea9debc7b72442e5
  fix(balatro): freeze tactical evidence snapshots

R5 tactical parity infrastructure:
7dd4f36341fd5624d05db2e7b59e808f81ceb5cd
  feat(balatro): add R5 tactical parity comparator
da7e4e9605d37584b116f28274bdb7fc91ac728a
  feat(balatro): adapt live run logs for R5 parity
GitHub Actions run 34005381429
GitHub Actions job 101411468974
2373 passed, 1595 deselected

0a657d961b13bac12371466418ff470c15e62a61
  feat(balatro): compare R5 tactical trajectories
GitHub Actions run 34005877151
GitHub Actions job 101412827495
2377 passed, 1595 deselected

R5 exact strategic reroll replay authority:
d82801c8
  feat(balatro): capture R5 live RNG replay authority
c9203f25
  feat(balatro): restore R5 reroll replay checkpoints
de1a53dc
  fix(balatro): require observed vouchers for reroll replay
e116bf09e0c13c6092dc57b7bc2dae5e7f9ee792
  feat(balatro): replay exact R5 shop reroll parity
GitHub Actions run 34022177202
GitHub Actions job 101456639275
2401 passed, 1595 deselected

R5 live paid-reroll capture wiring:
b15fab5fe2bec0080c383a009dbef4f00cc89e12
  feat(balatro): capture live R5 reroll parity
GitHub Actions run 34024889806
GitHub Actions job 101463994146
2409 passed, 1595 deselected

R5 paid-reroll live-fixture readiness repairs:
b092783e9bb44831e2333b5bf70439af4b37c785
  fix(balatro): admit depleted paid-reroll shops
fc65fa09855a7e3a2febf60c04c8a9ef9f86877a
  fix(balatro): expose reroll replay rejection cause
c3ed2b712fe3422c523ffe3e9ae67b604369facf
  fix(balatro): model shop consumable pool visibility
15db1dbc2d5fecd29d49c3ffa28b9bd6cb344562
  fix(balatro): observe consumable pool in production
9083d4170bad8d2ce799ec47debb585fe94d9943
  fix(balatro): admit Omen Globe for base shop parity
3f9ef026b768342aa18cbad4e5defda8b5a8bc1d
  fix(balatro): decouple exact reroll voucher capability
99a4776ce8d01b47fb0a460cdc31d5ea63558b2e
  test(balatro): cover Telescope paid reroll parity state
GitHub Actions run 34213635015
GitHub Actions job 102020161503
2419 passed, 1595 deselected

R5 first real paid-reroll fixture repair:
606c7b4535176e92f9bc87192cc9a049670a0d6e
  fix(balatro): align paid reroll with live parity
9fbfe70386e3141c565cd07c655decd5194dd1cb
  test(balatro): align exact reroll regressions
GitHub Actions run 34217561085
GitHub Actions job 102032815831
2421 passed, 1595 deselected

Canonical attempt-count correction and branch-tree repair:
7b1fb06f7a307a2ac2d0fec8613f18c6eaeeb79d
  fix(balatro): restore branch tree after launcher update
GitHub Actions run 34218019368
GitHub Actions job 102034289630
2427 passed, 1595 deselected

R5 supported Joker purchase evidence and true headless replay:
256d56baf36f0d5a32b9aabf827cbbdc2643c3f5
  feat(balatro): add Joker purchase parity evidence
adfa8458fbee9f6b51db0f7b8b25e8ab36d0c56c
  test(balatro): seed R5 joker purchase replay
0183d09d729dad15f72948be0326a10432ecea07
  test(balatro): complete R5 joker purchase fixture metadata
30b8ca49678f1826b92d8939d9337997d5275dbc
  test(balatro): replay R5 Joker purchase without normalization
8d6b64adc3ab2884d59e5d59a9d2a8f448f83ed5
  test(balatro): compare R5 purchase identity structurally
GitHub Actions run 34222351675
GitHub Actions job 102048209359
2431 passed, 1595 deselected

R5 first real ordinary Joker-purchase fixture:
e2e4c23ea669283fc3991cc5bf6ad10920a22f9b
  test(balatro): replay real R5 Joker purchase fixture
6b93714d3ca496d6440be75f3b169e5b48b04cd3
  fix(balatro): normalize exact live Joker prices
a709b9c74e688f20ebaa82ba8fed5e02d2e231fa
  test(balatro): freeze exact live Joker price translation
GitHub Actions run 34229665010
GitHub Actions job 102072335608
2437 passed, 1595 deselected
```

All counts above were read from the actual `balatro-deterministic-tests` job logs, not inferred from workflow status. The frozen strategic contract in `games/balatro/env_contract.py` contains no `PLANNED` entry; `BUY_CARD` and `REROLL_BOSS` remain explicitly unavailable and are excluded from `training_action_contracts()`.

## Immediate development position

- R1 deterministic state/acquisition: **SUBSTANTIALLY COMPLETE**.
- R2 RNG/lifecycle/shop/pack generation: **BROADLY GREEN; REMAINING GAPS ARE SPECIFIC**.
- R3 typed strategic action vocabulary: **COMPLETE / GREEN**.
- R4 deterministic tactical bridge: **COMPLETE / GREEN FOR THE REQUIRED REPRESENTATIVE GATE**.
- R5 live/simulator parity harness: **IN PROGRESS — TACTICAL EVIDENCE/COMPARISON, THE FIRST REAL ORDINARY PAID-REROLL FIXTURE, AND THE FIRST REAL ORDINARY `BUY_JOKER` FIXTURE ARE GREEN; THE NEXT SLICE IS REPRESENTATIVE VOUCHER REDEMPTION PARITY**.
- R6 environment performance gate: **NOT STARTED**.
- Observation/action encoding: **NOT STARTED**.
- PPO/observation training: **DO NOT START**.
- Live Balatro validation: **NOT CURRENTLY REQUIRED; INSPECT EXISTING DURABLE EVIDENCE FOR A SUPPORTED VOUCHER REDEMPTION BEFORE REQUESTING A NEW LIVE RUN**.

## Current strategic action contract

### SUPPORTED / training-exposed

```text
END_SHOP
REROLL_SHOP
BUY_JOKER          exact owned subset only
SELL_JOKER         audited inventory-only inverse lifecycle only
BUY_VOUCHER        exact owned subset only
BUY_CONSUMABLE     exact held-consumable purchase subset
OPEN_PACK          exact owned entry boundary
CHOOSE_PACK_OPTION exact admitted pack-option subset
SKIP_PACK          exact admitted pack-skip subset
USE_CONSUMABLE     exact held-Planet use subset
SKIP_BLIND         exact admitted Small-Blind/Tag subset
SELECT_BLIND       exact audited blind-start boundary
```

### UNAVAILABLE / never enters the training mask

```text
BUY_CARD
REROLL_BOSS
```

`BUY_CARD` is deliberately unavailable rather than planned: there is no dedicated canonical production `BUY_CARD` identifier and no frozen live shop legality/execution owner for Magic Trick / Illusion playing-card shop purchases. Do **not** invent an RL-only action to fill that gap.

`REROLL_BOSS` remains unavailable because no frozen canonical production action/owner exists for the current Red/White surface.

There is **no remaining PLANNED action in the frozen strategic contract**. If one appears later, it requires an explicit new canonical production capability, not a learner-side alias workaround.

---

# Foundation status

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
L3 environment freeze                COMPLETE
R0 headless environment architecture COMPLETE
R1 deterministic state/acquisition   SUBSTANTIALLY COMPLETE
R2 RNG/lifecycle/shop generation     BROADLY GREEN / SPECIFIC GAPS REMAIN
R3 typed action vocabulary           COMPLETE / GREEN
R4 deterministic tactical bridge     COMPLETE / GREEN
R5 live/simulator parity harness      IN PROGRESS
R6 environment performance gate      NOT STARTED
O observation/action encoding        NOT STARTED
B0 RL baseline infrastructure        NOT STARTED
PPO strategic learner                NOT STARTED
```

The simulator is **not authoritative game truth** until representative R5 live/simulator parity passes.

---

# Historical roadmap retention

The older roadmap contained more phases because it documented the symbolic/Bond competence path in implementation detail. Those phases were intentionally closed or superseded before the deterministic-environment/RL path began. They remain historical contracts and evidence; they are not active work and must not be silently reopened.

| Earlier phase family | Current status | What remains binding |
|---|---|---|
| A–K symbolic mechanics and Bond integration | **COMPLETE** | Exact mechanics, legality, public-state boundaries, canonical tactical owners, candidate projection, deterministic regressions, and useful Bond-derived features |
| L live stabilization and defect repair | **COMPLETE** | Classify a demonstrated failure before patching; repair the first wrong canonical owner; add a focused regression; use live runs only for hypotheses that require Balatro |
| L3 environment freeze | **COMPLETE** | Preserve the frozen production/environment boundary and fail closed when exact behavior is not owned |
| Manual Bond coefficient tuning | **RETIRED AS PRIMARY PATH** | Existing Bond signals may become observations/features, but manual coefficients do not replace the learned strategic policy |
| Higher-stake and additional-deck progression | **DEFERRED** | Begin only after Red Deck / White Stake competence passes the final learned-policy evaluation gate |

## Retained engineering invariants

1. **First wrong layer owns the defect.** Fix mechanics, state, RNG, projection, legality, consumer valuation, action arbitration, runtime, or telemetry at the earliest incorrect canonical boundary. Never compensate with a later rescue wrapper.
2. **Counterfactual influence must reach the final action.** For deterministic proofs, hold public state, legal actions, and unrelated evidence constant; change the relevant fact and prove that the final action changes when it should.
3. **Representative paths require end-to-end proof.** Unit correctness is insufficient when state acquisition, transition, mask, serialization/replay, tactical execution, or live dispatch can still disagree.
4. **Live batches are hypothesis-driven.** A loss is evidence to inspect, not proof of a defect. Do not run repeated open-ended Balatro batches merely to search for something to change.
5. **Run-level diagnosis remains connected.**

```text
early survival
→ first scoring engine
→ economy stabilization
→ scalable engine
→ boss-safe execution
```

6. **Evaluation must compare against frozen baselines.** The old minimum of 20 completed episodes per arm applied to manual live tuning; it is not automatically sufficient for RL. B0/PPO must define seeded and unseeded evaluation sets, sample size/power, promotion metrics, and regression/pathology gates before learned-policy promotion.
7. **CI validates the roadmap; it does not authoritatively rewrite development history.** Completed phases may be compressed only when their status, retained outputs, and superseded boundaries remain recorded here or in linked archival documents.

## Explicitly superseded concepts

Do not restore the old persistent strategy controller, named strategy identity as action authority, FORMING/PINNED states, `StrategyPlan`, goal/prescription plumbing, generic pivot FSM/resistance, one execution tree per Bond, post-owner rescue authority, or manual Bond tuning as the primary competence path.

The active development sequence is now:

```text
R5 live/simulator parity
→ R6 performance
→ O observation/action encoding
→ B0 baselines
→ PPO
→ controlled Red/White promotion
→ higher stakes/decks
```

---

# R1 — deterministic state/acquisition

## Owned

- Red Deck / White Stake canonical state validation.
- Strict public/private card-zone ownership.
- Permanent owned-deck truth from `G.playing_cards` with all-or-nothing LuaJIT/TValue decoding.
- Next-round hand/discard allowances where required.
- Exact resource-sensitive Joker acquisition effects for the admitted group.
- Broad static score/rule/retrigger Joker acquisition groups whose acquisition is inventory-only.
- Owned-deck-dependent scoring Jokers only when permanent deck state is authoritative.
- Exact supported Voucher acquisition effects listed below.
- Fail-closed malformed/noninteger prices.
- Exact audited Joker sale subset whose inverse lifecycle is inventory-only.

## Exact Joker acquisition families retained

The inventory-only/scoring-safe surface includes the previously audited static, hand-rule, hand-shape, suit, retrigger, money, and conditional scorers.

Resource-sensitive exact acquisitions include:

```text
Juggler
Stuntman
Drunkard
Troubadour
Merry Andy
```

Owned-deck-dependent scoring acquisitions include:

```text
Driver's License
Erosion
Steel Joker
Stone Joker
```

only when permanent deck state is authoritative.

Burglar's blind-selection consequence is now owned on the admitted exact `SELECT_BLIND` lifecycle path. Acquisition/sale legality must still be proven at their own boundaries rather than inferred merely from lifecycle support.

## Still fail closed

- unknown/unaudited Joker acquisitions;
- Joker editions whose acquisition changes capacity semantics, especially Negative;
- Joker sale/inverse lifecycle cases not in the audited exact sale subset;
- unsupported playing-card shop mechanics;
- unsupported Voucher mechanics listed below.

Representative historical gates:

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

### Hieroglyph / Petroglyph

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

Canonical ownership:

```text
HeadlessRunState.blind_progression_state
        ↓
ante_voucher_redemption.py
        ↓
ShopTransitionEngine legal mask + BUY_VOUCHER execution
```

The path fails closed when retained progression is absent/stale, the required current/persistent allowance is unobserved or irreducible, price is malformed/unaffordable, or Petroglyph lacks Hieroglyph. Successful redemption consumes no RNG and atomically updates public and private state.

### Boundary-limited or unsupported Voucher centers

```text
v_omen_globe      base-shop generation / paid-reroll zero-effect boundary only
v_telescope       base-shop generation / paid-reroll zero-effect boundary only
v_observatory
v_blank
v_magic_trick
v_illusion
v_directors_cut
v_retcon
```

Blocked by real mechanics:

- Omen Globe: Spectral generation inside Arcana packs.
- Telescope / Observatory: Celestial pack/Planet lifecycle and Observatory held-Planet scoring.
- Blank: progression/unlock semantics rather than an ordinary immediate gameplay modifier.
- Magic Trick / Illusion: exact playing-card shop generation/purchase/modifier generation; `BUY_CARD` is unavailable in the frozen action contract.
- Director's Cut / Retcon: exact Boss-reroll action/state ownership; `REROLL_BOSS` is unavailable in the frozen action contract.

Do not promote these through a blanket allowlist.

---

# R2 — RNG + lifecycle + shop/pack generation

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

Owned lifecycle details include:

- normal and pre-Ante blind progression;
- literal nonpositive Ante handling where vanilla permits it;
- exact base blind requirements for the modeled Red/White Ante range;
- Boss selection/activation/disable/defeat restoration;
- audited `setting_blind` lifecycle effects;
- exact physical shuffle/deal with hidden draw order retained privately;
- round-end cashout and ordinary next-blind/Ante transitions;
- exact admitted blind-skip progression/Tag behavior;
- canonical skip counter ownership where admitted.

Representative gates:

```text
33796012173  1467 passed, 1594 deselected
33855720629  1734 passed, 1595 deselected
33863345344  1794 passed, 1595 deselected
33873017991  1838 passed, 1595 deselected
33905449910  1876 passed, 1595 deselected
33915588784  1924 passed, 1595 deselected
33965599236  2233 passed, 1595 deselected
33966224227  2239 passed, 1595 deselected
33967536736  2257 passed, 1595 deselected
33971114617  2278 passed, 1595 deselected   SELECT_BLIND exposure guard closure
33975435937  2279 passed, 1595 deselected   retained blind skip tag prerequisite
33978049029  2320 passed, 1595 deselected   latest verified pre-R3-closure head
```

## Normal shop / Voucher / pack generation — GREEN FOR OWNED PATHS

Owned slices include:

- normal main-shop slot type polling;
- ordinary Joker rarity/center/edition generation for authoritative catalogues;
- Tarot/Planet normal generation;
- variable supported main-shop capacity;
- paid shop reroll at current exact capacity;
- centralized `Card:set_cost`-compatible pricing;
- generated visible-shop repricing from immutable base metadata;
- Voucher eligibility/identity polling;
- Voucher runtime metadata + exact price;
- separate normal Voucher slot publication;
- supported Voucher state through shop generation and ordinary cash-out;
- all supported Voucher effects consumed by canonical downstream owners;
- exact admitted Buffoon option ordering/choice/skip behavior;
- exact admitted held-Planet use behavior and guards;
- exact audited Joker sale path.

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
33978049029  2320 passed, 1595 deselected   pack/sale/Planet-use era latest verified head
```

### Headless `ROUND_EVAL` boundary

The project deliberately uses `ROUND_EVAL` as the headless pre-cashout boundary consumed by `cash_out_baseline_ordinary_blind()`. This name is not a claim that the card-zone timing is identical to vanilla's internal state label.

For the exact admitted lifecycle:

- a completed Play has already moved its selected cards from hand → play → discard and left `played_pile` empty;
- a cleared blind may still retain unplayed held cards in `public.hand` at this headless boundary;
- `round_end.py` / `repopulate_round_end_deck()` owns the admitted clear-path hand/discard → deck repopulation before payout/shop progression;
- final-hand failure enters `GAME_OVER` and does not execute clear-path repopulation.

Do not duplicate this repopulation inside the tactical Play owner merely to mirror vanilla's internal state-label timing.

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
- unsupported Tag outcomes stay masked rather than producing phantom post-skip states;
- unsupported pack option/skip/use paths stay masked;
- `BUY_CARD` and `REROLL_BOSS` are explicit unavailable capabilities rather than phantom learner actions;
- tests must mark authoritative empty/zero observations explicitly instead of relying on defaults.

---

# R3 — typed strategic action vocabulary — COMPLETE / GREEN

Every training-visible action requires:

1. canonical production action identifier;
2. frozen legality owner;
3. exact headless transition owner;
4. deterministic serialization/replay representation;
5. mask representation;
6. focused live/simulator parity fixture before the simulator becomes training truth.

## Supported / frozen

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

Each name above is an RL-facing alias over a canonical production identifier; it does not create a second action system. Each action remains narrow at runtime: only exact state/item/tag/pack/consumable subsets enter the legal mask.

## Explicitly unavailable

```text
BUY_CARD
REROLL_BOSS
```

`BUY_CARD` closure commits:

```text
1e6eca9  refactor(balatro): close unavailable card shop action
3a43797  test(balatro): freeze unavailable card shop capability
```

Reason: no dedicated canonical production identifier or live shop legality/execution owner exists. Magic Trick/Illusion playing-card shop support is a future mechanics expansion, not a missing R3 alias.

`REROLL_BOSS` remains unavailable for the same canonical-ownership reason.

## R3 closure proof

- `games/balatro/env_contract.py` contains no `PLANNED` contract in the frozen action surface.
- `BUY_CARD` and `REROLL_BOSS` remain outside `training_action_contracts()`.
- GitHub Actions run `33982517717` at `2e8daa4b64694cc22862f99ea16adea3c61c00f2` completed with **2331 passed, 1595 deselected**.
- R4 then advanced on top of this green gate without reopening the R3 vocabulary.

Do not reopen a supported R3 action without a concrete regression.

---

# R4 — deterministic tactical bridge — COMPLETE / GREEN

## Goal

RL controls strategic run-development boundaries while existing deterministic hand-level owners continue to choose exact play/discard actions. **Do not rewrite the tactical engine inside the learner or create a second scoring/hand-selection implementation.**

## Canonical tactical audit — retained findings

1. Canonical tactical payloads are `BalatroAction(PLAY_CARDS, cards=[...])` and `BalatroAction(DISCARD_CARDS, cards=[...])` from `games/balatro/actions.py`; selected cards are canonical public hand objects, not an RL-only index action type.
2. The production call chain is `StrategyAwareLiveMemoryInjectedSingleStepRunner` → `_recommend_hand_with_bonds()` → `PathAwareLiveHandActionDecisionEngine(policy=StrategyAwareLiveHandActionPolicy(...))` → `.decide(state)` → `HandActionDecision.action`. The headless bridge calls that same production-shaped `decide(state)` boundary and accepts only the canonical `BalatroAction` carried by `decision.action`; the former test-only `.plan(state)` shape is rejected rather than retained as a compatibility layer.
3. `D1LiveBlindClearPlanner` in `games/balatro/live/hand_action_planner.py` extends the core planner in `hand_action_planner_core.py`, obtains Play/Discard candidates from the shared generator, and filters Play candidates through `boss_play_action_is_legal`; Boss-aware score projection remains in the shared live evaluator path.
4. Runner / To Do List target-hand evidence is owned by `games/balatro/target_hand_engine_policy.py` and consumed inside canonical D1 ranking; R4 does not duplicate that heuristic.
5. `games/balatro/env/public_observation.py` is the policy-visible sanitization boundary. Private physical draw order remains on `HeadlessRunState` and is never passed to the tactical decision engine.
6. The frozen strategic action contract remains `games/balatro/env_contract.py`; there is no separate tactical learner action surface.
7. `games/balatro/env/play_transition.py` owns the narrow exact ordinary Small/Big-blind action-time lifecycle and now composes the admitted exact Boss `press_play` mutations at the canonical source-order position.
8. `games/balatro/env/tactical_transition.py` composes admitted Discard and Play owners behind the production `.decide()` boundary. Unsupported tactical states still fail closed.
9. Representative exact Boss tactical Play is admitted for **The Tooth** and **The Hook** only where their complete action-time lifecycle is owned. Other Bosses remain fail closed unless their full relevant behavior is exact.
10. `games/balatro/env/tactical_evidence.py` persists policy-visible pre/action/post evidence with selected visible hand indices while excluding simulator-private draw order, RNG, hidden identities, and local object identity. Durable snapshots are frozen so later simulator mutation cannot rewrite earlier trajectory evidence.

## Admitted R4 slice — green

```text
headless SELECTING_HAND
        ↓
policy-safe public observation
        ↓
production-shaped decision_engine.decide(state)
        ↓
HandActionDecision.action / canonical BalatroAction
        ↓
canonical PLAY_CARDS or DISCARD_CARDS
        ↓
visible-position mapping / exact action owner
        ↓
headless transition
        ↓
public tactical trajectory evidence
```

Exact admitted behavior:

- selected cards are validated as 1–5 distinct visible positions and resolved in current hand-area order;
- private/public draw and discard zones must agree before mutation;
- permanent playing-card order must remain authoritative;
- the input run is copy-on-write;
- Discard moves selected cards to the exact discard tail, updates `discards_remaining` / `discards_used`, and redraws from retained private physical order;
- ordinary Play decrements hands before movement, moves hand → play → discard, records played-this-ante history, evaluates the canonical poker hand and deterministic score, updates score/hand counters/visibility/last hand, and resolves clear vs continue/redraw vs final-hand loss;
- admitted Tooth and Hook Play effects compose through canonical Boss ownership/source order;
- policy input is `public_observation_state(run.public)`, so face-down identity remains masked;
- decision-selected foreign card objects fail closed;
- the legacy test-only `.plan(state)` shape fails closed rather than being supported in parallel;
- unsupported Joker/card callbacks, random scoring effects, unowned Boss effects, and unsupported decision actions fail closed.

## R4 closure proof

```text
c117ab054e8cebb8a402711cca46ed48fb076172
  feat(balatro): bridge public tactical discard

5d8565b6910eb9c77b8342465dc404bd6a902840
  refactor(balatro): wire R4 tactical decision engine

652b32624ae2feaad9e768baac9f505b386bb271
  feat(balatro): own ordinary R4 play lifecycle

98ab566071f0af94305ffaba5b9fa0482e25b4ad
  feat(balatro): admit exact Tooth tactical play

f8bc7aabafcd766fd9bcada15e8bef489977d7a5
  feat(balatro): admit exact Hook tactical play

e9408fa943bbc2609f3ee96e53318ba2ff2c874c
  feat(balatro): record public tactical trajectory evidence

0603f420ee7f7d1f235c21b0ea9debc7b72442e5
  fix(balatro): freeze tactical evidence snapshots
```

The required R4 exit gate is representative ordinary + Boss tactical correctness and R5-safe trajectory evidence, not exhaustive admission of all 28 Boss Play paths. Unsupported Boss tactical paths remain intentionally excluded rather than blocking R4 closure.

## R4 exit criteria — SATISFIED

- deterministic tactical owner callable from headless `SELECTING_HAND` states;
- exact play/discard legality shared with canonical mechanics;
- tactical action transitions return to the correct next owner/state;
- representative ordinary + Boss tactical regressions green;
- no hidden-information leakage;
- no second tactical strategy implementation;
- tactical trajectory metadata sufficient for R5 comparison.

Do not reopen R4 solely to increase Boss coverage. Reopen only for a concrete R5 parity defect or a separately scoped mechanics expansion.

---

# R5 — live/simulator parity harness — IN PROGRESS

Required before treating the simulator as authoritative training truth.

## Completed infrastructure — green

- `PublicTacticalTransitionEvidence` is the canonical public tactical pre/action/post evidence type; no second tactical action schema exists.
- `games/balatro/env/parity.py` canonicalizes policy-visible state while removing engine-local identity fields.
- single-transition tactical comparison reports differences in `before`, `action.name`, `action.selected_hand_indices`, and `after`.
- `games/balatro/live/parity_capture.py` converts successful durable live run-log observation/decision/action-result rows into canonical tactical evidence and rejects malformed or mismatched tactical records rather than repairing them heuristically.
- ordered tactical trajectory comparison treats transition count and order as evidence; it never truncates one side to manufacture a match.
- durable live-log rows can now be compared directly against an ordered simulator evidence trajectory through the same canonical comparator.
- `PublicStrategicTransitionEvidence` is the canonical public strategic pre/action/post record and reuses the frozen R3 `EnvAction` vocabulary rather than inventing a second strategic action schema.
- successful supported live `BUY_JOKER` run-log transitions map the combined live shop `area_index` to the exact translated Joker slot and fail closed when the target cannot identify exactly one supported translated Joker.
- the supported `BUY_JOKER` regression now rebuilds `HeadlessRunState` directly from the translated live-before state, executes `ShopTransitionEngine` through `buy_joker_with_public_evidence`, and compares the resulting strategic evidence without copying/normalizing live before/after state into the simulator side.
- `games/balatro/live/joker_purchase_fixture.py` provides an offline opt-in preservation seam that selects one coherent settled `BUY_JOKER` boundary from the canonical public run log and writes the original `balatro-run-experience-v1` observation/decision/action-result rows unchanged; it creates no production-side action/evidence schema.
- exact integral live Joker price metadata is canonicalized at `LiveJokerFactory`, aligning Lua numeric values such as `4.0` with the headless integer-price contract while leaving non-integral prices fail-closed.
- `games/balatro/live/reroll_parity_checkpoint.py` captures coherent complete-SHOP public state plus exact private RNG/reroll replay authority and rejects active Tags, free rerolls, unobserved Voucher state, or unstable checkpoints rather than normalizing them away.
- exact ordinary paid `REROLL_SHOP` can be rebuilt from a private checkpoint and replayed through the canonical headless reroll owner; the comparator checks public transition evidence, previous/next reroll cost, and post-action RNG snapshot.
- `games/balatro/live/reroll_parity_capture.py` persists this private replay authority in an opt-in per-run sidecar. The normal durable run-experience JSONL remains public-only.
- the production live entry exposes `--reroll-parity-directory`. Capture failures and replay mismatches are diagnostic/observational only: they cannot suppress, rewrite, or falsely relabel a successfully settled production action.

Green checkpoints:

```text
7dd4f36341fd5624d05db2e7b59e808f81ceb5cd
  feat(balatro): add R5 tactical parity comparator

da7e4e9605d37584b116f28274bdb7fc91ac728a
  feat(balatro): adapt live run logs for R5 parity
GitHub Actions run 34005381429
GitHub Actions job 101411468974
2373 passed, 1595 deselected

0a657d961b13bac12371466418ff470c15e62a61
  feat(balatro): compare R5 tactical trajectories
GitHub Actions run 34005877151
GitHub Actions job 101412827495
2377 passed, 1595 deselected

e116bf09e0c13c6092dc57b7bc2dae5e7f9ee792
  feat(balatro): replay exact R5 shop reroll parity
GitHub Actions run 34022177202
GitHub Actions job 101456639275
2401 passed, 1595 deselected

b15fab5fe2bec0080c383a009dbef4f00cc89e12
  feat(balatro): capture live R5 reroll parity
GitHub Actions run 34024889806
GitHub Actions job 101463994146
2409 passed, 1595 deselected

99a4776ce8d01b47fb0a460cdc31d5ea63558b2e
  test(balatro): cover Telescope paid reroll parity state
GitHub Actions run 34213635015
GitHub Actions job 102020161503
2419 passed, 1595 deselected

606c7b4535176e92f9bc87192cc9a049670a0d6e
  fix(balatro): align paid reroll with live parity
9fbfe70386e3141c565cd07c655decd5194dd1cb
  test(balatro): align exact reroll regressions
GitHub Actions run 34217561085
GitHub Actions job 102032815831
2421 passed, 1595 deselected

7b1fb06f7a307a2ac2d0fec8613f18c6eaeeb79d
  fix(balatro): restore branch tree after launcher update
GitHub Actions run 34218019368
GitHub Actions job 102034289630
2427 passed, 1595 deselected

256d56baf36f0d5a32b9aabf827cbbdc2643c3f5
  feat(balatro): add Joker purchase parity evidence
adfa8458fbee9f6b51db0f7b8b25e8ab36d0c56c
  test(balatro): seed R5 joker purchase replay
0183d09d729dad15f72948be0326a10432ecea07
  test(balatro): complete R5 joker purchase fixture metadata
30b8ca49678f1826b92d8939d9337997d5275dbc
  test(balatro): replay R5 Joker purchase without normalization
8d6b64adc3ab2884d59e5d59a9d2a8f448f83ed5
  test(balatro): compare R5 purchase identity structurally
GitHub Actions run 34222351675
GitHub Actions job 102048209359
2431 passed, 1595 deselected

e2e4c23ea669283fc3991cc5bf6ad10920a22f9b
  test(balatro): replay real R5 Joker purchase fixture
6b93714d3ca496d6440be75f3b169e5b48b04cd3
  fix(balatro): normalize exact live Joker prices
a709b9c74e688f20ebaa82ba8fed5e02d2e231fa
  test(balatro): freeze exact live Joker price translation
GitHub Actions run 34229665010
GitHub Actions job 102072335608
2437 passed, 1595 deselected
```

The first real paid-reroll fixture,
`balatro-20260908T091943Z-e7a1ad15-attempt-001`, contains two settled
`REFRESH_SHOP` transitions. Its original verdicts exposed exact canonical
defects: the Joker pool seed omitted Ante, White Stake failed to consume the
unconditional `etperpoll{ante}` draw, visible Joker pool lifecycle was not
restored/suppressed across reroll, Planet shop pricing was doubled contrary to
pinned vanilla, live shop cards did not retain exact base cost, and parity
compared engine-local item classes instead of public shop identity/price.
Those owners were repaired at `606c7b45` and their exact regressions aligned at
`9fbfe703`. Replaying the unchanged two-row fixture now yields
`comparison.matches == true` for both transitions, including public state,
reroll-cost state, and post-action RNG.

Post-capture readiness repairs now own depleted-shop rerolls, exact Tarot/Planet
duplicate-suppression pool lifecycle, production publication of authoritative
consumable-generation catalogues, surfaced replay rejection causes, and explicit
Omen Globe/Telescope zero-effect capability at the ordinary base-shop/paid-reroll
boundary. These repairs do not constitute a live parity fixture.

The first real ordinary Joker-purchase fixture is repository-preserved from
`balatro-20260831T082151Z-78326f05-attempt-001`, sequences 47–49. It is the
original canonical public observation/decision/action-result boundary for buying
Juggler at combined shop `area_index=1`. The unchanged fixture rebuilds a
headless SHOP state, resolves canonical Joker slot 1, spends money 14 → 10,
moves Juggler from the shop into owned Jokers, leaves Crafty Joker in the shop,
and applies Juggler's exact acquisition effect `hand_size: 8 → 9`. Its first CI
replay exposed a translation inconsistency: Lua-extracted exact prices arrived as
numeric `4.0` while the headless contract correctly requires exact integer shop
prices. `LiveJokerFactory` now canonicalizes only integral numeric price metadata;
non-integral values remain unsupported rather than rounded. The unchanged real
fixture then passed canonical strategic parity at `a709b9c7`.

## Priority parity fixtures

- ordinary shop generation/purchase/reroll;
- Voucher redemption;
- blind start/clear;
- blind skip/Tag flow;
- representative Buffoon pack choice/skip;
- held Planet use;
- audited Joker sale;
- representative Bosses;
- RNG/shuffle/draw;
- owned-deck composition;
- economy transitions;
- tactical PLAY_CARDS/DISCARD_CARDS decisions and resulting state.

R5 compares canonical state/action/transition evidence, not screenshots or ad-hoc prose logs. Simulator-private physical draw order and RNG state remain private unless a fixture explicitly compares deterministic replay authority at the private simulator boundary; they are never leaked into policy-visible evidence.

## Exact next task

The representative ordinary shop reroll and Joker-purchase gates are green. Do
not request another reroll or purchase run for those same gates.

Continue R5 with **representative supported Voucher redemption parity**:

1. inspect the canonical production `BUY_VOUCHER` target/dispatch/settlement path,
   the live Voucher translation fields, the existing `PublicStrategicTransitionEvidence`
   adapter/comparator, and the exact headless Voucher redemption owners before editing;
2. search existing durable Red/White run evidence for one settled supported
   `BUY_VOUCHER` transition whose complete public before/action/after state is
   sufficient to rebuild the exact headless boundary; prefer an existing fixture
   over requesting a new Balatro run;
3. add the smallest canonical run-log adapter/preservation seam needed for
   `BUY_VOUCHER`, reusing the frozen R3 action vocabulary and strategic evidence
   schema rather than creating Voucher-specific action truth;
4. add focused deterministic regressions for exact live target → headless slot
   mapping, before/after preservation, supported redemption effects, and
   malformed/unsupported/mismatched fail-closed behavior at the owning boundary;
5. replay one preserved real supported Voucher purchase unchanged through the
   canonical headless `BUY_VOUCHER` owner and require public strategic parity;
6. push and require the GitHub Actions deterministic gate to pass;
7. request one live Voucher purchase only if no existing durable supported
   transition can satisfy the unchanged real-fixture replay gate.

Do not broaden this slice to unsupported Voucher centers, playing-card shop
purchases, Boss reroll, policy tuning, or another open-ended live batch.
`BUY_CARD` and `REROLL_BOSS` remain unavailable.

## R5 exit criteria

- one canonical comparator/evidence path per public transition family, reusing frozen production/R3 action identifiers;
- representative tactical Play/Discard parity passes on captured live evidence;
- representative strategic fixtures above pass on captured live evidence;
- mismatch output identifies the first differing state/action/transition field rather than only returning false;
- no hidden-information leakage into policy evidence;
- deterministic replay/private authority remains separate from public parity signatures;
- parity failures route back to the first wrong canonical owner rather than being normalized away.

---

# R6 — environment performance gate — NOT STARTED

Measure only after semantics and representative parity are correct:

- headless steps/sec;
- complete Red/White runs/minute;
- parallel scaling;
- tactical-bridge cost;
- serialization/restore overhead;
- deterministic replay overhead.

Do not trade exactness for throughput before this phase.

---

# Later phases

## O — observation/action encoding — NOT STARTED

- versioned public observation schema;
- versioned action schema/mask;
- no hidden-information leakage;
- illegal action probability exactly zero after masking;
- Bond-derived signals may be observations/features but not hard-coded strategic authority.

## B0 — RL baseline infrastructure — NOT STARTED

Before PPO:

1. random legal strategic baseline;
2. deterministic symbolic/headless baseline;
3. fixed seeded evaluation set;
4. unseeded evaluation set;
5. Ante reached / Ante 8 clear / survival/economy diagnostics;
6. promotion and regression thresholds defined before training results are observed.

## PPO — NOT STARTED

Do not begin until R-phase exactness, representative parity, performance, observation/action encoding, and baseline gates are satisfied.

Primary promotion metric remains:

**P(clear Ante 8 | Red Deck, White Stake, normal mode).**

Only after controlled Red/White promotion should higher stakes or additional decks become active development targets.