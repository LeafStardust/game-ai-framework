# Wait-quality screening ? 21 October 2026

Decision: neither lookahead prototype is enabled in the live playbook. There is no measured win-rate improvement.

The strict `east_speed_lookahead` variant preserves immediate Shanten and Ukeire and uses next-useful-draw wait-copy quality only for closed one-Shanten ties. Its development seeds were 30?33; held-out seeds were 130?133.

The bounded `east_speed_two_draw` variant preserves Shanten but can consider discards within two immediate improving copies of the best. It compares useful-draw-weighted future wait copies rather than conditional wait quality alone. Its development seeds were 40?43; held-out seeds were 140?143. The two-copy bound and Ron/Tsumo weighting were frozen before evaluation.

Each split used all three candidate seats against the same fixed efficiency opponents, with matching seeded initial deals. Across both variants there were 96 completed matches, comprising 48 paired seat assignments.

| Candidate | Split | Pairs | Different full replays | Baseline hand-win rate | Candidate hand-win rate |
|---|---|---:|---:|---:|---:|
| Strict tie-break | development | 12 | 0 | 38.1% | 38.1% |
| Strict tie-break | held out | 12 | 0 | 21.2% | 21.2% |
| Bounded two-draw | development | 12 | 0 | 29.1% | 29.1% |
| Bounded two-draw | held out | 12 | 0 | 29.8% | 29.8% |

All full replays within each pair were identical, not merely final scores. The sample therefore lacks observed action-change exposure for these prototypes. It cannot establish that the proxies are universally equivalent to the existing policy or that they improve strength. Zero-width bootstrap differences in these files describe this unexercised sample; they must not be presented as precise evidence of general equivalence.

A recorded closed hand from session `20261020T124308-369100Z`, decision 941, has an offensive tie: 7 Sou and 7 Pin both preserve one-Shanten with 23 improving copies but differ on the future-wait proxy. The entire policy folds that original board against threats, selecting 1 Pin in both variants. Thus the fixture validates the isolated offensive calculation; it is not a discovered missed live win or an actual changed game decision. Direct instrumentation confirmed the new calculations are invoked when their settings are enabled.

The live defaults retain their original discard ordering and no extra lookahead computation. Future experiments should target earlier hand-development choices or broader candidate exposure, and first check whether the candidate changes any decisions. All seeds reported here have now been inspected and cannot serve as fresh holdouts for subsequent tuning. More samples of an unexercised tie-break are not a win-rate fix.
