# v0.7 follow-up live audit

Session `20261021T113012-670595Z`, revision `8240a1cd`.
Three-Player East Speed v0.7, authenticated AI opponents.

| Match | Recorded completion | Rank | Score | Hand wins | Deal-ins |
| --- | --- | --- | --- | --- | --- |
| 1 | Complete | 1 | 41,900 | 2 / 4 | 0 |
| 2 | Complete | 3 | 28,400 | 1 / 3 | 1 |
| 3 | Incomplete | Unknown | Unknown | 3 / 3 ended hands | 0 |

The third recording stops progressing at East 1, Honba 3 after three dealer
wins. Its last completed hand left our seat at 67,200; that is not a final score.
The records contain two complete matches, not five complete additional games.
All 97 controller submissions were confirmed. Fourteen decisions used completion
forecasts; one changed the baseline discard (5 Pin to Green Dragon). These games
are observational, not evidence of a causal strength improvement.

## Stop and correction

An Auto Discard ON click following Riichi was delivered just before the hand's
winning event. Its confirmation remained pending through the result screen. At
the next round the desired state was OFF; the old request's expired deadline
halted play instead of accepting the currently observed OFF state. The saved
frame `0002674.png` decodes to Auto Discard OFF (all decision assists OFF).

The handler now clears an obsolete request only when a fresh, recognizable
sidebar proves the current desired state. It logs `assist_superseded`, then
reconciles other switches normally. Unknown sidebar states and failures to reach
a still-required target retain the existing stop behavior. No blind toggle retry.

## Timing and reduction

Across 105 decisions, median preceding-event-to-decision interval was 0.217 s,
maximum 1.486 s. Across 97 unique submitted actions, median decision-to-submission
was 1.986 s, maximum 5.858 s. Duplicate console journal submission rows were not
additional actions. These intervals include polling and UI work, not isolated
policy CPU measurements. There were 65 rejected visual preflights, including
animation, ambiguous tiles/buttons, and five stale-capture failures.

Action polls now omit the passive observation screenshot immediately before the
two mandatory preflight screenshots. Both visual checks and the before-input
recording remain. Regression coverage verifies two frames and one input rather
than a redundant third frame. This removes work but its real live latency gain
has not yet been measured; it does not eliminate animation or recognition delays.

Next validation: user-started agent with the fix, checking Riichi-to-next-round
transitions and live input timing. No agent process was started for this audit.
