# Gameplay-priority live review

Reviewed the October 25 three-game batch on 19eaac99. Three completed, two custom-room restarts worked, and the game-limit shutdown was normal. All 316 submitted gameplay actions were confirmed. There were no recorded fatal blocks or input failures. No agent or game was started during review.

| Game | Placement | Own final score | Hand wins | Deal-in events |
| --- | --- | --- | --- | --- |
| 1 | Third | 27,300 | 4 | 2 |
| 2 | Third | 11,100 | 1 | 2 |
| 3 | First | 64,000 | 4 | 0 |

Own seat was resolved per connection. The batch produced nine hand wins and four deal-in events. These three placements do not establish long-run policy strength.

The unknown-assist recovery path was exercised live: a Skip Calls enable became unconfirmed, then two fresh matching frames established all switches OFF. Assist recovery was logged 1.363 seconds after the unconfirmed event, and follower resumption followed immediately. This time the agent did not remain halted. Eighty-one of 82 assist changes were confirmed; the remaining uncertain attempt was resolved by this recovery rather than represented as a successful toggle.

Median decision-to-input latency was 1.457 seconds; 160 of 316 actions (50.6 percent) were within 1.5 seconds. Maximum was 3.775 seconds, down from the previous 6.764-second outlier. The scheduling change removed optional preparation from visual retries, but the median worsened versus 1.377 seconds previously. Different hands and visual timing prevent a clean causal comparison.

Visual preflight failures increased from 290 to 474. Frequent reasons were drawn-slot checks (167), unavailable Skip (61), unavailable Kita (50), and unavailable Pon (26). Twenty-four checks reported an unavailable foreground 1920x1080 client. First Auto Win enable after round start had median 2.42 seconds; Auto Kita had median 5.07 seconds. Optional setup remains deferred to avoid delaying pending gameplay, so Kita setup itself is not consistently faster.

Next priority is offline analysis of the repeated drawn-slot and call-button failures, separating expected animation waits from persistent calibration or recognition errors. Preserve full-hand, foreground and board checks. No additional game is required before that analysis. No raw private session data was published.
