# Keep optional assists off the decision turn

Latest batch recommendation-to-submit groups: 106 clean actions had median
1.319 s and maximum 1.497; 86 with rejected preflight but no assist attempt had
median 2.050 s and maximum 4.444; twelve with assist setup had median 4.043 s
and maximum 6.163. These are descriptive groups, not controlled comparisons.

Own-turn reconciliation now defers optional Auto Win/Kita enable clicks. They
are still prepared between turns. A pending enable request that is freshly
observed OFF does not block native gameplay; the controller and normal fresh
board/visual preflight validate the resulting action. Unknown switch states and
restrictive Skip Calls/Auto Discard reconciliation still block as before. No
uncertain toggle is replayed. Existing native win/Kita actions remain available.
This removes setup work from the decision path without promising animation or
capture acquisition will fit the one-second target.

## South value and completion

The recorded discard rankings did not establish a broad new value/speed error.
Only two chosen discards sacrificed at least five improving copies at equal
Shanten; both retained an extra projected Han rather than discarding 5 Sou.
Do not attribute the losing placements to those choices from outcome alone.

A narrower model restriction was found: value-preserving completion comparisons
required identical target Yaku/suit. The latest rankings contained one two-
Shanten decision with another equal-or-better-value, no-more-expensive route.
South now admits those alternatives to the existing bounded forecast. It still
preserves minimum projected Han, route-cost ceiling, Dora/pair losses, nearest
scoring distance and the useful-draw floor. Terminal forecast Tsumo values must
meet the original baseline Han floor. A qualified Yakuman baseline retains its
specialized model; the ten-slot qualification gate is unchanged.

The forecast remains limited to closed, unthreatened two-Shanten hands and
baseline plus two alternatives at 2,000 states each. An unavailable estimate
keeps the baseline. This is a bounded planning improvement, not measured win-rate
gain. Three-Player South Attack is v0.4; Four-Player South Attack is v0.15.

Tests verify own-turn deferral, nonblocking freshly OFF optional pending state,
equal-value alternative-route comparison and rejection of lower-value/damaged
alternatives. No agent was started, no game input was sent, and no private
recording fixtures were added. Next user-started batch must validate response
timing and native turn completion under the new scheduling.
