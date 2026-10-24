# Three-game assist and pair-route review

The latest run completed all three requested matches, with two automatic room
restarts and normal budget stop. All 251 submitted gameplay actions and all 44
assist changes were confirmed; there were no blocked inputs or rejected decisions.
Own final scores were 41,100 (second), 15,400 (third), and 36,000 (second).

Recommendation-to-submit median was 1.341 s, maximum 3.775, with 142 of 251
meeting 1.5 s. Auto Win attempt-to-recorded-confirmation median was 1.134 s over
19 changes; Auto Kita median was 1.108 s over thirteen. These are recorded
confirmation intervals, not pure client response times. C had one much later
confirmation; do not infer the switch itself took that entire interval to react.
R/K preparation is scheduled between turns, but neither instantaneous switches
nor the overall one-second target have been demonstrated.

## C/D beyond Riichi

Previously accepted Riichi was the sole trigger. New bounded ready-hand checks
compare actual scoring/waits against hypothetical legal calls and one-draw
continuations, including red-five replacements. C can be enabled for a ready hand when no examined call improves
its value/waits. D additionally requires an open Tenpai hand with no better
one-draw discard, and confirmed Auto Win plus Auto Kita when extraction is desired.
Do not enable D before discarding a different selected tile. Closed hands retain
Riichi/value-development options; C is not enabled for a provisional unready plan.

Checks preserve South value-first versus East speed-first ordering. Furiten,
opponent Riichi, possible Kan, a beneficial call/draw, incomplete board or an
exhausted 120 ms check budget keeps options open. Cache results for bounded
repeated work; visibility, hand, melds, winds, Dora, rules and own scoring context
are part of the key. Fresh observations recompute preferences. These checks model
current value and one-draw development, not every future multi-draw plan or hidden
opponent danger. Unknown UI states still stop input. Any enable attempt freshly
verified OFF after timeout can use native policy actions without replaying that
switch in the same hand. Disable outcomes remain guarded.

All new enable clicks are prepared between turns. Needed disables still run
before native actions. Diagnostics remain in the journal, terminal action output
is unchanged. Regression examples enable C/D on an open flush Tenpai with no
modeled improvement, enable C without D on closed ready Seven Pairs, and keep
options open for threats, beneficial calls, future Kan and incomplete checks.

## Seven Pairs versus All Triplets

There were 27 Seven Pairs-target decisions. Measured alternative distances:
Six were Seven Pairs Tenpai versus All Triplets three-Shanten; fourteen were
one-Shanten versus three; seven were two-Shanten versus four. No Pon offer
occurred during those selected Seven Pairs decisions. Several had equal projected
Han, so there is no evidence that forcing All Triplets would improve them.
All Triplets distance is a draw-based shape estimate; future call opportunities
are uncertain and actual offers are evaluated separately. The agent did make
four Pon recommendations elsewhere in the run.

New pair_route_comparison diagnostics preserve both routes' Shanten, improving
copies and projected Han whenever generated. A synthetic three-triplet hand
verifies All Triplets is selected at Tenpai over three-Shanten Seven Pairs.
No blanket Seven Pairs or All Triplets preference was added.

Standard user-started validation batches are now three games using
`.\MahjongSoulAgent.bat 3`. No agent was launched, no native input was sent and
no new private session fixtures were added during this work. Next batch should
validate actual non-Riichi C/D reconciliation and measure their timing impact.
