# Call-capable and aggressive opponent comparison

## Frozen setup

The simulator now supports explicit `efficiency`, `callers`, `aggressive` and `mixed` opponent profiles. `callers` uses two independent current East Speed policy instances. `aggressive` uses two instances with always-push enabled; calling and legal-Yaku checks remain active. `mixed` rotates one of each relative to the candidate seat and has reproducible single-hand test coverage, but is not part of the outcome comparison below. Each agent sees only its own observation and public history.

The tested candidate is the unchanged offline `east_speed_ready_push`: permit danger 90 with at least three exact-scored legal Ron copies, while retaining the other defensive gates. The production baseline is `east_speed`. Neither production playbook settings nor native input behavior changed.

Development seeds are 80-83; held-out seeds are 180-183, each at all three candidate seats and against both tested opponent profiles. Both seed sets and the candidate definition were fixed before reading any results. All 96 matches completed with no policy or legality failures. Engine version is RiichiEnv 0.4.10, with Mahjong Soul default rules. Replay files retain initial deal digests and source hashes under local `logs/mahjong_soul/experiments/ready-push-{callers,aggressive}-{development,held-out}`.

Submitted native action counts are recorded per player, and the outcome review checks actual settled Pon, Kan and Riichi events in the MJAI replays. Comparisons reject pairs with different opponent profiles or opponent policies by seat. Each profile is reported separately.

## Interpretation limits

These are fixed heuristic opponents from the same code family, not independent learned agents, human opponents or Steam AI. Aggressive means always-push settings; it does not imply proven higher strength. The caller baseline is effectively self-play: all three players use the same deterministic policy, so rotating the candidate seat can replay the same trajectory and produces a one-third first-place baseline by construction when ranks are unique. It is not a measured universal win-rate target.

Seats and hands within a seed are correlated; the comparison resamples whole seeds. Four seeds per split are a small screen. Divergent decisions change later draws and game length. Submitted call attempts can differ from settled calls when simultaneous actions compete, so replay events provide the activity check. Timing includes shared caches and is not a comparative latency benchmark.

The full Mahjong suite passed 795 tests, including reproducibility under all new opponent profiles, relative mixed-seat assignment, and rejection of mismatched comparison opponents.

## Completed outcomes

Each row is twelve matches at all three seats on four seeds. Baseline and candidate comparisons use the same opponent profile, seat assignments and initial deal digests.

| Opponents / split | Policy | First places | Average rank | Hand wins | Deal-in hands | Changed paired replays |
| --- | --- | --- | --- | --- | --- | --- |
| [Callers / development](ready_push_callers_development.json) | Baseline | 4/12 | 2.000 | 13/45 | 10/45 | 3/12 |
| Callers / development | Narrow ready push | 4/12 | 2.000 | 13/45 | 10/45 | 3/12 |
| [Callers / held out](ready_push_callers_held_out.json) | Baseline | 4/12 | 2.000 | 16/48 | 10/48 | 3/12 |
| Callers / held out | Narrow ready push | 4/12 | 2.000 | 16/48 | 13/48 | 3/12 |
| [Aggressive / development](ready_push_aggressive_development.json) | Baseline | 3/12 | 2.083 | 11/41 | 9/41 | 3/12 |
| Aggressive / development | Narrow ready push | 3/12 | 2.083 | 11/41 | 9/41 | 3/12 |
| [Aggressive / held out](ready_push_aggressive_held_out.json) | Baseline | 3/12 | 1.917 | 16/46 | 9/46 | 3/12 |
| Aggressive / held out | Narrow ready push | 3/12 | 1.917 | 16/46 | 9/46 | 3/12 |

Twelve of 48 paired full replays changed, so this comparison actually exercised the candidate in both opponent styles and both seed sets. There were no missing replay pairs. Aggregate hand wins and placement did not improve in any group. Development timing/shape-Tenpai differences do not establish better winning decisions.

Against held-out callers, deal-in rate rose from 20.8% to 27.1%. Seed/seat pairs (180, 1), (181, 1) and (182, 0) each gained one deal-in hand and finished 600 points lower. Placement and hand-win count remained unchanged. Against held-out aggressive opponents, all final scores, ranks, hand counts, wins and deal-ins stayed unchanged despite three changed replays. Aggressive development included score differences but no aggregate placement, win or deal-in gain.

## Verified opponent activity

The following counts are actual settled opponent events in the twelve baseline replays per group, not merely configured capabilities or submitted mouse actions. Repeated seats are correlated and these totals are not independent samples. [Activity data](opponent_activity.json) also records the candidate runs.

| Profile / split | Pon | Kan (all types) | Accepted Riichi |
| --- | --- | --- | --- |
| Callers / development | 54 | 8 | 40 |
| Callers / held out | 38 | 0 | 34 |
| Aggressive / development | 36 | 6 | 41 |
| Aggressive / held out | 32 | 0 | 35 |

## Decision and next step

Keep `east_speed_ready_push` disabled in production. It has no demonstrated winning benefit here and incurs extra held-out deal-ins against active callers. This small screen does not validate every existing fold, but it gives no reason to loosen the live threshold. Three-Player East Speed remains v0.6; Four-Player East Speed and South Attack are unchanged. No live agent was launched and terminal recommendation formatting is unchanged.

The new opponent profiles remain available for future experiments. Next, inspect offensive hand development and call timing in the new losing replays rather than further loosening the same defense threshold. No game launch is needed.
