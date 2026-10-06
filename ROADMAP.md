# ROADMAP - SINGLE SOURCE OF TRUTH

Authoritative development state for Balatro Red Deck / White Stake competence
in `LeafStardust/game-ai-framework`, branch
`feat/v1.0-red-white-competence`.

Last synchronized implementation HEAD before this roadmap cleanup:
`ac4a9287260cc485e7eb5476854679ac9cbc2b8d`.

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

Latest implementation gate before cleanup:

- Commit `65e9d6f4d4733a18baa650a3fe850322edcf3a41`.
- GitHub Actions run `37413943005`, job `112108299554`.
- Actual job log: **3154 passed, 1613 deselected in 206.61s**.

## Exact active task

Read the canonical generated-consumable transition owner and its parity,
mutation-isolation, and capability tests. Design and implement the narrow
inert-capability optimization that avoids the unnecessary mutable tactical
projection demonstrated above while preserving exact behavior for every capable
Eight Ball, Main Generator, and Sixth Sense path.

Requirements:

- Make the change at the generated-consumable transition/state-projection owner,
  not in the PPO learner, search schedule, or a rescue cache.
- Prove the inert result is behaviorally identical and does not expose mutable
  aliases to any caller that can mutate it.
- Preserve full isolation and existing outcomes for capable paths.
- Treat unknown, malformed, subclassed, or ambiguous capability state as
  unsupported/fail-closed; never classify it inert by approximation.
- Add focused deterministic regressions for exact inert identity/value behavior,
  mutation isolation, capable paths, and malformed capability state.
- Re-profile the exact episode-43 decision-11 target after CI. Preserve the
  digest, selected action/indices, and search-attempt trace before evaluating
  performance.
- Do not profile decision 12, resume a second optimizer batch, start full
  training, change policy/hyperparameters/search schedule, or widen mechanics
  until this task is green and recorded here.

## Held and deferred work

- Natural Money Tree live parity evidence is explicitly on hold by user
  direction. It is not passed and must not be inferred.
- No live Balatro run is currently required.
- Decision 12 and the remaining slow-tail episodes are deferred until decision
  11 is repaired and re-profiled.
- Higher stakes and other decks begin only after controlled Red/White promotion.

## Resume evidence index

- `docs/balatro/BALATRO_PPO_EPISODE_43_TACTICAL_COST.json`
- `docs/balatro/BALATRO_PPO_EPISODE_43_DECISION_11_SUBOWNERS.json`
- Git history before `ac4a9287260cc485e7eb5476854679ac9cbc2b8d` for completed checkpoint
  narration intentionally removed by the roadmap cleanup.
