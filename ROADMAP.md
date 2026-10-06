# ROADMAP - SINGLE SOURCE OF TRUTH

Authoritative development state for Balatro Red Deck / White Stake competence
in `LeafStardust/game-ai-framework`, branch
`feat/v1.0-red-white-competence`.

Last synchronized implementation HEAD:
`c5f83675408a448ef4f4085398ea1fce9aa237d2`.

## Objective

Maximize **P(clear Ante 8 | Red Deck, White Stake, normal mode)** through the
headless deterministic RL environment. Manual Bond coefficient tuning is
retired as the primary competence path. Higher stakes and other decks remain
deferred until Red/White promotion passes.

## Required development workflow

For every continuation:

1. Fetch `origin/feat/v1.0-red-white-competence` and read this file from that
   remote branch before acting.
2. Treat the latest remote HEAD as authoritative; synchronize the local branch
   without discarding unrelated local changes.
3. Work only the exact active task below and inspect its canonical owners and
   tests first.
4. Fix the earliest incorrect owner. Do not add rescue layers, duplicated
   mechanics, or learner-only approximations.
5. Keep unsupported or ambiguous mechanics absent from the action mask and
   fail closed.
6. Add focused deterministic regressions for each exact behavior.
7. Push coherent commits directly to this branch.
8. Use GitHub Actions as the test gate and report the exact passed/deselected
   counts from the actual job log.
9. Update and verify this roadmap after every meaningful green checkpoint.
10. Request a live Balatro run only for genuinely live-only validation, and
    provide the exact commands. The held Money Tree live check remains on hold.
11. If context is insufficient, synchronize this roadmap and stop rather than
    guessing.

Pinned vanilla source:
`GladdonT/balatro-source-code@895ab3a25bc6f513fa80885eb59951bf8e76bc55`.

Authoritative CI workflow: `.github/workflows/balatro-l3.yml`.

## Non-negotiable technical contract

- Preserve exact Balatro mechanics, legality, Boss rules, economy, seeded RNG,
  and public-information boundaries.
- Permanent deck truth is `G.playing_cards`; never substitute `G.deck.cards`.
- Hidden draw order and face-down card/Joker identity-to-position mappings are
  not policy-visible.
- Python `random` is not Balatro RNG.
- Training code must consume canonical environment mechanics, not redefine
  them.
- Simulator shortcuts require behavioral equivalence plus regression/parity
  coverage.
- Model checkpoints are artifacts, not strategy source of truth.
- The only canonical attempt-count interface is `--attempt N`; do not restore
  legacy attempt flags.

## Current phase status

| Phase | Status |
|---|---|
| A-K symbolic/mechanical foundation | Complete |
| L live stabilization | Complete |
| L3 environment freeze | Complete |
| R0 headless architecture | Complete |
| R1 deterministic state/acquisition | Substantially complete |
| R2 RNG/lifecycle/shop generation | Green for the owned Red/White surface |
| R3 typed strategic actions | Complete / green |
| R4 deterministic tactical bridge | Complete / green |
| R5 live/simulator parity | Conditionally closed; Money Tree live fixture on hold |
| R6 performance gate | Complete / green |
| O observation/action encoding | Complete / green |
| B0 baseline/evaluation infrastructure | Complete / green |
| PPO learner and training path | In progress |

Completed phase details are intentionally removed from this roadmap. Git
history and the focused files under `docs/balatro/` retain the evidence. Do not
reopen a completed phase without a demonstrated failure at its boundary.

## Current strategic action surface

Training-exposed actions:

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
USE_CONSUMABLE     exact held-Planet subset
SKIP_BLIND         exact admitted Small-Blind/Tag subset
SELECT_BLIND       exact audited blind-start boundary
```

Never training-exposed:

```text
BUY_CARD
REROLL_BOSS
```

There is no `PLANNED` action in the frozen strategic contract. `BUY_CARD` and
`REROLL_BOSS` require new canonical production capabilities before they can be
considered; do not invent RL-only aliases.

## Frozen PPO contract

- Schemas: `balatro-red-white-ppo-training-v1`,
  `balatro-red-white-ppo-run-v1`, `balatro-red-white-ppo-policy-output-v1`, and
  `balatro-red-white-ppo-rollout-episode-v1`.
- Observation: 2,444 values. Output: 27 canonical action slots.
- Model: `(512, 256)` tanh MLP.
- Collection: 8 environments, 256 steps each, 2,048 transitions per batch.
- Optimization: 256-transition minibatches, 10 epochs, 1,024 batches,
  2,097,152 total environment steps.
- Hyperparameters: gamma 0.99, GAE lambda 0.95, policy/value clip 0.20,
  learning rate 0.0003, entropy coefficient 0.01, value coefficient 0.50,
  maximum gradient norm 0.50.
- Maximum complete-episode action count: 4,096.
- Reward: running `0.0`, loss `-1.0`, Ante-8 win `+1.0`.
- Root seeds derive isolated learner and rollout streams. Training seeds must
  not collide with the fixed evaluation corpus.
- Illegal probability mass is exactly zero. There is no empty-mask rescue.
- Incomplete/nonterminal evidence, illegal actions, schema/provenance drift,
  non-finite output, seed drift, and terminal contradictions fail closed.

## Frozen evaluation and promotion contract

- Primary metric: Ante-8 clear rate against both frozen B0 baselines.
- Fixed holdout: 64 episodes per arm; candidate clear count must be at least
  each baseline count.
- Unseeded gate: four complete 64-episode manifests (256 episodes per arm).
- Unseeded candidate clear rate must be at least 0.20 with at least a 0.05
  absolute advantage, and its one-sided 95% Wilson lower bound must exceed each
  baseline upper bound.
- Maximum permitted regression against each baseline: 0.25 mean Ante, 0.05
  mean terminal blind-requirement progress, $2 mean minimum cash, and $2 mean
  terminal cash.
- Illegal actions, unsupported mechanics, incomplete episodes, and provenance
  or schema drift have zero tolerance.
- Do not inspect learned-policy promotion results or tune hyperparameters before
  the frozen training run is valid.

## Current PPO evidence

The first real optimizer batch completed under root seed
`RED-WHITE-PPO-V1`:

- 312 complete episodes, 2,268 collected transitions.
- 2,048 optimizer-consumed transitions; Adam step 80.
- Carryover counts `(28, 52, 40, 32, 24, 8, 35, 1)` (220 total).
- Next episode indices `312..319`.
- Elapsed time 5,415.1250193 seconds (1:30:15.125).
- Checkpoint SHA-256
  `872f3be2dbce3e860b1151edef810df27157858e8f5202799869a75500038a4c`.
- Initial/trained parameter digests:
  `f82fdfda2d5448d27fe8c5af5298a8ce7d905f64f7bab37baa810c124ffd9d71`
  and
  `180d11d0971a3bdfb8f9a1f0c2251fcdce0e0d82456f9ef6a1abb61fd50e7567`.
- Sustained rate projects the frozen schedule to roughly 58 days, so full
  training is not yet authorized.

Initial-batch timing identified episode 43 / stream 3 / seed `EE424B52` as the
dominant outlier. The complete decision trace is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_TACTICAL_COST.json`.

Key episode-43 findings:

- 30 tactical decisions; 1,090.3553323000087 seconds tactical time.
- Candidate generation: 1,008.54513729979 seconds (92.4969%).
- Decisions 11 and 12 consume 96.8910% of tactical time.
- Decision 11 digest:
  `7fb297b6f491b1618c66c449c74d1bbb184559af6f9f8b99a55601758c07a21d`.
- Decision 11 selects `DISCARD_CARDS(5)` and searches
  `(h2,n252,max2000,complete)`, then
  `(h3,n2000,max2000,budget-exceeded)`.

The full decision-11 subowner report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_SUBOWNERS.json`.

Exact attribution:

- 728,887 generated-consumable transitions were evaluated.
- All 728,887 were inert: no Eight Ball, Main Generator, or Sixth Sense
  capability.
- Every inert call nevertheless entered
  `BalatroState.copy_for_tactical_projection`.
- Exclusive tactical-copy cost: 295.30642790847924 seconds.
- Additional measured recursive copy costs: dict 56.16093468970212 seconds,
  list 12.752040303312242, reconstruction 11.147607308492297, outer deepcopy
  3.463350795514998.
- Generated Joker projection/scoring costs: 90.13103089077049 and
  27.408676404418657 seconds.
- Evaluator cache: 1,860 hits, 945 misses.

Post-inert re-profile evidence is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_SUBOWNERS_POST_INERT.json`.
Its canonical 3,801-byte report has SHA-256
`7323e04147509eac1671361ebc51fc4309b1d41f3d50b1910307142b556786e5`;
the repository copy includes a terminal newline (3,802 bytes, SHA-256
`d0b08bc4f7ae756b6204c77e34a8997d5be16820bc419161cd915eba79cce038`).
The digest, `DISCARD_CARDS(5)`, selected index, both search attempts, all 12
verified prefix decisions, 1,860 cache hits, 945 misses, and 728,887 exact inert
generated transitions are unchanged.

Measured candidate time fell from **610.2228404998896** to
**459.629491099578 seconds** (**24.6784% lower**); total target time fell from
**648.5922759999958** to **496.955010399994 seconds** (**23.3794% lower**).
All 728,887 `copy_for_tactical_projection` calls and their dict/list/
reconstruction/deepcopy subcalls are eliminated. Generated Joker projector and
scorer calls also halved from 1,457,774 to 728,887 because the redundant probe
is skipped. The dominant remaining measured owner is now the 728,887 selective
generated-consumable transitions themselves at **308.02795810486714 seconds**.

Latest implementation gate:

- Commit `ba1ca8d716774bf7b5dbb79c37c1992c1b68c0fe`.
- The generated-consumable owner now uses a strict tri-state capability check.
  Exact inert states reuse the already-isolated parent transition and detach
  only mutable card, consumable, voucher, and shop-item aliases. Exact
  generator/copier capability keeps the full projection path; state/Joker
  subclasses and malformed containers remain conservative.
- The production alias comparator preserves identical public-state hashes
  (`78325d40...`) while reducing wrapped input-card aliases from the inherited
  60 to exactly 0.
- Focused local validation: **65 passed**.
- GitHub Actions run `37416886729`, job `112117355442`.
- Actual job log: **3158 passed, 1613 deselected in 118.18s**.

Detachment-attribution diagnostic gate:

- Commit `9badb2cc18fcebb468ac126b1e781f143eb20b88`.
- `BalatroState.detach_tactical_mutable_aliases` now exposes canonical,
  behavior-preserving card-collection and named-collection subowners solely so
  the frozen target can attribute their cost.
- Candidate-subowner schema v16 measures the detachment owner, card traversal,
  capped exact-scalar validation/copy samples, extended-card deepcopy, and each
  mutable consumable/shop/voucher collection. All temporary instrumentation is
  restored after both successful and failed diagnostic runs.
- Focused local validation: **65 passed in 1.01s**.
- GitHub Actions run `37419564525`, job `112125661818`.
- Actual job log: **3158 passed, 1613 deselected in 106.94s**.

The schema-v16 frozen-target report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_DETACHMENT_V16.json`.
Its canonical 4,666-byte report has SHA-256
`48665922dfc098d8281edc8346ff92790e83484ed5afec0a7551fb1de4252c9f`;
the repository copy includes a terminal newline (4,667 bytes, SHA-256
`68148e4f51f80d82c5235bf6a9eb287495d917da95e66833b6fafb0588ce7464`).
The required target identity, action, attempts, verified prefix, cache counts,
and 728,887 exact inert transitions are unchanged.

Exact detachment attribution:

- Total target time: **420.91189390000363 seconds**.
- Candidate generation: **389.38627049954084 seconds**.
- Card-collection detachment: **244.07908259911346 seconds** across 728,887
  calls (**62.6830%** of candidate generation).
- The detachment owner's remaining exclusive overhead: **5.499662598827854
  seconds**.
- Consumables, shop Jokers, shop consumables, shop boosters, shop vouchers,
  and vouchers together cost **11.061359712432 seconds**; no individual named
  collection exceeds 3.181 seconds.
- The capped first 100,000 exact-card samples cost 0.18630290101282299 seconds
  for scalar validation and 0.17939219769323245 seconds for shallow copying.
- No extended-card reconstruction was observed in the 100,000-call sample.

Card-detachment optimization gate:

- Commit `27f1c49058fc6eca8d64c4cd63abbd7b88f36833`.
- Exact Balatro-card field and scalar-type sets are now module constants;
  validation compares the card's key view without allocating a set, exact cards
  reconstruct directly through the canonical `BalatroCard` constructor, and the
  collection owner no longer invokes an inner closure for every card reference.
- Subclasses, extra attributes, and mutable field values still fail closed to
  graph-preserving `deepcopy`; shared cards retain cross-collection identity and
  no projected card aliases its input.
- A representative 20,000-iteration pristine-state microbenchmark measured
  2.1800945 seconds versus 3.4009327 seconds for the prior implementation
  (**35.8972% lower**).
- The production comparator preserved input hash `e855e86f...` and identical
  wrapped/inherited public-state hash `78325d40...`, with inherited input-card
  aliases 60 and wrapped aliases exactly 0.
- Focused local validation: **66 passed in 1.00s**.
- GitHub Actions run `37421013032`, job `112130135632`.
- Actual job log: **3159 passed, 1613 deselected in 197.05s**.

The post-fast-path schema-v16 report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_DETACHMENT_V16_POST_FAST.json`.
Its canonical 4,664-byte report has SHA-256
`d1f635c3b0332f06e92828e060f74f3b63e8fdea7b88a11d79d8904327968e43`;
the repository copy includes a terminal newline (4,665 bytes, SHA-256
`3b29e33be347e56dbd5ae3be5d73fa0960aec21b1c94e8b38d91d1659a90c47c`).
The target identity, action, attempts, 12-decision verified prefix, 1,860/945
cache counts, and 728,887 exact inert transitions are unchanged.

Before/after schema-v16 results:

- Total target time: 420.91189390000363 -> **324.3295658999996 seconds**
  (**22.9460% lower**).
- Candidate generation: 389.38627049954084 -> **291.82993469967914
  seconds** (**25.0539% lower**).
- Card-collection detachment: 244.07908259911346 ->
  **142.32064609440567 seconds** (**41.6908% lower**).
- The first 100,000 exact-card validation samples fell from
  0.18630290101282299 to 0.12925959857238922 seconds; copy samples fell from
  0.17939219769323245 to 0.09220489767903928 seconds.
- Extended-card reconstruction remains absent in the capped sample. Named
  non-card collections remain individually immaterial.

Exact-card helper optimization gate:

- Commit `898ac9cb0819c39a768d69dfd3fc49a1f42a8318`.
- Exact scalar validation now uses a fail-fast loop after the exact class/key
  gate. Exact-card copying clones the already-validated scalar-only instance
  dictionary directly, avoiding generic copy and constructor dispatch.
- Subclass, extra-field, mutable-field, and missing-instance-field cases remain
  on graph-preserving `deepcopy`.
- One-million-call microbenchmarks measured validation at 0.5376129 versus
  1.1120527 seconds (**51.6558% lower**) and exact copying at 0.2358578 versus
  1.2125076 seconds (**80.5479% lower**).
- Production alias/public-state hashes and the 60 -> 0 input-card alias result
  remain exact.
- Focused local validation: **66 passed in 1.04s**.
- GitHub Actions run `37422274157`, job `112134052768`.
- Actual job log: **3159 passed, 1613 deselected in 195.33s**.

The post-helper schema-v16 report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_DETACHMENT_V16_POST_HELPERS.json`.
Its canonical 4,659-byte report has SHA-256
`005a07acde897f4f9a0a7852d5e5f0ad44fd5e83b9c6234a69a3a3d6d40c7f00`;
the repository copy includes a terminal newline (4,660 bytes, SHA-256
`f2343df1f456b1adaa65cc75f70393d04408e1e0e3caa68752eb665eebd3f4a3`).
The complete frozen target identity and accounting remain unchanged.

Post-helper before/after results:

- Total target time: 324.3295658999996 -> **271.2601521000033 seconds**
  (**16.3628% lower**).
- Candidate generation: 291.82993469967914 -> **236.5192761994258
  seconds** (**18.9530% lower**).
- Card-collection detachment: 142.32064609440567 ->
  **83.54616560605064 seconds** (**41.2972% lower**).
- First-100,000 validation samples fell from 0.12925959857238922 to
  0.09267869967152365 seconds; exact-copy samples fell from
  0.09220489767903928 to 0.04373009837581776 seconds.
- Relative to the initial schema-v16 baseline, total target time is now
  **35.5542% lower**, candidate generation **39.2585% lower**, and card
  detachment **65.7711% lower**.

Decision-12 diagnostic gate:

- Commit `8f49d005696974483d7e6a3e27fc2cf3994e3d02`.
- The schema-v16 diagnostic now exposes an exact episode-43 decision-12 route
  whose prefix is the complete frozen decision-11 prefix plus only the pinned
  decision-12 digest/action/search contract.
- CLI selection remains mutually exclusive and uses the existing atomic
  candidate-subowner writer; the generic instrumentation/accounting/restoration
  owner is unchanged.
- Focused local validation: **69 passed in 1.03s**.
- GitHub Actions run `37423411824`, job `112137605591`.
- Actual job log: **3162 passed, 1613 deselected in 191.97s**.

The decision-12 schema-v16 report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_SUBOWNERS_V16.json`.
Its canonical 4,665-byte report has SHA-256
`0a17c4242c3a2cd07b6b697a1806b340bb5478ca55f175f56ba2261c16d33d1c`;
the repository copy includes a terminal newline (4,666 bytes, SHA-256
`e9dd1f03863bb0d328633336e97e1b5c97c26d76500e864919902235e930fdd5`).
All 13 prefix decisions, the pinned target identity, and both search attempts
are exact.

Decision-12 attribution:

- Total target time: **254.21451600000728 seconds**; candidate generation:
  **219.5430486999976 seconds**.
- Evaluator cache: 1,740 hits / 885 misses.
- Generated-consumable transitions: **682,505**, all exact inert and zero
  generator-capable.
- Card-collection detachment remains the largest measured owner at
  **76.9668123024021 seconds** (35.0577% of candidate generation), but its
  validation/copy paths are already attributed and optimized.
- The largest unexamined owner is The Hook transition at
  **47.01187289733207 seconds** across 83,408 calls (21.4135% of candidate
  generation). Generated Joker projection follows at 33.659568707080325
  seconds.
- Decision 12 therefore confirms decision 11's ownership shape rather than
  revealing a separate mechanic-specific regression.

Hook-attribution diagnostic gate:

- Commit `2ed3b9650e8d78342bcd863f4d34f9edc7b146fc`.
- Schema v17 adds behavior-preserving canonical helper boundaries for held-card
  selection, forced-branch construction, discard-Joker projection, hand
  removal, and Hook outcome aggregation.
- The diagnostic records exact forced branch-set/branch, discard projection,
  aggregation-call, and aggregated-outcome accounting. Every temporary
  instance wrapper is restored after both successful and failing traces.
- Focused local validation: **91 passed in 1.43s** (including the narrower Hook
  suite at **55 passed in 1.16s**).
- GitHub Actions run `37425237861`, job `112143289527`.
- Actual job log: **3163 passed, 1613 deselected in 197.76s**.

The decision-12 schema-v17 report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_HOOK_V17.json`. Its canonical
5,350-byte report has SHA-256
`65e73c9cb5c33c3992a5490efbe68e7557ee6404e0f77865e7d16e4c224264c6`;
the repository copy includes a terminal newline (5,351 bytes, SHA-256
`5b22c33f601852b70898945d897ba3ac62454ece858b99980570a3598c1c79f3`).
All 13 prefix decisions, the pinned target identity, and both search attempts
remain exact.

Schema-v17 Hook attribution:

- Total target time: **254.8979316999903 seconds**; candidate generation:
  **220.5095313998172 seconds**.
- Exactly **83,408** Hook forced-branch sets produced **682,505** forced
  branches, discard projections, aggregation calls, and aggregated outcomes.
- Discard-Joker projection is the dominant Hook subowner at
  **38.645466690388275 seconds**. The other separated Hook work is small:
  held-card selection 0.44416119770903606 seconds, forced-branch construction
  0.17402039893204346 seconds, hand removal 2.4097911006829236 seconds, and
  outcome aggregation 1.5502811945480062 seconds.
- The parent Hook transition's remaining exclusive work is
  **7.123402616314706 seconds**. The attribution accounts exactly for all
  branch sets and outcomes and isolates discard projection as the next owner.

Discard-projection attribution gate:

- Commit `c5f83675408a448ef4f4085398ea1fce9aa237d2`.
- Schema v18 introduces behavior-preserving canonical boundaries for state
  shell copying, Joker graph cloning, active-Joker selection, context
  preparation, Joker application, and discard side-effect finalization.
- The profiler records exact active-selection/application call and Joker counts
  and restores every temporary instance wrapper after both successful and
  failing traces.
- The canonical regression proves helper order, forced-discard semantics, and
  parent-state/Joker isolation. Focused local validation: **60 passed in
  1.27s**; broader affected projection validation: **145 passed in 2.50s**.
- GitHub Actions run `37426984252`, job `112148777942`.
- Actual job log: **3163 passed, 1614 deselected in 198.50s**.

## Exact active task

Run the single schema-v18 discard-projection attribution diagnostic at frozen
episode-43 decision 12, preserve the canonical report, and use its exact timing
and accounting to select the next owner.

Requirements:

- Require digest
  `9231aae5f2605e76643e38b36b74289533e11813c5f0304e0c8cf6f6d11fe23e`,
  `DISCARD_CARDS(1)`, and attempts `(h2,n252,max2000,complete)` then
  `(h3,n2000,max2000,budget-exceeded)` at decision index 12.
- Preserve all 13 prefix decisions and the pinned target/search identity.
- Record the exact schema-v18 discard helper timings, active-selection and
  application counts, and selected/applied Joker totals.
- Commit the report under `docs/balatro/` with canonical and repository-copy
  byte counts and SHA-256 values.
- Select any optimization only from the measured dominant safe subowner; do
  not infer it from the schema-v17 aggregate projector time.
- Do not optimize any named non-card collection.
- Do not resume a second optimizer batch, start full training, change
  policy/hyperparameters/search schedule, or widen mechanics until this task is
  recorded here.

## Held and deferred work

- Natural Money Tree live parity evidence is explicitly on hold by user
  direction. It is not passed and must not be inferred.
- No live Balatro run is currently required.
- Remaining slow-tail episodes are deferred until decision 12 is attributed.
- Higher stakes and other decks begin only after controlled Red/White promotion.

## Resume evidence index

- `docs/balatro/BALATRO_PPO_EPISODE_43_TACTICAL_COST.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_SUBOWNERS.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_SUBOWNERS_POST_INERT.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_DETACHMENT_V16.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_DETACHMENT_V16_POST_FAST.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_DETACHMENT_V16_POST_HELPERS.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_SUBOWNERS_V16.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_HOOK_V17.json`
- Git history before `ac4a9287260cc485e7eb5476854679ac9cbc2b8d` for completed checkpoint
  narration intentionally removed by the roadmap cleanup.
