# Earlier-hand development screening ? 21 October 2026

Decision: keep `early_development` disabled in live playbooks. No win-rate improvement was demonstrated.

This experiment targets closed two-/three-Shanten hands, rather than late one-Shanten ties. The bounded proxy compares the public remaining-copy-weighted next-stage Ukeire after a useful draw and best subsequent discard. It considers at most three candidates within two improving copies of the immediate maximum and never sacrifices nearest Shanten. It is an approximate shape-development objective, not a learned or calibrated win probability. Calls and fold handling are unchanged.

Before the full comparison, seed 50 seat 0 produced an identical replay and seed 51 seat 0 produced a changed replay. The generated hand fixture independently validates an offensive choice difference at equal 47-copy Ukeire. These inspected seeds are part of the development set, not the holdout. The candidate was frozen before running development seeds 50?53 and held-out seeds 150?153, across all three seats: 48 complete matches in 24 pairs.

| Split | Policy | Hand-win rate | Deal-in rate | Average rank | First places | Changed paired replays |
|---|---|---:|---:|---:|---:|---:|
| development | Current East Speed | 28.3% | 10.9% | 2.333 | 1/12 | 2/12 |
| development | Earlier-hand candidate | 27.7% | 14.9% | 2.417 | 1/12 | 2/12 |
| held out | Current East Speed | 26.7% | 0.0% | 1.667 | 4/12 | 9/12 |
| held out | Earlier-hand candidate | 26.7% | 0.0% | 1.667 | 4/12 | 9/12 |

The calculation was exercised: 2/12 development pairs and 9/12 held-out pairs have different full replays. Instrumenting seed 51 seat 0 identified an offensive change from 2 Pin to 8 Sou at equal two-Shanten and 33 improving copies, increasing the development proxy from 348 to 396. The full match did not gain a win or placement from that change. This confirms mechanism/exposure, not that the alternative was objectively stronger.

Held-out outcomes were unchanged despite replay differences. Development hand-win rate declined slightly and deal-in rate rose. Four independent seeds per split are too few for reliable general strength conclusions; this is a screening decision not to adopt an unproven change. Conditional Tenpai timing improved in development but did not improve held out, and remains a selection-biased diagnostic.

No live factory, default policy setting, launcher, capture or input behavior changed. Neither this candidate nor the previous inactive lookahead prototypes should be advertised as win-rate improvements. Replays remain local under `logs/mahjong_soul/experiments/early-development-*`; adjacent JSON includes paired seed details and source hashes. Seeds here are now inspected and cannot be reused as untouched holdout data.

The next research direction is to evaluate a trained Sanma policy as a decision reference, with verified observation/action/rule compatibility. The local hand-shape proxies tested so far have not demonstrated a win-rate gain; adding more of the same without a stronger reference is not justified by these results.

## Subsequent adapter correction

The [offense audit](OFFENSE_AUDIT_REVIEW.md) found duplicate physical-copy intents in the simulator. The three-entry shortlist in this historical run was therefore not guaranteed to contain three distinct discard choices. The recorded outcomes and source hashes remain valid for the old adapter, but a three-distinct-choice interpretation requires re-evaluation under the corrected contract. The prototype remains disabled and no strength gain is claimed.
