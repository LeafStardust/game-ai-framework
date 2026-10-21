# East Speed fold audit and narrow ready-push experiment

## Recorded folds

[Audit data](fold_audit.json) covers 69 unique current East Speed fold boards from six recorded sessions, found by scanning all 27 session directories and replaying historical fold snapshots with source revision `cebf0931`. Four additional historical folds now produce an attacking decision under the current policy and are outside these 69 current folds. Repeated board tokens were deduplicated. These are observed decisions, not a complete census of opportunities hidden by older client toggles.

- Forty selected discards have zero danger under the current heuristic; 29 have nonzero danger.
- Twenty-two folds increase legal winning distance relative to the fastest available route.
- Five break Tenpai. Two have Ron-blocking Furiten; the other three require danger-90 discards, above the live Sanma limit of 85.
- No selected fold has a faster alternative at no higher risk under the existing maximum-danger/total-danger ordering. This verifies the selection rule on these boards, not the accuracy of the risk model. Zero heuristic danger is not universally proof of safety.

The three non-Furiten ready folds are session `20261020T122443-992610Z`, sequences 818 and 841 (four legal Ron copies, 12,000 points), and `20261020T120330-675251Z`, sequence 816 (three legal Ron copies, 7,700 points). Two positions are repeated opportunities within one hand, not independent missed wins. No counterfactual win follows from the recorded board alone.

There is no demonstrated safe-progress selection bug in this sample. The question is whether a narrow, calculated push is preferable to the current danger threshold.

## Frozen candidate

`east_speed_ready_push` exists only in the offline simulator. It permits maximum heuristic danger 90 instead of 85 for an exact-scored, non-Furiten Tenpai with at least three available legal Ron copies. The number 90 is a relative risk score, not a deal-in percentage. All other gates remain: one threat, sufficient wall, legal Yaku, minimum points, available waits and legal-action bindings. It does not add a value-first strategy or change any production playbook setting.

Recorded-board regressions prove actual action exposure: the candidate discards 7 Pin to retain Tenpai where the baseline folds. Tests also preserve Furiten, two-threat, late-wall, two-copy, value and danger limits. The complete Mahjong suite passed 786 tests with the optional simulator enabled.

Development seeds are 70-73 and held-out seeds are 170-173, each at all three seats against two fixed efficiency opponents. The thresholds and seed sets were fixed before reading results. RiichiEnv is pinned to 0.4.10 with Mahjong Soul default rules. Paired starting deal digests match. Raw replays and source hashes remain in local `logs/mahjong_soul/experiments/ready-push-*`.

## Results and decision

| Split | Policy | First places | Average rank | Hand wins | Deal-in hands | Different paired replays |
| --- | --- | --- | --- | --- | --- | --- |
| [Development](ready_push_development.json) | Baseline | 8/12 | 1.500 | 20/58 (34.5%) | 3/58 (5.2%) | 0/12 |
| Development | Narrow ready push | 8/12 | 1.500 | 20/58 (34.5%) | 3/58 (5.2%) | 0/12 |
| [Held out](ready_push_held_out.json) | Baseline | 1/12 | 2.333 | 18/70 (25.7%) | 11/70 (15.7%) | 2/12 |
| Held out | Narrow ready push | 1/12 | 2.333 | 15/63 (23.8%) | 9/63 (14.3%) | 2/12 |

All 48 matches completed. Development did not exercise the candidate. Held-out play changed two actual discard choices:

- Seed 172, seat 1: first divergence is Red Dragon versus 5 Pin. Placement improves from third (-5,400 points) to second (32,000). Hand wins stay at one; deal-in hands fall from two to zero, with game length changing from eight hands to three.
- Seed 173, seat 0: first divergence is 8 Pin versus 7 Pin. Placement worsens from second (46,200) to third (17,000). Hand wins fall from three to zero; both have zero deal-in hands, with game length changing from five hands to three.

There is no aggregate placement gain and the hand-win rate is lower in the small held-out sample. Diverging draws and game lengths prevent treating individual hands as independent paired trials. Four independent seeds per split and fixed heuristic opponents are insufficient to infer a true strength difference. These are not Steam AI or human match results.

**Do not promote this candidate.** Live East Speed, South Attack, launcher behavior and terminal output remain unchanged. This is a rejected narrow-threshold experiment, not proof that every current fold is correct.

Next: evaluate with call-capable and aggressive fixed opponents before tuning further defense thresholds. More exposure is needed than replaying another small seed set against the same call-passing baseline. No game launch is needed.
