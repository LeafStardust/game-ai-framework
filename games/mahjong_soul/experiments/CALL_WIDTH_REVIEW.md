# Unsecured opening width: fresh-match screen

## Hypothesis and frozen candidate

The exhaustive [opening-call audit](ALL_OPENING_CALLS_REVIEW.md) recovered a target-hand win in four profile-specific branches, representing two public call contexts. Both calls changed a closed two-Shanten hand with 40 improving copies into an unsecured Tanyao one-Shanten route with seven improving copies. Those losing-match diagnostics suggested a narrow speed bottleneck, but were not an unbiased policy comparison.

`east_speed_call_width` is an offline-only candidate. It adds `calls.unsecured_opening_min_ukeire = 8` to Three-Player East Speed. Only an initial opening from raw two-Shanten into an unsecured one-Shanten route below that threshold is rejected. A call reaching Tenpai, a call already securing Yaku, and later calls after opening are unchanged. Value-honor calls naturally secure Yaku and are preserved. Existing defense, Riichi, Kan, North extraction and legal-Yaku gates are unchanged. Four-player East and South settings are untouched.

Eight is a hypothesis selected from the diagnostic set, not a universal optimal threshold or calibrated winning probability. No threshold or candidate behavior is tuned after inspecting the fresh match outcomes.

Development seeds are 200-203 and held-out seeds are 300-303, each at all three seats against caller and aggressive profiles. Include every finishing position, including baseline first places. The complete plan is 96 matches across both policies and opponent profiles. Every paired starting-deal digest is checked, and actual replay differences determine whether the candidate changed play. RiichiEnv is pinned to 0.4.10 with Mahjong Soul default rules. Source hashes and replays remain in local `logs/mahjong_soul/experiments/call-width-*`.

## Scope and limitations

The opponents are fixed heuristics from the same policy family, not Steam AI, human players or trained independent references. Caller baseline self-play has a one-third first-place rate by seat rotation. Repeated seats, hands and opponent profiles are correlated; seed-cluster intervals are exploratory with only four seeds per split. Divergent actions can change later draws and game length. Conditional shape-Tenpai timing is not a legal-win guarantee.

The development and held-out results must be shown separately by opponent profile. Identical replays mean no observed action-change exposure; they cannot establish a benefit, harm or universal equivalence for the rule. Passing the recorded recovered-win regressions shows those decisions change, not that live win rate improves.

## Completed results

All 96 matches completed. Every one of the 48 paired full replays is identical between baseline and candidate, with zero missing replay files. Adapter and policy-tree hashes match across all four sets; the audit commit advanced Git HEAD during the run but did not change the frozen experiment source. The candidate did not produce an observed action change in these fresh games.

The following metrics are identical for both policies within each row; each policy has twelve matches per row.

| Opponents / split | Hand wins | Deal-in hands | First places | Average rank | Different paired replays |
| --- | --- | --- | --- | --- | --- |
| [Callers / development](call_width_callers_development.json) | 14/42 | 6/42 | 4/12 | 2.000 | 0/12 |
| [Callers / held out](call_width_callers_held_out.json) | 16/48 | 8/48 | 4/12 | 2.000 | 0/12 |
| [Aggressive / development](call_width_aggressive_development.json) | 11/43 | 8/43 | 3/12 | 2.167 | 0/12 |
| [Aggressive / held out](call_width_aggressive_held_out.json) | 16/52 | 13/52 | 4/12 | 2.000 | 0/12 |

This screen is inconclusive for the cutoff because it did not exercise a changed decision. Equal outcomes are not evidence that the filter improves win rate, is harmless in every other hand, or is unnecessary. The recovered diagnostic wins remain specific counterexamples on the inspected deals.

## Decision

Keep the rule offline-only. Three-Player East Speed remains v0.6, and no live settings, launcher behavior, capture, input execution or terminal formatting changed. The exhaustive diagnostics are complete and pushed separately as `54c82617`; this follow-up adds a guarded experimental rule and transparent fresh-match results, not a claimed strength upgrade.

Focused regressions cover both recovered-win contexts, the inclusive copy threshold, preserved Tenpai, preserved secured-Yaku value calls, unaffected four-player settings, and productive calls made after the hand is already open. Next work should estimate completion speed beyond immediate Shanten/Ukeire and obtain actual changed-decision exposure before judging general winning benefit. No game launch is needed.

Final verification: all 817 Mahjong tests passed with the optional simulator enabled.
