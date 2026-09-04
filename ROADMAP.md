# ROADMAP — SINGLE SOURCE OF TRUTH

Authoritative roadmap for Balatro Red Deck / White Stake competence on `LeafStardust/game-ai-framework`, branch `feat/v1.0-red-white-competence`.

## Non-negotiable contract

- Objective: **maximize P(clear Ante 8 | Red Deck, White Stake, normal mode)**.
- Preserve exact Balatro mechanics, legality, Boss rules, economy, public-information boundaries, and seeded RNG.
- Unsupported/inexact transitions stay absent from the training mask.
- Prefer canonical ownership over rescue wrappers or approximations.
- Manual Bond tuning is retired as the primary competence path.
- Do **not** start PPO/observation training before exactness + parity gates.
- Work Chat runs deterministic/static validation itself; GitHub Actions is authoritative when no local clone exists.
- Ask the user only for validation that genuinely requires Windows/Balatro.
- Never substitute `G.deck.cards` for permanent owned-deck truth; permanent deck source is `G.playing_cards`.
- Do not reintroduce legacy attempt flags such as `--one`, `--three`, `--five`; retain the canonical attempt-count interface.
- Face-down card identity is **not public information**. Headless simulation may retain true identity internally for exact mechanics, but policy observations must mask it. Do not give the production/training agent an oracle/cheat view. Any future oracle mode must be explicit debug-only tooling.

## Development procedure — REQUIRED FOR CONTINUATION WORK

This section records the working procedure used by Work Chat so future sessions do not fall back to slower or less reliable habits.

### 1. Start from the repository, not chat memory

For every continuation session:

1. read the current `ROADMAP.md` first;
2. verify the current branch/head before editing;
3. inspect the canonical owner(s) for the next roadmap task;
4. check for intervening commits before writing;
5. treat chat summaries as navigation aids only — repository state is authoritative.

Target branch for this competence path:

```text
feat/v1.0-red-white-competence
```

`ROADMAP.md` is the single source of truth for phase status, blockers, next work, and validation state. Keep it synchronized whenever a completed slice materially changes any of those.

### 2. Implement in small exact slices

For each mechanics/state/lifecycle slice:

1. audit vanilla/source behavior and existing production owners;
2. classify the exact missing ownership boundary;
3. patch the canonical owner rather than adding a rescue wrapper;
4. add focused deterministic regression(s), including rejection/fail-closed behavior where relevant;
5. keep unsupported composition absent rather than approximating it;
6. run the deterministic CI gate;
7. inspect the actual pytest result and selection count;
8. only then mark the slice GREEN and synchronize the roadmap.

Do not bulk-admit Jokers/actions merely because a nearby class is supported. Each acquisition/lifecycle consequence must be audited for counters, RNG, economy, card mutation, sell/destruction behavior, and other persistent state.

### 3. Source-audit rule

When exact Balatro behavior is unclear, trace the pinned vanilla implementation or the repository's already-validated canonical implementation before coding. Do not infer mechanics from names, UI behavior, memory, wiki prose, or Python convenience semantics when source-exact behavior is available.

Current source audits have used the vanilla Balatro source mirror at pinned commit:

```text
GladdonT/balatro-source-code
895ab3a25bc6f513fa80885eb59951bf8e76bc55
```

If the source reference changes, record the new pin before depending on it for deterministic parity work.

### 4. Fail-closed rule

If exactness cannot be proved at the modeled boundary:

- reject the transition/action;
- omit it from the training mask;
- preserve `None`/unobserved state where applicable;
- do not silently substitute a related public field;
- do not add synthetic state solely to make a transition convenient unless that state is source-justified and its lifecycle is owned.

Examples already enforced:

- permanent owned deck is `G.playing_cards`, never `G.deck.cards`;
- partial LuaJIT array reads make owned-deck observation unavailable rather than shorter;
- future physical draw order remains private;
- face-down identity remains masked from policy observations;
- Python `random` is not a substitute for Balatro/LuaJIT RNG.

### 5. Deterministic pytest procedure — GITHUB ACTIONS IS THE WORK CHAT GATE

Work Chat does **not** ask the user to pull the branch and run deterministic pytest when GitHub Actions can run it. The authoritative workflow is:

```text
.github/workflows/balatro-l3.yml
```

It runs on pushes to `feat/v1.0-red-white-competence` affecting Balatro/tests/roadmap/workflow paths and executes:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

Required procedure after a relevant push:

1. locate the workflow run for the exact commit/head;
2. wait for the `balatro-deterministic-tests` job to complete;
3. require workflow/job conclusion `success`;
4. inspect the job log's final pytest line;
5. record the exact `passed` and `deselected` counts when reporting a gate;
6. confirm the intended new test family was selected by the `-k` expression;
7. if new tests were deselected, fix CI selection and rerun before calling the slice GREEN.

A green workflow badge alone is **not sufficient evidence**. Historical example: the first R2 card-order workflow succeeded while six `env_r2` tests were deselected; the workflow selector was then corrected to include `env_r2`, and only the corrected run counted as the gate.

Do not claim local pytest ran unless there is an actual local repository/runtime in the current environment. GitHub Actions is the default deterministic test executor for Work Chat when no local clone exists.

### 6. Commit/push procedure

The user has authorized pushing completed commits to the remote branch. Therefore:

- push coherent completed implementation/test/doc slices without asking for repeated permission;
- prefer separate implementation and focused regression commits when useful for auditability;
- do not claim a push/commit exists without GitHub evidence;
- do not stack large unrelated changes behind an unverified mechanics gate;
- synchronize `ROADMAP.md` after green checkpoints so another session can resume exactly.

### 7. Live Balatro validation procedure

Do **not** ask the user to run Balatro for deterministic/static questions that CI can answer.

Request a Windows/live Balatro run only when the remaining uncertainty genuinely depends on live game integration, memory observation, runtime parity, UI/execution behavior, or another condition that cannot be established from source + deterministic tests. When a live run is needed, state exactly what evidence/run is required rather than requesting an open-ended batch.

Current standing instruction: **no open-ended live batch** unless a later roadmap gate explicitly requires one.

### 8. Scope discipline

- Follow the roadmap's current primary workstream; do not pivot back to Bond coefficient tuning.
- Do not start PPO/observation training before the roadmap gates permit it.
- Do not reintroduce retired legacy attempt flags; use the canonical attempt-count interface.
- If context becomes insufficient to continue safely, stop rather than guessing or performing an ungrounded large change. Resume from repository + roadmap state in the next session.

---

# Completed foundation

```text
A–K symbolic/mechanical baseline      COMPLETE
L live stabilization                 COMPLETE
R0 headless environment architecture COMPLETE
```

L3 contract: `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`.

Key historical gates:

```text
33758680261  1223 passed, 1594 deselected
33760179448  1233 passed, 1594 deselected
```

Do not request another open-ended live batch at this stage.

---

# Phase R — exact headless Balatro environment — ACTIVE

The simulator is not authoritative game truth until R5 live/simulator parity passes.

## R1 — deterministic state/acquisition — SUBSTANTIALLY COMPLETE

Generic acquisition is not “append inventory + subtract money.” Persistent consequences must be exact.

Exact resource-sensitive acquisitions:

```text
Juggler      hand_size += 1
Stuntman     hand_size -= 2
Drunkard     round_reset_discards += 1
Troubadour   hand_size += 2; round_reset_hands -= 1
Merry Andy   hand_size -= 1; round_reset_discards += 3
```

The audited inventory-only score/rule/retrigger Joker set is owned incrementally in `ShopTransitionEngine`, including passive-rule, hand-shape, suit, conditional, money, owned-deck, and retrigger groups.

Permanent-deck authority:

- `G.playing_cards` only;
- all-or-nothing observation/translation;
- partial LuaJIT/TValue reads fail closed;
- malformed/count-mismatched cards make `owned_deck = None`;
- Steel Joker, Stone Joker, Driver's License, and Erosion are exact-gated on permanent owned deck.

Key R1 hardening gates:

```text
33788603611  1401 passed, 1594 deselected
33789894797  1405 passed, 1594 deselected
33790592775  1424 passed, 1594 deselected
```

Still fail closed:

- unknown/unaudited Joker acquisitions;
- Joker editions, especially Negative;
- generic voucher acquisition;
- packs until exact RNG/pack state exists;
- `SELL_JOKER` until inverse lifecycle effects exist;
- malformed/noninteger prices.

---

## R2 — RNG + round/blind/Boss lifecycle — ACTIVE / CURRENT PRIMARY WORKSTREAM

### R2.1 — Balatro/LuaJIT RNG — GREEN

Keyed pseudohash/pseudoseed over LuaJIT combined Tausworthe RNG; never Python `random`.

```text
2e61cd8  RNG primitives
290ff11  pinned vectors
CI 33791671797: 1432 passed, 1594 deselected
```

### R2.2 — pseudoshuffle — GREEN

One keyed pseudoseed advance, then one LuaJIT RNG stream drives Fisher–Yates.

```text
246f442  pseudoshuffle
d9662c6  vectors
CI 33791916289: 1435 passed, 1594 deselected
```

### R2.3 — playing-card creation order/private RNG — GREEN

Exact order only from unique integer live `playing_card` IDs or untouched vanilla one-of-each 52-card structure. Otherwise fail closed. No fake public `sort_id`.

```text
CI 33795507133: 1461 passed, 1594 deselected
```

### R2.4 — complete-deck exact shuffle/deal — GREEN FOR SUPPORTED DECKS

`deal_supported_round_start()` owns exact physical shuffle/deal while public `deck` remains canonicalized and does not reveal future order. `draw_one_supported_card_to_hand()` uses only an already-owned private physical draw pile.

```text
CI 33803629167: 1563 passed, 1594 deselected
```

### R2.5 — round resources/one-shot bonuses — GREEN

```text
hands_remaining    = max(1, round_reset_hands + round_bonus_hands)
discards_remaining = max(0, round_reset_discards + round_bonus_discards)
```

Bonuses are consumed before Boss `set_blind` and Joker `setting_blind` effects.

```text
CI 33804894982: 1593 passed, 1594 deselected
```

### R2.6 — Burglar `setting_blind` — GREEN FOR AUDITED STARTS

```text
hands += 3
discards_remaining = 0
```

Unknown lifecycle Jokers fail closed. Burglar acquisition remains fail-closed because a bought Burglar persists into future arbitrary lifecycle states.

### R2.7 — first-round parity — GREEN

Vanilla `G.GAME.round` initializes at 0 and first select-blind queues `ease_round(1)` before `new_round()`.

```text
CI 33797071526: 1482 passed, 1594 deselected
```

### R2.8 — Small/Big Blind start — GREEN

```text
CI 33798795353: 1497 passed, 1594 deselected
```

### R2.9 — Boss lifecycle — ACTIVE

Owned Boss slices:

```text
Wall + Violet Vessel            requirement-only             GREEN  CI 33799746434
Eye + Mouth                     mutable hand-rule             GREEN  CI 33800243393
Water + Needle                  reversible resources         GREEN  CI 33801195935
Manacle                         reversible hand size         GREEN  on owned boundaries
Goad/Window/Head/Club           static suit card debuffs     GREEN  CI 33803874842
Plant                           face-card debuffs             GREEN  CI 33804343818
pseudorandom_element            source-exact selection       GREEN  CI 33805699954
Cerulean Bell                   forced-selection lifecycle   GREEN  CI 33806527436
Psychic                         downstream hand rejection    GREEN  CI 33838722781
Flint                           downstream base-score halve  GREEN  CI 33838934769
Tooth                           -$1 per played card           GREEN  CI 33839102154
Hook                            keyed forced discards         GREEN  CI 33839910429
Ox                              matching hand -> money = 0   GREEN  CI 33841056452
Arm                             level > 1 -> level - 1       GREEN  CI 33841056452
Serpent                         post-action 3-card draw       GREEN  CI 33843165212
House + Mark                    deterministic card facing    GREEN  CI 33845952545
Wheel                           keyed per-draw card facing    GREEN  CI 33846232884
Fish                            temporal post-play facing     GREEN  CI 33846610717
```

#### Start-inert Boss family — GREEN

Current audited members:

```text
The Psychic
The Flint
The Tooth
The Hook
The Ox
The Arm
The Serpent
```

They have no additional `Blind:set_blind` / initial `Blind:drawn_to_hand` mutation; downstream effects are owned separately.

#### Hook exact semantics

At `Blind:press_play`:

1. player-selected play cards are already excluded from candidates;
2. choose up to two remaining hand cards using keyed `pseudorandom_element(..., "hook")` semantics;
3. remove first candidate before second selection;
4. move forced cards to discard;
5. do not decrement discard allowance;
6. do not draw replacements;
7. preserve exact RNG state.

Current narrow Hook implementation fails closed when unowned Joker/seal discard triggers would fire.

#### Ox exact semantics

- authoritative fixed target is `G.GAME.current_round.most_played_poker_hand`;
- process-memory observer exposes that public field;
- translator canonicalizes live names, e.g. `"Pair"` → `PAIR`;
- headless owner uses `BalatroState.round_most_played_hand` and **never recomputes** from mutable counts;
- match sets money exactly to `0`, including from negative money;
- missing/invalid target fails closed.

Relevant commits:

```text
0940a54  Ox headless economy
5eb7964  Ox regressions
226f148  observe live Ox round target
e11ac21  live observer/translator regressions
5169f7f  classify Ox start-inert
6a4a726  Ox start-inert tests
```

#### Arm exact semantics

Vanilla `Blind:debuff_hand` decrements the classified hand level only when level > 1. Canonical scoring already derives base Chips/Mult from `BalatroState.hand_levels`, so no duplicate Chips/Mult state is required.

Relevant commits:

```text
706173b  Arm hand-level decrement
6ab2683  Arm downstream regressions
735c181  classify Arm start-inert
a62b53a  Arm start-inert regressions
```

#### Serpent exact semantics

Vanilla `draw_from_deck_to_hand` overrides ordinary free-hand-capacity draw after at least one play or discard while The Serpent is enabled:

```text
draw_count = min(#remaining_deck, 3)
```

The dedicated headless owner:

- uses authoritative current-round play/discard history;
- uses the private physical draw pile and never leaks future order;
- may grow the hand above nominal hand capacity, as vanilla does;
- re-sorts the resulting hand using the exact owned-card sort boundary;
- consumes no RNG;
- fails closed for unknown history, private/public deck mismatch, wrong phase, wrong Boss, or disabled Serpent;
- composes with the audited start-inert Boss start and exact initial shuffle/deal.

Relevant commits:

```text
3a72e25  Serpent post-action draw owner
dbe52d8  Serpent downstream regressions
592081d  classify Serpent start-inert
fca90dc  start-inert family regression
723c8a5  composed start -> play-history -> Serpent draw regression
```

Current Serpent-composed gate:

```text
CI 33843165212: 1675 passed, 1594 deselected
```

### R2.10 — face-down / facing state ownership — GREEN FOR HOUSE/WHEEL/MARK/FISH

Canonical card state now includes authoritative facing without exposing hidden identity to the policy:

```text
BalatroCard.face_down
BalatroCard.facing_observed
```

Live/process-memory path:

- observer reads authoritative card facing;
- translator maps exact `front`/`back` state;
- malformed/unobserved facing remains explicit rather than guessed.

Policy/public observation path:

- internal simulator retains the true card object because exact game mechanics need it;
- a face-down hand card is copied into the policy observation with rank/suit and hidden modifiers masked;
- `live_id` is removed from the policy-facing hidden card;
- `forced_selection` remains visible because the game visibly forces the card;
- future physical draw order remains private.

Facing groundwork commits:

```text
eea5d32  track authoritative card facing observation
41db70f  cover live facing translation
ed1c449  translate authoritative card facing
```

#### The House — GREEN

Source semantics:

- initial hand stays face down while `hands_played == 0` and `discards_used == 0`;
- after any play or discard, newly drawn cards are face up;
- existing hidden cards are not retroactively revealed merely because history advanced;
- disable/defeat flips remaining hidden hand cards face up.

Implemented via canonical current-round play/discard history; unknown history fails closed.

#### The Mark — GREEN

Source semantics:

- each drawn face card stays face down;
- Boss face classification honors Pareidolia;
- debuff state does not suppress face classification at this Boss boundary;
- disable/defeat flips remaining hidden hand cards face up.

House/Mark commits and gate:

```text
6bca6c2  deterministic House/Mark facing owner
55df7ea  House/Mark regressions
CI 33845952545: 1686 passed, 1595 deselected
```

#### The Wheel — GREEN ON NORMAL-PROBABILITY BOUNDARY

Source semantics:

```text
for each physical card drawn to hand:
    face_down = pseudorandom(pseudoseed("wheel")) < probabilities.normal / 7
```

Exactness requirements:

- one keyed `wheel` RNG advance per **physical drawn card**;
- assignment happens before final hand sort;
- identical seed/state replays identically;
- hidden identity is masked only in policy/public observation;
- disable/defeat flips remaining hidden cards face up.

Current blind-start Joker ownership does not admit probability-modifying Jokers such as Oops! All 6s, so Wheel is exact at `probabilities.normal == 1`. Such unsupported composition fails closed rather than silently using the wrong probability.

Implementation reconstructs only the physical creation-order indices of the already-deterministic initial draw by replaying `nr{ante}` shuffle on an isolated copy, then consumes the returned run's independent keyed `wheel` RNG in that physical sequence. No future draw order leaks publicly.

```text
deb5ba1  Wheel facing RNG lifecycle
757cb27  Wheel per-card RNG regressions
CI 33846232884: 1692 passed, 1595 deselected
```

#### The Fish — GREEN

Source temporal semantics:

```text
set_blind:      prepped = nil
initial draw:   face up
press_play:     prepped = true
post-play draw: newly drawn cards face down
drawn_to_hand:  prepped = nil
post-discard:   newly drawn cards face up
```

The headless environment does **not** invent a persistent `fish_prepped` flag. Vanilla's flag exists only between `press_play` and the immediately following draw, so the simulator owns that effect atomically at the stable post-play draw boundary.

Owned behavior:

- initial Fish hand is authoritatively face up;
- ordinary capacity-limited post-play replacements are face down;
- ordinary post-discard replacements are face up;
- only newly drawn cards change facing, so older hidden cards can remain hidden;
- true identity remains internal and policy observation masks hidden cards;
- no RNG is consumed;
- action-history evidence is required; unknown/impossible timing fails closed;
- disable/defeat flips remaining hidden hand cards face up.

```text
a0beb66  Fish temporal facing owner
41af2ec  Fish facing regressions
CI 33846610717: 1700 passed, 1595 deselected
```

### NEXT R2 WORK — THE PILLAR / PERMANENT PLAYED-THIS-ANTE STATE

The next structural Boss blocker is **The Pillar**.

Vanilla semantics depend on each permanent playing card's persistent:

```text
card.ability.played_this_ante
```

A Pillar-active card is debuffed iff it has been played earlier in the current Ante. This is not a Boss-local counter and must not be approximated from current hand/discard zones.

Next implementation order:

1. audit every vanilla write/reset site for `played_this_ante` and its exact Ante boundary;
2. add the minimum canonical permanent-card state + an explicit observation/exactness bit if required;
3. wire `G.playing_cards` process-memory observation and translator fail-closed semantics;
4. update headless accepted-play lifecycle so played permanent cards set the flag in source order;
5. reset the flag exactly when vanilla advances/clears the Ante state;
6. implement Pillar's debuff projection/start lifecycle from that authoritative state;
7. cover live translation, headless mutation/reset, Pillar debuff, copy/isolation, and malformed/unobserved state;
8. keep policy observations public-information safe — `played_this_ante` is public deck history, but do not expose unrelated hidden card identity.

### Current hard blockers / later Boss categories

- Pillar — **NEXT**, persistent per-card `played_this_ante` history
- Verdant Leaf — all-card debuff + Joker-sale lifecycle
- Amber Acorn — Joker flip + seeded Joker-order shuffle
- Crimson Heart — per-hand random Joker debuff lifecycle
- Chicot composition, especially pre-deal Manacle
- prior-round arbitrary zone cleanup
- active tags
- voucher blind-start effects
- shop/reroll RNG
- pack RNG/state
- boss-selection RNG

`SELECT_BLIND` remains **PLANNED / NOT TRAINING-EXPOSED**.

---

## R3 — typed strategic action vocabulary — PARTIAL / TIED TO EXACTNESS

Every training-visible action requires exact legality, transition, serialization, and mask representation. `SELECT_BLIND` remains hidden until R2/R3 exact ownership is broad enough.

## R4 — deterministic tactical bridge — NOT STARTED

Reuse existing deterministic hand/discard tactical owners while RL initially controls strategic run development.

## R5 — live/simulator parity — NOT STARTED

Priority fixtures: shop paths, blind skip/start/clear, Boss restrictions, lifecycle-sensitive Jokers, owned deck, economy, RNG/shuffle/draw/facing parity.

## R6 — performance gate — NOT STARTED

Measure throughput only after semantics/parity are correct.

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

Authoritative Work Chat workflow:

```text
.github/workflows/balatro-l3.yml
```

Command:

```bash
python -m pytest -q tests/balatro -k "translator or mechanics or legality or shop or target_hand or joker or voucher or pack or consumable or arbiter or boss or rng or env_contract or env_r0 or env_r1 or env_r2"
```

A deterministic gate is valid only when the exact pushed head's Actions job succeeds **and** the job log confirms the intended tests were selected and gives the final pytest pass/deselect counts. Do not infer coverage from workflow success alone.

No local clone is assumed in Work Chat; never claim local pytest unless a real local runtime exists. Do not ask the user to run deterministic pytest that this workflow can run.

---

# Current exact checkpoint

```text
R1 deterministic state/acquisition     SUBSTANTIALLY COMPLETE
R2 RNG / round / Boss lifecycle        ACTIVE
R2 start-inert family                  GREEN THROUGH SERPENT
R2 Hook downstream                     GREEN — CI 33839910429
R2 Ox downstream + live target         GREEN — CI 33841056452
R2 Arm downstream                      GREEN — CI 33841056452
R2 Serpent downstream + composition    GREEN — CI 33843165212
R2 public facing schema/live wiring    GREEN
R2 House + Mark facing                 GREEN — CI 33845952545
R2 Wheel facing RNG                    GREEN — CI 33846232884
R2 Fish temporal facing                GREEN — CI 33846610717
NEXT                                   PILLAR / PLAYED_THIS_ANTE STATE
SELECT_BLIND                           NOT EXPOSED
Burglar acquisition                    FAIL-CLOSED
Generic/unknown acquisitions           FAIL-CLOSED
Joker editions                         FAIL-CLOSED
Generic vouchers/packs                 FAIL-CLOSED
SELL_JOKER                             FAIL-CLOSED
R4 tactical bridge                     NOT STARTED
R5 parity                              NOT STARTED
R6 performance                         NOT STARTED
Observation/PPO                        NOT STARTED
```

Current branch code head immediately before this roadmap procedure synchronization:

```text
41af2ecd201a882e429baae5a4b3fcddf9fdd0ca
```

The next code written should therefore be **exact permanent-card `played_this_ante` ownership and The Pillar lifecycle**. It should **not** be Bond tuning, PPO, or an approximation that derives persistent Ante history from current card zones.
