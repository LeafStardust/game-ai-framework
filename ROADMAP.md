# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

The project has pivoted from a hand-authored Bond-value strategy toward a reinforcement-learning (RL) strategy trained in a fast, deterministic Balatro environment. The existing deterministic mechanics, state translation, legality, tactical execution, candidate projection, telemetry, and Bond feature work remain valuable foundations. The old plan to manually tune Bond weights until competence emerges is retired.

---

# Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- Work Chat runs all deterministic/static tests itself in its isolated repository environment and keeps output quiet (`.venv/bin/python -m pytest -q` plus focused failure inspection).
- The user runs only actual Balatro gameplay or validation that genuinely requires the user's Windows/game environment.
- Do not ask the user to pull and run pytest when Work Chat can execute the test.
- Commands genuinely requiring the user's environment must begin with `git pull` and be PowerShell-compatible.
- Preserve exact mechanics, legality, boss rules, affordability, survival, public-information boundaries, and reproducible RNG semantics.
- Prefer canonical ownership over wrappers/rescue layers.
- Training code must never silently redefine Balatro mechanics to make learning easier.
- Simulator shortcuts are allowed only when they are behaviorally equivalent to live Balatro for the modeled state/action boundary and are covered by parity tests.
- Do not optimize training speed by introducing semantic divergence that cannot be quantified.
- Cleanup is part of migration completion.
- Model checkpoints are artifacts, not source-of-truth strategy definitions. Reproducible configs, seeds, environment versions, and evaluation results must accompany meaningful checkpoints.

---

# Primary objective

**Red Deck / White Stake, normal mode: maximize probability of clearing Ante 8.**

The terminal objective is run success, not score maximization, Joker collection, money maximization, Bond completion, or aesthetic build coherence.

Secondary objectives exist only to improve learning efficiency or diagnose behavior. They must never replace the terminal win objective.

---

# Architectural pivot

## Previous production strategy architecture

The completed symbolic strategy path was:

```text
PUBLIC GAME STATE
→ MECHANICAL DESCRIPTORS
→ WEIGHTED BOND CONTRIBUTIONS
→ BOND DEVELOPMENT + REALIZATION
→ SPARSE RELATIONSHIPS + EXCEPTIONAL MOTIFS
→ BuildValue(state)
→ PROJECTED STATE AFTER CANDIDATE
→ StrategyDelta(candidate)
→ CANONICAL DECISION OWNER
```

This architecture remains a valid deterministic baseline and a source of structured features, but it is no longer the intended final strategic authority.

## New target architecture

The target strategic architecture is:

```text
LIVE BALATRO OR HEADLESS ENVIRONMENT
        ↓
CANONICAL PUBLIC GAME STATE
        ↓
EXACT MECHANICS + LEGAL ACTION GENERATION
        ↓
OBSERVATION ENCODER
   ├─ raw/public state features
   └─ optional Bond/mechanical derived features
        ↓
LEARNED POLICY / VALUE MODEL
        ↓
LEGAL-ACTION MASK
        ↓
CANONICAL ACTION
        ↓
EXISTING EXECUTION OWNER / HEADLESS step(action)
        ↓
REWARD + NEXT STATE
```

Training loop:

```text
many parallel deterministic environments
→ collect trajectories
→ compute returns / advantages
→ PPO update
→ checkpoint
→ fixed-seed evaluation
→ regression comparison
→ repeat
```

Initial migration deliberately keeps tactical hand play deterministic while RL learns strategic run development first. Full hand-play RL is a later optional expansion, not a prerequisite for the first learned Red/White competence target.

---

# What the RL agent is intended to learn

The learned policy/value model should be able to discover, without explicit hand-authored strategy thresholds, that:

- some Jokers are useful only with sufficient supporting deck/Joker infrastructure;
- synergies can have nonlinear value and context-dependent timing;
- immediate scoring power can be inferior to economy or scaling when survival permits;
- economy can be inferior to immediate survival when a blind is dangerous;
- build transitions have opportunity cost;
- selling a locally strong Joker can be correct when it unlocks a higher-win-probability trajectory;
- packs, vouchers, rerolls, skips, consumables, and deck modification matter through their effect on eventual win probability;
- boss constraints alter the value of otherwise strong actions;
- the same candidate can be correct in one state and wrong in another without a fixed threshold such as `kings >= 5` being the strategic authority;
- long-horizon build formation matters more than maximizing one-step `BuildValue`.

The model is not required to expose a human-readable named strategy. Interpretability is provided through logged features, action probabilities, value estimates, counterfactual evaluation, and optional Bond diagnostics.

---

# Bond-system status under the new architecture

## Preserve

Keep the following unless an ablation later proves they are harmful or redundant:

- canonical Bond vocabulary;
- mechanics-to-Bond contribution extraction;
- realization semantics that describe actual public state correctly;
- sparse relationship/motif descriptors where they encode real structured information;
- deterministic tests proving those features do not hallucinate unavailable infrastructure;
- Bond telemetry for analysis.

## Change of authority

Bonds are no longer intended to define final strategy through manually calibrated formulas.

The old formulas remain as a frozen baseline only:

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

```text
BondValue = bond_strength(points) × realization × optional calibration weight
RelationshipValue = coefficient × min(BondValueA, BondValueB)
MotifValue = completion × estimated_payoff
BuildValue(state) = Σ BondValue + Σ RelationshipValue + Σ MotifValue
StrategyDelta(candidate) = BuildValue(projected) - BuildValue(current) - transition_cost
```

Do not spend a new development phase manually optimizing those constants as the primary route to competence.

## Planned use in RL

Run at least these observation ablations once training is stable:

```text
A. RAW: canonical raw/public state features only
B. RAW+BOND: raw features plus Bond development/realization/relationship/motif features
C. BOND-HEAVY diagnostic: structured features emphasized, only if useful for analysis
```

The default production model is chosen by measured held-out win rate and stability, not by architectural preference.

---

# Explicitly obsolete future development path

The following are retired as the main competence plan:

- manual Optuna tuning of Bond coefficients as the primary strategy-learning mechanism;
- endless live three-run loops whose purpose is to manually discover strategic thresholds one defect at a time;
- adding more named strategy states or strategy identities;
- rebuilding persistent `StrategyPlan` / FORMING / PINNED / commitment controllers;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- manual `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, or `commit_*` prescription plumbing;
- late rescue wrappers that override canonical legality/admission owners;
- treating a higher symbolic `BuildValue` as proof of higher win probability;
- adding Joker-specific strategic thresholds merely because a live loss looked suspicious, unless the threshold represents an actual mechanics/public-state truth needed by the simulator or feature encoder.

The historical Bond baseline remains useful for comparison and bootstrapping. It is not deleted until the RL replacement proves superior and migration cleanup reaches its explicit gate.

---

# Completed foundation — Phases A–K

## Phase A — Freeze Bond vocabulary — COMPLETE

Validated green. 46 canonical Bonds. Canonical renames include `burnt → hand_leveling`, `gold_economy → gold_cards`, and `vampire → enhancement_consumption`.

## Phase B — Mechanical descriptors — COMPLETE

Validated green. `games/balatro/mechanics.py` is the canonical public mechanics surface.

## Phase C — Mechanics → Bond contributions — COMPLETE

Validated green across all 46 Bonds. `games/balatro/bonds/contributions.py` owns keyed contribution normalization.

## Phase D — Bond strategic value — COMPLETE AS BASELINE

Validated green. `games/balatro/bonds/strategic_value.py` remains the frozen symbolic baseline. Bond rank is diagnostic rather than hard action authority.

## Phase E — Sparse relationships and exceptional motifs — COMPLETE AS BASELINE/FEATURES

Validated green. Relationships and motifs remain deliberately sparse; unlisted pairs are neutral.

## Phase F — Canonical `BuildValue(state)` — COMPLETE AS BASELINE

Validated green. `games/balatro/bonds/build_value.py` remains the deterministic whole-build baseline evaluator.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE AS BASELINE

Validated green. `strategy_delta_from_states(...)` remains a useful deterministic comparison baseline and projection test surface. It is not the final learned-policy boundary.

## Phase H — Canonical strategic decision-owner integration — COMPLETE

Validated green across Joker acquisition/replacement, pack choices, deterministic Tarot/Spectral transforms, Planet development, resource arbitration, and stateful Joker admission.

The canonical action/execution ownership built here is retained and will become the action interface used by the RL layer rather than being discarded.

## Phase I — Tactical exploitation — COMPLETE

Validated green.

Representative proofs cover:

1. Burnt Joker first-discard hand leveling.
2. Hanged Man / permanent deck thinning.
3. Steel / Baron / Mime held-card preservation and exploitation.

These deterministic tactical capabilities are intentionally retained for the first RL curriculum.

## Phase J — Deterministic end-to-end proofs — COMPLETE

Validated green for representative hand-leveling, deck-thinning, and held-card paths.

These tests become simulator/environment parity assets.

## Phase K — Legacy strategic migration cleanup — COMPLETE

Completed removal of the rejected persistent strategy-controller architecture while preserving mechanics/economics/health/D1/D2/D9/D14/boss/hidden-information/runtime constraints.

Notable retained semantic corrections include:

- Midas → Vampire trigger-order semantics;
- persistent enhancement feed behavior;
- renewable future-feed distinction;
- debuffed Gold-card handling;
- Midas scoring-face requirements;
- Stone-card rank-identity rules;
- Planet observed-hand and exotic-hand evidence semantics.

---

# Phase L — Live correctness stabilization before RL environment freeze — COMPLETE

Phase L is no longer a path toward manual Bond calibration. Its only remaining purpose is to ensure that the canonical live state/action/mechanics surfaces we are about to use as simulator truth are not carrying known correctness or severe runtime defects.

## L1 — September 2 baseline — COMPLETE

Batch: `balatro-20260902T200815Z-dba5db6f`

Outcomes:

- attempt 001: lost Ante 7 boss The House, `49,834 / 70,000`;
- attempt 002: lost Ante 3 boss The Needle, `770 / 2,000`;
- attempt 003: lost Ante 2 boss The Club, `1,404 / 1,600`.

Confirmed repairs from this batch:

- Baron exceptional-motif false positive — fixed;
- Flash Card canonical D2 HOLD authority violation — fixed;
- Throwback zero-skip ACTIVE realization — fixed;
- Card Sharp stale shop-history leakage — fixed;
- D14 standalone-Joker timing attribution — fixed;
- Director's Cut/Retcon unsupported boss-reroll admission — fixed/fail-closed.

## L2 — September 3 post-repair batch — INSPECTED

Batch: `balatro-20260903T094415Z-87fd8720`

Outcomes:

- attempt 001: lost Ante 1 boss The Club, `272 / 600`;
- attempt 002: lost Ante 3 boss The Water, `2,512 / 4,000`;
- attempt 003: lost Ante 7 Big Blind, `21,908 / 52,500`.

Confirmed repairs from this batch:

- D14 deterministic-policy timing blind spot — fixed and deterministically validated;
- The Sun optional proof starving D1 before root-node admission — fixed and deterministically validated.

## L3 — RL environment freeze gate — COMPLETE

Completion evidence (September 3, 2026):

- versioned environment contract frozen as `BALATRO_ENV_CONTRACT_VERSION = "l3-v1"`;
- training-exposed actions are fail-closed to entries with canonical legality and execution owners;
- unsupported boss reroll is explicitly `UNAVAILABLE`;
- translator phase-boundary regression covers stale-round reset and active-round preservation;
- focused L3 CI run `33758680261` passed: `1223 passed, 1594 deselected`;
- 7 preceding Linux-only failures were classified as environment-only `APPDATA` construction failures and corrected without skipping tests.

Do **not** begin another open-ended symbolic tuning campaign.

Before simulator/environment implementation is declared authoritative, perform only the following bounded checks:

1. run focused deterministic suites around the canonical state translator, mechanics, action legality, shop owners, D1 tactical owner, D2 Joker owner, D3 voucher owner, D9 pack/consumable paths, D14 shop arbiter, boss rules, and RNG-sensitive utilities;
2. classify remaining suite failures as real defects, stale tests, or environment-only construction failures;
3. repair only true mechanics/state/action/integration defects that would poison simulator parity or live policy execution;
4. ensure canonical public state does not contain stale previous-round values at phase boundaries;
5. ensure every action exposed to training has a deterministic legality predicate and a canonical execution owner;
6. inventory currently unsupported live capabilities such as boss reroll and mark them explicitly unavailable in the initial environment rather than assigning them phantom value;
7. snapshot the canonical environment contract and version it.

### L3 exit criteria

All must hold:

- no known mechanics contradiction in the modeled Red/White surface;
- no known legality/action-owner contradiction;
- no known stale-state phase leakage;
- no severe deterministic runtime path that prevents automated rollouts;
- the environment contract is documented and versioned;
- unsupported mechanics/actions are explicit rather than silently approximated.

Once L3 is green, stop manual Bond-strategy tuning and move directly to Phase R.

---

# Phase R — Headless Balatro environment — ACTIVE / NEXT MAJOR DEVELOPMENT

**Purpose:** create a fast, deterministic training environment that reproduces the canonical modeled Red Deck / White Stake game surface without requiring the live Windows/Balatro UI.

The environment is the most important new subsystem. RL work must not proceed on top of an unverified simulator.

## R0 — Environment architecture and ownership

Create a dedicated environment package, preferably under a clearly isolated path such as:

```text
games/balatro/env/
    __init__.py
    environment.py
    state.py
    actions.py
    legality.py
    rng.py
    rewards.py
    adapters.py
    serialization.py
```

Exact filenames may change if existing repository ownership suggests a cleaner fit, but responsibilities must remain separated.

Canonical interface target:

```python
obs, info = env.reset(seed=seed)
obs, reward, terminated, truncated, info = env.step(action)
legal = env.legal_actions()
```

Required properties:

- deterministic under identical seed + action sequence;
- resettable without process restart;
- no wall-clock dependence;
- serializable/replayable state;
- explicit environment version;
- exact legal-action filtering;
- terminal Ante-8 win/loss signal;
- no hidden live/UI state needed for training decisions;
- batch/parallel-safe design.

## R1 — State transition engine

Implement or integrate a headless transition engine for the modeled Red/White surface.

Required state categories:

- run seed / RNG state;
- ante, blind type, boss identity, blind score requirement;
- current score and round progress;
- money and interest-relevant economy state;
- hands/discards remaining;
- deck cards with rank/suit/enhancement/seal/edition/debuff/public properties;
- current hand;
- draw/discard piles or equivalent exact card-zone representation;
- Joker slots, identities, editions, relevant counters/state;
- consumable slots and contents;
- vouchers and shop modifiers;
- hand levels;
- tags/skips;
- shop inventory and reroll cost/state;
- pack state and choices;
- boss restrictions;
- run-wide counters required by Joker mechanics;
- current-round counters required by Joker mechanics.

Do not fake unavailable state with averages when exact deterministic state is required for training parity.

## R2 — RNG determinism

Create one canonical RNG abstraction for environment transitions.

Requirements:

- seed supplied by `reset(seed)`;
- deterministic shop generation, card draw, packs, boss selection, random Joker/card effects where modeled;
- no direct use of unrelated global random state in environment transitions;
- replay metadata records seed and action sequence;
- identical environment version + seed + action sequence produces identical terminal result.

Add tests for:

- same seed/same actions → identical trajectory;
- different seeds produce different legal stochastic outcomes;
- serialization/restoration preserves next RNG result.

## R3 — Action vocabulary

Define a typed canonical action representation.

Initial strategic action classes should cover the currently executable production surface, including as applicable:

```text
END_SHOP
REROLL_SHOP
BUY_JOKER(slot)
SELL_JOKER(slot)
BUY_VOUCHER(slot)
BUY_CONSUMABLE(slot)
BUY_CARD(slot)                 if shop card purchase is supported
OPEN_PACK(slot/type)
CHOOSE_PACK_OPTION(index)
SKIP_PACK
USE_CONSUMABLE(targets...)
SKIP_BLIND
SELECT_BLIND / START_BLIND     where needed by phase contract
```

Initial tactical play remains delegated to the deterministic tactical owner. If the environment needs a single abstract strategic action such as `PLAY_BLIND_WITH_TACTICAL_POLICY`, that boundary must still emit the detailed tactical trajectory to telemetry for parity/debugging.

Every action must provide:

- stable action type/id;
- required parameters;
- legality predicate;
- deterministic state transition;
- serialization representation;
- training mask representation.

Unsupported actions are excluded from the action vocabulary rather than assigned arbitrary low value.

## R4 — Deterministic tactical bridge

For the first RL curriculum, reuse existing deterministic D1/D9/tactical owners to resolve hand-level play/discard/consumable choices inside blinds.

Target strategic environment step pattern:

```text
RL strategic action
→ shop/pack/blind transition
→ when a blind must be played, deterministic tactical owner plays it
→ environment returns next strategic decision point or terminal result
```

This reduces the RL horizon and action combinatorics dramatically while retaining actual run consequences.

Log all tactical actions so later full-action RL can replace the bridge without changing environment truth.

## R5 — Live/simulator parity harness

Build snapshot-based parity tests using preserved live telemetry.

For each suitable live snapshot:

1. construct equivalent headless state;
2. compare canonical public/mechanical descriptors;
3. compare legal actions;
4. apply selected action;
5. compare resulting deterministic state components where stochastic outcomes are known/replayable;
6. compare boss restrictions, money, counters, card zones, Joker state, and phase transitions.

Priority parity fixtures:

- ordinary shop buy/hold/end-shop;
- Joker replacement;
- reroll;
- voucher purchase/rejection;
- pack open/choice/skip;
- blind skip;
- ordinary blind clear;
- boss blind restrictions;
- Card Sharp round-counter reset;
- Throwback skip counter;
- Baron/held-card relevant deck state;
- The Sun consumable path;
- representative economy/interest transitions.

## R6 — Environment performance gate

Measure environment throughput before RL.

Minimum requirement is not a fixed arbitrary number; it is that training can generate orders of magnitude more experience than live Balatro.

Record:

- environment steps/sec single process;
- completed runs/minute;
- parallel scaling at 2/4/8 workers where available;
- time spent in tactical bridge versus strategic transitions;
- serialization overhead.

Optimize only verified hot paths. Do not weaken semantics for speed without an explicit parity tradeoff record.

### Phase R exit criteria

- deterministic reset/step API exists;
- all initial strategic actions have legality + execution tests;
- Red/White run can proceed from reset to terminal entirely headlessly;
- fixed-seed replay is deterministic;
- representative live parity fixtures are green;
- throughput is sufficient for automated training experiments;
- environment version is recorded in trajectory metadata.

---

# Phase O — Observation and action encoding

**Purpose:** convert canonical environment state/actions into stable model inputs/outputs without leaking hidden information.

## O1 — Observation schema

Create a versioned observation schema. Do not feed arbitrary Python objects directly to the network.

Observation must include enough public information to make strategic decisions, including:

### Run context

- ante;
- blind type / boss identity;
- blind requirement;
- money;
- hands/discards;
- current relevant score/survival state;
- shop reroll cost;
- Joker/consumable capacity;
- skips/tags;
- hand levels;
- relevant run counters.

### Jokers

Represent each slot using a stable identity encoding plus public dynamic attributes:

- Joker id;
- edition;
- debuffed state;
- sell value where relevant;
- scaling counters/state;
- slot occupancy/order.

Avoid encoding display strings as model semantics.

### Deck

At minimum expose structured aggregates and, where necessary, per-card information:

- rank counts;
- suit counts;
- enhancement counts;
- seal counts;
- edition counts;
- face-card/King/held-card-relevant densities;
- deck size;
- destroyed/added-card consequences;
- exact per-card representation if aggregation loses strategically required information.

### Shop / offers

Encode visible:

- Joker offers;
- consumables;
- vouchers;
- packs;
- costs;
- reroll information;
- slot availability.

### Optional structured features

Expose current mechanics/Bond descriptors as a separately versioned feature block, not mixed anonymously into raw features.

## O2 — Normalization

Define deterministic scaling/normalization for continuous values:

- money;
- blind requirement;
- scores;
- counters;
- hand levels;
- deck counts;
- costs.

Avoid normalizations that depend on future information or dataset-wide statistics unavailable during inference unless the statistics are frozen with the model artifact.

## O3 — Action encoding

Use a stable discrete/parameterized representation suitable for action masking.

The initial strategic policy should not enumerate impossible card subsets if tactical decisions are still delegated.

Provide:

- action index ↔ typed action mapping;
- mask of currently legal action indices;
- deterministic ordering;
- schema version.

## O4 — Action masking

Illegal actions must have zero selection probability after masking.

Tests must prove:

- full Joker slots prevent illegal BUY unless a valid replacement action exists;
- insufficient money masks unaffordable actions;
- phase-inappropriate actions are masked;
- unsupported boss-reroll actions are absent;
- pack-only actions appear only inside pack state;
- skip rules obey boss/phase mechanics;
- at least one legal action exists in every nonterminal state.

## O5 — Observation invariants

Add invariants against hidden-information leakage.

Examples:

- no future shop contents;
- no unseen draw-order encoding unless genuinely public;
- no hidden boss/random outcome before reveal;
- no opponent concept is relevant here, but analogous hidden RNG outcomes remain inaccessible;
- training and live inference use the same public feature contract.

### Phase O exit criteria

- versioned observation schema;
- versioned action schema;
- legal mask complete;
- no known hidden-info leak;
- encode/decode deterministic;
- environment rollouts can be converted to model-ready tensors without ad-hoc feature extraction in training code.

---

# Phase B0 — RL baseline infrastructure

The `B0` label is intentionally distinct from historical Phase B.

**Purpose:** prove the environment/training plumbing before attempting a strong learned agent.

## B0.1 — Random legal baseline

Implement a policy that samples uniformly from legal strategic actions.

Measure on a fixed seed suite:

- Ante-8 win rate;
- mean/median ante reached;
- failure ante distribution;
- mean run length;
- invalid-action count (must be zero).

## B0.2 — Existing symbolic/Bond baseline

Run the current deterministic production strategic policy in the same headless environment wherever interfaces permit.

This provides the first meaningful benchmark:

```text
Random legal policy
vs
Current symbolic/Bond policy
```

Any large simulator-only discrepancy versus known live behavior must be investigated before RL.

## B0.3 — Dataset/trajectory format

Every rollout should log enough to reproduce training and inspect failures:

```text
environment_version
observation_schema_version
action_schema_version
seed
policy_version
step_index
phase
observation/features or reproducible state reference
legal_action_mask
selected_action
action_log_probability   when learned
value_estimate           when learned
reward
terminated/truncated
terminal outcome
```

Do not store only aggregate win/loss summaries.

### Phase B0 exit criteria

- random baseline runs headlessly;
- symbolic baseline runs headlessly or documented interface gaps are closed;
- fixed evaluation seed suite exists;
- trajectory format is stable enough for PPO rollout collection;
- baseline metrics are committed/documented.

---

# Phase P — PPO strategic learner

**Purpose:** train a non-LLM policy/value network to learn shop/build/economy/run-development decisions.

PPO is the initial algorithm because it is stable, well-understood, supports masked discrete policies, and works naturally with parallel on-policy environments. Changing algorithms later is allowed only after a measured baseline exists.

## P1 — Model architecture

Start modestly. Do not begin with an oversized network.

Required logical components:

```text
observation tensors
→ feature encoders
→ shared latent representation
   ├─ policy head → logits over strategic actions
   └─ value head  → expected return / win-related value
```

Potential structured encoders:

- scalar/run-context MLP;
- Joker slot embeddings;
- offer/item embeddings;
- deck aggregate encoder;
- Bond-feature encoder for RAW+BOND experiment.

The first implementation may concatenate fixed-size feature blocks into an MLP if the schema supports it. Architectural sophistication is justified only by measured failure.

## P2 — Masked categorical policy

Apply legal-action mask before action sampling and log-probability computation.

Requirements:

- illegal logits excluded robustly;
- entropy computed over legal support;
- deterministic evaluation mode selects highest-probability legal action;
- training mode samples according to masked distribution.

## P3 — Value function

Train a state-value head alongside the policy.

Primary interpretation:

```text
V(s) ≈ expected discounted return under current policy
```

For diagnostic evaluation, also log calibrated empirical Ante-8 win probability by value bucket. Do not assume PPO value output is automatically a calibrated probability.

## P4 — Rollout collector

Support multiple parallel environment instances.

Collect:

- observations;
- masks;
- actions;
- log probabilities;
- rewards;
- values;
- terminations;
- environment seeds.

Implement generalized advantage estimation (GAE) or equivalent standard PPO return processing.

## P5 — PPO update

Implement/configure:

- clipped policy objective;
- value loss;
- entropy bonus;
- advantage normalization;
- gradient clipping;
- minibatches;
- multiple epochs per rollout;
- learning-rate configuration;
- deterministic experiment seeding.

Prefer a mature RL library if integration cleanly supports custom masked actions and reproducible environment versions. Do not reimplement PPO purely for novelty if a library reduces risk.

## P6 — Reward v1

Primary terminal reward:

```text
Ante 8 cleared: +1
run lost:       0
```

Because this may initially be too sparse, permit minimal potential-based or progress shaping only under explicit experiments.

Candidate diagnostic shaping signals may include:

- ante advancement;
- blind clear;
- terminal survival progress.

Avoid directly rewarding:

- raw score maximization;
- money hoarding;
- Bond value;
- Joker rarity;
- number of synergies;
- high card levels;

unless an experiment proves the shaping preserves the actual win objective.

Every shaping term must be configurable and included in experiment metadata.

## P7 — First smoke training

Goal is not competence. Goal is to prove learning plumbing.

Success indicators:

- policy loss/value loss finite;
- entropy changes over training;
- no NaNs;
- invalid actions remain zero;
- checkpoint save/load reproduces inference;
- performance becomes measurably non-random on training/evaluation seeds.

### Phase P exit criteria

- PPO trains end-to-end;
- checkpoints load deterministically for inference;
- legal masking is correct;
- rollout and update metrics are logged;
- at least one learned checkpoint beats random baseline on held-out fixed seeds with a statistically meaningful margin.

---

# Phase C0 — Curriculum and sample-efficiency development

The `C0` label is distinct from historical Phase C.

**Purpose:** make learning feasible without forcing PPO to master all Balatro decisions simultaneously.

## C0.1 — Strategic-only curriculum

Initial RL controls:

- Joker purchases/replacements/sales;
- rerolls;
- vouchers;
- packs/pack choices where action space is stable;
- consumable acquisition/use at strategic boundaries;
- blind skips;
- economy/run-development decisions.

Existing deterministic tactical policy controls:

- cards played;
- cards discarded;
- exact hand selection;
- tactical held-card preservation;
- deterministic consumable execution inside hand play where currently owned by D1/D9.

## C0.2 — Curriculum progression

Possible staged training progression:

```text
Stage 1: shop decisions only with deterministic blind resolution
Stage 2: packs/vouchers/rerolls/skips
Stage 3: strategic consumable timing
Stage 4: broader strategic state/action surface
Stage 5: optional tactical RL
```

Do not advance stages because of elapsed time. Advance when the previous stage has stable learning and evaluation.

## C0.3 — Starting-state curriculum

If full-run sparse reward is too difficult, permit training episodes from sampled valid intermediate states.

Rules:

- sampled states must be reachable/valid under environment semantics;
- evaluation always includes full fresh runs from Ante 1;
- curriculum-state success must not be mistaken for run-level competence.

## C0.4 — Behavior cloning warm start — OPTIONAL

The current symbolic/Bond policy can generate demonstration trajectories.

If useful, pretrain the policy to imitate valid baseline decisions before PPO.

This is optional and must be evaluated against training from scratch. It may speed learning but may also anchor the policy to symbolic mistakes.

### Phase C0 exit criteria

- curriculum configuration is explicit;
- full-run evaluation remains authoritative;
- learned policy consistently beats random and begins approaching or exceeding symbolic baseline;
- no curriculum-only metric is used as the headline competence result.

---

# Phase E0 — Evaluation framework

The `E0` label is distinct from historical Phase E.

**Purpose:** make claims of improvement statistically meaningful and prevent training noise from being mistaken for progress.

## E0.1 — Fixed evaluation seeds

Maintain separate sets:

- training seeds/environment RNG streams;
- development evaluation seeds;
- held-out final evaluation seeds.

Do not tune repeatedly against the final held-out set.

## E0.2 — Core metrics

For every checkpoint considered for promotion, report:

- Ante-8 clear rate;
- confidence interval for clear rate;
- number of evaluated runs;
- ante-reached distribution;
- mean/median terminal ante;
- failure-blind distribution;
- average strategic decisions/run;
- illegal-action count;
- average environment runtime/run;
- deterministic policy entropy or action concentration diagnostics where useful.

## E0.3 — Baseline comparisons

Mandatory comparisons:

```text
Random legal policy
Current symbolic/Bond baseline
Learned RAW model
Learned RAW+BOND model
```

Later include ablations as required.

## E0.4 — Promotion rule

Do not promote a new checkpoint based on one lucky batch.

A candidate must:

- outperform current promoted model on sufficiently large held-out development evaluation;
- show no major legality/runtime regression;
- remain reproducible from committed config + code + seed;
- pass environment/schema compatibility checks.

## E0.5 — Live validation

Live Balatro is a simulator-fidelity check and final behavior check, not the primary training loop.

When a checkpoint is mature enough:

1. run a bounded live batch on exact published HEAD/model hash;
2. compare action legality/state interpretation against headless inference;
3. classify discrepancies as simulator mismatch, live translator mismatch, stochastic variance, or actual learned-policy weakness;
4. repair parity defects before trusting further simulated gains.

### Phase E0 exit criteria

- statistically grounded evaluation harness exists;
- symbolic and learned policies can be compared under identical seeds/environment;
- checkpoint promotion is reproducible;
- live validation has a defined role separate from training.

---

# Phase A0 — Observation/Bond ablation

The `A0` label is distinct from historical Phase A.

**Purpose:** determine whether the Bond work improves learning rather than assuming it does.

Train/evaluate at minimum:

## A0.1 — RAW

Canonical public state + mechanical raw features only.

## A0.2 — RAW+BOND

Same raw features plus:

- Bond development;
- realization;
- sparse relationship evidence;
- exceptional motif evidence;
- other existing structured mechanics descriptors that are public and deterministic.

## A0.3 — Compare

Compare:

- sample efficiency: environment steps required to reach specified win-rate thresholds;
- final win rate under equal training budget;
- stability across multiple training seeds;
- model size/inference cost;
- catastrophic strategic failure modes.

Decision rule:

- retain Bond features if they improve sample efficiency, final competence, stability, or interpretability at acceptable cost;
- otherwise remove them from learned inference while preserving deterministic diagnostics/tests until migration cleanup.

Do not manually change Bond coefficients merely to help the RL model unless the feature definition itself is semantically wrong. The network should learn weighting.

---

# Phase F0 — Reward and objective validation

The `F0` label is distinct from historical Phase F.

**Purpose:** prevent reward shaping from producing a strong optimizer of the wrong task.

## F0.1 — Sparse terminal baseline

Always retain a terminal-only reward experiment as reference.

## F0.2 — Shaping experiments

If shaping is needed, test each addition independently where practical.

Record whether shaping changes:

- learning speed;
- final win rate;
- tendency to hoard money;
- tendency to chase score;
- tendency to over-skip;
- tendency to over-reroll;
- tendency to buy superficially synergistic but losing items.

## F0.3 — Reward-hacking audit

Inspect high-reward losses and low-reward wins. Any shaping configuration where shaped return is poorly aligned with actual Ante-8 success is rejected.

### Phase F0 exit criteria

- selected reward configuration demonstrably improves or preserves held-out Ante-8 clear rate;
- no known dominant reward exploit;
- terminal win remains the authoritative evaluation objective.

---

# Phase T — Training scale-up

**Purpose:** move from proof-of-learning to serious competence training.

## T1 — Parallel rollout workers

Scale environment collection across available CPU workers/processes while preserving deterministic worker seeding.

## T2 — Experiment configuration

Every training run records:

- code commit;
- environment version;
- observation/action schema versions;
- model architecture;
- reward config;
- PPO hyperparameters;
- number of workers;
- random seeds;
- training steps;
- evaluation schedule.

## T3 — Checkpoint cadence

Save periodic checkpoints with enough metadata to reproduce evaluation.

Do not keep every trivial checkpoint indefinitely. Preserve milestone/best/diagnostic checkpoints.

## T4 — Hyperparameter tuning

Only after the training pipeline is stable may hyperparameter search begin.

Tune RL parameters such as:

- learning rate;
- rollout length;
- gamma;
- GAE lambda;
- PPO clip ratio;
- entropy coefficient;
- value coefficient;
- minibatch size;
- update epochs;
- network width/depth.

This replaces the retired plan to primarily tune Bond coefficients.

Hyperparameter objective: held-out simulated Ante-8 clear rate under controlled budget, with stability constraints.

## T5 — Multi-seed robustness

Promising configs must be trained from multiple independent seeds. Reject configurations that only work from one lucky initialization.

### Phase T exit criteria

- sustained training can run unattended in the foreground/session where tooling permits;
- checkpoints improve beyond symbolic baseline on statistically meaningful evaluation;
- results are reproducible across multiple training seeds;
- throughput bottlenecks are measured and understood.

---

# Phase V — Simulator-to-live validation

**Purpose:** prove that learned competence transfers from headless environment to actual Balatro.

## V1 — Frozen checkpoint

Select one promoted checkpoint and freeze:

- model file/hash;
- code commit;
- environment version;
- observation/action schema versions.

## V2 — Live inference adapter

Route live translated canonical state through the same observation encoder and action decoder used in headless evaluation.

No separate hand-written "live version" of the learned policy is allowed.

## V3 — Live legality guard

Canonical live legality remains a final safety boundary. If the model selects an action that the live owner rejects despite the model mask marking it legal, record a parity defect and fail closed rather than inventing a replacement strategy silently.

## V4 — Live telemetry

For each strategic action log:

- model/checkpoint id;
- observation schema version;
- legal mask summary;
- selected action;
- selected action probability/logit where useful;
- value estimate;
- top alternative actions;
- Bond diagnostics if enabled;
- live execution result;
- latency.

## V5 — Transfer diagnosis

Classify simulator/live disagreements before modifying the policy:

1. state translation mismatch;
2. simulator mechanics mismatch;
3. action legality/execution mismatch;
4. RNG/fidelity mismatch;
5. learned strategic error;
6. ordinary stochastic variance.

Do not patch the neural policy with hand-coded exception wrappers unless the behavior is a hard mechanics/legality safety requirement.

### Phase V exit criteria

- no recurring simulator/live state or action mismatch;
- live model inference is stable and interactive;
- learned agent demonstrates meaningful Red/White competence in actual Balatro;
- simulated and live failure modes are qualitatively consistent.

---

# Phase Q — Competence gate for Red Deck / White Stake

**Purpose:** determine whether the RL pivot achieved the original v1.0 competence target.

The exact numeric win-rate threshold may be set after reliable baseline measurements exist, but the gate must be materially stronger than random and demonstrably stronger than the frozen symbolic baseline.

Required evidence:

- large held-out simulated evaluation;
- confidence interval;
- comparison to random baseline;
- comparison to frozen Bond/symbolic baseline;
- multiple training seeds;
- live validation batch on frozen checkpoint;
- no unresolved high-impact parity defect.

At this point, the controlling metric is:

```text
P(clear Ante 8 | Red Deck, White Stake, normal mode)
```

not symbolic BuildValue quality.

---

# Phase X — Optional full tactical RL

**NOT REQUIRED FOR INITIAL RL COMPETENCE GATE.**

Only begin if strategic-only RL with deterministic tactical execution has plateaued for reasons attributable to hand/discard decisions.

## X1 — Expand action space

Expose:

- PLAY selected card subset;
- DISCARD selected card subset;
- consumable use during hand play;
- held-card decisions.

Because arbitrary card subsets create a large combinatorial action space, do not naively assign one flat action id to every theoretical subset across all states.

Investigate structured/parameterized policy designs such as:

- action type head + card-selection head;
- autoregressive card selection;
- candidate-hand generation followed by learned ranking;
- retained deterministic candidate generator + learned value/ranking.

## X2 — Tactical baseline distillation

Use existing D1 tactical policy as:

- teacher demonstrations;
- candidate generator;
- performance baseline.

## X3 — Full-policy evaluation

Only replace deterministic tactical control if learned tactical policy improves overall Ante-8 clear rate, not merely per-hand score.

---

# Phase M — Migration cleanup after learned policy proves superior

**NOT STARTED.**

Do not delete the symbolic/Bond baseline before the RL policy passes Phase Q.

After learned production authority is proven:

1. make learned strategic policy the canonical strategic owner;
2. retain deterministic mechanics/legality/tactical safety boundaries;
3. keep Bonds as diagnostics/features only if A0 justifies them;
4. remove obsolete manual `BuildValue`/`StrategyDelta` production authority if no longer used;
5. remove dead calibration/Optuna code for symbolic weights;
6. remove compatibility wrappers created only for the retired symbolic strategy;
7. keep replay/evaluation adapters for historical baseline comparison where inexpensive;
8. update docs/tests so there is exactly one production learned-strategy path.

Required end state:

```text
ONE canonical environment/state/action semantics
ONE observation/action encoding path shared by training and live inference
ONE learned strategic production owner
ONE deterministic legality/mechanics boundary
OPTIONAL Bond diagnostics/features, not parallel authority
NO post-policy rescue strategy wrappers
NO hidden symbolic strategy controller competing with the learned policy
```

---

# Phase N — Broader competence after Red/White RL success

**NOT STARTED.**

Only after Phase Q/M:

- additional decks;
- higher stakes;
- broader voucher/action support such as boss reroll if desired;
- optional endless-mode objectives;
- improved tactical RL;
- transfer/generalization experiments;
- opponent/game-general framework integration where relevant.

Do not broaden the environment before the Red/White target is reliable unless a missing mechanic is required for fidelity.

---

# Testing strategy under the new path

## Deterministic unit/integration tests

Continue using pytest for:

- mechanics;
- state transitions;
- legality;
- phase boundaries;
- RNG determinism;
- serialization;
- observation encoding;
- action masks;
- live/headless parity;
- checkpoint loading;
- deterministic inference.

## Statistical tests/evaluation

Use large rollout batches for:

- win rate;
- learning curves;
- model comparisons;
- ablations;
- reward validation;
- hyperparameter comparison.

Do not encode stochastic performance expectations as brittle one-seed pytest assertions.

## Live tests

Use actual Balatro only for:

- translator parity;
- execution parity;
- UI/live integration;
- final model behavior validation;
- simulator fidelity checks that cannot be resolved headlessly.

---

# Artifact and reproducibility contract

Every promoted model must be associated with:

```text
source commit
model checkpoint hash/path
environment version
observation schema version
action schema version
reward configuration
training configuration
training seed(s)
training step count
evaluation seed set id
evaluation results
```

Never report "model improved" without identifying the exact checkpoint and evaluation protocol.

Training logs should distinguish:

- training return;
- shaped return if any;
- true terminal win rate;
- evaluation win rate;
- environment throughput;
- policy/value losses;
- entropy;
- KL/clip diagnostics where available.

---

# Failure-classification contract

When a bad decision is observed after the RL pivot, classify it before changing code:

1. **mechanics bug** — simulator/live rules wrong;
2. **state bug** — observation or canonical state wrong/stale;
3. **legality/action bug** — action mask or execution wrong;
4. **parity bug** — simulator and live environment disagree;
5. **training bug** — PPO/update/checkpoint/data pipeline wrong;
6. **reward bug** — model is optimizing an unintended shaped objective;
7. **representation limitation** — required public information is missing/poorly encoded;
8. **capacity/optimization issue** — model/training cannot learn available signal;
9. **ordinary learned-policy error** — no implementation contradiction; improve through training/data/model rather than one-off rescue rules.

A single bad run is not sufficient evidence for a hand-coded strategic exception.

---

# Current checkpoint — EXACT PROJECT STATE

```text
Historical symbolic/Bond architecture             COMPLETE AS BASELINE
Mechanics/state/action deterministic foundation   SUBSTANTIALLY COMPLETE
Phase K legacy-controller cleanup                  COMPLETE
September 2 live baseline                         INSPECTED
Baron semantic repair                             GREEN
Flash Card D2 authority repair                    GREEN
Throwback realization repair                      GREEN
Card Sharp phase-history repair                   GREEN (DETERMINISTIC)
Director's Cut/Retcon fail-closed repair          GREEN (DETERMINISTIC)
D14 standalone-Joker attribution                  GREEN (DETERMINISTIC)
September 3 post-repair batch                     INSPECTED
D14 deterministic attribution repair              GREEN (DETERMINISTIC)
The Sun D1 budget repair                          GREEN (DETERMINISTIC)
Manual Bond numerical tuning                      RETIRED AS PRIMARY PATH
RL pivot                                           APPROVED / ROADMAP ACTIVE
L3 environment-freeze correctness gate            COMPLETE
Headless training environment                     ACTIVE — R0 NEXT
Observation/action encoding                       NOT STARTED
Random/symbolic headless baselines                 NOT STARTED
PPO strategic learner                             NOT STARTED
RL curriculum                                     NOT STARTED
Statistical evaluation framework                  NOT STARTED
Bond feature ablation                             NOT STARTED
Training scale-up                                 NOT STARTED
Simulator-to-live learned-policy validation        NOT STARTED
Red/White learned competence gate                 NOT STARTED
Full tactical RL                                  OPTIONAL / NOT STARTED
Post-RL symbolic cleanup                          NOT STARTED
```

---

# Exact next development action

**L3 is complete. Do not request another Balatro live batch yet and do not resume manual Bond tuning. Begin Phase R by implementing the headless environment on top of the frozen `l3-v1` contract.**

Order:

1. **L3.1 — Inventory canonical state/action owners.**
   - identify the exact existing state representation used by production;
   - identify canonical mechanics helpers;
   - enumerate strategic phases/actions currently executable;
   - enumerate unsupported actions/mechanics explicitly;
   - document which tactical owners can be reused headlessly.

2. **L3.2 — Run/fix deterministic environment-prerequisite tests.**
   - translator phase boundaries;
   - mechanics;
   - legality;
   - D1/D2/D3/D9/D14 owner interfaces;
   - boss rules;
   - RNG-sensitive helpers.
   - repair only defects that would corrupt environment truth.

3. **R0 — Create the headless environment skeleton.**
   - `reset(seed)`;
   - `step(action)`;
   - `legal_actions()`;
   - environment version;
   - state serialization;
   - deterministic RNG ownership.

4. **R1/R3 — Implement enough state transitions and action vocabulary to complete a Red/White run headlessly with deterministic tactical play.**

5. **R5 — Add snapshot/live parity fixtures before training.**

6. **R6 — Benchmark throughput.**

7. Only after Phase R is green, build observation/action tensors and RL training code.

The next code written should therefore be **environment-contract/headless-simulator work**, not another Bond coefficient or strategy exception.

---

# Progress criterion

```text
mechanical/state/action foundation                 ✓
Bond symbolic baseline                             ✓
legacy strategic-controller cleanup                ✓
live correctness stabilization                     COMPLETE
        ↓
HEADLESS ENVIRONMENT                               ← NEXT MAJOR BUILD
        ↓
OBSERVATION + ACTION ENCODING
        ↓
RANDOM + SYMBOLIC HEADLESS BASELINES
        ↓
PPO STRATEGIC LEARNER
        ↓
CURRICULUM + REWARD VALIDATION
        ↓
STATISTICAL EVALUATION + BOND ABLATION
        ↓
TRAINING SCALE-UP
        ↓
SIMULATOR ↔ LIVE TRANSFER VALIDATION
        ↓
RED/WHITE RL COMPETENCE GATE
        ↓
POST-RL SYMBOLIC CLEANUP
        ↓
OPTIONAL FULL TACTICAL RL / BROADER COMPETENCE
```

Controlling question for implementation correctness:

> **Does the environment expose the same public Balatro problem and legal consequences that the live agent faces?**

Controlling question for learned strategy:

> **Does this policy increase the probability of clearing Ante 8 on held-out Red Deck / White Stake runs?**
