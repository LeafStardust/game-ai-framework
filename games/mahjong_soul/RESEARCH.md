# Research and evaluation

## Relevant primary sources

- [Meowjong: Building a 3-Player Mahjong AI using Deep Reinforcement Learning](https://arxiv.org/html/2202.12847v3), Zhao and Holden, 2022. Separates Discard, Pon, Kan, Kita and Riichi models; supervised pretraining precedes self-play improvement of discards. Its evaluation uses many rounds and explicit outcome statistics. Its reported outcomes and opponents must not be treated as our Steam match benchmark.
- [Suphx: Mastering Mahjong with Deep Reinforcement Learning](https://arxiv.org/html/2003.13590v2), Li et al., 2020. Uses reinforcement learning with global reward prediction, oracle guidance during training and runtime policy adaptation. This motivates evaluating whole-game outcomes in addition to local hand progress. Hidden opponent information must never enter our live policy.
- [Mortal source](https://github.com/Equim-chan/Mortal) and [documentation](https://mortal.ekyu.moe/). An implementation reference for learned Riichi policies. No Mortal code or model weights have been integrated here; four-player capability must not be assumed to transfer to Sanma.

These are research references, not evidence that our heuristic agent has their strength. Our agent is still a hand-written policy, without supervised pretraining or self-play learning.

## Recorded-game benchmark

Run from the Mahjong worktree:

```powershell
.\.venv\Scripts\python.exe -m agents.mahjong_soul.benchmark --output logs/mahjong_soul/benchmark.json
```

This reads recordings only, with no game launch or input. It reports hand-win and deal-in rates, match first-place rate and average score rank, plus a clearly labeled Tenpai-speed proxy: the own-discard count at the first recorded positive-copy Tenpai recommendation. That proxy is conditional on reaching a recorded ready recommendation and may miss client-automated turns. It is not server-confirmed time to Tenpai.

Server Hule events count wins even when Auto Win handled the click. Double Ron counts once per hand for deal-in rate. Restored event histories are deduplicated with live history by connection, round, event name and step. Complete matches need captured initial-round history and final match scores; incomplete/reconnection fragments remain listed but are excluded from aggregates. Halted matches that reach their end remain included, with issue counts. Score ties are excluded from placement statistics rather than guessing the client's tiebreak.

Groups separate player count, East/South, AI-room verification, rule configuration, source revision and playbook version. Wilson 95% intervals show the uncertainty of rate estimates, assuming independent observations; correlated hands and uncontrolled human interventions limit that interpretation. Different revisions or opponents are not a controlled A/B experiment. A single match cannot establish a strength improvement.

## Next development decisions

Keep East Speed's requested order: fastest legal winning progress, then defense, then value. Use actual boards to diagnose missed wins and preserve legal-action masking and Yaku validation. Keep hand-win rate distinct from match first-place rate: small fast wins do not automatically maximize final placement.

An initial [offline Sanma harness](SIMULATION.md) now runs the current policy and a fixed efficiency baseline on matching seeds and seat assignments using RiichiEnv. Engine parity remains under validation. Candidate policies should play the same deals before comparing speed and outcomes. Recorded-board replays alone still show action differences only; they cannot measure counterfactual wins. Learned policies or external-engine adapters require a separately verified rules/features/action mapping and actual usable model artifacts. They are not implemented by adding these references.

## Trained Sanma reference availability

The [checkpoint audit](experiments/TRAINED_SANMA_REVIEW.md) records the inspected revisions and artifact blockers. No trained Sanma model has been integrated or benchmarked. The linked c3 checkpoint in the inspected Sanma-named fork is documented as four-player, so it is not a valid Sanma substitute.
