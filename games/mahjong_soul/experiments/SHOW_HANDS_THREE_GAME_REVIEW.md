# Show Hands three-game review

Reviewed the October 25 batch launched on revision c2c56456, with Show Hands enabled. The captured open_hand flag was enabled. All three games completed, both custom-room restarts worked, and the configured limit stopped the worker normally. No new game or agent was started during review.

| Game | Placement | Own final score | Hand wins | Deal-in events |
| --- | --- | --- | --- | --- |
| 1 | First | 59,500 | 3 | 0 |
| 2 | First | 56,500 | 3 | 1 |
| 3 | Third | -7,900 | 0 | 1 |

Placements use the actual own seat for each game. The last deal-in event paid two winners, so two events across the batch represent three individual Ron payments. Six total hand wins in this batch do not establish long-run strength.

## Execution

All 274 submitted gameplay actions and all 61 assist changes were confirmed. There were no recorded input failures, blocked states or rejected policy proposals. Show Hands compatibility is now validated in this live AI batch.

Skip Calls enabled twice outside accepted Riichi; Auto Discard enabled twice outside accepted Riichi and was disabled once outside Riichi. First Auto Win enable after round start had median 2.38 seconds; Auto Kita had median 6.04 seconds. Kita setup therefore remains slower than desirable and was slower than the previous batch's 4.19-second median.

The policy selected five Pon, sixteen Kita actions, nine Riichi declarations, six offered wins and no Kan. Twenty-one result transitions were confirmed, including both restarts. Counts of attempted result clicks are not counts of distinct completed transitions.

## Latency

Median decision-to-input latency was 1.291 seconds, compared with 1.425 in the previous batch. 161 of 274 actions (58.8 percent) were within 1.5 seconds, versus 54.8 percent previously. Maximum was 4.125 seconds. Different hands, animation timing and foreground state prevent attributing the entire improvement to the optimization.

There were 354 failed visual preflights. Forty-four explicitly reported that the foreground Mahjong client was unavailable at 1920x1080. Other frequent failures involved the drawn slot (114), Skip button visibility (75), and Kita button visibility (31). Guards recovered sufficiently to confirm every submitted action, but that does not prove every transient offer was handled before expiry. Do not remove foreground or visual verification requirements to reduce these counts.

## Last-hand loss

The third game had no wins and ended with a 24,000-point double Ron against the agent. The preceding policy decision declared Riichi discarding 9 Sou, in Seven Pairs Tenpai with three publicly unseen 6 Sou waits, while both opponents were already in accepted Riichi and thirteen tiles remained. The journal's score model estimated a five-Han Riichi hand. This was an aggressive push under the current South always-push preference, not a missing legal Yaku or execution failure. The observation setting does not authorize using revealed opponent hands to choose safe tiles.

Next strategic review should examine the late two-threat Riichi choice and its alternatives using normal policy information. Continue investigating Kita setup and drawn-slot/button animation delays offline before requesting another batch. No strategic behavior was changed in this review.
