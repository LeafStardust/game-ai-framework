# ROADMAP - SINGLE SOURCE OF TRUTH

Authoritative development state for Balatro Red Deck / White Stake competence
in `LeafStardust/game-ai-framework`, branch
`feat/v1.0-red-white-competence`.

Last synchronized implementation HEAD:
`4a86d7905371da9ab5d63bbeabaeb337f87b3cc9`.

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
| PPO learner and training path | Frozen 1,024-batch schedule complete; promotion integration active |

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

The decision-12 schema-v18 report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_DISCARD_V18.json`. Its
canonical 6,152-byte report has SHA-256
`6ac5a5721ffe8e8098f088262de4ab4154beb3f85e7dfa4cc4b3c73dca699e9f`;
the repository copy includes a terminal newline (6,153 bytes, SHA-256
`7338d58b4a7cf6263f84164a932edfa9e4deb56bd21197eb4bc5d56bac503b7a`).
All 13 prefix decisions, the pinned target identity, and both search attempts
remain exact.

Schema-v18 discard attribution:

- Total target time: **298.35111329999927 seconds**; candidate generation:
  **261.7304256993957 seconds**.
- Exactly **682,505** discard projections performed **682,505** active-Joker
  selections and application calls, but selected and applied **zero** discard
  Jokers.
- State-shell copying is the largest discard subowner at
  **34.927474298587185 seconds**, but widening into its named collection-copy
  responsibilities is explicitly out of scope.
- The largest safe redundant owner is context preparation at
  **7.1288739017472835 seconds**: it constructs hand rules, evaluates the
  discarded hand, and allocates a Joker context despite the exact empty active
  set. Empty Joker application adds 0.6197887022863142 seconds.
- Joker graph cloning remains required for output isolation; discard side-effect
  finalization remains required for Purple Seals, destruction, discard-pile,
  and discard-use semantics.

Empty-active discard optimization gate:

- Commit `49e758db33054040e190a36fa62bc6a8e5724282`.
- The canonical discard projector now skips hand evaluation, Joker-context
  construction, and the empty application loop only after exact active-Joker
  selection returns empty. State-shell copying, Joker graph cloning, and every
  discard side effect remain on the canonical path.
- Exact before/after public state matches for the inert forced-discard path;
  returned Jokers remain detached from the parent. Player/Hook discard-use,
  Purple Seal, active Joker, and Blueprint-copy fallback regressions are green.
- Focused local validation: **63 passed in 1.33s**; broader affected projection
  validation: **148 passed in 2.64s**.
- GitHub Actions run `37466943628`, job `112280263173`.
- Actual job log: **3164 passed, 1616 deselected in 197.34s**.

The post-optimization schema-v18 report is committed at
`docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_DISCARD_V18_POST_INERT.json`.
Its canonical 5,933-byte report has SHA-256
`fe46d20819f5362beed09ba76e65a9df7bf57f28dac5f90a224a4a3fd7531ed7`;
the repository copy includes a terminal newline (5,934 bytes, SHA-256
`ffddcb1f5c57d125192e3c4bf4990151eaaf4a27b6c8b2279cc522c1487f126d`).
The full frozen target identity, cache/branch/outcome accounting, and search
attempts remain exact.

Post-optimization comparison:

- All **682,505** active-Joker selections still select zero Jokers; context
  preparation and Joker application fall from 682,505 calls each to exactly
  zero.
- The directly attributed discard pipeline (parent plus all six subowners)
  falls from **53.94128589928732** to **48.57139330080827 seconds**
  (**9.9551% lower**).
- The sample ran under slower surrounding machine conditions: total target time
  rose from 298.35111329999927 to 310.44034400000237 seconds and candidate time
  from 261.7304256993957 to 270.1883482000703 seconds. Those aggregate values
  are not claimed as a speedup or regression; the exact owned pipeline delta is
  the valid comparison.
- Decision 12 is now fully attributed through its safe optimization boundary.
  Named non-card collection copying remains intentionally untouched.

Bounded second-batch resume boundary:

- The required campaign-v12 checkpoint preflight matched exactly: 46,954,547
  bytes, SHA-256
  `872f3be2dbce3e860b1151edef810df27157858e8f5202799869a75500038a4c`,
  one completed batch, 2,268 collected / 2,048 consumed transitions, and next
  episode indices 312..319.
- The eight-worker one-additional-batch resume stopped fail-closed after
  **60.2378246 seconds** when a worker reached the unowned tactical discard
  redraw for `The Wheel`. The ordered wave was not admitted; checkpoint and
  progress bytes and hashes remain unchanged.
- Read-only ordered isolation from the same trained checkpoint proves episode
  312 / seed `61B70EF9` completes in 3 decisions. Episode 313 / stream 1 / seed
  `88DB75F5` is the earliest failure and raises the exact Wheel discard boundary.
- This is a narrow missing R4 redraw owner. The existing R2 Wheel start already
  owns the keyed `wheel` RNG, physical draw order, 1-in-7 face-down predicate,
  policy masking, and cleanup semantics.

Wheel tactical-redraw gate:

- Commit `9052c97dafe65b6ecca2d52078ffcd2605b6e9c5`.
- The canonical facing owner now replenishes both Wheel play and discard draws
  from retained physical draw-pile order and consumes exactly one keyed
  `wheel` poll per replacement before public hand sorting.
- Selected hidden Wheel cards are revealed before hand evaluation. Retained
  hand-card facing is unchanged, newly hidden identities remain masked from the
  policy, and invalid Boss/resource/zone state fails atomically without RNG
  advancement.
- The deterministic episode-313 regression uses seed `88DB75F5`, crosses both
  Wheel redraw boundaries without changing the prior strategic decisions, and
  completes after 13 decisions as an Ante-1 loss with score 364.
- Focused local validation: **43 passed, 34 deselected in 5.31s**. Broader
  affected Boss lifecycle validation: **80 passed in 5.78s**.
- GitHub Actions run `37473389349`, job `112302411629`.
- Actual job log: **3170 passed, 1616 deselected in 205.07s**.

Post-Wheel bounded campaign boundary:

- The exact eight-worker one-additional-batch command resumed the verified
  campaign-v12 artifact and durably committed 96 further complete episodes
  before the next fail-closed wave.
- The valid checkpoint is now 53,677,812 bytes with SHA-256
  `e2c75781f556bf197c0c5edce4c98fd2761550fb439aaf1d8a770a6246745a64`.
  Progress names the same hash, one completed batch, 2,922 collected / 2,048
  consumed transitions, and next episode indices 408..415.
- The failed ordered wave was not admitted. Read-only sequential isolation from
  that trained checkpoint proves episodes 408 through 412 complete. Episode
  413 / stream 5 / seed `DDE9AB93` is the earliest failure and raises the
  active `The House` play boundary.

House play-facing gate:

- Commit `afc237b1f7c5281dee63aa4c15743ec9ddbfd73e`.
- Pinned vanilla source confirms The House keeps new hand draws face-down only
  while both round hands played and discards used are zero. The canonical play
  owner now reveals selected hidden cards before classification/scoring, keeps
  unselected initial cards hidden, and draws post-play replacements face-up.
- Policy observation continues to mask only retained hidden identities; input
  state and RNG remain immutable, and facing/zone drift fails closed.
- The exact trained checkpoint completes episode 413 / stream 5 / seed
  `DDE9AB93` in 14 decisions as an Ante-1 loss with score 132. Its strategic
  actions are `SELECT_BLIND`, `END_SHOP`, `SELECT_BLIND`, `END_SHOP`,
  `SELECT_BLIND`, `BUY_VOUCHER`, `BUY_CONSUMABLE`, `END_SHOP`, `SELECT_BLIND`,
  `BUY_VOUCHER`, `END_SHOP`, `SELECT_BLIND`, `END_SHOP`, `SELECT_BLIND`.
- Focused local validation: **58 passed in 1.37s**. Broader affected play-path
  validation: **84 passed in 6.57s**.
- GitHub Actions run `37476160011`, job `112311981772`.
- Actual job log: **3176 passed, 1616 deselected in 151.29s**.

Second optimizer-batch checkpoint:

- The exact eight-worker one-additional-batch command completed successfully.
  It committed episodes 408 through 631 inclusive (224 episodes) and added
  1,703 environment transitions without another mechanics failure.
- The checkpoint is 50,131,709 bytes with SHA-256
  `8baf6ec84b6a52b142c60f74df281757de74d0873ba5f4cd9e816945b5f6e631`.
  The 670-byte progress manifest has SHA-256
  `1e4e9d080ce8653fb299d59caf1c09b0e923ad02bab63f37dfa5883183387638`
  and names the same checkpoint hash.
- Exact state: two completed batches, 4,625 collected / 4,096 optimizer-consumed
  transitions, Adam step 160, next episode indices 632..639, and per-stream
  carryovers `(83, 145, 70, 41, 25, 65, 93, 7)` (529 total).
- Trained parameter SHA-256:
  `bfb43f14285cd724c54f90f3132f61dc0f67817be47347b3194b286e13154fa4`.
- The campaign CLI does not emit elapsed telemetry. The conservative interval
  from the immediately preceding roadmap commit through final artifact
  publication is at most 2,370 seconds and includes push, fetch, and preflight
  overhead. Therefore sustained collection was at least 0.0945148 episodes/s
  and 0.7185654 transitions/s. At that lower-bound rate, 1,022 remaining
  batches still project to at most roughly 33.7 days of collection, so full
  training remains unauthorized pending exact timing attribution.

Checkpoint-wave timing gate:

- Commit `6923361ceea2a0e7cd7c36b3fb1d9c73c87223fa`.
- Schema `balatro-red-white-ppo-campaign-wave-timing-v1` restores the exact
  campaign checkpoint and reuses the production environment, policy, rollout,
  and existing timed-worker owner for one ordered eight-stream wave.
- Reports bind campaign/checkpoint/training-run/policy provenance, exact episode
  and stream indices, terminal episode digests, per-episode timings, and total
  wave time. Every episode is explicitly uncommitted.
- The full restored session is canonically hashed before and after collection;
  partial/malformed results, policy mutation, clock drift, noncanonical input,
  or stream-order drift fail closed. Only a complete report is atomically
  written, and campaign artifacts are never written.
- Focused local validation: **22 passed in 11.07s**. Broader affected PPO
  validation: **49 passed in 14.62s**.
- GitHub Actions run `37510354233`, job `112429587728`.
- Actual job log: **3181 passed, 1616 deselected in 222.04s**.

Batch-2 next-wave timing evidence:

- The exact read-only eight-worker timing wave for episodes 632..639 completed
  in **30.619382000004407 seconds**. All eight episodes are complete losses and
  explicitly uncommitted; the campaign checkpoint and progress bytes, hashes,
  sizes, timestamps, counters, and next indices remain unchanged.
- The canonical 3,244-byte report has SHA-256
  `f09972189c3d558dd80337f99f2704e30e7d6dd0d4c867faa670cdc4551eee4d`.
  The repository copy at
  `docs/balatro/BALATRO_PPO_BATCH2_WAVE_632_639_TIMING.json` includes a terminal
  newline (3,245 bytes, SHA-256
  `b995a4e634f3d5a03b1e33990e763a305a7df746cc8ee833f18592ecfb385e67`).
- Per-episode seconds for 632..639 are `(3.4269816000014544,
  4.365689199999906, 1.368142400024226, 4.692953899997519,
  1.894835500017507, 29.75549409998348, 3.1748885000124574,
  7.477424499986228)`.
- Episode 637 / stream 5 / seed `4BA9B47B` is the demonstrated dominant owner:
  **29.75549409998348 seconds**, **97.1786%** of wave wall time and **3.9794x**
  the next-slowest episode, despite only seven decisions.

Checkpoint tactical-attribution gate:

- Commit `7d14b89d91f2d19658c6b88bd455e539ae0bc462`.
- Schema `balatro-red-white-ppo-checkpoint-tactical-episode-v1` restores the
  exact canonical campaign checkpoint, requires the requested episode to be
  the current pending index for its production stream, and reuses the existing
  tactical instrumentation, environment, trained policy, and rollout owner.
- Reports bind campaign/checkpoint/training-run/policy provenance, the complete
  terminal episode digest, ordered per-decision public-input digests, actions,
  selected indices, search attempts, balanced timing buckets, and explicit
  `committed=false` status.
- The restored session is canonically hashed before and after tracing. Policy
  mutation, session mutation, clock drift, timing imbalance, noncanonical
  checkpoints, episode drift, and stream-selection drift fail closed; no
  campaign artifact is written or advanced.
- Focused local validation: **7 passed**. Broader affected tactical/timing
  validation: **46 passed in 15.70s**.
- GitHub Actions run `37512036854`, job `112435369114`.
- Actual job log: **3188 passed, 1616 deselected in 138.75s**.

Immediate-fallback attribution correction:

- The first exact episode-637 trace failed closed before publication because
  production immediate-fallback candidate generation was timed while its
  enclosing `_rank_immediate_plans` search owner was not. The checkpoint and
  progress hashes, sizes, timestamps, counters, and indices remained unchanged,
  and no output report was created.
- Commit `a80c6d215c5573a2e66bc8e6a139dd25d8446cbf` instruments that canonical
  search owner. A focused regression now proves candidate generation, search
  evaluation, policy arbitration, and residual time balance exactly for this
  path; no report-side approximation or rescue layer was added.
- Broader affected tactical/timing validation: **47 passed in 14.84s**.
- GitHub Actions run `37512835152`, job `112438129938`.
- Actual job log: **3189 passed, 1616 deselected in 191.93s**.

Batch-2 episode-637 tactical evidence:

- The exact checkpoint-backed trace completed episode 637 / stream 5 / seed
  `4BA9B47B` as the same seven-transition loss previously observed. Its complete
  terminal episode SHA-256 is
  `0899f4127cfa8f6094ba49692215bde2c091af73d3bda5c0a02c70ad63eebc98`.
- The trace contains 24 ordered tactical decisions, took
  **23.848412799998187 seconds** end to end, and attributes
  **23.472520100069232 seconds** to tactical decisions. Session hashes before
  and after are both
  `c1a695faf0ccab8b9d68af96eae2e14fd0fcdad00c85f91e67d3935956afddda`;
  `committed=false`.
- The canonical 11,725-byte report has SHA-256
  `782fc0de3c97bb07f562a199ecfd1462471154074d779d4e0a884ea8c9c19840`.
  The repository copy at
  `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_TACTICAL.json` includes a
  terminal newline (11,726 bytes, SHA-256
  `593f6fd2ed1054d1a9e76fe3fd52b8c777ca060728c901939fdde0250813effc`).
- Zero-based tactical decision index 11 (the twelfth tactical decision), public
  input SHA-256
  `43da28597c26c6d105cb187b762f3cc81bf1fd13472228659fb9f2ed6a6465f4`,
  is dominant at **7.839980100019602 seconds**: **33.4007%** of tactical time
  and **32.8742%** of complete episode time. It selects `DISCARD_CARDS` indices
  `(0, 1, 3, 4, 7)` after one `(2, 292, 2000, false)` search attempt.
- Its canonical next subowner is search evaluation:
  **3.9363454995618667 seconds (50.2086%)**, ahead of candidate generation at
  **3.1596215004392434 seconds (40.3014%)**, policy arbitration at
  **0.7429765000124462 seconds (9.4768%)**, and residual at
  **0.0010366000060457736 seconds**. Decisions 11 and 14 together own
  **61.7455%** of tactical time, so the next diagnostic remains pinned to the
  demonstrated decision-11 search-evaluation owner.
- Checkpoint/progress hashes, sizes, timestamps, counters, and next indices
  remained unchanged after the trace.

Checkpoint search-subowner attribution gate:

- Commit `acfebfe075f8d24117cdaea5d44d34e541124a3a`.
- Schema `balatro-red-white-ppo-checkpoint-search-subowner-v1` restores the
  exact trained checkpoint, pins the first 12 tactical decision signatures to
  the committed episode-637 report, and reuses the existing exclusive helper
  instrumentation at zero-based target decision 11.
- The new `search_evaluation` scope times candidate generation and policy
  arbitration but disables helper accumulation inside them, leaving helper
  call counts and exclusive timings owned only by search evaluation. It records
  the residual search time without report-side estimates.
- The diagnostic replays the same trained-policy episode to a complete terminal
  boundary for its episode digest, binds checkpoint/training/policy/session
  provenance, and remains explicitly uncommitted. Prefix, stream, target,
  clock, timing, policy, terminal episode, and session drift fail closed.
- Focused local validation: **42 passed in 8.97s**. Broader affected PPO
  diagnostic validation: **54 passed in 36.23s**.
- GitHub Actions run `37518995187`, job `112459167769`.
- Actual job log: **3196 passed, 1616 deselected in 196.39s**.

Batch-2 decision-11 search-subowner evidence:

- The exact trained-policy diagnostic reproduced the pinned 12-decision prefix,
  target digest/action/indices/search attempt, and complete terminal episode SHA
  `0899f4127cfa8f6094ba49692215bde2c091af73d3bda5c0a02c70ad63eebc98`.
  It remained explicitly uncommitted; session SHA before and after is
  `c1a695faf0ccab8b9d68af96eae2e14fd0fcdad00c85f91e67d3935956afddda`.
- The canonical 5,094-byte report has SHA-256
  `f1623caf2a7c66f810f124aff0fa80dd0d9d07d2a648c9f9109f3e859a545297`.
  The repository copy at
  `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_DECISION_11_SEARCH_SUBOWNERS.json`
  includes a terminal newline (5,095 bytes, SHA-256
  `ae113ef5f9f0f0fa56cd11973cb185bddf1918798d9c2304e5e5802f1c594684`).
- Under helper instrumentation the target search evaluation took
  **8.68869749995065 seconds**. Existing exclusive helper attribution covers
  only **0.8965%**; the demonstrated dominant owner is the still-unattributed
  search-evaluation residual at **8.61080069997115 seconds (99.1035%)**.
- The largest currently measured helper, `_state_detach_card_collections`, is
  only **0.04038159968331456 seconds (0.4648%)** across 100 calls and therefore
  is not an authorized optimization target. The production call graph places
  the residual immediately under the planner estimate path entered through
  `_estimate_action`, which is not yet split by the current helper report.
- Checkpoint/progress hashes, sizes, timestamps, counters, and next indices
  remained unchanged after the diagnostic.

Planner estimate-path attribution gate:

- Commit `cfed457f6626859e7f72ec21f0a62fd82d0314ab`.
- The existing checkpoint search diagnostic now extends its exclusive helper
  stack at the production planner owner across `_estimate_action`, play/discard
  branches, recursive best-value and guaranteed-play work, evaluator projection,
  draw distribution/card reconstruction, discard projection, and estimator
  deep copies. Nested elapsed time remains exclusive and balanced.
- Candidate generation and policy arbitration remain excluded from helper
  attribution; existing candidate diagnostics retain their prior default scope.
- Focused local validation: **42 passed in 8.13s**. Broader affected PPO
  diagnostic validation: **54 passed in 32.33s**.
- GitHub Actions run `37520246148`, job `112463504931`.
- Actual job log: **3196 passed, 1616 deselected in 137.99s**.
- The first expanded trace failed closed before publication because helper
  accumulation also covered decision logic outside the timed search envelope;
  checkpoint/progress artifacts remained unchanged and no report was written.
  Commit `490be3c16fef243a69366006f908f9c757e4da96` makes the target-active
  state explicit and enables helpers only inside `rank_plans` or immediate
  fallback search, while candidate and policy work remain excluded. A focused
  regression exercises an evaluator call outside search and proves exclusion.
- Corrected focused validation: **42 passed in 10.45s**. Corrected broader
  validation: **54 passed in 31.39s**.
- Corrected GitHub Actions run `37521009246`, job `112466082351`.
- Actual corrected job log: **3196 passed, 1616 deselected in 172.06s**.
- The second expanded trace also failed closed before publication: recursive
  candidate generation was disabled for helper collection but remained inside
  its active parent estimate frame's exclusive elapsed time, so it was then
  subtracted twice from search evaluation. Artifacts again remained unchanged
  and no report was written.
- Commit `93b116b2dbe7d89937d5a5c5cdd245fb467de3fb` charges excluded nested
  candidate elapsed as child time on the active exclusive-helper frame. The
  focused regression now executes candidate generation inside `_estimate_action`
  and preserves balanced search-only accounting.
- Local broader validation: **54 passed in 34.22s**.
- GitHub Actions run `37521605140`, job `112468163846`.
- Actual job log: **3196 passed, 1616 deselected in 131.07s**.

Batch-2 decision-11 estimate-path evidence:

- The third exact trained-policy attempt completed with the same pinned prefix,
  target decision, trained policy, and terminal episode SHA
  `0899f4127cfa8f6094ba49692215bde2c091af73d3bda5c0a02c70ad63eebc98`.
  Session SHA before and after is
  `c1a695faf0ccab8b9d68af96eae2e14fd0fcdad00c85f91e67d3935956afddda`;
  `committed=false`.
- The canonical 6,045-byte report has SHA-256
  `e49beeafc47ef9aa5a3a0f65924ceddcffc3b3322eff76de047e17605298b3f1`.
  The repository copy at
  `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_DECISION_11_ESTIMATE_SUBOWNERS.json`
  includes a terminal newline (6,046 bytes, SHA-256
  `868d055c7a6355b4431dbc7ac06bc4c8e20243e02a674ab65a1d1c4918da34ef`).
- Search evaluation is **9.130538300378248 seconds** under expanded
  instrumentation. Direct estimator state deep-copying is the demonstrated
  dominant owner: **8.780730300059076 seconds (96.1688%)** across **3,403**
  calls. Estimate-play is next at only **0.18722279911162332 seconds (2.0505%)**.
- Accounting now closes: residual search evaluation is only
  **0.00013689999468624592 seconds**. Checkpoint/progress hashes, sizes,
  timestamps, counters, and indices remained unchanged.

Estimator deepcopy call-site attribution gate:

- Commit `1b7306ef1f31314c105b780d0b4c2584099482f6`.
- Checkpoint search schema v2 classifies every timed estimator state deepcopy
  by its runtime module, qualified function, source line, and active production
  estimate stack. Each sample is timed once and charged to both the existing
  canonical deepcopy owner and exactly one call-site record, without changing
  planner or environment behavior.
- Publication fails closed unless call-site calls and elapsed time exactly
  reconcile with the canonical `_estimate_state_deepcopy` helper owner. The
  checkpoint, pinned prefix, trained policy, complete terminal replay, and
  campaign immutability gates remain unchanged.
- Focused local validation: **42 passed in 7.28s**. Broader affected local
  validation: **55 passed in 26.81s**.
- GitHub Actions run `37571734757`, job `112631669469`.
- Actual job log: **3197 passed, 1616 deselected in 138.78s**.

Batch-2 decision-11 estimator deepcopy call-site evidence:

- The exact checkpoint-backed schema-v2 trace preserved the pinned 12-decision
  prefix, target action/indices/search attempt, trained policy, and complete
  terminal episode SHA
  `0899f4127cfa8f6094ba49692215bde2c091af73d3bda5c0a02c70ad63eebc98`.
  It remained explicitly uncommitted with seven environment transitions.
- The canonical 8,797-byte report at
  `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_DECISION_11_DEEPCOPY_CALLSITES.json`
  has SHA-256
  `aa76ff7740e72daf3bfdebd2854fc3776354a16798a6a005ceafe1d157b9c69e`.
- All **3,403** estimator deep copies are classified across ten exact runtime
  call-site/path groups. Their elapsed time sums exactly to the canonical
  deepcopy owner at **5.342927900492214 seconds**; residual is **0.0**.
- The demonstrated dominant owner is the recursive depth-one play-outcome clone
  in `D1LiveBlindClearPlanner._estimate_play` at
  `games/balatro/live/hand_action_planner.py:432`, on active path
  `_estimate_action > _estimate_play > _best_value > _estimate_action >
  _estimate_play`: **2,666 calls** and **4.305431399989175 seconds**. It owns
  **80.581873%** of estimator-copy time and **77.476645%** of measured search
  evaluation time.
- Checkpoint and progress sizes, SHA-256 hashes, timestamps, counters, and next
  indices remained unchanged.

Recursive terminal-play clone optimization gate:

- Implementation commit `e2581cdc490b278c2074fe3469a9cd906145a4d5`;
  CI-selector correction commit `0b10b495138114158a0461e4321aa7fccee5922e`.
- Only the demonstrated recursive depth-one play-outcome clone now uses an
  isolated shallow `BalatroState` shell before changing score and remaining
  hands. The canonical terminal evaluator is read-only over the nested graph;
  the input state and all nested aliases therefore remain unchanged.
- State subclasses and overridden terminal evaluators retain the original
  graph-preserving deepcopy fallback. Malformed unsupported objects continue to
  fail closed rather than entering the exact-state fast path.
- Focused CI-filter validation: **4 passed in 0.37s**. Broader affected local
  validation: **78 passed in 9.37s**.
- GitHub Actions run `37572976261`, job `112635524272`.
- Actual job log: **3201 passed, 1616 deselected in 121.69s**. An earlier run
  deselected the four new tests; renaming their nodes to the existing `env_ppo`
  selector corrected the gate before this checkpoint was admitted.

Post-terminal-shell estimator call-site evidence:

- The exact post-optimization schema-v2 trace preserved the pinned prefix,
  target action/indices/search attempt, trained policy, seven-transition terminal
  loss, terminal episode SHA
  `0899f4127cfa8f6094ba49692215bde2c091af73d3bda5c0a02c70ad63eebc98`,
  and identical before/after session hashes; `committed=false`.
- The canonical 8,011-byte report at
  `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_DECISION_11_DEEPCOPY_CALLSITES_POST_TERMINAL_SHELL.json`
  has SHA-256
  `3a0b7a0ed5115efa3a93203757b043e6d36b8ccf2d3c65d5f92954291fbcbca2`.
- Estimator deep copies fell from **3,403 to 624 calls** (**81.663238% lower**)
  and from **5.342927900492214 to 0.8477093002584297 seconds**
  (**84.133993% lower**), with exact **0.0** attribution residual. The optimized
  source owner covered 2,779 executions across its three observed parent paths;
  no other deepcopy source site was changed.
- Search evaluation fell from **5.557069999485975 to 0.9710263999004383
  seconds** (**82.526288% lower**). Total instrumented target time fell from
  **12.287601799995173 to 7.209747599990806 seconds** (**41.325022% lower**).
- The largest remaining individual clone site costs only
  **0.4370175001968164 seconds** (6.061481% of target time). No remaining clone
  is a demonstrated multi-second owner, so another clone optimization is not
  authorized from this evidence.
- Checkpoint and progress sizes, SHA-256 hashes, timestamps, counters, and next
  indices remained unchanged.

Post-terminal-shell batch-2 wave timing evidence:

- The exact read-only eight-worker wave reproduced episodes 632..639 with the
  same streams, seeds, action counts `(8, 5, 4, 11, 5, 7, 7, 10)`, terminal
  losses, episode digests, trained policy, and uncommitted/session-immutability
  evidence as the pre-optimization wave.
- The canonical 3,246-byte report at
  `docs/balatro/BALATRO_PPO_BATCH2_WAVE_632_639_TIMING_POST_TERMINAL_SHELL.json`
  has SHA-256
  `0afc1252592bbec6e6ce8fe57773130201d465bd7c37a129f3dd75e32094e6f6`.
- Eight-worker wall time fell from **30.619382000004407 to
  17.673559499991825 seconds** (**42.279829% lower**). Every episode improved;
  individual reductions range from 18.830400% to 43.399100%.
- Episode 637 fell from **29.75549409998348 to 16.841877500002738 seconds**
  (**43.399100% lower**). It still owns 95.294202% of wave wall time, but the
  demonstrated multi-second estimator-copy owner is removed and no remaining
  clone site exceeds 0.438 seconds in the bounded attribution trace.
- Checkpoint and progress sizes, SHA-256 hashes, timestamps, counters, and next
  indices remained unchanged. The improved representative wave authorizes one
  bounded additional optimizer batch, not unbounded training.

Bounded batch-3 attempt boundary:

- The exact eight-worker one-batch command stopped fail-closed after
  **280.2249957 seconds** at the unowned `The Mark` tactical discard
  callback/redraw boundary. The failed ordered wave was not admitted.
- Forty complete episodes, 632 through 671 inclusive, were durably committed
  before that boundary, adding 313 environment transitions. The valid checkpoint
  is 53,349,447 bytes with SHA-256
  `95d178c8731c4b9b2b41f597e9753d4c191a891465b914ee66f4dddcf18f5e79`.
  The 670-byte progress manifest has SHA-256
  `cf02d9e046efb93a5e97d77d7e4a29cbb2fae59c79dad22033aaed489daaf998`
  and names the same checkpoint hash.
- Exact durable state remains two completed optimizer batches, 4,938 collected /
  4,096 optimizer-consumed transitions, Adam step 160, next episode indices
  672..679, and per-stream carryovers `(128, 174, 99, 86, 71, 106, 128, 50)`
  (842 total). Policy SHA-256 remains
  `bfb43f14285cd724c54f90f3132f61dc0f67817be47347b3194b286e13154fa4`.
- Read-only ordered isolation from that exact checkpoint proves episode 672 /
  stream 0 / seed `AC0F67EC` and episode 673 / stream 1 / seed `8E3054C4`
  complete as losses in eight and three actions. Episode 674 / stream 2 / seed
  `977AD3AC` is the earliest failure and raises the exact `The Mark` discard
  boundary. Isolation did not change checkpoint or progress bytes, hashes,
  sizes, or timestamps.

The Mark tactical-facing gate:

- Commit `0520e22bb108003ec3105c3dabc9bd8a1e4949b2` owns the pinned
  deterministic Mark redraw lifecycle at the canonical facing, play, and
  discard boundaries. Physical deck-tail draw order is preserved; each newly
  drawn face card is hidden without RNG, retained cards keep their facing, and
  selected played cards are revealed before hand classification and scoring.
  Unsupported callback, resource, zone, and facing drift remains atomic and
  fail-closed.
- Focused Mark validation: **6 passed in 0.65s**. Broader affected R2/R4/PPO
  backend validation: **1106 passed, 3716 deselected in 27.81s**.
- GitHub Actions run `37575036618`, job `112641906914`.
  Actual job log: **3206 passed, 1616 deselected in 162.83s**.
- The exact read-only trained-policy replay now completes episode 674 / stream
  2 / seed `977AD3AC` as a 12-transition loss with 32 tactical decisions and
  episode SHA-256
  `d47ea76db7fe0d67b8dc365617b2eb6dfc083ad7a88a213a07e8b9b63c92bfbf`.
  The canonical 15,310-byte report has SHA-256
  `4cdac8a1b14cfc79e16683db608eb7122ca7512a03e287021d405bdf54820746`;
  the repository copy at
  `docs/balatro/BALATRO_PPO_BATCH3_EPISODE_674_MARK_FIXED.json` includes a
  terminal newline (15,311 bytes, SHA-256
  `5b60615ba0d1d08286a912c6d3dd82377b535b3d08ce39621cda107f74a9dd04`).
- Replay session hashes before and after are both
  `be44b4817bc994002353c9149a902c2e147695a1239eb8d365750811f0dfc338`;
  `committed=false`. Checkpoint and progress sizes and hashes remain exactly
  unchanged from the valid 632..671 boundary above.

Bounded batch-3 completion:

- The resumed eight-worker one-batch command completed cleanly after the Mark
  gate. The observed worker-start to final-checkpoint interval was approximately
  **1660.8 seconds (27:40.8)**; the campaign CLI does not publish a canonical
  elapsed-time field, so this wall interval is explicitly observational.
- Durable state is now **3 completed optimizer batches**, **6549 collected /
  6144 optimizer-consumed transitions**, Adam step **240**, and next episode
  indices `(904, 905, 906, 907, 908, 901, 902, 903)`.
- Per-stream carryovers are `(71, 120, 54, 40, 4, 43, 65, 8)` (**405 total**).
  The trained policy SHA-256 is
  `e7530802f3458cb21d088c8ccf33075d8b017581ca2e1e3a265a4d3d8fac72cc`.
- The final checkpoint is 48,856,453 bytes with SHA-256
  `70b6d867f0a0a63beb3a69e938b3557637f951de0edce12735cff017808ad340`.
  The 670-byte progress manifest has SHA-256
  `7ab00acc8b71bc17b0782d03bdd1679eb8a56538ae3b41c613428f532943dca0`
  and names the same checkpoint hash. The campaign remains incomplete by
  design; only one additional optimizer batch was authorized.

Batch-3 next-wave timing evidence:

- The exact read-only eight-worker wave covered stream-ordered episodes
  `(904, 905, 906, 907, 908, 901, 902, 903)` under trained policy SHA-256
  `e7530802f3458cb21d088c8ccf33075d8b017581ca2e1e3a265a4d3d8fac72cc`.
  All eight completed as uncommitted losses with action counts
  `(5, 11, 5, 6, 8, 7, 5, 8)`.
- Wall time was **461.17360730000655 seconds**, 26.093986 times the admitted
  batch-2 post-terminal-shell wave. This is a different trained policy and
  episode set, so the comparison identifies a new slow tail rather than a
  same-seed regression.
- Episode 908 / stream 4 / seed `FF9E2691` is dominant at
  **460.3707985999936 seconds** (**99.825921%** of wave wall time), eight
  actions, terminal loss, episode SHA-256
  `bd07be95d4c817029704391f5c4cbcc61b8d914356239c4060bc81c34ab92115`.
  Episode 907 is next at only 21.829461600020295 seconds.
- The canonical 3,246-byte report has SHA-256
  `669189e15fd8881de836959c0c0fde6f7832781d04b8835e94fa8aa1b6a339c4`;
  the repository copy at
  `docs/balatro/BALATRO_PPO_BATCH3_WAVE_901_908_TIMING.json` includes a
  terminal newline (3,247 bytes, SHA-256
  `663dcef326a3f9b5ff649741bd80c22beed4c4c136ff3b9585223dc55eea1d7c`).
- Checkpoint and progress sizes and hashes remain exactly unchanged from the
  completed batch-3 state above. No additional batch is authorized from this
  evidence.

Batch-3 episode-908 tactical evidence:

- The exact checkpoint-backed trace reproduced episode 908 / stream 4 / seed
  `FF9E2691` as the same eight-transition loss with episode SHA-256
  `bd07be95d4c817029704391f5c4cbcc61b8d914356239c4060bc81c34ab92115`.
  It contains 22 tactical decisions, took **440.5229011000192 seconds** end to
  end, and attributes **440.107706699986 seconds** to tactical decisions.
- Zero-based tactical decision 13, public input SHA-256
  `ab0790fbe59d21e18c52077a6894a4f7a4145d32901c94b39e35e1027bc346c7`,
  selects `DISCARD_CARDS` indices `(2, 3, 5)` after search attempts
  `(h2,n420,max2000,complete)`, `(h3,n1122,max2000,complete)`, and
  `(h3,n1000,max1000,budget-exceeded)`.
- Decision 13 takes **426.3605272999848 seconds**: **96.876406%** of tactical
  time and **96.785099%** of complete episode time. Its demonstrated dominant
  subowner is candidate generation at **408.3104317999969 seconds
  (95.766471%)**, ahead of search evaluation at 16.12419919995591 seconds and
  policy arbitration at 1.9241610000026412 seconds.
- The canonical 10,850-byte report has SHA-256
  `cb8cf52a3ed790940a2cc16936d89ac2eb6a28b35ee026cc2eb4e9f3aa48c22b`;
  the repository copy at
  `docs/balatro/BALATRO_PPO_BATCH3_EPISODE_908_TACTICAL.json` includes a
  terminal newline (10,851 bytes, SHA-256
  `d3394c59c1b2e41d64750dc3fd5c99c7e6db474d48c4d054402c8e14588d2855`).
- Session hashes before and after are both
  `cb226e5192c23fa465574b198bc8f093c93703b402c5a5e29e0b4a1efa07d487`;
  `committed=false`. Checkpoint and progress sizes and hashes remain unchanged.

Episode-908 candidate-subowner diagnostic gate:

- Commit `e322767e0e6e58069ea47a1f96c6da0a70a74593` extends the existing
  checkpoint attribution owner with a candidate-scope route pinned to episode
  908's first 14 tactical decision signatures and target decision 13.
- The route reuses production candidate-helper instrumentation, replays the
  complete terminal episode, and fails closed on pending-index, prefix/target,
  policy, terminal provenance, session mutation, scope, non-finite timing, or
  unbalanced helper accounting drift. It remains explicitly uncommitted.
- Focused local validation: **10 passed in 14.29s**. Broader PPO diagnostic
  validation: **59 passed in 35.78s**.
- GitHub Actions run `37604291611`, job `112735914206`.
  Actual job log: **3210 passed, 1616 deselected in 117.51s**.

Episode-908 decision-13 candidate-subowner evidence:

- The exact checkpoint-backed diagnostic reproduced the pinned 14-decision
  prefix, target digest/action/indices/three search attempts, trained policy,
  and eight-transition terminal episode SHA
  `bd07be95d4c817029704391f5c4cbcc61b8d914356239c4060bc81c34ab92115`.
  Session hashes before and after are both
  `cb226e5192c23fa465574b198bc8f093c93703b402c5a5e29e0b4a1efa07d487`;
  `committed=false`.
- Under exclusive helper instrumentation the target took
  **736.3106001999986 seconds** and candidate generation took
  **709.3464598998253 seconds**. Helper accounting closes to a residual of
  only **0.18333580199396238 seconds**.
- The demonstrated dominant owner is `_state_detach_card_collections` at
  **187.44446322350996 seconds** across **1,319,642 calls** (**26.424952%**
  of candidate time). `_discard_state_shell_copy` is next at
  147.97607499462902 seconds and `_generated_joker_projector_score` at
  103.49483380399761 seconds.
- All **1,319,642** generated-consumable transitions are exact inert; the same
  number of Hook forced branches is projected, while discard-Joker applications
  remain zero. Evaluator cache accounting is 3,500 hits / 1,765 misses.
- The first 100,000 exact-card scalar-validation samples cost only
  0.16106300035608 seconds and shallow copies only 0.08510200277669355 seconds;
  no extended-card reconstruction was observed. The dominant card-detachment
  cost is therefore repeated whole-collection traversal/identity reconstruction,
  not the already-optimized scalar helpers.
- The canonical 6,502-byte report has SHA-256
  `8b7a42e533bdb4b1b4356b6f0f05476bbd5ee3c17b0a2db3e5804c8a8ebee5a7`;
  the repository copy at
  `docs/balatro/BALATRO_PPO_BATCH3_EPISODE_908_DECISION_13_CANDIDATE_SUBOWNERS.json`
  includes a terminal newline (6,503 bytes, SHA-256
  `6235e153703f8eff6620aeeb1e2c1dae131cdb6ecb7f1fe01a4762f6289ec00b`).
- Checkpoint and progress sizes and hashes remain exactly unchanged from the
  completed batch-3 state. No additional batch is authorized.

Exact-card detachment optimization audit:

- The canonical owner and its exact inert generated-consumable/Hook discard
  call path were inspected without accepting a production change. The current
  owner already performs the minimum required fresh graph copy: one new exact
  card per unique input card plus remapping of every card-collection reference.
- An owned-deck-first two-pass implementation preserved isolation but measured
  **1.2526780999905895 seconds** versus **1.1135649999778252 seconds** for the
  current owner over 20,000 representative exact-state copies (**12.493%
  slower**). It was rejected and removed.
- C-backed mapping/list-comprehension variants were also slower. Replacing
  references in the list shells already allocated by `BalatroState.copy()`
  measured **6.43140949998633 seconds** versus **6.038698399992427 seconds**
  over 100,000 copies (**6.503% slower**). Generic graph-preserving `deepcopy`
  measured **45.450786100002006 seconds** versus **6.230268799990881 seconds**
  (**7.295x slower**).
- No cache, hidden-identity shortcut, lazy alias, production code, or test was
  retained. The worktree returned clean, so the exact decision-13 diagnostic
  and GitHub Actions were not rerun or claimed. The demonstrated detachment
  cost remains real, but no measured safe implementation improves it under the
  required per-output card-isolation contract.

Exact discard-shell optimization gate:

- Commit `9b7d0cca985ff82858e4ecdda7f46538686edae4` adds an exact
  `BalatroState.copy_for_tactical_shell` owner and routes only exact discard
  projections through it. One attribute-table copy plus explicit mutable
  gameplay-container copies replaces repeated scalar assignment and rebuilding
  of generation evidence already frozen by tactical projection.
- The fast path requires the exact state class, canonical field set, exact
  mutable-container shapes, and exact immutable policy-extension booleans.
  State subclasses, unknown fields, container subclasses, malformed extension
  values, and later shape drift retain the ordinary copy path. Blind, card-list,
  Joker-list, hand-level, discard, and shop shell semantics are unchanged;
  Joker graph cloning remains owned by the discard projector.
- A 200,000-copy runtime microbenchmark with the installed state-policy wrappers
  measured **0.4644548000069335 seconds** versus **0.5872723000065889 seconds**
  for ordinary copy (**20.912% lower**).
- Focused local alias/parity/fallback validation: **40 passed in 0.62s**.
- GitHub Actions run `37609021365`, job `112751462512`.
  Actual job log: **3210 passed, 1618 deselected in 224.85s**.

Post-discard-shell episode-908 evidence:

- The exact checkpoint-backed diagnostic preserved episode 908 / stream 4 /
  seed `FF9E2691`, the complete 14-decision prefix, target digest,
  `DISCARD_CARDS(2,3,5)`, all three search attempts, 3,500/1,765 evaluator
  cache accounting, 1,319,642 Hook branches, the eight-transition terminal
  loss, episode/policy/checkpoint hashes, and identical before/after session
  SHA-256; `committed=false`.
- `_discard_state_shell_copy` fell from **147.97607499462902** to
  **10.291453918529442 seconds** (**93.045191% lower**). Candidate generation
  fell from **709.3464598998253** to **453.6136594003183 seconds**
  (**36.051889% lower**), and total target time fell from
  **736.3106001999986** to **474.64604490000056 seconds** (**35.537252%
  lower**). Helper accounting residual is only 0.08355880016461015 seconds.
- Card detachment remains largest at 168.73725790064782 seconds, but the safe
  implementation audit above rejected every measured alternative. The next
  actionable demonstrated owner is `_generated_joker_projector_score` at
  **92.99003390062717 seconds**; all 1,319,642 generated-consumable transitions
  remain exact inert.
- The canonical 6,509-byte report at
  `docs/balatro/BALATRO_PPO_BATCH3_EPISODE_908_DECISION_13_CANDIDATE_SUBOWNERS_POST_DISCARD_SHELL.json`
  has SHA-256
  `b822838a7548c278a99ac53d3898c355850e8f2ac26b230006f24f0de5c87c87`.
  Checkpoint/progress sizes, hashes, and timestamps remain unchanged.

Exact Joker-scoring shell optimization gate:

- Commit `0bd0948eb2154e1538db94478f5eb6e35fd22412` routes only exact
  `BalatroState` inputs at `LiveJokerScoreProjector._copy_projection_state`
  through the proven tactical shell owner. State subclasses retain their
  overridden `copy()` behavior, while exact field/container drift still falls
  back inside the shell owner.
- Scoring parity, scoring-card identity, mutable gameplay-container isolation,
  Joker graph isolation, supported Joker mutation, and frozen generation
  evidence semantics are unchanged. No generated-consumable, scoring, or search
  approximation was introduced.
- Focused local validation: **61 passed in 0.80s**. Broader affected Joker
  projection validation: **179 passed in 3.91s**.
- GitHub Actions run `37611617691`, job `112759942258`.
  Actual job log: **3212 passed, 1618 deselected in 186.35s**.

Candidate-subowner accounting gate:

- Commit `7ca268244a8f02ea6c610b391635c8003bbd27fe` scopes candidate-helper
  instrumentation to the canonical `_candidate_actions` boundary. Helper calls
  elsewhere in the same tactical decision are no longer charged against
  candidate-only elapsed time; search-evaluation instrumentation retains its
  existing nested exclusion behavior.
- The deterministic regression invokes an additional generated-Joker score
  after candidate generation and proves it is excluded from all three pinned
  candidate-subowner routes. Focused local validation: **3 passed in 0.58s**.
- GitHub Actions run `37665189968`, job `112942496811`.
  Actual job log: **3212 passed, 1618 deselected in 217.91s**.

Post-scoring-shell episode-908 evidence:

- The exact checkpoint-backed diagnostic again preserves episode 908 / stream
  4 / seed `FF9E2691`, the complete 14-decision prefix, target digest,
  `DISCARD_CARDS(2,3,5)`, all three search attempts, the eight-transition
  terminal loss, episode/policy/checkpoint hashes, and identical before/after
  session SHA-256; `committed=false`.
- Correct candidate-only instrumentation records 1,312,374 exact inert
  generated-consumable transitions, 159,970 Hook branch sets, 1,312,374 Hook
  branches, and 3,490/1,745 evaluator cache hits/misses. The earlier report's
  1,319,642 transitions included 7,268 calls outside `_candidate_actions`
  (**0.550755%**); the episode SHA is unchanged, so this is the repaired
  diagnostic boundary rather than gameplay drift.
- Candidate generation fell from **453.6136594003183** to
  **279.36648330051685 seconds** (**38.413124% lower**). Total instrumented
  target time fell from **474.64604490000056** to **295.0614466999832
  seconds** (**37.835478% lower**). Corrected helper accounting closes exactly
  at 278.624115797225 measured seconds plus a 0.7423675032914616-second
  residual.
- `_generated_joker_projector_score` records 31.08582649967866 seconds versus
  the prior 92.99003390062717 seconds. That helper comparison includes the
  0.550755% scope correction above; the directly comparable outer candidate
  boundary is the authoritative improvement measure. Card detachment remains
  the largest corrected helper at 115.24145650560968 seconds, but its safe
  optimization audit already rejected all measured alternatives.
- The canonical 6,508-byte report at
  `docs/balatro/BALATRO_PPO_BATCH3_EPISODE_908_DECISION_13_CANDIDATE_SUBOWNERS_POST_SCORING_SHELL.json`
  has SHA-256
  `96935cab396f123e0ad4aa1e672ff3a3931965c410164a75f397b558477c8ab5`.
  Checkpoint/progress hashes remain exactly
  `70b6d867f0a0a63beb3a69e938b3557637f951de0edce12735cff017808ad340`
  and `7ab00acc8b71bc17b0782d03bdd1679eb8a56538ae3b41c613428f532943dca0`.

Post-scoring-shell batch-3 wave evidence:

- The exact read-only eight-worker production wave reproduced ordered episodes
  `(904,905,906,907,908,901,902,903)` on streams 0..7. Every seed, action
  count `(5,11,5,6,8,7,5,8)`, terminal loss, episode digest, checkpoint,
  policy, and before/after session hash matches the pre-optimization report;
  every episode remains explicitly uncommitted.
- Wave wall time fell from **461.17360730000655** to
  **249.28650410001865 seconds** (**45.945193% lower**). Episode 908 fell from
  **460.3707985999936** to **248.45095130000846 seconds** (**46.032426%
  lower**) and still owns 99.664822% of wave wall time. The other seven
  episodes remain bounded between 1.660514 and 15.888090 seconds; episode 904's
  0.059566-second increase is timing noise, not behavioral drift.
- The canonical 3,248-byte report at
  `docs/balatro/BALATRO_PPO_BATCH3_WAVE_901_908_TIMING_POST_SCORING_SHELL.json`
  has SHA-256
  `30d6feac77d83ce75c5bc4997e70b2e823b3ec878ced6e15b836362520c8849c`.
  Checkpoint/progress sizes and hashes remain unchanged. This exact production
  evidence authorizes one bounded optimizer batch, not unbounded training.

Bounded batch-4 Needle boundary and mechanics gate:

- The authorized eight-worker campaign resumed from completed batch 3 and
  atomically committed 489 additional transitions before stopping fail-closed
  at the next unowned boundary. Durable state remains 3 completed batches,
  7,038 collected / 6,144 optimizer-consumed transitions, Adam step 240, next
  episode indices `(976,977,978,979,980,973,974,975)`, and per-stream
  carryovers `(128,193,104,104,79,98,121,67)` (894 total). Policy SHA-256
  remains `e7530802f3458cb21d088c8ccf33075d8b017581ca2e1e3a265a4d3d8fac72cc`.
- The exact durable checkpoint is 53,883,699 bytes with SHA-256
  `085c1b104b606d91fd361c8c8fdc13471e0a3f745b8b82fd3d40ca2b819925f8`.
  Its linked 670-byte progress manifest has SHA-256
  `a09d96b2552d28b51b4dd1cc30659c44c3a402de54d6b74bc349d326d71dde79`.
- Read-only isolation proves the first pending stream episode 976 / stream 0 /
  seed `EDF19EC1` reaches active `The Needle` with exact public hand size 8,
  expected Voucher hand size 8, `boss_hands_sub=3`, and both other Boss deltas
  absent. Needle had incorrectly remained in the ordinary-discard Boss set,
  whose guard rejects every active resource delta.
- Commit `f0a662af60cefe9c2cb35aeca069952ebbedcf72` gives Needle its exact tactical
  discard guard. It requires the active unmodified Boss, authoritative
  round-reset hands, `boss_hands_sub == round_reset_hands - 1`, ordinary exact
  Voucher hand size, and absent discard/hand-size Boss deltas. Discard/redraw
  preserves the stored hands adjustment and deterministic RNG; all malformed
  states remain atomic and fail-closed.
- Focused local validation: **52 passed in 0.91s**. GitHub Actions run
  `37670304885`, job `112960066745`. Actual job log: **3218 passed, 1618
  deselected in 219.15s**.

Episode-976 Needle replay evidence:

- The exact read-only replay now completes episode 976 / stream 0 / seed
  `EDF19EC1` as a 13-transition terminal loss with 34 tactical decisions and
  episode SHA-256
  `c5848f0161d1652cb4632db9e4687bbdf50442d31052da55f1b875e9188d43d4`.
  Total elapsed time is 3.282007799978601 seconds, including
  2.7117509000818245 tactical seconds.
- Before/after session SHA-256 values are both
  `6420cc3c49b40eb61718d47b88ab3d104bb680bd84fa832e3656f04948ee4caf`;
  `committed=false`. The durable checkpoint/progress files remain byte-for-byte
  unchanged at their hashes above.
- The canonical 16,254-byte report at
  `docs/balatro/BALATRO_PPO_BATCH4_EPISODE_976_NEEDLE_FIXED.json` has SHA-256
  `92806cc8e52154b1077c4b831437776b94e491a19365bf25bf43aeb2f049c524`.

Bounded batch-4 Wheel-facing boundary and mechanics gate:

- The resumed campaign cleared the Needle wave and atomically advanced to
  7,761 collected / 6,144 optimizer-consumed transitions before stopping
  fail-closed at a Wheel play. Durable state remains 3 completed batches, Adam
  step 240, next episode indices `(1080,1081,1082,1083,1084,1077,1078,1079)`,
  and per-stream carryovers `(220,267,179,222,163,202,203,161)` (1,617 total).
- The linked checkpoint is 61,317,217 bytes with SHA-256
  `fb99e87f6b969d91a2a9e102d5ad23b59ea8df72d96df782336a5b5451df9d3e`.
  Its 678-byte progress manifest has SHA-256
  `e02dd5eac490a3a7a51fa447ad589c9483f819106e22f0bb46db59829a7fdb90`.
  Policy SHA-256 remains
  `e7530802f3458cb21d088c8ccf33075d8b017581ca2e1e3a265a4d3d8fac72cc`.
- Ordered isolation proves episode 1080 / stream 0 / seed `51547AD6`
  completes, while episode 1081 / stream 1 / seed `3F78BC58` is the first
  failure. At the exact boundary The Wheel has zero hidden cards in hand/deck,
  two authoritative face-down cards in both public/private discard, and no
  unobserved facing. Those are cards legitimately discarded face-down before a
  later play; the old play validator incorrectly admitted face-down cards only
  in the current hand.
- Commit `dc26f7381654281d3abbc1fc2063c1085ce11746` admits authoritative
  face-down cards in the exact hand or discard zones for facing Boss play.
  Face-down cards in draw/deck and unobserved face-down discard state remain
  atomic and fail-closed. Physical identity, keyed Wheel RNG, public masking,
  draw order, and discard orientation are unchanged.
- Focused local validation: **66 passed in 1.22s**. GitHub Actions run
  `37672011538`, job `112965867177`. Actual job log: **3221 passed, 1618
  deselected in 209.70s**.

Episode-1081 Wheel replay evidence:

- The exact read-only replay now completes episode 1081 / stream 1 / seed
  `3F78BC58` as a 14-transition terminal loss with 36 tactical decisions and
  episode SHA-256
  `27025bc643cf03e4d099e8dbc30641ff05d5761a460702904f8cc9a240baf1cc`.
  Total elapsed time is 4.208208900003228 seconds, including
  3.606286100053694 tactical seconds.
- Before/after session SHA-256 values are both
  `234fa39261db94cc54e0e5d6daad9eabe087105c419fb0cb9907007f196789b7`;
  `committed=false`. Checkpoint and progress bytes/hashes remain exactly at the
  durable 7,761-transition boundary above.
- The canonical 17,186-byte report at
  `docs/balatro/BALATRO_PPO_BATCH4_EPISODE_1081_WHEEL_FIXED.json` has SHA-256
  `a3127804ea765d767206c1f4c3f001efbc21412b3615eeeb0e64dac97160ecca`.

Bounded batch-4 Water boundary and mechanics gate:

- The resumed campaign cleared the Wheel boundary and atomically advanced to
  8,324 collected / 6,144 optimizer-consumed transitions before stopping
  fail-closed at a Water play. Durable state remains 3 completed batches, Adam
  step 240, next episode indices `(1168,1169,1170,1171,1172,1165,1166,1167)`,
  and per-stream carryovers `(292,349,238,276,244,273,277,231)` (2,180 total).
- The linked checkpoint is 67,105,631 bytes with SHA-256
  `44e9ffc39fbabc745f7ffeb0f6b25f6a84ef6419b4839baa7560ec20bda29e14`.
  Its 678-byte progress manifest has SHA-256
  `c570200d26b1ac0865321c92b88be6a16757bbd99f64b730cfc78d439d545314`.
  Policy SHA-256 remains
  `e7530802f3458cb21d088c8ccf33075d8b017581ca2e1e3a265a4d3d8fac72cc`.
- Ordered read-only isolation proves pending episodes 1165 through 1168
  complete, while episode 1169 / stream 1 / seed `191C744D` is the first
  failure. Its exact Water state has zero current discards, authoritative reset
  discards 3, stored `boss_discards_sub=3`, ordinary Voucher-derived hand size
  8, and no Jokers or Tags.
- Commit `93f0a00bda15c9d80e9da4b93120ac1f4798583f` adds the canonical active-Water
  resource guard beside the existing resource-Boss owners and admits Water play
  only through that guard. It requires an active unmodified Boss, authoritative
  nonnegative reset discards, an exact nonnegative stored discard adjustment,
  zero current discards, exact Voucher hand size, and absent hands/hand-size
  Boss deltas. Malformed states remain atomic and fail closed.
- Focused local validation: **61 passed in 1.01s**. GitHub Actions run
  `37673817051`, job `112972039756`. Actual job log: **3232 passed, 1618
  deselected in 127.03s**.

Episode-1169 Water replay evidence:

- The exact read-only replay now completes episode 1169 / stream 1 / seed
  `191C744D` as a 14-transition terminal loss with 23 tactical decisions and
  episode SHA-256
  `f38a16c411de221b1b294db160aa15592f3f1f9a8b147cd1097afa947967fc7d`.
  Total elapsed time is 2.2936752999958117 seconds, including
  1.8018532000132836 tactical seconds.
- Before/after session SHA-256 values are both
  `644c9a3406256ee2e6a34ee77f8c4d108f3735cf50b4b57e1618a2213ce92dfd`;
  `committed=false`. Checkpoint and progress bytes/hashes remain exactly at the
  durable 8,324-transition boundary above.
- The canonical 11,288-byte report at
  `docs/balatro/BALATRO_PPO_BATCH4_EPISODE_1169_WATER_FIXED.json` has SHA-256
  `ba8f4715e6269c81ac7554811f8e759469313442d54b8f986467d08780c9b49f`.

Completed optimizer batch 4:

- The bounded campaign completed optimizer batch 4 with Adam step 320 and
  exactly 8,192 optimizer-consumed transitions. The trained policy parameter
  SHA-256 is
  `7591307d0d81c26febaf5dd8faafa1f39bfcada14e85342c52ccf90c366f108e`.
- Canonical `--maximum-batches` semantics are incremental per invocation, not
  an absolute completed-batch target. The roadmap-prescribed value 4 therefore
  left the resumed process eligible for three more updates. It was interrupted
  after two post-update episode waves had committed, before any fifth optimizer
  update. Those 106 valid post-batch-4-policy transitions are retained rather
  than destructively rewriting the artifact history.
- The authoritative durable state is consequently 4 completed batches, 8,738
  collected / 8,192 optimizer-consumed transitions, Adam step 320, next episode
  indices `(1216,1217,1218,1219,1220,1221,1222,1223)`, and per-stream
  carryovers `(90,147,22,66,35,77,82,27)` (546 total).
- The linked checkpoint is 50,306,968 bytes with SHA-256
  `f5f71cbe8afa8800f6f9d62e4a910b954f703bfe1ddc0d507ce49b5b9abb181f`.
  Its 678-byte progress manifest has SHA-256
  `7d131681a49c4ebda8a1d3cde870d743b733233cf13fc23189723dc82234c154`.
  The progress manifest links that exact checkpoint digest; no campaign process
  remains active.

Bounded batch-5 Mark-facing boundary and mechanics gate:

- The first batch-5 wave stopped before any commit with the completed-batch-4
  checkpoint unchanged. Ordered read-only isolation proves episodes 1216 through
  1222 complete, while episode 1223 / stream 7 / seed `5F612C4C` is the first
  failure.
- At the first boundary, the defeated Mark had left three authoritative
  back-facing face cards in the repopulated shop deck. Permanent `owned_deck`
  aliases exposed those transient facing assignments beside known rank/suit and
  the encoder correctly failed closed. After shop exit, two were dealt face-up;
  the remaining authoritative back-facing draw card was inert but the ordinary
  Play guard rejected it before the canonical draw owner could flip it on hand
  entry.
- Commits `dd366cd2d88f8231053636a00ac4a6fa1bd9ae6b` and
  `d5cec03db5b63b618ecf63a196f29091f58ceddd` repair the two canonical owners.
  Public deck-composition views clone and clear only back-facing card orientation,
  preserving known composition, private identity-to-orientation masking, source
  immutability, and the established alias contract for ordinary face-up cards.
  Ordinary Play admits authoritative observed back-facing cards only while they
  remain in both public/private draw zones; the existing deal owner flips them
  face-up on entry. Hidden hand/discard state and unobserved or zone-inconsistent
  facing remain fail closed.
- Focused local validation after the CI compatibility correction: **77 passed in
  1.34s**. GitHub Actions run `37718739384`, job `113121225831`. Actual job log:
  **3235 passed, 1618 deselected in 216.08s**.

Episode-1223 Mark-facing replay evidence:

- The exact read-only replay now completes episode 1223 / stream 7 / seed
  `5F612C4C` as a 17-transition terminal loss with 31 tactical decisions and
  episode SHA-256
  `95ecfac115e89f87fd61ab85915f0eb024e6be3507521075f36204e12810d830`.
  Total elapsed time is 2.778464000002714 seconds, including
  2.1484955001214985 tactical seconds.
- Before/after session SHA-256 values are both
  `5af9b810cd5283a48110384b30944fc7f12ce935dcdc96d92c22bd2c9d9d3265`;
  `committed=false`. The completed-batch-4 checkpoint/progress pair remains
  byte-for-byte unchanged at the hashes above.
- The canonical 14,905-byte report at
  `docs/balatro/BALATRO_PPO_BATCH5_EPISODE_1223_MARK_FACING_FIXED.json` has
  SHA-256
  `822e20a6cbe39acdc507a8dcaba9f45c98412da673130a02456565d9b429a84e`.

Completed optimizer batch 5 / development handoff checkpoint:

- The corrected one-batch resume completed optimizer batch 5 and exited without
  collecting beyond its authorized optimizer boundary. It crossed episodes
  1216 through 1482 after the Mark-facing repair without another unsupported
  mechanic.
- Authoritative state is 5 completed batches, 10,706 collected / 10,240
  optimizer-consumed transitions, Adam step 400, next episode indices
  `(1488,1489,1490,1483,1484,1485,1486,1487)`, and per-stream carryovers
  `(75,138,5,57,3,88,80,20)` (466 total).
- The trained policy parameter SHA-256 is
  `0844424f528c14d52943319697321292b7f7bd9663fd871cf4a9fc3c0c5c580b`.
  The linked checkpoint is 49,484,440 bytes with SHA-256
  `56150ee4f64b382e5912b3898b940294bebc2bed15343a8145b025c361208df7`.
  Its 680-byte progress manifest has SHA-256
  `b72ef8d3af3183a82691081f991aa74299693e86987508f39aa68f9b975ccece`
  and links that exact checkpoint digest.
- The Red/White headless PPO implementation is now green for controlled training
  continuation. This does not mean the policy is trained or promoted: 37 of the
  frozen 1,024 optimizer batches are complete. Later training may still expose a
  rare fail-closed mechanic, which reopens development at that exact boundary.

Completed optimizer batch 6 / batch-7 Wall boundary:

- The authorized four-batch training chunk completed optimizer batch 6, then
  atomically committed additional batch-7-policy waves before stopping
  fail-closed at active `The Wall`. Durable state is 6 completed batches, 13,765
  collected / 12,288 optimizer-consumed transitions, Adam step 480, next episode
  indices `(1912,1913,1914,1907,1908,1909,1910,1911)`, and per-stream
  carryovers `(190,276,124,212,122,200,220,133)` (1,477 total).
- The trained policy parameter SHA-256 is
  `3639ab71f4fad1c38b67a2223c87076790a0930987940c0513e46e024c664fef`.
  The linked checkpoint is 59,878,714 bytes with SHA-256
  `332a57fe5a1c4a424683ce4353e89a970e1037e4f4b1e88e9f9e3c438242bb90`.
  Its 680-byte progress manifest has SHA-256
  `f470fe3bcc3ab998e9f7cda0d27bbeeb0cd6582bdecffadd0e56602fdb277e4a`
  and links that exact checkpoint digest.
- Ordered read-only isolation proves episodes 1907 through 1910 complete, while
  episode 1911 / stream 7 / seed `604F1347` is the first failure. Wall's only
  active mechanic is its already-generated 4x blind requirement; its start,
  discard, defeat, and requirement generation were already exact, but Play had
  remained absent from the admitted Boss set.
- Commits `44daadf3b7b0f3440cec2530739bc14ab381d787` and
  `db1dbd44cb8855ae8556a408e667f8825513558a` centralize the canonical
  Wall/Violet requirement-only family at the Boss-requirement owner and admit
  Play only when the active requirement and `blind_score` equal the exact
  Red/White target and all Boss resource adjustments are absent. Unknown Bosses
  and malformed targets remain atomic and fail closed.
- Focused local validation: **111 passed in 1.79s**. The first Actions run
  `37725408400` correctly failed collection because one existing test still
  imported the retired private constant (**1618 deselected, 1 error in
  12.26s**). After the canonical-import correction, GitHub Actions run
  `37725669607`, job `113143140647`, passed with **3242 passed, 1618 deselected
  in 214.76s**.

Episode-1911 Wall replay evidence:

- The exact read-only replay now completes episode 1911 / stream 7 / seed
  `604F1347` as a 14-transition terminal loss with 33 tactical decisions and
  episode SHA-256
  `36beb3d6b96e6c0c0042906c37df80a46a65050747863c3dc4f690988efd7982`.
  Total elapsed time is 4.317668699979549 seconds, including
  3.7212461000308394 tactical seconds.
- Before/after session SHA-256 values are both
  `5134bf980fdbe990454efc293e06104dc98125e580334df246263c65b6f56303`;
  `committed=false`. The batch-6 checkpoint/progress pair remains byte-for-byte
  unchanged at the hashes above.
- The canonical 15,820-byte report at
  `docs/balatro/BALATRO_PPO_BATCH7_EPISODE_1911_WALL_FIXED.json` has SHA-256
  `c16046ca90ead07dc4165f1f7c402c2d5b659c54fc1f39c2121ce54825e9c52c`.

Completed optimizer batches 7 through 9:

- The corrected three-batch resume completed every remaining optimizer update
  in the authorized chunk and exited at its exact batch boundary without another
  unsupported mechanic. Durable state is 9 completed batches, 18,938 collected
  / 18,432 optimizer-consumed transitions, Adam step 720, next episode indices
  `(2592,2593,2594,2587,2588,2589,2590,2591)`, and per-stream carryovers
  `(80,154,1,102,18,63,82,6)` (506 total).
- The trained policy parameter SHA-256 is
  `f7d5982b35ea58cdf3f26525e8277826ab72eee4e16a12bf59d1ebe2adf29966`.
  The linked checkpoint is 49,895,515 bytes with SHA-256
  `966f582d3def982f93e52c9692dc38a216be4b5d2900c9791a64b8f7f084bfb3`.
  Its 680-byte progress manifest has SHA-256
  `e1f31d642a24548498b49845b1ae387f8d4dd6dbe85667d9d308df27db272c7a`
  and links that exact checkpoint digest. The campaign remains incomplete, as
  required; no final artifact exists and no campaign process remains active.

Continuous-training deliberate stop / batch-37 recovery checkpoint:

- The operator-managed loop advanced without an unsupported mechanic from batch
  9 through completed batch 37. The process was no longer active when inspected;
  this was an interrupted publication boundary rather than a gameplay failure.
- `checkpoint.json` had atomically committed one more episode than
  `progress.json`: the stale manifest reported 78,014 collected transitions and
  stream-6 next index 10,070 while pointing at checkpoint SHA-256
  `93c38051bd6c897d987db1146ae52e6e2d661e6061a09ed90349ffc74dc0c25e`.
  The newer checkpoint restored canonically with 78,021 transitions and stream-6
  next index 10,078. Every other stream index, batch/optimizer count, and
  provenance field was unchanged.
- Commit `e33c422d6b8f3b47e9a6257135a2d77957d896a0` closes this exact
  two-file crash window at the campaign artifact owner. Resume now rebuilds a
  missing manifest and repairs only an exact one-episode-stale canonical
  manifest: one stream advances by eight, transition delta is 1..4,096, and
  optimizer/batch deltas are exactly consistent. Cross-run, noncanonical,
  multi-episode, ahead-of-checkpoint, or otherwise malformed mismatches remain
  fail closed and unchanged.
- Focused local validation: **19 passed in 0.75s**. GitHub Actions run
  `37917460295`, job `113777025191`, passed with **3248 passed, 1618 deselected
  in 216.99s**.
- The repaired authoritative state is 37 completed batches, 78,021 collected /
  75,776 optimizer-consumed transitions, Adam step 2,960, next episode indices
  `(10072,10073,10074,10075,10076,10077,10078,10071)`, and per-stream
  carryovers `(533,391,236,350,137,361,98,139)` (2,245 total). Policy parameter
  SHA-256 is
  `3c17edf8ae600d419293545266f78185e7b83700692e9c8fb9c10be81a880f32`.
- The canonical checkpoint is 67,776,281 bytes with SHA-256
  `f16b4f0c05d1c1810182b5bdfc82736e854776e7ce018c1c76bae0690995326d`.
  The atomically repaired 689-byte progress manifest has SHA-256
  `871b569aca3881262a8f3d278fad921e70f9f458dc8af745af8b01e6c4ab60de`
  and links that exact checkpoint digest. No final artifact exists.

Continuous-training batch-41 checkpoint:

- The operator-managed loop completed four more optimizer batches, advancing
  the durable campaign from batch 37 through batch 41 without exposing a new
  unsupported mechanic. No campaign process remained active when inspected.
- The stop again landed in the exact checkpoint-written/progress-not-written
  crash window already owned by commit
  `e33c422d6b8f3b47e9a6257135a2d77957d896a0`: only stream 7 advanced from
  episode index 11,063 to 11,071, adding four transitions, while batch and
  optimizer counters remained unchanged. Canonical reconciliation repaired the
  stale progress manifest without collecting an episode or changing policy.
- Authoritative state is 41 completed batches, 85,996 collected / 83,968
  optimizer-consumed transitions, Adam step 3,280, next episode indices
  `(11064,11065,11066,11067,11068,11069,11070,11071)`, and per-stream
  carryovers `(475,350,180,327,129,339,121,107)` (2,028 total). Policy
  parameter SHA-256 is
  `02ba55d1a97341f225e88f2eb21d7661523d2ca4ef4cbb1288dc24949b39260d`.
- The canonical checkpoint is 65,546,659 bytes with SHA-256
  `1ad9a97069533997ece3623782e023aa89528cd02241552516fd91ab7b44c07a`.
  The reconciled 689-byte progress manifest has SHA-256
  `51e8f36c15387dba845826a926601baf9af89f502b4451433e8b2e677301dd38`
  and links that exact checkpoint digest. No final artifact exists.

Continuous-training interrupted batch-42 checkpoint:

- The next operator-managed invocation advanced through optimizer batch 42,
  then ended during a later episode-publication boundary. The checkpoint had
  committed stream 1 episode 11,393 while the progress manifest remained one
  episode stale. This was the exact crash window owned by commit
  `e33c422d6b8f3b47e9a6257135a2d77957d896a0`; canonical reconciliation added
  11 transitions and advanced only stream 1 from 11,393 to 11,401. No campaign
  process remained active when inspected.
- The earliest pending episode 11,394 / stream 2 replayed read-only to a
  complete terminal episode with 13 tactical decisions in
  1.2986277999953018 seconds. Its episode SHA-256 is
  `2af63845facc41a61ba063dd617d62c735741d0ebac02448c44244cb3c4b86a6`;
  the checkpoint remained unchanged. This rules out an immediate deterministic
  gameplay failure at the resume boundary.
- Authoritative state is 42 completed batches, 88,533 collected / 86,016
  optimizer-consumed transitions, Adam step 3,360, next episode indices
  `(11400,11401,11394,11395,11396,11397,11398,11399)`, and per-stream
  carryovers `(526,423,245,398,174,393,196,162)` (2,517 total). Policy
  parameter SHA-256 is
  `7e84d7ce28f81be421d234add30ab8eb3e7373a665cc3cc2441e4485937905d9`.
- The canonical checkpoint is 70,574,844 bytes with SHA-256
  `5e4690db68fcce0c90103a7132a77a4719228caa131257ffec12969b54954531`.
  The reconciled 689-byte progress manifest has SHA-256
  `c985ceae8decdeb984213a9bf9765da73f63dd7e321c90f9bc7e33dfc01c1a27`
  and links that exact checkpoint digest. No final artifact exists.

Continuous-training interrupted batch-81 checkpoint:

- The continuous operator loop advanced from batch 42 through batch 81 without
  exposing a new unsupported mechanic, then ended during a later
  episode-publication boundary. The checkpoint had committed stream 2 episode
  21,682 while the progress manifest remained one episode stale. Canonical
  reconciliation added one transition and advanced only stream 2 from 21,682
  to 21,690; batch and optimizer counters were unchanged. No campaign process
  remained active when inspected.
- The earliest pending episode 21,683 / stream 3 replayed read-only to a
  complete terminal episode with 14 tactical decisions in
  1.8507737000036286 seconds. Its episode SHA-256 is
  `a7ff570a6d48501a9e3fc572edb5c4f2afb217f17042a8aa72490c831274f37b`;
  the checkpoint remained unchanged. There is no deterministic gameplay
  failure at the resume boundary.
- Authoritative state is 81 completed batches, 169,582 collected / 165,888
  optimizer-consumed transitions, Adam step 6,480, next episode indices
  `(21688,21689,21690,21683,21684,21685,21686,21687)`, and per-stream
  carryovers `(604,585,493,781,193,180,481,377)` (3,694 total). Policy
  parameter SHA-256 is
  `80e4f50c9257e17d955a8e619d3c925e1d7cc37eb45d5e83784fb00b0d4ca2c1`.
- The canonical checkpoint is 82,678,810 bytes with SHA-256
  `aaafbd988de567e3cfc9bdef321a3b5297fd7894b47fc36331894a44212308e2`.
  The reconciled 691-byte progress manifest has SHA-256
  `58d1d29a6e6fa8554eb7af77b6719b432052a87e446612e49fce4f9634a3f410`
  and links that exact checkpoint digest. No final artifact exists.

Continuous-training interrupted batch-87 checkpoint:

- The next continuous run advanced from batch 81 through batch 87 without a
  new unsupported mechanic, then ended during an episode-publication boundary.
  The checkpoint had committed stream 0 episode 23,152 while the progress
  manifest remained one episode stale. Canonical reconciliation added seven
  transitions and advanced only stream 0 from 23,152 to 23,160; batch and
  optimizer counters were unchanged. No campaign process remained active.
- The earliest pending episode 23,153 / stream 1 replayed read-only to a
  complete terminal episode with 10 tactical decisions in
  0.7447734999877866 seconds. Its episode SHA-256 is
  `4bda0a8c85b92b86295afaf017bb1ea17fc250d00e800002397e71303a64826b`;
  the checkpoint remained unchanged. There is no deterministic gameplay
  failure at the resume boundary.
- Authoritative state is 87 completed batches, 180,965 collected / 178,176
  optimizer-consumed transitions, Adam step 6,960, next episode indices
  `(23160,23153,23154,23155,23156,23157,23158,23159)`, and per-stream
  carryovers `(504,540,383,724,58,67,242,271)` (2,789 total). Policy parameter
  SHA-256 is
  `edb9441c491285aa24aa7a242318fafb206b8c98aeeccb351c8e49635fa1adee`.
- The canonical checkpoint is 73,372,303 bytes with SHA-256
  `099e3d9f356eb006100174df9bfefc2e37615d14c2a7592a45ba50e6892bc30c`.
  The reconciled 691-byte progress manifest has SHA-256
  `c4e4e265fbf1689b7c120f9750187fdf9934aa0e518d2e61a466a94899772174`
  and links that exact checkpoint digest. No final artifact exists.

Windows atomic-publication access-denial fix:

- The next attempted resume made no artifact progress and exposed the actual
  recurring stop cause: Windows raised `PermissionError: [WinError 5] Access
  is denied` while replacing `.progress.json.tmp` with `progress.json`. The
  previously observed one-episode-stale manifests were therefore interrupted
  two-file publications, not gameplay failures. All eight episodes in the
  pending batch-87 wave replayed successfully and left the checkpoint
  unchanged.
- Commit `97594716dd2542553ac32cb6c648229e4da32fac` fixes the canonical atomic
  artifact writer. A completed and fsynced temporary file now retries only
  `PermissionError` from `os.replace`, for at most 20 attempts with bounded
  exponential delays totaling 4.125 seconds. Other errors remain immediate;
  persistent access denial preserves the prior destination, removes the
  temporary file, and fails closed.
- Focused local validation: **21 passed in 0.77s**. GitHub Actions run
  `38058016898`, job `114230353655`, passed with **3250 passed, 1618 deselected
  in 224.11s**. The authoritative campaign remains at the exact batch-87
  checkpoint above and is ready to resume.

Continuous-training batch-211 short-redraw gate:

- The operator-managed loop advanced from batch 87 through batch 211, then
  stopped fail-closed at the first unowned mid-blind short redraw. The linked
  checkpoint/progress pair is canonical and unchanged by diagnosis: 211
  completed batches, 437,416 collected / 432,128 optimizer-consumed
  transitions, Adam step 16,880, next episode indices
  `(55872,55873,55874,55875,55876,55869,55870,55871)`, and per-stream
  carryovers `(731,590,788,1029,202,586,797,565)` (5,288 total). Policy
  parameter SHA-256 is
  `377cbe8a4ca1b31e49cda3cfb6a5efe71b556fde9a4b46597ff7d9e3b9790a86`.
- The 99,069,702-byte checkpoint SHA-256 is
  `d88110d75d0b284bb6e046237c96b4c59ff8cdaae1252274b903f037f1c992ef`.
  The 692-byte progress manifest SHA-256 is
  `235bd67687432322443e91f6d79fe9cfbae473ebd8ecc477ed0c58a2fee801b3`
  and links that exact checkpoint digest. No final artifact exists.
- Ordered read-only isolation proves episodes 55,872 / stream 0 and 55,873 /
  stream 1 complete. Episode 55,874 / stream 2 / seed `17A791BE` is the first
  failure. Against The Hook, a five-card play plus Hook's two exact forced
  discards leaves one held card and five cards in the draw pile. Vanilla draws
  those five remaining cards without a mid-blind reshuffle and continues with a
  six-card final hand; the old Play owner incorrectly required a full
  eight-card refill.
- Commit `a59e3a964f80d77d4f33151800f5a0033e171557` makes the canonical Play
  transition consume the available physical draw-pile tail up to hand capacity.
  It preserves physical order, public canonicalization, RNG, input isolation,
  and every existing Fish/Wheel/Mark facing owner. A deterministic Hook
  regression pins the exact five-card remainder and six-card continuation.
- Focused local validation: **62 passed in 3.84s**. Full R4 transition
  validation: **177 passed in 8.13s**. The exact checkpoint-backed episode
  55,874 replay now completes as a 13-transition loss with episode SHA-256
  `1c773e62077c0242dc2b685cf756ada6b8020403de43e32d1d2a73409cd3ef51`;
  `committed=false` and the campaign checkpoint remains unchanged.
- GitHub Actions run `38431523581`, job `115414640257`. Actual job log:
  **3251 passed, 1618 deselected in 210.14s**.

Frozen PPO training completion:

- The operator-managed `RED-WHITE-PPO-V1` campaign completed the frozen
  1,024-batch schedule with `complete=true`. The final checkpoint restores
  through the canonical learner owner with 2,104,439 collected environment
  transitions, exactly 2,097,152 optimizer-consumed transitions, and Adam step
  81,920.
- Final next episode indices are
  `(267304,267305,267306,267307,267308,267301,267302,267303)`. Per-stream
  carryovers are `(763,1372,705,1520,1,589,1228,1109)` (7,287 total).
- Final policy parameter SHA-256 is
  `c544a516bc3263f482c676f913fe678dc948f5943b08c44eb32cdc41a859d5bb`.
  The 119,632,012-byte checkpoint SHA-256 is
  `1b0cc0d872b0a7f2625f746dcab97b90026b69093863f3d8e9f5f7a88c7b654d`.
  The 702-byte progress manifest SHA-256 is
  `411dc42cad6e76fb4a02ef6ab85b995b5c1160414deffe8a033b1a98bf89b580`
  and links that exact checkpoint digest.
- The first final invocation correctly failed closed because a four-batch
  request exceeded the two batches remaining in the frozen schedule. A bounded
  two-batch invocation then completed batches 1,023 and 1,024 with exit code
  zero. This was a schedule-boundary command correction, not a mechanic or
  checkpoint failure.
- Training results have not been inspected or tuned. The learned policy remains
  an unpromoted candidate until the frozen evaluation contract is executed by a
  canonical checkpoint-bound candidate owner.

PPO candidate provenance and scheduling checkpoint:

- `ppo_campaign.load_completed_ppo_campaign` now restores only a complete,
  canonical `checkpoint.json` / `progress.json` / `final.json` set. It verifies
  all three artifacts byte-canonically, restores the canonical learner, requires
  the frozen schedule end, and binds checkpoint, progress, final, training-run,
  and policy-parameter SHA-256 identities without a caller-supplied rescue path.
- `ppo_candidate_evaluation` adds a separate versioned candidate arm without
  weakening or rewriting either frozen baseline schema. Candidate identity binds
  the completed campaign, promotion contract, observation/action schemas, and
  exact Red/White/normal scope.
- Fixed and fresh-unseeded candidate schedulers each require all 64 paired game
  seeds in canonical order. Candidate policy sampling uses a separately derived,
  replayable evaluation stream bound to the corpus/manifest; it does not reuse
  training rollout randomness or either baseline's policy seed.
- Missing/reordered evidence, stale artifact linkage, noncanonical JSON,
  incomplete training, policy/schema drift, empty legal masks, malformed seeds,
  nonterminal results, and executor type drift all fail closed.
- Focused local validation: **88 passed in 1.52s**. No real candidate or
  baseline promotion episode has been executed or inspected.

PPO evaluation executor and promotion-report checkpoint:

- `ppo_candidate_evaluation` now executes a restored candidate through the exact
  `PPOHeadlessBackend` from reset to a terminal boundary. The executor binds the
  completed campaign identity, isolated evaluation policy stream, exact backend
  schema, game seed, action count, and immutable reset-to-terminal frame trace;
  truncation, action-cap exhaustion, nonterminal completion, model/backend drift,
  malformed provenance, and unsupported/illegal mechanics fail closed.
- `evaluation_diagnostics` now owns policy-neutral terminal trace metrics. Both
  the frozen baseline diagnostics and the candidate diagnostics derive Ante-8
  clear, Ante reached, blind-requirement progress, and cash metrics from that
  single canonical owner.
- `ppo_promotion` adds complete fixed/fresh candidate execution bundles and the
  versioned promotion decision report. The report requires one fixed arm plus
  four unique paired unseeded manifests, applies every unchanged
  `B0_PROMOTION_CONTRACT` clear-count, minimum-rate, absolute-delta, one-sided
  Wilson, per-evidence-set secondary-regression, and zero-tolerance pathology
  gate, and rejects ordering, provenance, source-digest, gate, or decision
  tampering.
- Focused local validation: **139 passed in 7.53s** across the frozen B0
  schedulers/baselines, diagnostics, campaign loader, candidate executor, and
  promotion report. No real candidate or baseline promotion episode has been
  executed or inspected.
- GitHub Actions run `43461291480`, job `132008579076`, passed the pushed
  checkpoint at commit `ab066686`: **3285 passed, 1618 deselected in 173.00s**.

## Atomic promotion-evaluation owner checkpoint

- `ppo_promotion_evaluation` now owns exact random-legal and conservative
  symbolic baseline execution over `PPOHeadlessBackend`, including complete
  reset-to-terminal traces and canonical baseline diagnostics. The frozen
  symbolic authority selects the ordinary Blind, delegates non-pack shop
  choices to `BalatroShopPolicy`, never opens a Booster, and otherwise fails
  closed rather than using hidden pack choices or a fallback action.
- One versioned evaluation identity binds the trained candidate, promotion
  contract, fixed corpus, both baseline versions, symbolic authority, and four
  fresh unique manifests. The owner schedules all **960** episodes: 64 fixed
  candidate, 128 fixed baseline, 256 fresh candidate, and 512 fresh baseline.
- No source or outcome artifact is published until every arm and every frozen
  gate completes. The owner then writes 27 canonical indexed artifacts into a
  private staging directory and atomically publishes the directory plus its
  final digest index. Existing complete publications resume by verification
  without rerunning; incomplete or tampered publications fail closed.
- The production CLI emits outcome-free arm progress (`completed_arms / 10`)
  and reveals the decision only after atomic final publication.
- Focused local validation: **50 passed in 86.90s** across atomic execution,
  promotion, candidate, and diagnostic owners; the final progress-reporting
  regression rerun passed **6 tests in 78.67s**. No production promotion episode
  has been executed or inspected.
- GitHub Actions run `43463744422`, job `132017216593`, passed the pushed atomic
  owner at commit `b09d2dbe`: **3291 passed, 1618 deselected in 264.87s**.

First production-evaluation attempt gate:

- The run entered `fixed_baselines` and failed closed with exit code 1 before
  completing an arm or publishing the output directory. No partial outcome was
  inspected and no artifact was promoted.
- Exact exception: `dataclasses.FrozenInstanceError: cannot assign to field
  'area_index'` in `symbolic_baseline._symbolic_policy_state`. The public-state
  masker attempted in-place identity stripping on immutable generated Voucher
  metadata.
- The canonical symbolic owner now replaces dataclass items with detached
  identity-masked copies while preserving the authoritative source object.
  Focused regression validation: **10 passed in 10.87s**, including the exact
  frozen generated-Voucher case and the complete fixed baseline bundle.
- GitHub Actions run `43560464305`, job `132342758142`, passed the fix at commit
  `27e2f65a`: **3292 passed, 1618 deselected in 192.79s**.

Second production-evaluation attempt gate:

- The retry completed fixed baseline episode execution, then failed closed
  during diagnostics aggregation with exit code 1. The output directory again
  remained absent and no partial outcome was inspected.
- Exact exception: `EvaluationDiagnosticsError: frame ante must be at least 1`.
  Exact Hieroglyph/Petroglyph mechanics can authoritatively decrement an early
  run through Ante 0 (and the mechanics owner supports lower values), so the
  diagnostics owner had incorrectly imposed monotonic positive Ante progression.
- Terminal diagnostics now accept every exact integer Ante in authoritative
  frames and continue to define `ante_reached` as the maximum observed value;
  reset still must begin at Ante 1 and all other terminal/provenance checks stay
  unchanged. Focused diagnostics/aggregation/promotion validation: **30 passed
  in 5.23s**.
- The first CI attempt for this fix, run `43562474557`, was canceled by the
  workflow's 5-minute job limit rather than a test assertion. The atomic suite
  now shares its single complete synthetic 960-episode publication across
  publication/resume/tamper checks instead of executing that schedule twice;
  the retained suite passed **5 tests in 62.66s**. The deterministic workflow
  timeout is raised to 10 minutes so the expanded gate can finish without
  weakening or deselecting coverage.
- GitHub Actions run `43563203268`, job `132351244839`, passed the final retry
  gate at commit `157b9b5d`: **3292 passed, 1618 deselected in 165.10s**.

Completed frozen promotion evaluation:

- The production CLI completed all 10 arms / **960 episodes** with exit code 0
  and atomically published 28 files at
  `C:\Users\user\AppData\Local\Temp\balatro-ppo-promotion-v1-c544a516`.
  All 27 indexed artifact SHA-256 digests were independently rechecked with
  zero mismatches.
- Evaluation identity SHA-256:
  `f1db56dee4cdb30b024436fe2d4ca6f5aa5698b55e1c03748a8f60454373682e`.
  Promotion report SHA-256:
  `7485df29a7ba575cdab28676e0003a776b8dac33ce2f6bd4179f8b1c279928c2`.
- Final decision: **NOT PROMOTED**. The report passed 41 of 54 gates and failed
  13. All seven zero-tolerance pathology counts are zero; the result is a
  competence failure, not incomplete, illegal, unsupported, schema, seed, or
  diagnostic evidence.
- Fixed holdout: candidate **0/64**, random baseline **0/64**, symbolic baseline
  **0/64**. Both frozen fixed-clear nonregression gates pass. Candidate means:
  Ante `1.5`, terminal requirement progress `0.6189615885416667`, minimum cash
  `$3.171875`, and terminal cash `$11.09375`.
- Fresh unseeded evidence: candidate **0/256**, random baseline **0/256**, and
  symbolic baseline **0/256**. The candidate fails the 0.20 minimum clear rate,
  both required +0.05 deltas, and both Wilson-superiority gates.
- All Ante, requirement-progress, and minimum-cash secondary gates pass. Eight
  terminal-cash comparisons fail the allowed `-$2` bound: fixed versus symbolic
  (`-$2.890625`); manifest 0 versus random/symbolic (`-$2.234375`, `-$3.90625`);
  manifest 1 versus symbolic (`-$3.890625`); manifest 2 versus random/symbolic
  (`-$3.078125`, `-$4.46875`); and manifest 3 versus random/symbolic
  (`-$2.984375`, `-$4.25`).

Checkpoint-backed failure-trace tooling checkpoint:

- Published fixed evidence canonically selects episode 5 / seed `5C7469F4`
  and episode 15 / seed `FE32359A` as the two one-action losses, plus episode 12
  / seed `D9605DEC` as the unique longest candidate trajectory at 17 strategic
  actions.
- `ppo_candidate_evaluation` now retains the exact ordered candidate decisions
  alongside its reset-to-terminal frames. `ppo_promotion_evaluation` likewise
  retains each baseline's ordered strategic actions; neither change alters
  environment mechanics, policy sampling, or published promotion evidence.
- `ppo_candidate_trace` loads only digest-bound canonical fixed source reports,
  restores the completed checkpoint, and requires candidate and both baseline
  replays to match the published status/action count. Every candidate decision
  binds the complete observation vector and SHA-256, legal mask, masked
  probabilities, value estimate, selected action/index, and public strategic
  frame. Source, candidate, evaluation, promotion-report, ordering, probability,
  and replay drift fail closed.
- Focused local validation: **20 passed in 4.25s**. Broader fixed-evaluation,
  both-baseline, candidate, promotion, and trace validation: **69 passed in
  6.87s**.
- GitHub Actions run `43572237626`, job `132378903831`, passed commit
  `3e526d09`: **3296 passed, 1618 deselected in 215.13s**. No production
  diagnostic replay had been executed at that gate.

Completed checkpoint-backed failure trace:

- The CI-gated production replay completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_PROMOTION_FAILURE_TRACE.json`, report SHA-256
  `587171df91cc54f9a8ce72f2bb2817334ea6e95af402e2c472df792200881fed`.
  All three candidate episodes and both baseline replays reproduced their
  digest-bound published status and action count exactly.
- Episodes 5 (`5C7469F4`) and 15 (`FE32359A`) expose only `SELECT_BLIND` at
  their sole strategic decision. Candidate, random, and symbolic therefore
  take the identical forced action and produce the identical respective
  terminal frames: Ante 1 / round 1 / `$4` / scores 204 and 212. These losses
  occur entirely inside the shared tactical blind-play authority; no strategic
  observation, action mask, sampling, or baseline choice can alter them.
- Episode 12 (`D9605DEC`) demonstrates a functioning, state-sensitive policy
  interface rather than probability collapse or illegal masking. Its learned
  shop distributions include `BUY_VOUCHER` at `0.8271` and `0.5474`, and
  `BUY_CONSUMABLE` at `0.7459` and `0.6159`; every forced blind-select and
  singleton shop state correctly has probability 1. The candidate buys two
  vouchers and two consumables, reaches Ante 2 / round 7, and loses with `$10`.
  Random reaches the same terminal blind with `$28`; symbolic loses earlier at
  round 4 with `$12`. All three still lose under the shared tactical authority.
- The candidate critic is already loss-saturated across the representative
  trajectories: every estimate lies from `-0.9197` through `-0.9868` under the
  frozen `0/-1/+1` sparse terminal reward. This is consistent with the
  promotion result's **0/960 aggregate clears across candidate and both
  baselines**, not with an unseen successful strategic mode.
- Attribution: the demonstrated primary blocker is the deterministic tactical
  blind-play competence ceiling, including two failures before PPO receives
  any strategic choice. Candidate shop overspending is a real secondary policy
  weakness, but strategic retraining, reward tuning, or promotion-threshold
  changes cannot repair the forced first-blind losses. The environment and PPO
  observation/action contracts reproduced without drift; no contract defect
  is demonstrated.

Tactical first-blind trace tooling checkpoint:

- The production tactical factory is now a named canonical owner shared by the
  training environment and diagnostics; the environment configuration itself
  is unchanged. The digest-bound tactical trace invokes each production hand
  decision once through the existing public-safe evidence transition and
  records ordered actions, resource frames, fallback candidates, projected
  scores/probabilities, search attempts, and the exact terminal transition.
- Exact authoritative counterfactual replay proves that both representative
  blinds are clearable without hidden-state policy input. `5C7469F4` diverges
  at decision 0 from production discard `(0,2,3,4,5)` to play
  `(2,4,5,6,7)` and clears in two plays at score 396 rather than losing at
  204. `FE32359A` preserves production decision 0, then diverges at decision 1
  from play `(1,2,5,6)` to discard `(0,3,4,5,6)` and clears at 348 rather
  than losing at 212.
- These are diagnostic counterfactuals, not a seed-specific rescue policy. They
  pin the first demonstrated decision divergence while leaving tactical policy
  unchanged. Focused factory/trace validation: **31 passed in 2.28s**. Broader
  backend, tactical-evidence, decision-engine, campaign, and trace validation:
  **60 passed in 8.81s**.
- GitHub Actions run `43573336508`, job `132382183164`, passed commit
  `ba8a5a49`: **3300 passed, 1618 deselected in 162.62s**. Production report
  publication was gated on this result.
- The production CLI completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_TACTICAL_FAILURE_TRACE.json`, report SHA-256
  `ea47e4281504c769e7c693ee93da1eae5e5cd80e2cbe78992a0f281ff32da01f`.
  Its source link is the verified candidate trace SHA-256
  `587171df91cc54f9a8ce72f2bb2817334ea6e95af402e2c472df792200881fed`.
  Independent inspection confirmed both production `GAME_OVER` scores
  (204/212), both exact `ROUND_EVAL` clear scores (396/348), the 300-chip
  requirement, and divergence indices 0/1.

Frozen bounded tactical experiment (`tactical-arbitration-shadow-v1`):

- Hypothesis: the current hard arbitration discards useful graded evidence in
  two distinct ways: a best immediate play at pace ratio `0.96` falls just
  below the `1.0` pace cliff and enters recovery on `5C7469F4`; a completed
  deeper discard with clear probability `0.375` is below the `0.75` clear-path
  floor and is discarded in favour of an immediate pace play on `FE32359A`.
- First retain each completed adaptive attempt's exact public action signature
  and plan values in diagnostic decision evidence. Production selection must
  remain byte-for-byte behaviorally unchanged.
- Add a shadow-only selector frozen before evaluation: prefer an immediate Play
  at pace ratio at least `0.95` over recovery; otherwise prefer the best
  completed adaptive plan when its clear probability is at least `0.25`;
  otherwise retain the production decision. It may consume only the same
  public observation and already-computed plans.
- Evaluate production and shadow policies on the promotion contract's 64 fixed
  seeds through the first blind only. Acceptance requires zero illegal,
  unsupported, incomplete, or replay-drift episodes; exact clears for both
  pinned failures; a strict first-blind clear-count improvement; and no lower
  mean terminal score or mean remaining hands/discards. Reject the hypothesis
  rather than tune thresholds after seeing the 64-seed result.

Shadow tooling checkpoint:

- `HandActionDecision` now retains the best plan from every completed adaptive
  attempt as diagnostic evidence. All production arbitration continues through
  the same owners and returns the same pinned 204/212 losses; direct timeout and
  specialized policy owners remain backward compatible.
- The shadow wrapper consumes only the current public state and the production
  decision's already-computed immediate/deeper plans. On the two pinned seeds,
  the frozen rule clears at 548 and 348 and records every selected signature and
  retained plan value; it has no seed, run, RNG, or private-zone authority.
- The report owner binds the published tactical trace and fixed 64-seed corpus,
  publishes paired actions/resources/outcomes and all predeclared acceptance
  gates, and rejects source drift. Focused rule/replay/report validation:
  **5 passed in 2.35s**. Broader shadow, tactical trace, campaign, backend,
  decision-engine, timeout, and strategy-authority validation: **69 passed in
  10.89s**.
- GitHub Actions run `43574063741`, job `132384357558`, passed commit
  `26226a9f`: **3305 passed, 1618 deselected in 163.82s**. The frozen 64-seed
  execution was gated on this result.

Completed `tactical-arbitration-shadow-v1` evaluation:

- The 128 first-blind replays completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_TACTICAL_SHADOW_REPORT.json`, report SHA-256
  `86509cbde581a94ee0a302adc6f13b049e9034f485713bab3e8752e3267326c2`.
  The report is bound to tactical trace SHA-256
  `ea47e4281504c769e7c693ee93da1eae5e5cd80e2cbe78992a0f281ff32da01f`
  and the frozen 64-seed corpus.
- Final decision: **REJECTED** with three of five gates passing. The shadow
  fixes both pinned failures and strictly improves first-blind clears from
  **62/64 to 63/64**. Mean remaining hands improves from `1.390625` to
  `1.71875`.
- It fails the two predeclared nonregression gates: mean terminal score falls
  from `390.75` to `360.78125`, and mean remaining discards falls from
  `1.890625` to `1.6875`. Episode 25 / seed `3D74174A` regresses from a 476
  clear to a 256 loss after the graded-search override at decision 1; 38 of 64
  trajectories change. The frozen thresholds will not be tuned against this
  result, and production tactical arbitration remains unchanged.
- The paired evidence also corrects the scope of the blocker: production clears
  62 of 64 first blinds, while the full promotion candidate clears 0 of 64
  games. The dominant competence loss is therefore after the first blind;
  repairing two first-blind tails cannot establish Red/White competence.

Later-blind attribution tooling checkpoint:

- The digest-bound fixed diagnostics contain exactly 2 losses at requirement
  300 and 62 post-first-blind losses. Terminal groups are: 10 at 450, 20 at
  600, 14 at 800, 13 at 1200, 4 at 1600, and 1 at 3200. This confirms that the
  full-game failure is dominated by later blinds rather than the two first-blind
  tails.
- Canonical selection (maximum post-first terminal chip margin, then earliest
  episode) chooses episode 1 / seed `F222A3BD`: Ante 1, requirement 600, score
  588, margin `-12`, and seven strategic actions. The new later-tactical trace
  owner verifies the publication index and diagnostics digests, replays those
  exact strategic actions to the terminal blind, and captures every public-safe
  tactical decision and plan value.
- Its counterfactual rule is deliberately narrow and diagnostic: at the first
  production divergence, substitute only a different already-computed plan
  that is exact with clear probability 1, then resume production decisions. It
  does not inspect the seed, RNG, private zones, or tune a threshold.
- Focused selection/distribution/counterfactual and existing trace validation:
  **16 passed in 4.56s**. Broader candidate, campaign, backend,
  tactical-evidence, decision-engine, and later-trace validation: **83 passed
  in 14.95s**.
- GitHub Actions run `43590589957`, job `132434252970`, passed commit
  `0661cf05`: **3308 passed, 1618 deselected in 181.30s**. Production trace
  publication was gated on this result.

Completed later-blind tactical trace:

- The production CLI completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_LATER_TACTICAL_TRACE.json`, report SHA-256
  `d2995f1854af16b18ae23bebe710098f3c4c456d01d32b7bbe16ec85f4b75878`.
  It binds fixed-candidate SHA-256
  `0e6868c9d783910318187ab7391925d005d6baac10ac90c853b99d7327eb49cb`
  and diagnostics SHA-256
  `a59f2ba33fe3a516ec4ea789a16252072785f982046b99d1c5f9b5aa192d7fad`.
- The report reproduces episode 1 / `F222A3BD` at The Club exactly: production
  loses 588/600. At tactical decision 3, production chooses inexact Play
  `(0,1,2,5,6)` with projected clear probability 1 and expected score 700,
  while the completed search already contains a different exact horizon-2 Play
  `(0,1,2,3,4)` with clear probability 1 and expected score 744.
- Substituting only that exact public plan and then resuming production decisions
  clears the same authoritative blind at 610. The override count is exactly one;
  no seed, RNG, private zone, reward, strategic action, or environment mechanic
  changes. This demonstrates a tactical arbitration defect: the strategy-aware
  Boss exactness downgrade discards an exact clear path, after which safe-pace
  arbitration selects an inexact alternative that loses.

Frozen bounded experiment (`boss-exact-path-preservation-shadow-v1`):

- Shadow only: at a Boss decision, when production differs from an
  already-computed exact plan with clear probability 1, choose the highest
  expected-score exact clear plan; otherwise preserve production verbatim. The
  rule consumes only the public state and retained production search evidence.
- Evaluate the trained candidate on all 64 fixed seeds with the frozen policy
  seeds and compare to the published fixed candidate. Acceptance requires zero
  illegal, unsupported, incomplete, or provenance-drift episodes; episode 1
  must clear its 600-chip Club boundary; fixed full-game clear count may not
  regress; mean Ante, terminal requirement progress, minimum cash, and terminal
  cash may not regress; and at least one of full-game clears, mean Ante, or mean
  terminal requirement progress must strictly improve.
- Reject rather than tune after the 64-seed result. Do not modify production
  arbitration until this separately versioned shadow passes.

Boss exact-path shadow implementation checkpoint:

- Commit `ee46f9601d681d65335a80c11f8f78b5d5f35357` adds the separately versioned
  shadow decision engine and report owner. It preserves production verbatim
  outside Boss decisions or when no different completed exact clear exists;
  otherwise it selects the highest expected-score completed exact clear.
- The report reruns the trained candidate on the canonical fixed 64-seed
  corpus with the frozen policy seeds, pairs every shadow result with the
  digest-bound published production result, and exposes the complete-evidence,
  pinned-Club-clear, nonregression, and strict-improvement gates.
- Focused local validation: **28 passed in 3.69s**. Broader candidate,
  campaign, backend, tactical, promotion, decision-engine, and strategy
  validation: **89 passed in 51.93s**.
- GitHub Actions run `43591631191`, job `132437402307`, passed roadmap HEAD
  `057d5727`: **3311 passed, 1618 deselected in 218.93s**. The frozen 64-seed
  report is now authorized.

Completed `boss-exact-path-preservation-shadow-v1` evaluation:

- The 64 paired full-game episodes completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_BOSS_EXACT_SHADOW_REPORT.json`, report SHA-256
  `242b057a63294087d9ba025cef5b88b8c3c680594f459d02564d9d2a96abeac0`.
  All canonical episode/game/policy seeds and both digest-bound published
  source reports verified; 11 episodes contain 12 exact-path overrides.
- Final decision: **REJECTED** with four of eight gates passing. Episode 1 /
  `F222A3BD` clears The Club's 600-chip boundary and advances from Ante 1 to
  Ante 2, but then loses the 800-chip blind at 696. Full-game clears remain
  **0/64**, so there is no strict competence improvement.
- The shadow preserves mean minimum cash at `3.171875` but regresses mean Ante
  `1.5 -> 1.484375`, mean terminal requirement progress
  `0.6189615885416667 -> 0.6184537760416666`, and mean terminal cash
  `11.09375 -> 11.046875`. Seven trajectories change terminal metrics; notably
  episodes 3 and 9 fall from Ante 2 to Ante 1. Production arbitration remains
  unchanged and this rejected rule will not be tuned.

Terminal-loss tactical census implementation checkpoint:

- Commit `713820131257bf614e5322518b3b1baae2511fad` adds a read-only fixed-corpus
  census around the unchanged production tactical engine. Every episode must
  reproduce the digest-bound published candidate result and diagnostic metrics
  before its terminal-blind evidence is admitted.
- The census records public action/plan/search evidence only, classifies losses
  by different completed exact-clear availability, budget exhaustion, and
  selected-plan exactness, and deterministically selects the closest terminal
  loss in each demonstrated class.
- Focused local validation: **23 passed in 1.65s**. Broader candidate,
  campaign, backend, tactical, promotion, decision-engine, and strategy
  validation: **92 passed in 51.37s**.
- GitHub Actions run `43592696170`, job `132440604603`, passed roadmap HEAD
  `70066288`: **3314 passed, 1618 deselected in 183.56s**. The frozen 64-seed
  census is now authorized.

Completed terminal-loss tactical census:

- The fixed 64-seed production replay completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_TERMINAL_LOSS_CENSUS.json`, report SHA-256
  `ee4c04bef116d2885890c00ebe86b0bf0496222473d37ff9cc00cac951f859e6`.
  All 64 result/action counts and diagnostic metric payloads reproduce their
  digest-bound published sources exactly; the census contains 454 terminal-
  blind tactical decisions.
- All 64 episodes lose and **none** exhausts a tactical search budget. The 39
  non-Boss losses (16 Small, 23 Big) select exact plans without a different
  exact clear. The 25 Boss losses split into 23 with an inexact selection and
  no different exact clear, plus the two known different-exact-clear cases
  (The Club episode 1 and The Pillar episode 37).
- The canonical closest inexact-selection representative is episode 0 / seed
  `9CA6BDC0`: The Psychic, requirement 600, score 579, margin `-21`. Its
  completed searches are not budget exhausted and report exact best results,
  while production repeatedly retains inexact horizon-1 decisions. This pins
  the next diagnostic to Boss-specific post-search arbitration rather than
  search capacity, PPO strategic sampling, or a non-Boss policy path.

Boss exactness-boundary trace implementation checkpoint:

- Commit `d8bab4a648c2221e18f65314a0462a96d9ac928a` adds a read-only recorder around
  the exact production `StrategyAwareLiveHandActionPolicy.decide` boundary for
  episode 0. It records the public input plans and keyword evidence before the
  owner runs and the unchanged production decision afterward.
- The trace binds the completed campaign, published fixed candidate, frozen
  corpus, and terminal-census SHA-256. It requires exact published result parity
  and exact terminal action/selected-plan parity with the census before
  admitting the first exact-input to inexact-output boundary.
- Focused local validation: **16 passed in 1.55s**. Broader candidate,
  backend, tactical, promotion, decision-engine, and strategy validation:
  **95 passed in 50.83s**.
- GitHub Actions run `43593741682`, job `132443751954`, passed roadmap HEAD
  `afa28e55`: **3317 passed, 1618 deselected in 219.96s**. The pinned
  production trace is now authorized.
- The first authorized execution failed closed before publication because its
  linkage check compared the trace's richer selected-plan payload to the
  census's compact payload as whole dictionaries. Commit
  `cc9788b0ffb8feaf071a53cf41c55c248d02a210` now requires exact equality for
  every census-owned field while permitting only the trace's additional
  diagnostic fields. Focused local validation: **17 passed in 1.54s**. A new
  CI gate is required before retrying execution.
- GitHub Actions run `43594278202`, job `132445359828`, passed roadmap HEAD
  `c93850de`: **3318 passed, 1618 deselected in 224.52s**. The corrected pinned
  trace is now authorized.

Completed Boss exactness-boundary trace:

- The corrected pinned replay completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_BOSS_INEXACT_TRACE.json`, report SHA-256
  `7ddd94f58990dcd1373860028e5df891a6b2305b6ce1c00b9276ad3ab12e3d05`.
  It reproduces episode 0 / `9CA6BDC0` / The Psychic at 579/600 and all seven
  terminal tactical decisions exactly against the census.
- The first policy decision is already the first exact-input to inexact-output
  boundary. All 10 input plans are exact; the completed horizon-2 plan is an
  exact Play with expected score 112. With `boss_projection_unconfirmed=true`,
  `StrategyAwareLiveHandActionPolicy.decide` returns an inexact horizon-1
  `PACE_RECOVERY` discard with expected score 0.
- The output rationale then enters canonical safe pace because no current Play
  meets remaining-score / hands-left pace. The trace demonstrates the
  Boss-specific exactness downgrade at the canonical owner, but does not yet
  establish that preserving exactness changes the selected action or outcome.

Frozen bounded experiment (`boss-projection-exactness-preservation-shadow-v1`):

- Shadow only: at the existing `boss_projection_unconfirmed` branch, retain the
  planner's exact flags instead of cloning all exact input plans as inexact.
  Every subsequent constraint, parent-policy, safe-pace, strategy, transition,
  and PPO decision remains production-identical.
- Evaluate all 64 fixed candidate seeds against the published production arm.
  Acceptance requires complete canonical evidence; episode 0 must clear The
  Psychic's 600-chip boundary; full-game clear count, mean Ante, terminal
  requirement progress, minimum cash, and terminal cash may not regress; and at
  least one of full-game clears, mean Ante, or mean requirement progress must
  strictly improve. Reject rather than tune after the frozen result.

Boss projection exactness-shadow implementation checkpoint:

- Commit `91517a83a41c866b8f9fc22aa8de7e11962aa8f2` adds the option at the canonical
  `StrategyAwareLiveHandActionPolicy` owner. Its default retains production's
  exact-to-inexact Boss behavior; the shadow value suppresses only that one
  demonstrated downgrade before all existing downstream arbitration.
- The separately versioned report reruns all 64 fixed candidate seeds, pairs
  each result with the digest-bound production evidence, and publishes the
  pinned-Psychic, nonregression, and strict-improvement gates frozen above.
- Focused local validation: **23 passed in 1.54s**. Broader candidate, backend,
  tactical, promotion, decision-engine, and strategy validation: **98 passed
  in 51.43s**. GitHub Actions remains required before executing the report.
- GitHub Actions run `43595096562`, job `132447806020`, correctly blocked
  execution: **2 failed, 3318 passed, 1618 deselected in 297.27s**. Both failures
  were constructor-bypassing isolated policy fixtures that lacked the new
  defaulted attribute. Commit `2a2f3b58811d9e3fc29d8a85dac0570b1f450ed0`
  now reads an absent attribute as `False`, preserving exact production
  behavior. The two failures plus shadow/strategy regressions are locally green:
  **11 passed in 1.37s**. A fresh CI gate is required.
- GitHub Actions run `43595636057`, job `132449397140`, passed roadmap HEAD
  `43b4c0ce`: **3320 passed, 1618 deselected in 218.91s**. The frozen shadow
  evaluation is now authorized.

Completed `boss-projection-exactness-preservation-shadow-v1` evaluation:

- The 64 paired episodes completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_BOSS_EXACTNESS_SHADOW_REPORT.json`, report SHA-256
  `a2eac8d31d1accea4795fbe469498419de82a2534ec72ee2e4ba90e8685290dc`.
  Complete evidence and every nonregression gate pass.
- Final decision: **REJECTED**. All 64 shadow outcomes and diagnostic metrics
  are identical to production: 0/64 clears, mean Ante `1.5`, mean requirement
  progress `0.6189615885416667`, mean minimum cash `3.171875`, and mean terminal
  cash `11.09375`. Episode 0 remains 579/600 at The Psychic, so the pinned-clear
  and strict-improvement gates fail.
- Preserving the input plans' exact flags therefore has no behavioral effect.
  The causal question moves one boundary downstream to safe-pace recovery's
  Play-versus-Discard selection; the rejected exactness shadow will not be
  tuned and production remains unchanged.

Boss safe-pace counterfactual tooling checkpoint:

- Commit `5494cb37778015619a240b0aa983ad1ee3f0439f` adds a digest-bound episode-0
  replay that reconstructs The Psychic boundary from the exact published PPO
  strategic prefix. Production and counterfactual settle independently from
  that same authoritative public state.
- The counterfactual can act only at tactical decision 0 and can select only
  the highest expected-score completed exact Play already computed by
  production; all later decisions return to the unchanged production engine.
  Missing source, plan, outcome, or exactly-one-override evidence fails closed.
- Focused local validation: **19 passed in 1.07s**. Broader candidate, backend,
  tactical, promotion, decision-engine, and strategy validation: **100 passed
  in 50.86s**.
- GitHub Actions run `43596752979`, job `132452787025`, passed roadmap HEAD
  `7e36f72d`: **3322 passed, 1618 deselected in 218.11s**. The pinned
  counterfactual trace is now authorized.

Completed decision-0 safe-pace counterfactual:

- The pinned replay completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_BOSS_SAFE_PACE_COUNTERFACTUAL.json`, report SHA-256
  `360b992c29d4a5bf7fccec57807aa915fd8a8564beab4f8615b6b3fb39781985`.
  Production reproduces the authoritative 579/600 loss and the counterfactual
  records exactly one public decision override.
- Replacing production's first `PACE_RECOVERY` discard with the already-computed
  exact horizon-2 Play (expected score 112) worsens the terminal result to
  **448/600**, a `-131` chip delta. All subsequent decisions use production.
- The demonstrated first safe-pace discard is therefore protective, not the
  cause of the near miss. Do not broaden it into a 64-seed rule. The remaining
  causal search stays pinned to later decisions in this same terminal blind.

Later-decision safe-pace sweep implementation checkpoint:

- Commit `72be6e279d07e79dbb737d02d62291231d7ca660` freezes the three eligible
  later substitutions demonstrated by the boundary trace: tactical decisions
  2, 3, and 6. Decisions 1, 4, and 5 already match their completed exact plan.
- Each arm reconstructs the same authoritative Psychic start, preserves the
  production prefix, substitutes only the highest expected-score different
  completed exact plan at its target, and resumes production afterward. Exact
  source digests and exactly one override per arm are mandatory.
- Focused local validation: **18 passed in 1.12s**. Broader candidate, backend,
  tactical, promotion, decision-engine, and strategy validation: **102 passed
  in 50.95s**.
- GitHub Actions run `43597769335`, job `132455836655`, passed roadmap HEAD
  `3df77d32`: **3324 passed, 1618 deselected in 289.18s**. The fixed sweep is
  now authorized.

Completed later-decision safe-pace sweep:

- The three fixed arms completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_BOSS_SAFE_PACE_SWEEP.json`, report SHA-256
  `0f6a97e134599805b01fa7ebbeca02e7ccc9776afbf843889c3db1e31751339a`.
  Every arm applies exactly one different completed exact plan and otherwise
  resumes production from the same authoritative Psychic boundary.
- Decision 2 substitutes an exact horizon-2 Play at score 264 and clears
  **664/600** (`+85` versus production). Decision 3 independently substitutes
  another exact horizon-2 Play at score 264 and clears **648/600** (`+69`).
  Decision 6's different exact Play worsens the loss to **444/600** (`-135`).
- Combined with decision 0's 448/600 result, the demonstrated defect is narrow:
  later `PACE_RECOVERY` discards after positive Boss-blind scoring progress can
  suppress a winning completed exact Play. Initial setup recovery and arbitrary
  Play-to-Play substitution are not safe to override.

Frozen bounded experiment (`boss-progress-exact-play-shadow-v1`):

- Shadow only: when the public state is in a Boss blind with positive score,
  production selects `PACE_RECOVERY` `DISCARD_CARDS`, and a different completed
  exact `PLAY_CARDS` plan exists, choose the highest expected-score such Play.
  Otherwise return production verbatim. No score threshold, seed, hidden zone,
  RNG, search, mechanic, or subsequent-policy change is permitted.
- Evaluate all 64 fixed candidate seeds against the digest-bound published arm.
  Acceptance requires complete canonical evidence; episode 0 must clear The
  Psychic; full-game clears, mean Ante, requirement progress, minimum cash, and
  terminal cash may not regress; and full-game clears, mean Ante, or mean
  requirement progress must strictly improve. Reject rather than tune.

Boss progress exact-Play shadow implementation checkpoint:

- Commit `c9e8784dd97fc096d5cc2344fe865c6b3c336f19` adds the separately versioned
  shadow selector and paired fixed-corpus report. The selector requires Boss,
  positive public score, production `PACE_RECOVERY` discard, and a different
  completed exact Play; all other decisions preserve production object identity.
- Every override records its public Boss/score/action/plan evidence. The report
  binds the completed campaign, published candidate/diagnostics, fixed corpus,
  and frozen policy seeds, and publishes all gates declared above.
- Focused local validation: **16 passed in 3.43s**. Broader candidate, backend,
  tactical, promotion, decision-engine, and strategy validation: **104 passed
  in 107.94s**.
- GitHub Actions run `43633127462`, job `132563939788`, passed roadmap HEAD
  `11e1f162`: **3326 passed, 1618 deselected in 206.43s**. The frozen 64-seed
  report is now authorized.

Completed `boss-progress-exact-play-shadow-v1` evaluation:

- The 64 paired episodes completed with exit code 0 and published
  `docs/balatro/BALATRO_PPO_BOSS_PROGRESS_SHADOW_REPORT.json`, report SHA-256
  `8bd3b2b3c73ecaecd428f11e799266a84c2c4315988338d57b05f8c0bca5e71d`.
  Thirteen episodes contain 25 overrides and 11 terminal outcomes change.
- Final decision: **REJECTED**. Episode 0 clears The Psychic and advances to
  Ante 2, then loses 736/1200. Full-game clears remain 0/64 and mean Ante stays
  `1.5`, so strict competence does not improve. Mean requirement progress
  regresses `0.6189615885416667 -> 0.616259765625` and mean terminal cash
  regresses `11.09375 -> 11.015625`; two episodes gain an Ante and two lose one.
- The bounded tactical rule is therefore not promotable and will not be tuned.
  Together with the two earlier rejected 64-seed tactical shadows, the evidence
  now supports returning to the demonstrated sparse-learning-signal failure
  rather than adding another action exception.

Frozen reward experiment (`balatro-red-white-progress-potential-reward-v2`):

- Preserve the current sparse v1 backend as the default. Add a separately
  versioned training-only backend reward option whose public potential is
  `round / 24` for running frames and exactly `0` for terminal frames.
- For discount `gamma=0.99`, emit
  `sparse_terminal_reward(after.status) + gamma * potential(after) - potential(before)`.
  This redistributes the same terminal objective across exact public progress;
  it does not alter mechanics, observations, legal actions, evaluation rewards,
  promotion gates, or the v1 completed campaign.
- Require exact reward-contract provenance in frame info and serialization,
  deterministic nonzero intermediate rewards, fail-closed malformed frames,
  and telescoping-return regressions. Do not start a full training run during
  this task.

Progress-reward backend implementation checkpoint:

- Implementation commit `0c4ff150901ea79fbc5998ee23fd2b7f7d195b50`
  adds the optional v2 reward at the canonical headless backend owner while
  retaining sparse v1 as the constructor default. Running potential is exactly
  `round / 24`, terminal potential is exactly zero, unknown contracts and
  malformed running rounds fail closed, and v2 snapshots bind their reward
  contract. Default and explicit sparse-v1 snapshots remain byte-identical.
- Focused deterministic backend/collector regression gate: **15 passed in
  7.92s**. The broader contract, batch, campaign, candidate-evaluation, and
  promotion-evaluation gate completed before the final test-only telescoping
  addition with **101 passed in 119.98s**. Syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `43634906518`, job `132569469289`, passed the authoritative
  Balatro deterministic gate with **3331 passed, 1618 deselected in 289.97s**.
  The optional backend is therefore green. No pilot has run yet.

Progress-reward rollout/training provenance checkpoint:

- Implementation commit `5e3df790f9b557702aed2702a79d508d85ca2b4b`
  registers a distinct immutable v2 training-contract digest and rollout
  schema. Training runs resolve only registered contracts; rollout collection
  derives its schema and action cap from that run and rejects reset or step
  frames advertising a different reward contract. Sparse v1 remains the
  default, and explicit-v1 and default-v1 training-run JSON bytes are identical.
- V2 episode serialization binds the registered training-contract digest, and
  the existing batch owner consumes shaped rewards through the frozen
  `gamma=0.99`, `lambda=0.95` GAE path. Fixed v2 advantages and returns have a
  deterministic regression.
- Focused rollout/GAE gate: **61 passed in 45.24s**. Broader backend, contract,
  batch, model, learner, session, campaign, candidate-evaluation, and
  promotion-evaluation gate: **144 passed in 96.97s**. Syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `43636137696`, job `132573237203`, passed the authoritative
  Balatro deterministic gate with **3337 passed, 1618 deselected in 221.16s**.
  The v2 backend and rollout/training provenance path are now CI-green. No
  pilot has run yet.

Progress-reward one-batch pilot implementation checkpoint:

- Implementation commit `316150817fa7c097a99dcaf2d60a9b4037167e3f`
  routes v2 workers through the same production mechanics and tactical factory
  with only the registered reward contract changed. Campaign orchestration
  preserves v1 defaults and artifacts, while v2 is executable only as one
  fresh non-resumable optimizer batch; multi-batch and resume requests fail
  closed.
- The dedicated pilot requires a fresh empty artifact directory and publishes
  a canonically serialized report linked to checkpoint/progress hashes. It
  records reward and advantage count/range/mean/variance, episode-depth
  statistics, terminal statuses, elapsed runtime, policy hashes before/after,
  exact batch/transition counters, and explicit fail-closed counters.
- Pilot/campaign safety gate: **31 passed in 0.97s**. Broader backend, contract,
  rollout, batch, model, learner, session, campaign, candidate-evaluation, and
  promotion-evaluation gate: **148 passed in 96.50s**. Syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `43637218779`, job `132576551806`, passed the authoritative
  Balatro deterministic gate with **3341 passed, 1618 deselected in 155.16s**.
  The fresh one-batch pilot runner is authorized.

Completed progress-reward one-batch pilot:

- The isolated pilot completed exactly **1 optimizer batch**, with **2243
  collected / 2048 optimizer-consumed transitions** across **285 committed
  episodes** in **1184.0724201 seconds (19:44.1)**. All 285 episodes terminated
  in `LOSS`; action depth ranged 1 through 17 with mean `7.870175438596491`.
- Reward variance is `0.14074160133962618`; advantage variance is
  `0.3975327050717248`. The policy changed from SHA-256
  `3c31dc9bac8512b3e42e628597560eaf60b238be2863f80bf0fac185a27326f6`
  to `2069d19b1a683e12047e937996a3cc8615ed923de20e707c43bba38c6e91cf03`.
  All six published fail-closed counters are zero.
- The 46,697,911-byte checkpoint SHA-256 is
  `e6e5d5831a4f6bcb5a3d53a68bb2ec2b89ab95d30ae87dca81f2b7da25cefb37`;
  the 670-byte progress SHA-256 is
  `10e7795e1ce85f9b52b9eb8f2b222702473b4d3319e2ccd23af2887d68f2070c`;
  the 1504-byte canonical report SHA-256 is
  `983ee1c6e5bb32202c1d2f7e5172c8bb364691a4afd79e1001db3ecfdfeb015d`.
  Restoring the checkpoint reproduced its counters and final policy hash, and
  all checkpoint/progress/report links verified exactly.
- Evaluation: the learning-signal gate **passes** because reward and advantage
  variance are finite and nonzero, parameters updated, and no fail-closed
  counter fired. Competence is **not established** because every pilot episode
  lost. This authorizes a paired evaluation, not more optimizer batches or a
  new full campaign.
- Published evidence commit `01ccf57e5667219761aa8baf31bc4d273929f856`
  passed GitHub Actions run `43688229315`, job `132733106758`, with **3341
  passed, 1618 deselected in 223.13s**.

Progress-reward paired-evaluation implementation checkpoint:

- Implementation commit `5e7306c3ea85c8e1b0b3195790ebd150bb8b5395`
  cryptographically loads the linked pilot checkpoint/progress/report,
  reconstructs the exact initial model from the same v2 training run, and
  restores the exact one-batch model. It evaluates both read-only on each fixed
  corpus seed with production mechanics, sparse evaluation rewards, and the
  frozen masked-greedy/lowest-index tie-break contract.
- The report binds both policy hashes and all pilot artifact hashes, publishes
  exact per-seed terminal metrics/deltas, and summarizes clears, Ante,
  requirement progress, terminal cash, and action depth. The CLI emits one
  progress record per completed seed pair; progress timing cannot enter the
  deterministic report.
- Actual pilot seed-0 smoke evidence restored the expected initial/final policy
  hashes and produced identical `579/600`, Ante-1, seven-action losses on both
  arms. Focused evaluator/pilot/candidate/diagnostics gate: **39 passed in
  4.40s**; broader PPO/evaluation gate: **170 passed in 89.47s**; final
  evaluator gate: **5 passed in 0.91s**. Syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `43689127769`, job `132735804366`, passed the authoritative
  Balatro deterministic gate with **3346 passed, 1618 deselected in 293.22s**.
  The single 64-pair read-only evaluation is authorized.

Completed progress-reward paired evaluation:

- The read-only run completed all **64 fixed seed pairs** with exit code 0.
  Its 53,453-byte canonical report has SHA-256
  `4e5bd721dc9db556b946c8e1f7651923ff947f0beda5eb4f7b9a72b9cbe01fe7`
  and exactly links the pilot training run, checkpoint, progress, report, and
  both policy parameter hashes.
- Initial versus one-batch results are **0 -> 0 Ante-8 clears**, mean Ante
  `1.515625 -> 1.515625`, mean terminal requirement progress
  `0.6345062934027778 -> 0.6328917100694444`, mean terminal cash
  `8.421875 -> 8.3125`, and mean action count `8.09375 -> 8.109375`.
- Seven episodes changed. Requirement progress improved on 2 seeds, regressed
  on 1, and tied on 61; terminal cash improved on 3 and regressed on 4. No seed
  gained or lost Ante. Independent recomputation exactly matched the stored
  aggregate deltas.
- Evaluation: one batch is **not an improvement checkpoint** because clears and
  Ante are unchanged while aggregate requirement progress and cash regress.
  The v2 learning signal remains real and nonzero, so this rejects immediate
  promotion/full training but permits one capped staged learning-curve study.
- Published evidence commit `ede70eda6a34b7d8087135b9ef899b03b55da7f1`
  passed GitHub Actions run `43689888402`, job `132738107772`, with **3346
  passed, 1618 deselected in 164.63s**.

## Exact active task

Add the thirtieth exact generated-Joker acquisition bridge for only
uneditioned `j_juggler`. The committed trace contains exact uneditioned,
affordable Juggler observations in episode 17 / decisions 3 and 4 and episode
33 / decision 1, all with `rarity=1`, `base_cost=4`, `price=4`, no edition, and
no edited copy. Its +1 hand-size acquisition lifecycle is already owned by
the canonical shop transition and round lifecycle; its scored-hand callbacks
are inert. The canonical Joker-sale owner currently keeps Juggler fail-closed
because its inverse hand-size lifecycle is not yet implemented.

Extend the canonical generated-item materializer with an explicit
`j_juggler` to `JugglerJoker` entry and exact vanilla identity (`rarity=1`,
`base_cost=4`, public label, purchase price, discovery transition, and sale
value). Extend the generated-Joker tactical capability only for its already-
owned blind-neutral behavior. At the canonical sale owner, add the exact
Juggler removal inverse that decrements hand size once and preserves every
existing inventory/order/pool invariant. Add deterministic materialization,
mask, purchase, hand-size, sale/inverse, isolation, natural production-
backend, and complete rollout coverage. Keep the first twenty-nine centers
unchanged and every other generated center/edition/malformed state fail-
closed. Do not add a generic factory, batch multiple centers, open boosters,
change PPO, rewards, or tactics, or request an operator run during this
checkpoint. Keep Drunkard, 8 Ball, Hallucination, Dusk, Faceless Joker, and
Gros Michel fail-closed for their unowned callbacks, and do not batch another
Joker into this checkpoint.

Exact generated Fibonacci acquisition checkpoint:

- Implementation commit `4a86d7905371da9ab5d63bbeabaeb337f87b3cc9` adds
  only exact uneditioned `j_fibonacci` (`rarity=2`, `base_cost=8`) as the
  audited `FibonacciJoker`, with exact discovery, price/sale metadata, scored-
  rank Mult, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `122` proves unsupported Delayed
  Gratification remains masked while natural Fibonacci generation, legal
  masking, purchase, discovery, and sale are exact. Complete rollout episode
  50 / seed `05B3FF62` locks the fifteen-action Fibonacci, Greedy, Crazy, and
  Sly Joker lifecycle sequence.
- Admitting Fibonacci leaves every pre-existing frozen actor and lifecycle
  trajectory unchanged. The combined shop/backend/tactical/complete-rollout
  local gate passed **321 tests in 130.29s**; syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `44357740300`, job `134990307744`, passed the authoritative
  Balatro deterministic gate with **3640 passed, 1621 deselected in 486.11s**.

Exact generated Wrathful Joker acquisition checkpoint:

- Implementation commit `93d2dd19a3c76147f52891a0edda281794ab8a75` adds
  only exact uneditioned `j_wrathful_joker` (`rarity=1`, `base_cost=5`) as the
  audited `WrathfulJoker`, with exact discovery, price/sale metadata, scored-
  Spade Mult, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `129` proves unsupported Baron remains
  masked while natural Wrathful generation, legal masking, purchase,
  discovery, and sale are exact. Complete rollout episode 41 / seed `20C74BCD`
  locks the thirteen-action Wrathful and Blue Joker lifecycle sequence.
- The actor-critic trajectory for the same episode now exactly locks its
  twelve-action Tarot Merchant route, including the 4.0 to 9.6 Tarot-rate
  transition and visible legal Wrathful purchase. The combined shop/backend/
  tactical/complete-rollout local gate passed **313 tests in 126.45s**; syntax
  compilation and `git diff --check` are clean.
- GitHub Actions run `44308751353`, job `134817065071`, passed the authoritative
  Balatro deterministic gate with **3632 passed, 1621 deselected in 269.67s**.

Exact generated Lusty Joker acquisition checkpoint:

- Implementation commit `cfa56fa691e08bbc0112dc15fbb02cc7d561e5e4` adds
  only exact uneditioned `j_lusty_joker` (`rarity=1`, `base_cost=5`) as the
  audited `LustyJoker`, with exact discovery, price/sale metadata, scored-Heart
  Mult, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `285` proves deferred Gros Michel
  remains masked while natural Lusty generation, legal masking, purchase,
  discovery, and sale are exact. Complete rollout episode 8 / seed `E4205D09`
  locks the eleven-action Zany, Lusty, and Mad lifecycle sequence.
- Admitting Lusty leaves every pre-existing frozen actor and lifecycle
  trajectory unchanged. The combined shop/backend/tactical/complete-rollout
  local gate passed **305 tests in 131.90s**; syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `44303917312`, job `134800413060`, passed the authoritative
  Balatro deterministic gate with **3624 passed, 1621 deselected in 482.02s**.

Exact generated Greedy Joker acquisition checkpoint:

- Implementation commit `e6912c99b0825a67c1e1cfbdbe16c94617296e20` adds
  only exact uneditioned `j_greedy_joker` (`rarity=1`, `base_cost=5`) as the
  audited `GreedyJoker`, with exact discovery, price/sale metadata, scored-
  Diamond Mult, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `147` proves unsupported Baron remains
  masked while natural Greedy generation, legal masking, purchase, discovery,
  and sale are exact. Complete rollout episode 13 / seed `D691C2E4` locks the
  seven-action Greedy lifecycle while a second unsupported shop item remains
  masked.
- Lifecycle-policy episodes 46 and 59 add exact Greedy ownership to their
  existing Joker sequences. Actor-critic episodes 50 and 86 lock the resulting
  exact shop, voucher, Joker, and terminal trajectories. Paint Brush coverage
  remains independently locked by the deterministic voucher-priority episode
  46 / seed `9AC8FAC6` trajectory across its boss boundary.
- The combined shop/backend/tactical/complete-rollout local gate passed **297
  tests in 125.23s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44299688223`, job `134785952898`, passed the authoritative
  Balatro deterministic gate with **3616 passed, 1621 deselected in 364.26s**.
- Repository cleanup removed **95** generated pytest/Python cache directories
  and left zero root pytest caches, `__pycache__` directories, or loose Python
  bytecode files. No tracked or ambiguous project file was removed.

Exact generated Crazy Joker acquisition checkpoint:

- Implementation commit `2201c9f409d5f83fe264de5607259dfa3740cf04` adds only
  exact uneditioned `j_crazy` (`rarity=1`, `base_cost=4`) as the audited
  `CrazyJoker`, with exact discovery, price/sale metadata, Straight Mult,
  tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `164` proves unsupported Runner remains
  masked while natural Crazy generation, legal masking, purchase, discovery,
  and sale are exact. Complete rollout episode 12 / seed `BAA636D2` locks the
  fifteen-action Crazy lifecycle between existing Walkie Talkie and Even Steven
  coverage. Actor-critic episodes 50 and 86 lock Crazy's exact downstream
  Hieroglyph, Zany, Photograph, Sly, Paint Brush, shop, and terminal boundaries.
- The combined shop/backend/tactical/complete-rollout local gate passed **290
  tests in 121.04s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44258638120`, job `134646301807`, passed the authoritative
  Balatro deterministic gate with **3609 passed, 1621 deselected in 286.98s**.

Exact generated Crafty Joker acquisition checkpoint:

- Implementation commit `694fae1d9cb1e1d3777cdec0209eb8f10ca8b089` adds only
  exact uneditioned `j_crafty` (`rarity=1`, `base_cost=4`) as the audited
  `CraftyJoker`, with exact discovery, price/sale metadata, Flush Chips,
  tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `5` proves unsupported To Do List
  remains masked while natural Crafty generation, legal masking, purchase,
  discovery, and sale are exact. Complete rollout episode 110 / seed
  `6C803767` locks the seven-action Crafty lifecycle while unsupported Erosion
  remains masked.
- The combined shop/backend/tactical/complete-rollout local gate passed **282
  tests in 115.52s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44253660682`, job `134630084472`, passed the authoritative
  Balatro deterministic gate with **3601 passed, 1621 deselected in 337.00s**.

Exact generated Zany Joker acquisition checkpoint:

- Implementation commit `1b6500b35511582d86176a2df47b70c04da8402a` adds only
  exact uneditioned `j_zany` (`rarity=1`, `base_cost=4`) as the audited
  `ZanyJoker`, with exact discovery, price/sale metadata, Three of a Kind Mult,
  tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `78` proves unsupported Ride the Bus
  remains masked while natural Zany generation, legal masking, purchase,
  discovery, and sale are exact. Complete rollout episode 24 / seed `66F36434`
  locks the seven-action Zany lifecycle. Actor-critic episode 50 / seed
  `05B3FF62` locks the added Zany lifecycle and its exact downstream Banner,
  Photograph, Hieroglyph, shop, and terminal-score trajectory.
- The combined shop/backend/tactical/complete-rollout local gate passed **274
  tests in 116.14s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44251291173`, job `134622340504`, passed the authoritative
  Balatro deterministic gate with **3593 passed, 1621 deselected in 280.90s**.

Exact generated Mad Joker acquisition checkpoint:

- Implementation commit `4e49a4c82ee0c822b42e30c9cd93bc961cb0a332` adds only
  exact uneditioned `j_mad` (`rarity=1`, `base_cost=4`) as the audited
  `MadJoker`, with exact discovery, price/sale metadata, Two Pair Mult,
  tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `96` proves single-slot natural Mad
  generation, legal masking, purchase, discovery, and sale. The existing seed
  `24` ante-2 shop now locks exact Mad purchase legality. Complete rollout
  episode 140 / seed `7FBB953D` proves unsupported Seltzer remains masked while
  Mad completes its lifecycle; episode 31 / seed `19F511BC` now locks Mad after
  the existing Gluttonous and Abstract lifecycles.
- The combined shop/backend/tactical/complete-rollout local gate passed **266
  tests in 115.36s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44248876890`, job `134614384279`, passed the authoritative
  Balatro deterministic gate with **3585 passed, 1621 deselected in 258.75s**.

Exact generated Clever Joker acquisition checkpoint:

- Implementation commit `e0014948a1c91a2b98efdd5e489a86e20d3485e6` adds only
  exact uneditioned `j_clever` (`rarity=1`, `base_cost=4`) as the audited
  `CleverJoker`, with exact discovery, price/sale metadata, Two Pair Chips,
  tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `19` proves unsupported Drunkard
  remains masked while natural Clever generation, legal masking, purchase,
  discovery, and sale are exact. Complete rollout episode 5 / seed `59B15C34`
  locks the seven-action Clever lifecycle; episode 9 / seed `4104A2D5` locks
  Photograph followed by Clever buy/sale lifecycles in the same trajectory.
- The combined shop/backend/tactical/complete-rollout local gate passed **258
  tests in 116.52s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44246313281`, job `134606010935`, passed the authoritative
  Balatro deterministic gate with **3577 passed, 1621 deselected in 233.26s**.

Exact generated Raised Fist acquisition checkpoint:

- Implementation commit `4deec6283677ecccd2696a24ef47450cbaef44d9` adds only
  exact uneditioned `j_raised_fist` (`rarity=1`, `base_cost=5`) as the audited
  `RaisedFistJoker`, with exact discovery, price/sale metadata, held-lowest-rank
  scoring, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `15` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 62 / seed
  `43F62C55` locks Raised Fist before existing Scary Face and Walkie Talkie
  lifecycles in the fifteen-action trajectory.
- The combined shop/backend/tactical/complete-rollout local gate passed **250
  tests in 95.46s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44157989080`, job `134303797020`, passed the authoritative
  Balatro deterministic gate with **3569 passed, 1621 deselected in 403.78s**.

Exact generated Smiley Face acquisition checkpoint:

- Implementation commit `b19ffc80e202da66b735cedb503a8264c597172c` adds only
  exact uneditioned `j_smiley` (`rarity=1`, `base_cost=4`) as the audited
  `SmileyFaceJoker`, with exact discovery, price/sale metadata, scored-face
  Mult, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `57` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 46 / seed
  `9AC8FAC6` locks Smiley Face followed by Blue Joker buy/sale lifecycles and
  the resulting nine-action trajectory.
- The combined shop/backend/tactical/complete-rollout local gate passed **242
  tests in 99.66s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44147799540`, job `134267561814`, passed the authoritative
  Balatro deterministic gate with **3561 passed, 1621 deselected in 305.17s**.

Exact generated Walkie Talkie acquisition checkpoint:

- Implementation commit `b3e0b6903e39a8bd6a715ecf6f0d48993d8c1023` adds only
  exact uneditioned `j_walkie_talkie` (`rarity=1`, `base_cost=4`) as the
  audited `WalkieTalkieJoker`, with exact discovery, price/sale metadata,
  scored-10/4 Chips and Mult, tactical continuation, and inverse sale
  lifecycle. The observed Polychrome copy remains fail-closed.
- Deterministic production-backend seed `77` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 12 / seed
  `BAA636D2` locks Walkie Talkie followed by Even Steven buy/sale lifecycles and
  the resulting thirteen-action trajectory.
- The combined shop/backend/tactical/complete-rollout local gate passed **234
  tests in 89.11s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44144356090`, job `134255304473`, passed the authoritative
  Balatro deterministic gate with **3553 passed, 1621 deselected in 314.53s**.

Exact generated Scary Face acquisition checkpoint:

- Implementation commit `7c87ac4824669018d870b3f38d342b318130fefc` adds only
  exact uneditioned `j_scary_face` (`rarity=1`, `base_cost=4`) as the audited
  `ScaryFaceJoker`, with exact discovery, price/sale metadata, scored-face
  Chips, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `13` proves unsupported Faceless Joker
  remains masked while natural Scary Face generation, legal masking, purchase,
  discovery, and sale are exact. Complete rollout episode 27 / seed `68E835DA`
  locks Abstract Joker followed by Scary Face buy/sale lifecycles in the same
  shop and the resulting eleven-action trajectory.
- The combined shop/backend/tactical/complete-rollout local gate passed **227
  tests in 85.28s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44141076987`, job `134243712350`, passed the authoritative
  Balatro deterministic gate with **3546 passed, 1621 deselected in 316.70s**.

Exact generated Banner acquisition checkpoint:

- Implementation commit `7d6891cf613673f6d2696e962a460e81e036fe37` adds only
  exact uneditioned `j_banner` (`rarity=1`, `base_cost=5`) as the audited
  `BannerJoker`, with exact discovery, price/sale metadata, remaining-discard
  scoring, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `31` proves unsupported 8 Ball remains
  masked while natural Banner generation, legal masking, purchase, discovery,
  and sale are exact. Complete rollout episode 6 / seed `FE98D556` locks the
  seven-action Banner lifecycle. Existing episodes 21 and 50 now lock one and
  two additional exact Banner buy/sale lifecycles respectively.
- The combined shop/backend/tactical/complete-rollout local gate passed **239
  tests in 86.44s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44096135343`, job `134083618263`, passed the authoritative
  Balatro deterministic gate with **3539 passed, 1621 deselected in 252.99s**.

Exact generated Mystic Summit acquisition checkpoint:

- Implementation commit `1152e556537e5fcc665fda84edceaa97f548513b` adds only
  exact uneditioned `j_mystic_summit` (`rarity=1`, `base_cost=5`) as the audited
  `MysticSummitJoker`, with exact discovery, price/sale metadata, zero-discard
  scoring, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `11` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 59 / seed
  `3293F37E` locks two exact Mystic Summit buy/sale lifecycles and their
  thirteen-action money trajectory. A separate deterministic regression locks
  the exact unaffordable mask and illegal transition.
- The combined shop/backend/tactical/complete-rollout local gate passed **220
  tests in 85.44s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44092481953`, job `134070911176`, passed the authoritative
  Balatro deterministic gate with **3531 passed, 1621 deselected in 364.89s**.

Exact generated Half Joker acquisition checkpoint:

- Implementation commit `e7bbb5160681dd6b8e5983c074e9ea4e11764aec` fixes the
  canonical scoring-only callback to return inertly without a score and adds
  only exact uneditioned `j_half` (`rarity=1`, `base_cost=5`) as the audited
  `HalfJoker`, with exact discovery, price/sale metadata, at-most-three-card
  scoring, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `12` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 65 / seed
  `08718DA1` locks two exact Half buy/sale lifecycles and their nine-action money
  trajectory.
- The combined callback/shop/backend/tactical/complete-rollout local gate passed
  **222 tests in 82.76s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44089720277`, job `134061366833`, passed the authoritative
  Balatro deterministic gate with **3522 passed, 1621 deselected in 216.88s**.

Exact generated Photograph acquisition checkpoint:

- Implementation commit `3e7225f0cf017eed2b197cef3f28aa9637e1fe7c` adds only
  exact uneditioned `j_photograph` (`rarity=1`, `base_cost=5`) as the audited
  `PhotographJoker`, with exact discovery, price/sale metadata, ordered
  first-scoring-face x2 Mult, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `61` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 9 / seed
  `4104A2D5` locks the exact eleven-action buy/sell lifecycle.
- The combined shop/backend/tactical/complete-rollout local gate passed **195
  tests in 70.51s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44086650320`, job `134050712971`, passed the authoritative
  Balatro deterministic gate with **3514 passed, 1621 deselected in 388.71s**.

Exact generated Abstract Joker acquisition checkpoint:

- Implementation commit `34cae679a8319f52a21e5d9a72a7d235b351baa3` adds only
  exact uneditioned `j_abstract` (`rarity=1`, `base_cost=4`) as the audited
  `AbstractJoker`, with exact discovery, price/sale metadata, inventory-count
  scoring, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `311` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 27 / seed
  `68E835DA` locks the exact nine-action buy/sell lifecycle.
- Lifecycle-policy episode 31 naturally adds a second-shop Abstract buy/sale
  after its existing Gluttonous lifecycle; the exact eleven-action and money
  trajectory is locked without weakening the original Gluttonous assertions.
- The combined shop/backend/tactical/complete-rollout local gate passed **187
  tests in 67.39s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44053167477`, job `133935747417`, passed the authoritative
  Balatro deterministic gate with **3506 passed, 1621 deselected in 290.82s**.

Exact generated Wily Joker acquisition checkpoint:

- Implementation commit `8086c714b47f1ad2aa9aa8ae09f3c5a8eacf9727` adds only
  exact uneditioned `j_wily` (`rarity=1`, `base_cost=4`) as the audited
  `WilyJoker`, with exact discovery, price/sale metadata, Three-of-a-Kind
  scoring, tactical continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `17` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 10 / seed
  `435A60DF` locks the exact seven-action buy/sell lifecycle.
- Lifecycle-policy episode 33 naturally adds a second-shop Wily buy/sale after
  its existing Jolly lifecycle; the exact nine-action and money trajectory is
  locked without weakening the original Jolly assertions.
- The combined shop/backend/tactical/complete-rollout local gate passed **179
  tests in 94.91s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44048538813`, job `133920208943`, passed the authoritative
  Balatro deterministic gate with **3498 passed, 1621 deselected in 238.63s**.

Exact generated Sly Joker acquisition checkpoint:

- Implementation commit `89d8e825810a0cf222d29bb32e320ea9bf1da52e` adds only
  exact uneditioned `j_sly` (`rarity=1`, `base_cost=3`) as the audited
  `SlyJoker`, with exact discovery, price/sale metadata, Pair scoring, tactical
  continuation, and inverse sale lifecycle.
- Deterministic production-backend seed `29` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 35 / seed
  `8E5CE4B5` locks the exact seven-action buy/sell lifecycle.
- Frozen actor episode 41 naturally buys/sells Sly before acquiring Hone;
  episode 50 buys and retains Sly through its terminal loss. Their complete
  action, money, center, voucher, Ante, and terminal trajectories are locked.
- The combined shop/backend/tactical/complete-rollout local gate passed **171
  tests in 108.20s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44043143263`, job `133902310101`, passed the authoritative
  Balatro deterministic gate with **3490 passed, 1621 deselected in 371.63s**.

Exact generated Jolly Joker acquisition checkpoint:

- Implementation commit `d33fb5ce9622991a42ac95d176af0bb7a3602aeb` adds only
  exact uneditioned `j_jolly` (`rarity=1`, `base_cost=3`) as the audited
  `JollyJoker`, with exact discovery, price/sale metadata, Pair scoring,
  tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Jolly only through its
  existing exact `BalatroScorer` / `HandEvaluator` owner and inert discard
  callback. Other centers, mutations, and editions remain fail-closed.
- Deterministic production-backend seed `23` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 33 / seed
  `A801C474` locks the exact seven-action buy/sell lifecycle.
- The combined shop/backend/tactical/complete-rollout local gate passed **163
  tests in 102.34s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `44039264402`, job `133889598652`, passed the authoritative
  Balatro deterministic gate with **3482 passed, 1621 deselected in 274.40s**.

Exact generated Blue Joker acquisition checkpoint:

- Implementation commit `4cdc4521f742df9df49f9e3d2876b6a5cecd0997` adds only
  exact uneditioned `j_blue_joker` (`rarity=1`, `base_cost=5`) as the audited
  `BlueJoker`, with exact discovery, price/sale metadata, remaining-draw-pile
  scoring, tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Blue Joker only through its
  existing exact `BalatroScorer` and private/public draw-zone owners plus inert
  discard callback. Other centers, mutations, and editions remain fail-closed.
- Deterministic production-backend seed `28` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 34 / seed
  `2B8499E6` locks the exact seven-action buy/sell lifecycle.
- Frozen actor episodes 41, 46, and 89 naturally add exact Blue Joker buy/sale
  lifecycles. Their complete action, money, center-encoding, voucher, hand-size,
  and terminal trajectories are locked rather than weakened or approximated.
- The combined shop/backend/tactical/complete-rollout local gate passed **155
  tests in 57.31s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43959841985`, job `133623981756`, passed the authoritative
  Balatro deterministic gate with **3474 passed, 1621 deselected in 285.88s**.

Exact generated Scholar acquisition checkpoint:

- Implementation commit `4a0fefc6a5979d4447cf884a2d9150497a1b1bae` adds only
  exact uneditioned `j_scholar` (`rarity=1`, `base_cost=4`) as the audited
  `ScholarJoker`, with exact discovery, price/sale metadata, Ace scoring,
  tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Scholar only through its
  existing exact `BalatroScorer` owner and inert discard callback. Other
  centers, mutations, and editions remain fail-closed.
- Deterministic production-backend seed `27` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 115 / seed
  `58918DC7` locks the exact seven-action buy/sell lifecycle.
- The combined shop/backend/tactical/complete-rollout local gate passed **147
  tests in 55.27s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43956682316`, job `133612960160`, passed the authoritative
  Balatro deterministic gate with **3466 passed, 1621 deselected in 275.85s**.

Exact generated Gluttonous Joker acquisition checkpoint:

- Implementation commit `ce8f98023cc9d278e8f892b827aa6e1cc002df8c` adds only
  exact uneditioned `j_gluttenous_joker` (`rarity=1`, `base_cost=5`) as the
  audited `GluttonousJoker`, with exact discovery, price/sale metadata, Club
  scoring, tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Gluttonous only through its
  existing exact `BalatroScorer` suit-projection owner and inert discard
  callback. Other centers, mutations, and editions remain fail-closed.
- Deterministic production-backend seed `9` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 31 / seed
  `19F511BC` locks the exact nine-action buy/sell lifecycle.
- The combined shop/backend/tactical/complete-rollout local gate passed **139
  tests in 52.88s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43952933447`, job `133599919293`, passed the authoritative
  Balatro deterministic gate with **3458 passed, 1621 deselected in 231.75s**.

Exact generated Devious Joker acquisition checkpoint:

- Implementation commit `eed2f41f9bc705bb00ce0e353ad6357dbfaf398c` adds only
  exact uneditioned `j_devious` (`rarity=1`, `base_cost=4`) as the audited
  `DeviousJoker`, with exact discovery, price/sale metadata, Straight scoring,
  tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Devious only through its
  existing exact `BalatroScorer` / `HandEvaluator` owner and inert discard
  callback. Other centers, mutations, and editions remain fail-closed.
- Deterministic production-backend seed `44` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 21 / seed
  `1D88A8A1` locks the exact seven-action buy/sell trajectory. The frozen actor
  also naturally buys Devious in Wheel episode 313 / seed `88DB75F5`; its exact
  six-action loss now scores 576 chips.
- The combined shop/backend/tactical/frozen-rollout local gate passed **131
  tests in 49.65s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43949565640`, job `133588119358`, passed the
  authoritative **3450 passed, 1621 deselected in 223.37s**.

Exact generated Even Steven acquisition checkpoint:

- Implementation commit `300d94f67fc7a264db77650ed1a594c6f7a30c46` adds only
  exact uneditioned `j_even_steven` (`rarity=1`, `base_cost=4`) as the audited
  `EvenStevenJoker`, with exact discovery, price/sale metadata, on-scored-card
  +4 Mult per even rank, tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Even Steven only through its
  existing exact on-scored-card owner and inert discard callback. Other centers,
  mutations, and editions remain fail-closed.
- Deterministic production-backend seed `40` proves natural generation, legal
  masking, purchase, discovery, and sale. Complete rollout episode 12 / seed
  `BAA636D2` locks the exact 11-action terminal trajectory, including the
  $31-to-$27 purchase and $27-to-$29 sale boundaries.
- The combined shop/backend/tactical/frozen-rollout local gate passed **123
  tests in 47.55s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43946541239`, job `133577602316`, passed the
  authoritative **3442 passed, 1621 deselected in 263.48s**.

Exact generated Odd Todd acquisition checkpoint:

- Implementation commit `61210b6d4f106eabe660a433854e7994ee849751`
  adds only exact uneditioned `j_odd_todd` (`rarity=1`, `base_cost=4`) as the
  audited `OddToddJoker`, with exact discovery, price/sale metadata, scoring,
  tactical continuation, and inverse sale lifecycle.
- The generated-Joker tactical capability admits Odd Todd only through its
  existing exact on-scored-card owner and inert discard callback. Other centers,
  mutations, and editions remain fail-closed.
- The combined shop/backend/tactical/frozen-rollout gate passed **115 tests**.
  Episode 45 now locks Droll purchase/sale followed by Odd Todd purchase/sale
  and complete tactical continuation in its exact 13-action loss trajectory.
- GitHub Actions run `43896566063`, job `133401594528`, passed with **3434
  passed, 1621 deselected in 227.15s**.

Exact generated Droll Joker acquisition checkpoint:

- Implementation commit `50606156dfd06a4bf8b7c6665fa3df78eb45ca64`
  adds only exact uneditioned `j_droll` (`rarity=1`, `base_cost=4`) as the
  audited `DrollJoker`. Purchase updates both retained generation discovery and
  Tag-profile discovery exactly, preserves immutable source state, installs the
  vanilla price/sale metadata, and remains sellable through the existing exact
  inverse lifecycle.
- The checkpoint also closes the necessary downstream capability boundary:
  materialized base/Droll Jokers are admitted through Play only for their exact
  scoring callbacks and through Discard only as audited callback no-ops.
  Unsupported identities, mutations, editions, and Verdant-with-Joker Play
  remain fail-closed.
- Focused shop/backend/tactical validation passed **74 tests**; frozen rollout
  and public-observation validation passed **51 tests**. Episode 45 now locks
  the exact natural Droll buy, tactical continuation, later sale, and complete
  13-action loss trajectory instead of crashing at the first discard.
- GitHub Actions run `43894715826`, job `133395006103`, passed with **3429
  passed, 1621 deselected in 318.72s**.

Exact generated base-Joker acquisition checkpoint:

- Implementation commit `91ec1092231694ce8377bf629a84b707b978e2c9`
  materializes only exact discovered, uneditioned `j_joker` metadata with
  canonical rarity 1/base cost 2 as `FlatMultJoker(+4 Mult)`. The purchase
  preserves exact public metadata, uses vanilla `max(1, floor(cost / 2))` sale
  value, and reuses the existing shop debit/order/acquisition and Joker-sale
  owners.
- Other centers, editions, wrong rarity/cost, unknown discovery, malformed
  prices, and non-exact item types remain unavailable. Existing modeled runtime
  Joker acquisition is unchanged.
- Focused pricing/materialization/production-backend validation passed **48
  tests**. The natural production seed `225` proves generation, legal-action
  masking, purchase, exact +4 Mult scoring, sale masking, and exact resale.
- GitHub Actions run `43892042820`, job `133385564033`, passed with **3424
  passed, 1621 deselected in 316.08s**.

Exact paid-reroll action-bridge checkpoint:

- Implementation commit `c55704d1887ff820c9e76e57dce4bf7ba14b33ea`
  restores parameterless `REROLL_SHOP` at `ShopTransitionEngine` only when
  `shop_reroll.can_reroll_base_main_shop` accepts the run, and executes only
  through `reroll_base_main_shop(...).run`. The production change is nine lines
  and duplicates no reroll mechanics.
- Focused transition/backend validation passed **45 tests**. The broader local
  environment gate passed **1213 tests, 3818 deselected**.
- The first CI run correctly exposed one stale legal-mask assertion and 15
  exact seeded rollout expectations whose trajectories changed because paid
  reroll became genuinely selectable. No assertion was weakened; commit
  `8744753ce19b837b2ba2078dc01c3861ce3ccec7` updates those deterministic
  trajectory contracts and the affected exact corruption indices.
- GitHub Actions run `43888746568`, job `133373881308`, passed the corrected
  authoritative branch with **3410 passed, 1621 deselected in 276.24s**.

Completed current-production strategic/shop attribution:

- The fixed ordered 64-episode run completed with exit code 0 and exactly
  reproduced every published production terminal result. The canonical and
  committed 1,173,389-byte reports are byte-identical with SHA-256
  `4f8902061a2d042cf27320e34337b7037884921f1ca91165eedb400eea4d44fc`.
- The trace records 512 strategic decisions: 245 BLIND_SELECT and 267 SHOP
  decisions across 62 shop-reaching episodes. Actions are 241 `SELECT_BLIND`,
  4 `SKIP_BLIND`, 177 `END_SHOP`, 48 `BUY_CONSUMABLE`, and 42 `BUY_VOUCHER`.
  `BUY_JOKER`, `OPEN_PACK`, and `REROLL_SHOP` are never legal or selected.
- `END_SHOP` is selected 42 times while a currently legal affordable purchase
  exists: 23 with consumable availability, 13 with Voucher availability, and 6
  with both/two consumables. Those 42 choices span 34 episodes. The candidate
  makes 90 purchases with mean immediate money delta `-$6.266666666666667`.
- The stronger owner is the missing action bridge, not learned purchase refusal.
  Affordable visible Jokers exist at 206/267 SHOP decisions across all 62 such
  episodes, including 133 `END_SHOP` decisions. Affordable visible boosters
  exist at 239/267 decisions, including 150 `END_SHOP` decisions. Money is at
  least the environment-owned reroll cost at 233/267 decisions across all 62
  episodes, including 146 `END_SHOP` decisions. These are availability counts,
  not claims that currently absent transitions are legal.
- Descriptively, the 48 episodes making any legal purchase average Ante
  `1.64583333333333`, versus `1.0625` for the 16 without a purchase, but this is
  observational trajectory evidence and does not establish causal policy value.
  No acquisition-policy shadow is authorized until the action bridge is exact.

Current-production strategic/shop trace implementation checkpoint:

- Commit `b42050c986cb3b592522ce6fd40d92a7af5add62` adds the
  separately versioned read-only trace owner and CLI. It uses the unchanged
  selective production tactical factory and records every PPO strategic
  boundary without changing backend state, policy sampling, rewards, tactics,
  mechanics, or the action surface.
- Each decision records the public strategic frame, observation digest and
  schema, complete 27-slot legal mask and masked probabilities, value estimate,
  selected indexed action, and immediate next public frame. SHOP boundaries use
  the canonical generated-item serializer for exact visible metadata/prices and
  record owned capacity/counts, exact environment reroll cost, all legal actions,
  the purchase/end/reroll subset, and legal affordable acquisitions. The report
  explicitly marks reroll cost as environment-owned but absent from the current
  policy observation.
- The runner pins the exact current-production reproduction report by its
  3,988,609-byte SHA-256, enforces fixed corpus order and campaign/promotion/
  corpus linkage, and requires every terminal result to reproduce exactly before
  writing canonical output. Malformed masks, probabilities, indexed actions,
  decision order, source order, overwrite, or provenance fail closed.
- Focused validation: **7 passed in 1.53s**. Broader affected local validation:
  **67 passed in 15.46s**. CLI import/help, syntax compilation, and
  `git diff --check` are clean. GitHub Actions run `43865361267`, job
  `133292403885`, passed with **3407 passed, 1621 deselected in 248.10s**.
- The real-artifact episode-0 / seed `9CA6BDC0` smoke is green. It exactly
  reproduces the published production result (`LOSS`, 6 strategic actions),
  records all 6 PPO decisions including 3 SHOP decisions, and produces episode
  trace SHA-256
  `f35b46ec0a5f7b3ad1c12f133b6bc761f50910d85c12cdc5f9d7400c19257342`.
  The fixed ordered 64-episode strategic/shop trace is now authorized; its
  canonical report must complete with exit code 0 before attribution begins.

Completed stable-discard deep-search shadow:

- The canonical 64-episode run completed with exit code 0, canonical bytes,
  exact source/corpus order, and zero illegal, unsupported, truncated, or
  incomplete outcomes.
- Final decision: **REJECTED**. First-blind clears remain **62/64** and full-game
  clears remain **0/64**. Mean requirement progress improves from
  `0.6189615885416667` to `0.6384233940972223` and mean minimum cash from
  `$3.171875` to `$3.25`, but mean Ante regresses from `1.5` to `1.484375` and
  terminal cash from `$11.09375` to `$11.03125`.
- The rule admitted 159 stable-discard consensus decisions across 1,194 tactical
  decisions and still produced 33 trajectory divergences. It prevents the full
  shadow's Ante regressions on episodes 21 and 40, but introduces a new Ante
  regression on episode 2. Relative to production, four seeds regress by one
  Ante and three improve by one; the mandatory nonregression gate remains false.
- Tactical search consumed 19,091.189077496994 CPU-seconds; the slowest decision
  took 1,899.1425431999378 seconds. This is slower than the rejected unrestricted
  full shadow and is not production-viable.
- The canonical and committed 2,574,290-byte reports are byte-identical with
  SHA-256
  `f9cdcc3d44d5ddb1570187e3ef14d019386aca7ab8d4b4b75a0fb89312ec74ba`.
  Evidence commit `902ad9c65d9037ca86d33d1f976fc7e002a5cdd7` passed manually
  dispatched GitHub Actions run `43862084657`, job `133281184889`, with
  **3400 passed, 1621 deselected in 247.06s**. Do not tune or rerun either
  rejected deep-search shadow.

Stable-discard deep-search implementation checkpoint:

- Commit `6f0d9b519862a28f9b2714197e17b06b46ccf45e` adds the explicit
  shadow-only schedule mode at `LiveHandActionDecisionEngine` and a separately
  versioned fixed-corpus runner. Production remains on the unchanged selective
  mode.
- The shadow retains the full owned schedule and unchanged play/exact-discard
  clear-path behavior. An inexact discard clear path now continues until the
  existing three-recommendation `stable_discard_consensus` agrees with the
  selected action, then must pass the existing stronger same-horizon
  confirmation. Otherwise the engine continues to its existing fallback.
- The runner pins the exact 3,988,609-byte current-production reproduction
  source by SHA-256, validates all campaign/promotion/corpus links, records
  consensus decisions and full tactical traces, and applies the frozen paired
  acceptance gates against the reproduced selective baseline.
- Focused/broader local validation: **45 passed in 1.54s**. Syntax compilation
  and `git diff --check` are clean. GitHub Actions run `43846807688`, job
  `133228915853`, passed the authoritative **3400 passed, 1621 deselected in
  280.37s**.
- The real-artifact episode-0 / seed `9CA6BDC0` smoke is green: status `LOSS`,
  6 strategic actions, 13 tactical decisions, first-blind clear, Ante 1, and
  zero stable-discard consensus admissions. Tactical search consumed
  23.540129899978638 seconds; the slowest decision took
  11.665872200159356 seconds. This authorized the now-completed canonical fixed
  64-episode stable-discard shadow. No production change was authorized.

Completed current-production reproduction audit:

- The canonical run completed with exit code 0 and reproduced all **64/64**
  published production episodes exactly: status, action count, first-blind
  result, and every terminal metric have zero mismatches. This establishes that
  the rejected full-horizon result is schedule-caused rather than code-era drift.
- All **33** current-selective/full-horizon trajectory differences have a common
  state followed by a tactical action divergence; none begin with unexplained
  state, trace-length, or terminal-only drift. Earliest changes comprise 24
  discard-to-different-discard choices, 8 play-to-different-play choices, and 1
  play-to-discard choice.
- The eight Ante-changing first divergences all replace a horizon-1 fallback
  with a horizon-3/4 sampled clear path at reported probability 0.75 through
  1.0. Five reduce final Ante and three improve it. Four of the five regressions
  replace a smaller discard with a five-card discard; sampled deep-discard
  admission is therefore the earliest demonstrated owner.
- Full horizon remains **REJECTED** against the exactly reproduced current
  selective baseline: mean Ante and terminal cash regress despite improved
  requirement progress and minimum cash. All failure counters remain zero.
- The canonical and committed 3,988,609-byte audit reports are byte-identical
  with SHA-256
  `984ee7441025b6744bba988509bc2fa0ac35765acb85ccc4f77fa8ff42097ec8`.
  Evidence commit `528d626f4f038b11ab5373bb3123f58f412c2ad8` passed manually
  dispatched GitHub Actions run `43844844195`, job `133222345488`, with
  **3396 passed, 1618 deselected in 322.46s**.

Current-production reproduction audit implementation checkpoint:

- Commit `de3a3a268e20276aea890769a8890ca47f826798` adds the separately
  versioned read-only audit owner and CLI. It validates and uses the canonical
  selective production factory unchanged, replays the fixed 64-seed candidate,
  and links the completed campaign, promotion, diagnostics, first-blind source,
  and committed full-horizon report by their exact digests.
- The audit compares current selective outcomes independently with the published
  production outcomes and current-code full-horizon outcomes. It records the
  earliest state, tactical action, trace-length, or post-trace terminal
  divergence instead of treating equal terminal metrics as equal trajectories,
  and reapplies the frozen full-horizon gates against the current replay.
- Source drift, noncanonical bytes, corpus/order drift, output overwrite,
  production-factory drift, malformed decision evidence, and missing tactical
  traces fail closed. The implementation changes no production factory, policy,
  planner, evaluator, PPO, reward, or mechanic.
- Focused local validation: **13 passed in 0.87s**. Broader affected local
  validation: **70 passed in 4.69s**. Syntax compilation and `git diff --check`
  are clean. GitHub Actions run `43841767886`, job `133211928439`, passed the
  authoritative **3396 passed, 1618 deselected in 177.47s**.
- The one-episode real-artifact smoke is green. Episode 0 / seed `9CA6BDC0`
  completed normally with status `LOSS`, 6 strategic actions, 13 tactical
  decisions, first-blind clear, and Ante 1. Selective tactical search consumed
  0.97287020040676 seconds in total; the slowest decision took
  0.12128830002620816 seconds. This authorized the now-completed canonical
  fixed 64-episode reproduction audit. No production change was authorized.

Completed full-horizon tactical shadow:

- The canonical 64-episode run completed with exit code 0. All source hashes,
  fixed-corpus ordering, canonical bytes, and terminal statuses validate; there
  are zero illegal, unsupported, truncated, or incomplete outcomes.
- Final decision: **REJECTED**. First-blind clears remain **62/64** and full-game
  clears remain **0/64**. Mean terminal requirement progress improves from
  `0.6189615885416667` to `0.6402810329861112`, and mean minimum cash improves
  from `$3.171875` to `$3.25`, but mean Ante regresses from `1.5` to `1.46875`
  and mean terminal cash regresses from `$11.09375` to `$11.0`. Mandatory
  nonregression therefore fails despite a strict competence-metric improvement.
- The reference made 1,187 tactical decisions. Measured tactical search totals
  17,098.247011898784 CPU-seconds; the slowest single decision took
  1,394.076732199872 seconds. Runtime remains diagnostic and is not promotable.
- The canonical and committed 2,393,562-byte reports are byte-identical with
  SHA-256
  `3147f3b6144303952c3d105444ce0791b9cb8e031b6ae2810b63dd4e1744d77e`.
  Evidence commit `73420a1e18893654bdccc9eef2dc894ed02de1ce` passed manually
  dispatched GitHub Actions run `43839855740`, job `133205534851`, with
  **3390 passed, 1618 deselected in 257.46s**. Do not tune or rerun the rejected
  full-horizon reference.

Full-horizon tactical shadow implementation checkpoint:

- Commit `df192fcb7f94be54ee5c98018db28d6a0e315f7f` adds the separately
  versioned read-only shadow owner and CLI. It reconstructs the production
  tactical engine and changes only its existing adaptive schedule from
  selective to full, retaining the useful horizon-5 cap, 5,000-node ceiling,
  draw contracts, policy, mechanics, and trained PPO candidate.
- The runner cryptographically loads the completed campaign, promotion result,
  fixed 64-seed candidate corpus, published production candidate, and published
  first-blind evidence. It records ordered full-game outcomes plus every
  tactical decision, public action, search attempt, selected plan, first-blind
  result, and elapsed decision time. Source/order drift, artifact overwrite,
  malformed counters, illegal/unsupported/truncated/incomplete outcomes, and
  failure of any frozen acceptance gate fail closed.
- Deterministic regressions prove that only the schedule mode changes, exercise
  acceptance and each rejection family, verify the exact published first-blind
  source and SHOP boundary, and cover ordering, overwrite, and counter
  validation. Focused local validation: **7 passed in 0.69s**; broader affected
  validation: **38 passed, 1 deselected in 3.19s**. Syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `43829109036`, job `133169836913`, passed the
  authoritative **3390 passed, 1618 deselected in 279.36s**. This authorized
  the subsequent minimal read-only integration smoke against the real immutable
  artifacts.
- The read-only real-artifact smoke is green. Fixed-corpus episode 0 / game seed
  `9CA6BDC0` completed normally with status `LOSS`, 6 strategic actions, 13
  tactical decisions, first-blind clear, and Ante 1. Tactical search consumed
  27.853473500115797 seconds in total; the slowest decision took
  11.943723100004718 seconds. This authorized the now-completed canonical fixed
  64-episode operator execution. No production change was authorized by the
  smoke.

Advantage-normalization shadow core checkpoint:

- Commit `b63535013dbdba69ae62a7fb4c84b3d0345632c0` adds a separately
  versioned diagnostic owner that clones the immutable initial learner twice,
  applies the unchanged batch to one clone, and applies population
  zero-mean/unit-variance normalization only to the other clone's advantages
  before the existing PPO optimizer. It rejects non-2048 batches, zero or
  nonfinite variance, source-policy reproduction drift, incomplete optimizer
  evidence, and any mutation of the initial learner.
- Deterministic regressions prove every non-advantage batch field is unchanged,
  the normalized batch has mean 0 and variance 1, the unchanged branch exactly
  reproduces its expected policy digest, the normalized branch is independent,
  and invalid variance/source digests fail closed. Focused local validation:
  **25 passed in 36.13s**; syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43818158567`, job `133134846462`, passed the
  authoritative **3379 passed, 1618 deselected in 180.93s**. The active task
  remained the exact canonical batch-1 reconstruction, three-arm fixed-corpus
  report, and frozen accept/reject decision.
- Commit `2eb46bd529b5ec8148510f390605cb86cdb52757` completes that bounded
  runner. It loads only the immutable batch-0/batch-1 milestones, replays the
  published journal through the production collector, captures the exact
  2,048-transition optimizer batch, and requires the replayed checkpoint and
  unnormalized policy digests to reproduce batch 1. It then evaluates initial,
  published unnormalized, and normalized-shadow policies on the same fixed
  sparse-reward corpus and writes all 64 ordered three-arm outcomes, source and
  batch hashes, both 80-step optimizer traces, normalization statistics, and
  the predeclared decision.
- The frozen decision requires the normalized arm to match or exceed both
  source arms on clears, mean Ante, mean terminal requirement progress, mean
  minimum cash, and mean terminal cash, plus strictly exceed both sources on at
  least one of clears, Ante, or requirement progress. Regression, a tie on all
  three competence metrics, journal/order drift, repeated-initial evaluation
  drift, incomplete provenance, and output overwrite all fail closed.
- Focused local validation: **29 passed in 31.22s**; syntax compilation and
  `git diff --check` are clean. GitHub Actions run `43819636136`, job
  `133139496817`, passed the authoritative **3383 passed, 1618 deselected in
  248.75s**.
- Commit `6dd56ba902c42ae0219605f502096651e2af25bc` adds deterministic
  `reconstruct_batch_1` progress for all 288 source episodes before the two
  64-seed evaluation stages, without changing replay, optimization, or
  acceptance semantics. Focused local validation: **7 passed in 28.18s**.
  GitHub Actions run `43820451272`, job `133142088973`, passed the
  authoritative **3383 passed, 1618 deselected in 247.42s**. At that
  checkpoint, one canonical shadow execution and frozen accept/reject
  publication were authorized; no production change or larger training was.

Completed advantage-normalization shadow:

- The canonical run completed with exit code 0 and exactly replayed all **288
  batch-1 episodes / 2,048 optimizer transitions**. Its source batch SHA-256 is
  `34612afdc697fa12a2bb18ce5af82f3788c13ba8d05ddb96d293dfaac805ea8d`.
  Batch-0 and batch-1 milestone manifests, the published batch-1 checkpoint,
  and the batch-1 journal all link exactly; the unchanged optimizer branch
  reproduces published policy
  `95b67aef977ba5c8c47ac48833970a2f72876c167b9ee4ef9b3e1027d99b1c90`.
- The source advantage mean is `-0.7945601920605306` with variance
  `0.5202687204900613`. The cloned shadow has mean
  `-1.10588621593521e-17` and variance exactly `1.0`, consumes the same batch
  through the existing 80-step optimizer, and produces policy
  `6bac0d282112d8e5fffef299740de3496da34185ca74fd87baaf60b3e1d033be`.
- Final decision: **REJECTED**. All three arms clear **0/64**. Initial,
  published unnormalized, and normalized-shadow mean Ante are respectively
  `1.515625`, `1.515625`, and `1.5`; mean terminal requirement progress is
  `0.6561360677083333`, `0.6454286024305556`, and `0.649833984375`; mean
  minimum cash is `$3.125`, `$3.1875`, and `$3.09375`; mean terminal cash is
  `$9.5`, `$9.71875`, and `$9.484375`. The shadow regresses four protected
  gates versus at least one source and strictly improves none of clears, Ante,
  or requirement progress versus both sources.
- The canonical 99,230-byte report and committed repository copy are
  byte-identical with SHA-256
  `13d68b9cbe9d74bb5b4fdbde077767bff58e636e5f55f77fb70b034e667e8f04`.
  Evidence commit `9db22a480ae9f20634adb3a2aa705e8042b502c6` passed manually dispatched
  GitHub Actions run `43823610291`, job `133152122846`, with **3383 passed,
  1618 deselected in 250.92s**. V2 progress reward, its larger study,
  advantage normalization, and further training on this line remain rejected.

Eight-batch campaign-boundary checkpoint:

- Implementation commit `c647550f9e17c245160c091bd436bcf56566f89d`
  preserves the default one-fresh-batch v2 restriction and adds only an exact
  eight-batch study opt-in. The opt-in accepts canonical campaign resume,
  rejects any other limit, rejects sparse-v1 use, and fails closed if the
  requested advance could cross or restart at the batch-8 cap.
- Campaign regression gate: **30 passed in 0.86s**. Syntax compilation and
  `git diff --check` are clean.
- GitHub Actions run `43690266537`, job `132739248975`, passed the authoritative
  Balatro deterministic gate with **3347 passed, 1618 deselected in 157.91s**.
  The campaign cap/resume boundary is green.

Crash-consistent progress-study journal checkpoint:

- Implementation commit `8cfa5fad8f833f3daab9f536fc592e675c30e578`
  adds a canonical v2-only per-episode
  journal containing exact rewards, recomputed frozen GAE advantages, terminal
  depth/status, cumulative learner counters, and the post-commit policy hash.
- Journal publication now precedes checkpoint publication. Resume may trim
  exactly one journal-ahead episode after an interrupted checkpoint write;
  journal-behind-checkpoint, larger drift, noncanonical bytes, malformed
  provenance, and counter/order drift fail closed.
- Focused journal/campaign validation: **36 passed in 0.98s**. Broader PPO
  campaign, reward, pilot, evaluation, batch, model, and learner validation:
  **81 passed in 14.25s**. Syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43691189501`, job `132742003967`, passed roadmap HEAD
  `26b34f588c77ef1556e322c00282b0185958f053` with **3353 passed, 1618
  deselected in 220.15s**.

Immutable progress-study milestone checkpoint:

- Implementation commit `b17c7213752230868fb9eb8216a60cc492cac88b`
  publishes canonical snapshots only at batches 0, 1, 2, 4, and 8. Each
  immutable manifest links its exact checkpoint, progress, journal, learner
  counters, and policy parameter digest.
- A missing manifest permits recovery only when every existing partial file
  exactly matches the current staged session. A present manifest, cross-run
  link, noncanonical file, unstaged batch, or signal/counter mismatch fails
  closed. Loading restores the exact v2 session and revalidates every link.
- The existing paired evaluator now exposes one shared fixed-corpus execution
  owner for any two same-run policies while preserving the published
  one-batch report format and bytes.
- Focused milestone/evaluator/campaign validation: **45 passed in 4.37s**.
  Syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43691877543`, job `132744055807`, passed roadmap HEAD
  `61a1b1dd63ca14b25b77d3bb45542caf0be45d47` with **3357 passed, 1618
  deselected in 244.31s**.

Progress-study paired-evaluation checkpoint:

- Implementation commit `364ecc3f55c3e91dccbe67102e081de02a5cee3b`
  adds the study-specific immutable fixed-corpus report. It loads only the
  cryptographically verified batch-0 and candidate milestone models and
  publishes all 64 ordered seed pairs, aggregate metrics, and deltas using the
  frozen sparse evaluation environment and greedy selection contract.
- Existing one-batch evaluation serialization remains unchanged. Completed
  study reports reject overwrite, malformed/noncanonical episodes, reordered
  seeds, altered summaries, policy drift, and milestone-link drift.
- Focused study-evaluation/milestone validation: **16 passed in 12.16s**.
  Broader PPO evaluation, campaign, reward, batch, model, and learner gate:
  **82 passed in 14.84s**. Syntax compilation and `git diff --check` are clean.
- GitHub Actions run `43693674092`, job `132749436846`, passed roadmap HEAD
  `2749b5dc3bec7fd89ce28d2b2689752b00ec1e57` with **3359 passed, 1618
  deselected in 193.09s**.

Final progress-study runner checkpoint:

- Implementation commit `69851274d1057df68b78d847c6c772b5fc674ad8`
  adds the fixed-root, fresh-directory study owner and CLI. It resumes the
  canonical live campaign one bounded call at a time, journals before each
  checkpoint, revalidates every prior milestone, and publishes/evaluates only
  batches 0, 1, 2, 4, and 8.
- The fixed root seed is `RED-WHITE-PROGRESS-STUDY-V1`; the identity binds the
  v2 training/reward contracts, eight-batch cap, staged batches, training run,
  and initial policy. Foreign/noncanonical directories, cross-run artifacts,
  progress/journal drift, missing earlier milestones, and any attempt beyond
  batch 8 fail closed.
- The final immutable report links each milestone/evaluation and publishes its
  exact policy/checkpoint/progress/journal hashes, cumulative reward,
  advantage, episode-depth and terminal-status statistics, paired fixed-corpus
  summary, measured training time, unmeasured interrupted episode count, and
  all six fail-closed counters.
- Focused runner/journal/milestone/evaluation validation: **16 passed in
  13.15s**. Broader PPO runner, serialization, session, evaluation, campaign,
  model, batch, and learner gate: **96 passed in 18.23s**. CLI import/help,
  syntax compilation, and `git diff --check` are clean.
- GitHub Actions run `43694986901`, job `132753425581`, passed roadmap HEAD
  `891fbd554fa54767d07fd87ce9b512739c00e3ba` with **3365 passed, 1618
  deselected in 300.49s**. Development for the bounded study is complete.

Authorized operator run:

- Fixed training-run SHA-256:
  `ec3329a143c489b6e43888737cc19dc6e0cc158ceb23792e0e053f7d3fc41862`.
- Fresh artifact directory verified absent on 2026-11-15:
  `%LOCALAPPDATA%\Temp\balatro-ppo-progress-study-v1`.
- Run from PowerShell in the canonical repository checkout. The same command
  safely resumes after interruption and stops permanently at batch 8:

```powershell
Set-Location -LiteralPath 'D:\0.5 - Coding\0. game-ai\game-ai-framework'; py -3.13 -m games.balatro.env.ppo_progress_study_runner --artifact-directory "$env:LOCALAPPDATA\Temp\balatro-ppo-progress-study-v1" --maximum-episodes-per-call 512 --maximum-workers 8
```

- After exit code 0, inspect and publish `progress_study_report.json`, verify
  all five milestone/evaluation links and the final report hash, then decide
  the next roadmap task from the measured learning curve. Do not infer
  competence, change production policy, or authorize 1,024 batches from study
  completion alone.

Completed eight-batch progress study:

- The run completed all **8 optimizer batches** with **16,968 collected / 16,384
  optimized transitions** across **2,183 committed episodes**. All 2,183
  training episodes ended in `LOSS`; every published fail-closed counter is
  zero and no interrupted episode time is unmeasured.
- Measured training time is **12,105.384424200049 seconds (3:21:45.384)**.
  The final policy SHA-256 is
  `25be7197a79aa8e914b589fbf7a1267a64a6d6f323197713bec5d5fc366683b2`.
- Fixed 64-seed evaluation clears remain **0 at every checkpoint**. Batch 0 to
  batch 8 changes are: mean Ante `1.515625 -> 1.5` (`-0.015625`), mean terminal
  requirement progress `0.6561360677083333 -> 0.6186881510416666`
  (`-0.03744791666666669`), mean terminal cash `9.5 -> 7.1875` (`-2.3125`),
  and mean action count `7.890625 -> 8.28125` (`+0.390625`).
- Decision: **REJECTED**. The shaped signal remains finite and nonzero, but the
  measured policy curve does not improve competence and regresses all three
  protected non-clear metrics by batch 8. Do not extend this run, promote its
  policy, tune from its fixed outcomes, or authorize a larger campaign.
- The canonical artifact is 10,623 bytes with SHA-256
  `2ba60fca57702f86a5bbc10796205f469274e89c516d2dde22a7725055a1a654`.
  The committed repository copy includes a terminal newline (10,624 bytes,
  SHA-256 `f11055b582058b9c45f54471d2c9bd48da8b41573974cad7ccd725cf66d49986`).
  Independent reconstruction from all milestone, journal, runtime, and
  evaluation artifacts is byte-identical to the canonical artifact.
- Published evidence commit `d7dc8e0f9df149c6344f15146b307334fb2ff158`
  passed GitHub Actions run `43716085630`, job `132817814011`, with **3365
  passed, 1618 deselected in 302.31s**.

Next diagnostic boundary:

- Read only the existing milestone policies and fixed seeds. Record canonical
  per-checkpoint greedy action frequencies, first divergence from batch 0,
  selected-action probability and legal-action entropy, plus exact per-seed
  links to the existing terminal deltas.
- Use the earliest divergence owner to distinguish action-distribution collapse
  from value-only drift before proposing any new reward, optimizer, model, or
  training schedule. No additional optimizer batch or live Balatro run is
  authorized during this diagnostic.

Policy-behavior attribution implementation checkpoint:

- Implementation commit `a6fc86d8130db243204663996a9eb3f33f9512ea`
  adds a read-only five-policy/64-seed trace owner. Every decision binds the
  public observation digest, sorted legal action slots, frozen greedy choice,
  selected-action probability, legal-action entropy, and value estimate.
- The canonical report publishes all 27 action-slot frequencies per milestone,
  aggregate confidence/entropy/value statistics, each seed's first shared-state
  greedy divergence from batch 0, action-transition counts, and the exact
  terminal delta from the immutable milestone evaluation.
- Loading requires the fixed study identity, all five exact milestone and
  evaluation hashes, fixed corpus digest, policy parameter digests, and public
  action schema digest. Sparse evaluation terminal status, action count, and
  complete terminal metrics must reproduce the existing evidence exactly;
  overwrite, missing seeds, reordered batches, state drift, truncation, and
  provenance mismatch fail closed.
- Focused behavior/evaluation/milestone gate: **14 passed in 10.95s**. Broader
  diagnostic, PPO serialization, campaign, session, model, batch, and learner
  gate: **98 passed in 21.04s**. Syntax compilation and `git diff --check` are
  clean.
- GitHub Actions run `43718146335`, job `132824048878`, passed roadmap HEAD
  `56fa6c74bc23da794a0d9ef9328bf38694742054` with **3369 passed, 1618
  deselected in 181.23s**. The complete read-only diagnostic is authorized.

Completed policy-behavior attribution:

- The read-only run completed all **5 milestone policies x 64 fixed seeds**
  (**320 complete episodes**) without optimization. Its 1,131,416-byte
  canonical artifact has SHA-256
  `987a9124ab194092b6511ec6dbd3896db6f64a73a79a588f86853546f27d2d39`.
  All five milestone-manifest and evaluation hashes independently match their
  immutable files. The formatted repository copy is 1,706,241 bytes with
  SHA-256
  `4aa1d8bad2ce5640780c26295ca71955ca1ef47906db360b7a9ee28676498d4d`
  and parses to exactly the same report value.
- Batch 0/1/2/4/8 mean selected-action probabilities are respectively
  `0.9212059834`, `0.9110330358`, `0.9134378747`, `0.9042042915`, and
  `0.9147900861`; mean legal entropies are `0.1651058618`, `0.1732872309`,
  `0.1707863908`, `0.1737917740`, and `0.1680346309`. This is not broad
  action-distribution collapse.
- Mean value estimates move from `-0.0749238948` at batch 0 to
  `-0.6923439775`, `-0.9251577955`, `-1.0628463624`, and `-1.0451597069`.
  Greedy behavior diverges from batch 0 on 29, 29, 23, and 22 of 64 seeds.
  Every non-divergent seed reproduces zero terminal delta, so the changed
  greedy decisions completely localize the observed evaluation changes.
- At batch 8, the 22 divergent seeds average `-0.0454545455` Ante,
  `-0.1089393939` terminal requirement progress, `-$6.7272727273`, and
  `+1.1363636364` actions relative to batch 0. The dominant first divergence
  is action slot `0 -> 4` (`END_SHOP -> BUY_VOUCHER`) on 12 seeds; those seeds
  average `-0.0833333333` Ante, `-0.1457986111` progress, `-$8.6666666667`,
  and `+1.8333333333` actions. First divergences occur only at decision indices
  1 through 7 by batch 8.
- Decision: the v2 curve is **not** failing through global confidence collapse
  or value-only drift. It learns selective, early shop-policy changes while the
  critic becomes substantially more negative; the dominant learned voucher
  purchase shift is harmful on the fixed corpus. No further training or tuning
  is authorized until the exact optimizer inputs causing that shift are
  attributed.
- Published evidence commit `673edd3574fd5c1443698c479dd70cc4e186c098`
  passed GitHub Actions run `43727697440`, job `132853120476`, with **3369
  passed, 1618 deselected in 195.07s**.

Optimizer-attribution requirements:

- Reconstruct, do not approximate, the exact complete episodes, stream slices,
  GAE values, minibatch order, optimizer state, and post-update policy hashes
  for all eight completed batches.
- Bind each aggregate to its batch, episode/decision provenance, public action
  slot/legal set, sampled action probability, advantage, return, and immutable
  milestone/journal/checkpoint hashes.
- Separate direct sampled-action gradient support from changes caused through
  shared hidden layers and report the implicated evaluation states read-only.
- CI-gate the diagnostic before any full replay. Do not alter the v2 reward,
  optimizer, model, production policy, or promotion contract during this task.

Optimizer-attribution implementation checkpoint:

- Implementation commit `dfcce1087a8f4cf46306b681347f4eea45fc4955`
  adds a detached canonical pre-update batch observer and an eight-batch
  deterministic replay owner. Every replayed episode must equal its immutable
  journal record, every 2,048-transition stream slice receives a content hash,
  and every post-batch policy must reproduce the stored digest before a report
  can be written.
- The report attributes action-slot legality/selections, advantages, returns,
  and the exact initial unclipped voucher-minus-end policy signal for every
  implicated shop transition. It also performs a three-block Shapley
  decomposition of the voucher-minus-end logit-margin change at every harmful
  fixed-corpus divergence, separating the policy head from both shared hidden
  layers with an exact closure check.
- Real immutable-state smoke evidence passed. At batch 8 the 12 harmful
  `END_SHOP -> BUY_VOUCHER` states gain `1.192015217635949` mean logit margin;
  mean Shapley contributions are `0.5730679789410504` from the first hidden
  block, `0.5375031284198918` from the second hidden block, and only
  `0.08144411027500693` from the policy head. Shared representation drift is
  therefore dominant at those states; the full replay still must determine
  whether collected advantages directly support the same direction.
- Focused observer/model/batch/session/attribution validation: **46 passed in
  5.04s**. CLI import/help, syntax compilation, and `git diff --check` are
  clean. GitHub Actions run `43729336935`, job `132858100773`, passed with
  **3374 passed, 1618 deselected in 304.54s**.
- Resume implementation commit
  `1192a64b98d42fc64a8a90c0463425e5181fdefe` writes cryptographically linked
  replay progress only at immutable batch 1/2/4 boundaries. Restart loads the
  exact corresponding milestone session/journal, validates all prior batch
  summaries and policy linkage, and continues without mutating source
  artifacts. At batches 1/2/4/8, the entire reconstructed checkpoint hash must
  equal the immutable source checkpoint; direct verification of all five
  source milestone checkpoint reconstructions passed.
- Focused resume/observer/attribution validation: **33 passed in 4.16s**.
  GitHub Actions run `43730143157`, job `132860588486`, passed with **3375
  passed, 1618 deselected in 169.94s**. The complete replay is authorized.

Authorized optimizer-attribution replay:

- The initial run published a valid canonical batch-1 replay checkpoint at
  `%LOCALAPPDATA%\Temp\balatro-ppo-progress-study-v1\optimizer_input_attribution_progress.json`
  (8,436 bytes, SHA-256
  `272aee3f24a168881c22d2bd9e9e29ec766ba71b17947e2353fb6bdaee5e70f1`).
  The final output remains absent.
- Run from PowerShell in the canonical repository checkout. The same command
  resumes from the latest verified batch 1/2/4 boundary after interruption:

```powershell
Set-Location -LiteralPath 'D:\0.5 - Coding\0. game-ai\game-ai-framework'; py -3.13 -m games.balatro.env.ppo_progress_study_optimizer_attribution --artifact-directory "$env:LOCALAPPDATA\Temp\balatro-ppo-progress-study-v1" --output-path "$env:LOCALAPPDATA\Temp\balatro-ppo-progress-study-v1\optimizer_input_attribution.json" --maximum-workers 8
```

- Expected wall time is approximately the original eight-batch study runtime
  (about 3 hours 22 minutes), plus small attribution overhead. Progress prints
  once per completed batch. Exit code 0 and the final report are required; a
  replay mismatch fails closed and must not be bypassed.
- The first batch-2 resume failed closed because the diagnostic incorrectly
  required every carryover transition's stored old value/probability to equal
  the current pre-update model. That assumption is invalid: stream carryover
  can legitimately have been collected under the preceding policy.
- Fix commit `c8d220de0234e28ca57f8a21381590bb7135cebb` removes that false
  equality requirement and computes the direct first-step policy signal with
  the frozen PPO importance ratio and clipping gate. A deterministic regression
  now evaluates an exact batch collected under one policy after both policy and
  value heads change. Focused validation: **48 passed in 4.96s**. GitHub Actions
  run `43738547562`, job `132886452168`, passed with **3376 passed, 1618
  deselected in 170.54s**. The existing batch-1 checkpoint remains valid and
  resume is reauthorized.

Completed optimizer-input attribution:

- The crash-resumed run completed with exit code 0 and exactly replayed all
  **2,183 episodes / 8 x 2,048-transition batches**. Every replayed episode,
  post-batch policy, staged checkpoint, behavior report, final journal, replay
  progress file, and all five milestone manifests verified against immutable
  source evidence.
- The canonical 93,889-byte report has SHA-256
  `13ecab65dc77f2386c412e24ff3b360d102aadf9fc01bda63682bc7ad6915d79`.
  The committed copy has a terminal newline (93,890 bytes, SHA-256
  `0cdc60c43f085190bae1e1f33704218e365662d4e3c5f81d974f048c2554984f`)
  and parses to exactly the same report value.
- Whole-batch mean advantages for batches 1 through 8 are respectively
  `-0.7945601921`, `-0.3211239513`, `-0.1284189517`, `-0.0299296852`,
  `0.0118731277`, `0.0131106568`, `0.0156215802`, and `0.0096626447`.
  Thus the earliest and largest updates carry a substantial nonzero global
  advantage offset rather than a centered policy-learning signal.
- Exact voucher-minus-end direct first-step signals are `16.1794780904`,
  `10.8436878355`, `4.9612217819`, `-1.0518518729`, `1.9164966792`,
  `1.8294723610`, `1.1467288187`, and `0.8596393604`, totaling
  **`36.6848730542` toward `BUY_VOUCHER`**. The optimizer inputs therefore
  directly support the harmful shift in seven of eight batches; it is not only
  critic/value drift.
- By batches 5 through 8, voucher selections themselves have positive mean
  advantages (`0.0097435161`, `0.0244353626`, `0.0303672681`, and
  `0.0206094309`) and contribute positive voucher-margin signals. At the 12
  batch-8 harmful fixed states, the actual mean margin shift remains
  `1.1920152176`; its Shapley split is `0.5730679789` first hidden,
  `0.5375031284` second hidden, and only `0.0814441103` policy head. Direct
  advantage support is therefore amplified primarily through shared features.
- Decision: v2 remains rejected and no larger training is authorized. The
  evidence supports one bounded advantage-normalization shadow to test whether
  removing the demonstrated batch-wide offset stabilizes learning; it does not
  yet prove normalization will improve competence.
- Published evidence commit `bde6120aef94f886360302717af7c1f0c21080c1`
  passed GitHub Actions run `43817120680`, job `133131599629`, with **3376
  passed, 1618 deselected in 234.41s**.

## Held and deferred work

- Natural Money Tree live parity evidence is explicitly on hold by user
  direction. It is not passed and must not be inferred.
- No live Balatro run is currently required.
- The frozen training schedule is complete; do not resume or extend it unless a
  later roadmap task explicitly freezes a new experiment.
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
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_DISCARD_V18.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_12_DISCARD_V18_POST_INERT.json`
- `docs/balatro/BALATRO_PPO_BATCH2_WAVE_632_639_TIMING.json`
- `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_TACTICAL.json`
- `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_DECISION_11_SEARCH_SUBOWNERS.json`
- `docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_DECISION_11_ESTIMATE_SUBOWNERS.json`
- `docs/balatro/BALATRO_PPO_BATCH3_EPISODE_908_DECISION_13_CANDIDATE_SUBOWNERS_POST_SCORING_SHELL.json`
- `docs/balatro/BALATRO_PPO_BATCH3_WAVE_901_908_TIMING_POST_SCORING_SHELL.json`
- `docs/balatro/BALATRO_PPO_BATCH4_EPISODE_976_NEEDLE_FIXED.json`
- `docs/balatro/BALATRO_PPO_BATCH4_EPISODE_1081_WHEEL_FIXED.json`
- `docs/balatro/BALATRO_PPO_BATCH4_EPISODE_1169_WATER_FIXED.json`
- `docs/balatro/BALATRO_PPO_BATCH5_EPISODE_1223_MARK_FACING_FIXED.json`
- `docs/balatro/BALATRO_PPO_BATCH7_EPISODE_1911_WALL_FIXED.json`
- `docs/balatro/BALATRO_PPO_BOSS_EXACT_SHADOW_REPORT.json`
- `docs/balatro/BALATRO_PPO_TERMINAL_LOSS_CENSUS.json`
- `docs/balatro/BALATRO_PPO_BOSS_INEXACT_TRACE.json`
- `docs/balatro/BALATRO_PPO_BOSS_EXACTNESS_SHADOW_REPORT.json`
- `docs/balatro/BALATRO_PPO_BOSS_SAFE_PACE_COUNTERFACTUAL.json`
- `docs/balatro/BALATRO_PPO_BOSS_SAFE_PACE_SWEEP.json`
- `docs/balatro/BALATRO_PPO_BOSS_PROGRESS_SHADOW_REPORT.json`
- `docs/balatro/BALATRO_PPO_PROGRESS_REWARD_PILOT_REPORT.json`
- `docs/balatro/BALATRO_PPO_PROGRESS_REWARD_PAIRED_EVALUATION.json`
- `docs/balatro/BALATRO_PPO_PROGRESS_STUDY_REPORT.json`
- `docs/balatro/BALATRO_PPO_PROGRESS_STUDY_BEHAVIOR.json`
- `docs/balatro/BALATRO_PPO_PROGRESS_STUDY_OPTIMIZER_ATTRIBUTION.json`
- `docs/balatro/BALATRO_PPO_STRATEGIC_SHOP_TRACE.json`
- Git history before `ac4a9287260cc485e7eb5476854679ac9cbc2b8d` for completed checkpoint
  narration intentionally removed by the roadmap cleanup.
