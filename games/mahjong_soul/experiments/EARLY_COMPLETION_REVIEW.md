# Earlier-hand discard completion

`east_speed_discard_completion` was evaluated as an offline Three-Player East candidate. It compares earlier discard choices using bounded legal-Tsumo completion cost, rather than treating immediate improving-copy count as the entire speed objective. After the completed fresh evaluation below, Three-Player East v0.7 provisionally enables it. Other playbooks and terminal formatting are unchanged.

## Frozen candidate

The candidate applies only to closed hands with no fixed melds, nearest legal-route Shanten two, and no recognized opponent threat or accepted/declared Riichi. It preserves that nearest Shanten and all existing call, North, Kan, Riichi and defensive logic. Four-Player East and Four-Player South settings do not enable it.

The existing policy's preferred discard is always included. Two alternatives are shortlisted using the existing public-copy-weighted two-stage development proxy. These alternatives must retain two Shanten and positive improving copies. Their immediate Ukeire may be lower: the completion estimate explicitly includes the wait for the first useful draw. The proxy is a shortlist heuristic, not a win probability.

Normal/red discards with the same retained kind counts share a forecast. Honor permutations with the same retained-count/unseen-copy profiles also share a forecast in this closed Tsumo-only model. The original safety/value order chooses the representative, so interchangeable honor discards cannot crowd all three slots. Other equal-cost states are not assumed equivalent.

Each of at most three shortlisted states is evaluated using `estimate_tsumo_draws`, with a 2,000-state budget and horizon `min(12, floor(wall_remaining / 3))`, at least one. An absent wall estimate uses twelve. With fewer than three estimated own draws the policy retains its original discard without forecasting. This wall calculation is an approximation: calls, Kan and North extraction can change turn order and draws.

The selected option minimizes expected draw cost capped at that horizon. Costs rounded to twelve decimals tie using the original immediate-speed, danger and value order. If any shortlisted forecast is unavailable, the original choice is retained rather than selecting opportunistically among incomplete estimates. Diagnostics record every completed or unavailable shortlisted forecast and the original offensive choice; normal terminal output stays action-only.

## Model limits

The model uses own hand and public counts, not hidden hands or future wall order. Useful draws deplete the unknown pool; unchanged-hand failures are returned to it. It only follows Shanten-reducing progress and scores actual legal terminal Tsumo waits. Future Ron, calls, Riichi, ready repairs and non-ready equal-Shanten changes are excluded. The unknown pool includes opponents' concealed tiles. These forecasts are model quantities, not calibrated real-game win odds, nor a claim that a larger model probability guarantees the better play.

This candidate deliberately uses the cheaper monotonic Tsumo estimator instead of the more expensive ready-repair/Ron sensitivity model. It forecasts a closed continuation even though the actual policy can subsequently call. That mismatch must be judged with fresh match outcomes. Hand value remains a tie-break; the forecast does not optimize Han. This is a speed experiment for Three-Player East, not a replacement for the South Attack playbook.

## Development exposure

An initial radius-of-two-copies prototype produced identical paired full-game replays at seed 600 seat 0 and seed 601 seat 0. The shortlist was then broadened to distinct development paths, with equivalent honor forecasts collapsed. These inspected prototypes are not strength evidence or held-out tests.

A generated legal hand, `Random(612)` sample 101, supplies a reproducible choice difference: the baseline discards 6 Sou, while the candidate discards 9 Pin. Both retain two Shanten. Immediate improving copies fall from 35 to 22, while the model's twelve-draw capped cost improves from about 11.567 to 11.323. The corresponding model completion probability rises from about 13.86% to 21.71%. This is a diagnostic example, not a measured real-game win probability or an endorsement of that discard in general.

The final frozen exposure screen covers seed 602 seat 0 and seeds 603-608 at all three seats: nineteen paired assignments, thirty-eight full matches against callers. It records 91 forecasted decisions. One pair, seed 606 seat 0, changed its full replay and contained two changed discard decisions. The first switches 7 Sou to Green Dragon; its public request reproduces through the complete policy pipeline. The baseline won three of four hands and placed first, while the candidate won none of three hands, dealt in twice and placed last. That inspected adverse outcome is retained rather than presented as a gain. Later draws and opponent actions diverge after the changed decisions, so it does not establish expected strength on its own.

[The complete exposure summary](discard_completion_exposure.json) includes every positive and negative pair with verified frozen source hashes. The generated and native public positions are regression fixtures under `tests/mahjong_soul/fixtures/`. The exposure screen is excluded from the fresh strength comparison.

`python -m agents.mahjong_soul.discard_probe --seed <seed> --seat <seat> --output <new-directory>` saves both full offline replays, shortlisted forecasts, the original offensive action, and the first changed public request. It refuses existing output and requires the pinned simulator. This makes coverage failures distinguishable from a ranking that genuinely changes play.

## Fresh evaluation plan

Settings are frozen before these outcomes: development seeds 610-613 and held-out seeds 710-713, each at all three seats, current policy versus candidate, separately against caller and aggressive profiles. This gives 96 full East matches and 48 pairs. Check actual replay differences before interpreting outcome differences. Report hand wins, deal-ins and placement separately by profile and split; do not pool this with the inspected exposure screen.

The four seed clusters in each split are small, rotated seats are correlated, caller baseline games repeat across seats, and both opponent profiles share the same heuristic family. They do not stand in for humans, Steam AI or an independent trained engine. No threshold or shortlist tuning is permitted using held-out outcomes. Concurrent-run timings and cache effects are not a controlled latency comparison.

## Verification

All 870 Mahjong tests passed with pinned optional simulator dependencies available. New tests cover real forecasts, immutable public state, nearest-Shanten preservation, insufficient-wall bypass, unavailable-option fallback, open/threat protection, equivalent-honor grouping, a generated choice difference, the captured native policy decision and isolation from production factories. This verifies behavior, not improved win rate.

## Completed fresh results and promotion

All 96 full East matches completed, with identical initial deals in all 48 paired assignments and one verified frozen policy hash. Fourteen pairs changed their actual full replay: one per development profile, five caller held-out pairs and seven aggressive held-out pairs.

| Opponents / split | Baseline to candidate hand wins | Deal-ins | First places / 12 | Average rank | Changed pairs / 12 |
| --- | --- | --- | --- | --- | --- |
| Callers / development | 17/54 to 17/54 | 9 to 9 | 4 to 4 | 2.000 to 2.000 | 1 |
| Aggressive / development | 15/48 to 15/48 | 7 to 7 | 4 to 4 | 2.083 to 2.083 | 1 |
| Callers / held-out | 15/54 to 17/54 | 14 to 13 | 4 to 6 | 2.000 to 1.833 | 5 |
| Aggressive / held-out | 7/50 to 8/51 | 11 to 11 | 2 to 2 | 2.333 to 2.333 | 7 |

Thus the held-out realized hand-win rate rose from 27.78% to 31.48% against callers and 14.00% to 15.69% against aggressive opponents. Development outcome totals were unchanged. The aggressive candidate played one additional hand; its denominator must not be silently held at fifty. These are small offline sample results, not a measured improvement against Steam AI or humans. Caller baseline seat rotations reuse the same all-baseline game, so their one-third first-place rate is not independent strength evidence.

[Caller development](early_completion_callers_development.json), [caller held-out](early_completion_callers_held_out.json), [aggressive development](early_completion_aggressive_development.json), and [aggressive held-out](early_completion_aggressive_held_out.json) retain full paired comparisons, replay coverage and seed-cluster uncertainty. No setting was tuned using these outcomes.

The consistent direction across both held-out profiles, unchanged development outcomes and no extra held-out deal-ins support a **provisional** promotion to Three-Player East Speed v0.7. This is not evidence of a universally stronger policy; four seed clusters per split remain a limited screen. Four-Player East, Four-Player South, calls and defense thresholds are unchanged. The adverse inspected seed-606 game is preserved above and remains outside the prospective comparison.

The [latency observations](early_completion_latency.json) cover two inspected fixtures, not worst-case latency. Full policy selection took 1.658 seconds on the first native fixture and a 0.113-second warm median. The generated fixture's first evaluation took 0.678 seconds after shared caches were already warm, then a 0.124-second warm median. Input recognition/clicking was not included and no live gameplay input was sent. Existing freshness and native preflight checks remain in force.

The fresh runs recorded HEAD `0cd992c7` while the pending candidate source was subsequently committed as `1bb6080f`. All four frozen policy hashes were verified against that unchanged candidate before promotion. Historical reproduction should use `1bb6080f`, rather than the recorded earlier HEAD alone. Promotion changes the default factory afterward. The simulator explicitly disables the promoted flag for its `east_speed` control and older experimental variants; `east_speed_discard_completion` explicitly enables it, preserving a meaningful control/candidate comparison.

The final production configuration passes all 870 Mahjong tests, including native fixture parity between the enabled policy and evaluated candidate. Next is live Three-Player East AI-room validation using the normal agent launcher and its existing recordings. The Steam app and live automatic runner were not launched during this work.
