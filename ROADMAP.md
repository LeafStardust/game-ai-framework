# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Primary objective: **maximize P(clear Ante 8 | Red Deck, White Stake, normal mode)**.
- Work Chat runs deterministic/static tests itself where available; GitHub Actions is currently authoritative.
- User runs only validation that genuinely requires Windows/Balatro.
- Preserve exact mechanics, legality, boss rules, economy, public-information boundaries, and reproducible RNG.
- Prefer canonical ownership over rescue wrappers or approximations.
- Unsupported/inexact transitions stay absent from the training mask.
- Manual Bond coefficient tuning is retired as the primary competence path.
- Do **not** start PPO/observation training before the exactness/parity gates.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, or `--five`; retain the canonical attempt-count interface.

---

# Completed foundation

## A–K — symbolic/mechanical foundation — COMPLETE AS BASELINE

Retain deterministic mechanics/state/legality/tactical execution, Bond features, `BuildValue` / `StrategyDelta`, telemetry, and motifs as baselines/features. Do not resume manual strategy tuning as the primary path.

## L — live stabilization — COMPLETE

Historical validation batches are preserved in project docs. L3 froze the environment contract:

```text
BALATRO_ENV_CONTRACT_VERSION = "l3-v1"
CI 33758680261: 1223 passed, 1594 deselected
```

Do not request another open-ended live batch at this stage.

## R0 — headless environment architecture — COMPLETE

Authoritative environment: `games/balatro/env/`.

- deterministic reset/step/legal-actions facade
- canonical `BalatroState`
- serialization/restore and illegal-action rejection boundary
- CI `33760179448`: `1233 passed, 1594 deselected`

Legacy `games/balatro/environment.py` is not authoritative RL environment truth.

---

# Phase R — exact headless Balatro environment — ACTIVE

The simulator is not authoritative game truth until R5 live/simulator parity passes.

## R1 — deterministic state/acquisition transitions — SUBSTANTIALLY COMPLETE; OPEN LIFECYCLES REMAIN

### Acquisition contract

Generic acquisition is not “append inventory + subtract money.” Every persistent consequence must be exact.

Current hard fail-closed surfaces:

- Joker editions, especially Negative
- unknown/unaudited Joker identities
- generic voucher acquisition
- packs until exact pack/RNG state exists
- `SELL_JOKER` until inverse lifecycle effects exist
- malformed/noninteger prices

Exact resource-sensitive Joker acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

The large audited inventory-only scoring/rule/retrigger acquisition set remains green, including Four Fingers/Pareidolia/Shortcut/Smeared/Splash, hand-shape groups, suit groups, Scary Face/Arrowhead/Onyx Agate/Flower Pot/Seeing Double, Joker Stencil/Shoot the Moon/Triboulet, Bull/Bootstraps, and Dusk/Hack/Hanging Chad/Mime/Sock and Buskin.

### Permanent owned deck — GREEN

Exact deck-dependent Jokers:

```text
Steel Joker
Stone Joker
Driver's License
Erosion
```

Authority rules:

- permanent deck truth comes from `G.playing_cards`
- **never** substitute `G.deck.cards`
- translation is all-or-nothing
- malformed/count-mismatched cards make `owned_deck = None`
- low-level LuaJIT TValue failures cannot silently shorten the authoritative deck

Key gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Private deterministic state also validates exact card zones, seed type, tags, pack container shape, and round-reset baselines.

---

## R2 — RNG + exact round/blind lifecycle — ACTIVE / CURRENT PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

Balatro keyed pseudohash/pseudoseed over LuaJIT combined Tausworthe `math.random`; never Python `random`.

Commits `2e61cd8`, `290ff11`.
CI `33791671797`: **1432 passed, 1594 deselected**.

### R2.2 — pseudoshuffle — GREEN

One keyed pseudoseed advance, then one LuaJIT RNG stream drives Fisher–Yates.

Commits `246f442`, `d9662c6`.
CI `33791916289`: **1435 passed, 1594 deselected**.

### R2.3 — playing-card creation order + headless RNG ownership — GREEN

Exact private order is reconstructable only from:

1. unique integer live `playing_card` IDs; or
2. the untouched vanilla one-of-each 52-card deck.

Unprovable order fails closed. No fake public `sort_id` is introduced.

Relevant commits: `e7b0bb0`, `2a26e79`, `34d88e9`, `7c070b2`, `2dc47eb`, `0a7f845`, `eed926e`.
CI `33795507133`: **1461 passed, 1594 deselected**.

### R2.4 — exact complete-deck shuffle/deal — GREEN FOR SUPPORTED COMPLETE DECKS

Pristine implementation: `61ec993`, `2d37016`.
Generalized implementation:

```text
fa6c40e  retain original suit nominal for vanilla Card:get_nominal
1f35a5c  generalize exact complete owned-deck round-start deal
```

`deal_supported_round_start()` requires authoritative complete deck composition, exact object identity, exact retained creation order, and original-suit nominal where needed. Hidden physical draw order remains private; public remaining deck is canonicalized.

Pinned `TESTSEED` first hand remains:

```text
A Hearts, K Hearts, Q Diamonds, 9 Spades,
9 Clubs, 5 Clubs, 5 Diamonds, 4 Clubs
```

### R2.5 — round bonuses/resources — GREEN

Private signed one-shot fields:

```text
round_bonus_hands
round_bonus_discards
```

Vanilla baseline:

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

Bonuses are consumed only after blind setup / `setting_blind` Joker processing.

Commits `906719d`, `d727221`, `58ac3cc`, `bd07ffe`.
CI `33796637904`: **1479 passed, 1594 deselected**.

### R2.6 — `setting_blind` Joker lifecycle / Burglar — GREEN FOR AUDITED IDENTITIES

Burglar:

```text
hands += 3
discards_remaining = 0
```

Source order:

```text
round resource baseline
→ Boss set_blind mutation
→ audited Joker setting_blind pass
→ consume one-shot round bonuses
```

All currently R1-admitted identities are explicitly classified at this trigger; unknown lifecycle identities fail closed.

CI `33797436606`: **1483 passed, 1594 deselected**.

### R2.7 — first-round counter parity — GREEN

Vanilla `G.GAME.round` begins at `0`; selecting the first blind queues `ease_round(1)` before `new_round()`. First start is therefore `0 → 1`.

CI `33797071526`: **1482 passed, 1594 deselected**.

### R2.8 — Small/Big Blind start — GREEN

`prepare_supported_nonboss_blind_start()` owns:

```text
BLIND_SELECT
→ round += 1
→ blind requirement
→ round-resource baseline
→ audited setting_blind Jokers
→ consume bonuses
→ DRAW_TO_HAND
```

`start_supported_nonboss_blind()` composes this with exact generalized shuffle/deal.

Constraints remain: no active tags, no vouchers, exact reset allowances, empty transition zones, unclassified Joker identities rejected.

Key gates:

```text
33797587142  1492 passed, 1594 deselected
33798795353  1497 passed, 1594 deselected
```

### R2.9 — Boss blind-start lifecycle — ACTIVE

Bosses must be admitted by exact source-audited start semantics, not display text.

#### R2.9a — requirement-only Bosses — GREEN

Audited set:

```text
The Wall
Violet Vessel
```

Neither has an explicit `Blind:set_blind` start mutation nor a card-debuff rule; the enlarged requirement is already represented by authoritative `Blind.requirement`.

Wall commits: `4f5b476`, `e3f1bd5`, validation-contract fix `7c27802`.
Wall CI `33799302675`: **1502 passed, 1594 deselected**.

Requirement-only generalization:

```text
8980579  admit explicit {The Wall, Violet Vessel} start allowlist
a1214f2  pin requirement-only Boss tests
```

Violet Vessel CI `33799746434`: **1509 passed, 1594 deselected**.

Every other Boss remains rejected by this path.

#### R2.9b — mutable hand-rule Bosses — GREEN

Audited set:

```text
The Eye
The Mouth
```

Vanilla `Blind:set_blind` initializes these after the resource baseline and before Joker `setting_blind`:

- Eye: empty per-hand-used table
- Mouth: no hand locked yet

Canonical state represents this exactly as:

```text
boss_blind_state_observed = True
boss_blind_hands = set()
boss_blind_only_hand = None
```

Implementation:

```text
0594735  own Eye/Mouth start state and source ordering
42bb495  pin stale-state replacement, Burglar/bonus ordering,
         exact deal composition, identity rejection, tag/voucher rejection
```

CI `33800243393`: **1518 passed, 1594 deselected**.

#### R2.9c — resource-mutating Bosses — NEXT

Next candidates:

```text
The Water
The Needle
```

Vanilla start behavior:

```text
Water:
  discards_sub = current_round.discards_left
  ease_discard(-discards_sub)

Needle:
  hands_sub = round_resets.hands - 1
  ease_hands_played(-hands_sub)
```

Important: vanilla stores `discards_sub` / `hands_sub` because `Blind:disable()` restores them. Therefore do **not** implement these Bosses by only changing public resource counts. First add validated simulator-private reversible Boss adjustment state, then implement exact start ordering and later disable/cleanup semantics.

Manacle also requires reversible hand-size ownership. Amber Acorn requires exact Joker flipping/shuffling RNG. Card/Joker-debuff Bosses require exact debuff application. These remain blocked.

### Current R2 fail-closed boundary

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

Burglar purchase remains **FAIL-CLOSED** even though its Small/Big, requirement-only Boss, and Eye/Mouth start effects are now owned. A purchased Burglar persists into all Bosses, so full supported Boss-start coverage is required before admitting it as run-safe.

Still high-priority/unowned:

- Water/Needle reversible resource state and start lifecycle
- Manacle reversible hand-size lifecycle
- other Boss card/Joker debuffs and mutable states
- Amber Acorn RNG/Joker order
- prior-round zone cleanup for all supported trajectories
- active tag effects
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG
- remaining modeled random effects

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Target actions include `END_SHOP`, reroll/buy/sell/use/pack actions, `SKIP_BLIND`, and `SELECT_BLIND`.

Every training-visible action needs exact legality, exact transition, stable serialization, and mask representation.

**Do not expose `SELECT_BLIND` yet.**

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity — NOT STARTED

Priority parity fixtures include shop transitions, blind skip/start/clear, Boss restrictions, lifecycle-sensitive Jokers, owned-deck composition, economy, and RNG/shuffle/initial draw.

## R6 — performance gate — NOT STARTED

Measure throughput only after correctness/parity.

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
V   simulator→live learned-policy validation
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

# Deterministic CI contract

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

No local clone is assumed in Work Chat; never claim local pytest unless a real local runtime exists.

---

# Current exact checkpoint

```text
A–K symbolic/mechanical baseline                  COMPLETE
L live stabilization                             COMPLETE
R0 environment architecture                      COMPLETE
R1 deterministic state/acquisition               SUBSTANTIALLY COMPLETE
R2 exact RNG / round start                       ACTIVE
R2.1 LuaJIT RNG                                  GREEN — CI 33791671797
R2.2 pseudoshuffle                               GREEN — CI 33791916289
R2.3 creation order / private RNG                GREEN — CI 33795507133
R2.4 complete-deck exact deal                    GREEN
R2.5 round resources / bonuses                   GREEN — CI 33796637904
R2.6 Burglar setting_blind                       GREEN — CI 33797436606
R2.7 first round 0→1                             GREEN — CI 33797071526
R2.8 Small/Big start + deal                      GREEN — CI 33798795353
R2.9a Wall + Violet Vessel                       GREEN — CI 33799746434
R2.9b Eye + Mouth                                GREEN — CI 33800243393
R2.9c Water + Needle reversible resource state   NEXT
SELECT_BLIND                                      NOT EXPOSED
Burglar acquisition                              FAIL-CLOSED
Generic/unknown acquisitions                     FAIL-CLOSED
Joker editions                                   FAIL-CLOSED
Generic vouchers/packs                           FAIL-CLOSED
SELL_JOKER                                       FAIL-CLOSED
R4 tactical bridge                               NOT STARTED
R5 parity                                        NOT STARTED
R6 performance                                   NOT STARTED
Observation/PPO                                  NOT STARTED
```

Current branch code head immediately before this roadmap synchronization:

```text
42bb495983cacdb23fb18f17024ef2b2415fcc0b
```

---

# Exact next development action

**Continue R2 Boss-start lifecycle. Do not start PPO/observation training.**

Immediate order:

1. add validated private reversible Boss resource fields for Water/Needle (`discards_sub`, `hands_sub` equivalents);
2. prove copy/validation/isolation for those hidden fields;
3. implement Water and Needle source ordering after baseline and before `setting_blind` Jokers;
4. pin Burglar interactions and exact deal composition;
5. add exact disable/restore semantics before treating these Bosses as lifecycle-complete;
6. then handle Manacle and remaining Boss debuff/RNG groups separately;
7. keep tags, vouchers, editions, packs, unknown acquisitions, sell effects, and `SELECT_BLIND` fail-closed until exact;
8. add R5 live/simulator parity before declaring the environment authoritative for training.

Controlling environment question:

> **Does the environment expose the same public Balatro problem and exact legal consequences that the live agent faces?**

Controlling learned-strategy question:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
