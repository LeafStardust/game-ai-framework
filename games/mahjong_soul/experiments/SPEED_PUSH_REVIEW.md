# Speed/push screening ? 21 October 2026

Decision: do not promote `east_speed_push`. The live playbook is unchanged.

The experiment changes only `defense.always_push` in an isolated Three-Player East policy. Two fixed efficiency opponents, engine version 0.4.10 and the same starting deals are used for each pair. Development seeds 20?23 and predeclared held-out seeds 120?123 each cover all three candidate seats: 48 complete matches across both policies and splits. Seed-level paired details and exploratory intervals are in the adjacent JSON files. Replays remain under local `logs/mahjong_soul/experiments/`.

| Split | Policy | First places | Average rank | Hand wins | Deal-in hands | Shape Tenpai reach |
|---|---|---:|---:|---:|---:|---:|
| development | Current East Speed | 2/12 | 1.833 | 25.0% | 8.8% | 44.1% |
| development | Always-push diagnostic | 2/12 | 2.333 | 19.4% | 20.9% | 56.7% |
| held out | Current East Speed | 1/12 | 1.917 | 30.9% | 23.6% | 49.1% |
| held out | Always-push diagnostic | 2/12 | 1.833 | 29.1% | 23.6% | 54.5% |

Always-push reached shape Tenpai more often but had a lower hand-win rate in both splits. Development placement and deal-in results deteriorated substantially. Held-out placement improved by one first place while hand-win rate remained lower; this is a mixed, very small result, not proof that either policy has a superior true match win rate. Four independent seeds per split are insufficient for reliable deployment claims. Hands and rotated seats are correlated; the bootstrap resamples seeds, not individual hands.

Conditional Tenpai timing was later for always-push in both splits (development 7.50 versus 6.83 own discards; held-out 7.33 versus 6.89). Because more hands reached Tenpai, these conditional means are selection-biased and cannot be interpreted as a direct causal slowdown.

The experiment rejects blanket removal of folding as a justified win-rate improvement. It does not validate the current defense model or show that individual folds are correct. The next candidate should improve discard development/wait quality while preserving legal-Yaku checks, then be evaluated with new development and held-out seeds. Seeds in this report have now been inspected and are no longer untouched holdout data for later tuning.

The engine remains a research environment with fixed baseline opponents. These are not Steam AI results. No live capture, game process or native input was used. The production policy factories remain untouched; regression tests verify that constructing the diagnostic agent does not mutate them.
