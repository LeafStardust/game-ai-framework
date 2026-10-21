# East Speed call and ready-Yaku review

## Recorded-board audit

Replayed the current policy on 50 distinct Chi/Pon decision boards found in the ten newest session directories (nine contained those boards). Sources span `20261020T060105-596741Z` through `20261020T124308-369100Z`. Repeated frame snapshots were deduplicated by decision board token. These are recorded opportunities, not all possible calls suppressed by an older client setting.

Before this fix, the current policy chose 17 Pon, two Open Kan and 31 Skip actions. The two Open Kan choices occurred on boards also offering Pon. Rejected post-call discard options were primarily slower legal routes or losses of improving copies; rejection counts are not counts of missed wins. No claim is made that all accepted or skipped calls are optimal.

The concrete bug is in the defensive push gate. In session `20261020T062747-902083Z`, the hand could Pon 2 Pin, discard 3 Pin, and wait on White Dragon or Red Dragon. Exact scoring finds four available legal Ron copies, each completing a Yakuhai triplet for 2,000 points. The partial hand has only Dragon pairs, so its already-completed-Yaku flag is false. The old push gate treated that as no legal Yaku even after the complete-hand scorer proved the winning route.

The recorded 3 Pin discard had danger 90, above Sanma East's limit of 85. Its original Skip remains justified by that limit. A derived regression adds 3 Pin to the threatening player's earlier river, making the discard Genbutsu while preserving the called tile as the latest discard. The old gate still skips; the corrected gate takes the legal Tenpai call. This is a counterfactual correctness regression, not evidence of an actual missed win in that recording.

## Change and constraints

Four-Player East Speed v0.3 and Three-Player East Speed v0.6 allow exact legal ready-hand Ron scoring to prove the Yaku for the push gate. This applies to both call follow-ups and normal discards. It does not waive danger, wall, number of threats, available-copy, Furiten or minimum-point checks. Non-ready hands still need the existing partial-Yaku proof. South Attack retains its previous settings and behavior. Terminal output is unchanged.

Eight focused regression cases cover the safe Sanma pair wait, the equivalent four-player East hand, danger, Furiten, exhausted waits, minimum value, the former gate, and East-only configuration. The full Mahjong suite passed 776 tests before the additional four-player regression was added; all eight focused cases passed afterward. No native input or live agent process was started.

Replaying the same 50 recorded boards after the fix changed zero actions. That is expected for the recorded dangerous pair wait and does not establish general equivalence.

## Full-match screening

The offline `east_speed_partial_yaku` reference disables only the new scored-ready-Yaku setting. Current `east_speed` enables it. Development seeds are 60-63; held-out seeds are 160-163. Each covers all three seats against two fixed efficiency opponents, using RiichiEnv 0.4.10 and Mahjong Soul default rules. The candidate definition was fixed before either outcome set was inspected. Raw replays and source hashes remain under `logs/mahjong_soul/experiments/scored-ready-yaku-*`.

The comparison reports linked below record outcomes and actual replay differences. This small screen cannot establish a Steam win-rate improvement, and passing the regression proves a decision-gate correction rather than overall playing strength.

| Split | Paired matches per policy | Changed paired replays | Hand wins per policy | First places per policy | Deal-in hands per policy |
| --- | --- | --- | --- | --- | --- |
| [Development](scored_ready_yaku_development.json) | 12 | 0/12 | 49/88 (55.7%) | 11/12 | 0/88 |
| [Held out](scored_ready_yaku_held_out.json) | 12 | 0/12 | 17/54 (31.5%) | 6/12 | 0/54 |

All 48 matches completed, with 24 exact paired replay matches and no missing replays. These seeds did not exercise the changed gate. Identical outcomes therefore provide no measured strength gain. The correction is enabled because the scored legal-Yaku regression establishes the old rejection was wrong under its existing thresholds, not because these match results favor it. The fixed efficiency opponents are weak references and these rates must not be advertised as expected Steam performance.

Next: inspect speed lost through actual fold decisions and evaluate against more than one fixed opponent style before further policy tuning. No live game launch is needed for that work.
