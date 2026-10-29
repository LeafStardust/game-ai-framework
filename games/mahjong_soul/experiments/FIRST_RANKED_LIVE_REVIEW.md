# Ranked live validation ? October 29, 2026

Reviewed the one-match run on dd92fe51. Captured authentication verified a three-player South ranked game (category 2, mode ID 20), and all 146 policy decisions used Three-Player South Attack. The configured one-game limit stopped the worker normally when the match completed. No matchmaking, game, or agent was started during this review.

The agent finished first with 52,000 points, five hand wins and one deal-in event. This single ranked result does not establish long-run ranked strength. All 136 submitted gameplay actions and all 36 assist changes were confirmed. No policy rejection, gameplay input failure, blocked state, unconfirmed assist or retry was recorded. Eleven intermediate result transitions were confirmed. The final result navigation was intentionally not continued after the one-match budget finished.

## Kan after Riichi

The own Riichi state was accepted when a concealed-Kan-only offer for Green Dragon arrived. The policy selected the exact server combination in sole_server_closed_kan mode. Native visual preflight waited for the label, then delivered the action. A matching own ActionAnGangAddGang confirmed it, followed by the replacement draw. This validates live recognition, execution and confirmation of the Riichi Kan-only path that previously raised a policy exception.

This is not validation of every open-ready added-Kan or multiple-choice Kan path. The separate observed open Kan was explicitly rejected because it did not secure a legal Yaku. Do not present that rejection as a read failure.

## Timing and remaining work

Median initial decision-to-input latency was 1.234 seconds; 100 of 136 actions (73.5 percent) were within 1.5 seconds. Maximum was 3.931 seconds, with two actions exceeding three seconds. There were 159 failed preflights, mostly temporary button absence, tile/animation checks and moving UI. These are retries of checks, not distinct failed deliveries. The one-to-one-and-a-half-second target remains inconsistent.

Ranked authentication, automatic format selection, ordinary action delivery, assist/result handling and normal game-budget shutdown now have live evidence for three-player South. Four-player ranked and East ranked have synthetic coverage but were not exercised in this match. Ranked queueing remains manual; custom-room Start remains restricted to AI rooms. The agent continues using own-hand/public information only.

No implementation change was warranted by this run. Next work is decision-quality and latency review across additional ordinary ranked records, without claiming the first-place result proves strength. Only aggregate observations are committed; private session records stay local.
