# ROADMAP - SINGLE SOURCE OF TRUTH

Authoritative development state for Balatro Red Deck / White Stake competence
in `LeafStardust/game-ai-framework`, branch
`feat/v1.0-red-white-competence`.

Last synchronized implementation HEAD:
`e322767e0e6e58069ea47a1f96c6da0a70a74593`.

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

## Exact active task

Optimize the demonstrated repeated exact-card collection detachment owner for
episode-908 tactical decision 13, without weakening alias isolation.

Requirements:

- Inspect the canonical `BalatroState` tactical alias-detachment owner and the
  exact inert generated-consumable/discard shell call path before changing it.
  Remove only repeated exact-state traversal whose replacement preserves the
  same graph identity, card isolation, public-state hashes, and input
  immutability.
- State/card subclasses, extra or mutable card fields, cross-collection shared
  identity, and malformed unsupported containers must retain graph-preserving
  fail-closed behavior. Do not cache by hidden identity across state changes.
- Add focused deterministic alias/parity regressions, pass GitHub Actions, and
  rerun the exact decision-13 diagnostic before considering the next owner or
  any additional bounded batch.
- Do not start unbounded/full training, inspect promotion results, change
  policy/hyperparameters/search schedule, or authorize another batch without
  new timing evidence.

## Held and deferred work

- Natural Money Tree live parity evidence is explicitly on hold by user
  direction. It is not passed and must not be inferred.
- No live Balatro run is currently required.
- Remaining slow-tail episodes are admitted only through the bounded campaign
  task above.
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
- Git history before `ac4a9287260cc485e7eb5476854679ac9cbc2b8d` for completed checkpoint
  narration intentionally removed by the roadmap cleanup.
