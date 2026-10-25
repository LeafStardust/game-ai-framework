# Restart and recovery batch review

Reviewed the October 25 three-game batch on revision 7f832cb3. All three completed, both custom-room restarts were delivered, and the game limit stopped the worker normally. No fatal halt, input failure or rejected policy proposal was recorded.

| Game | Placement | Own final score | Hand wins | Deal-in events |
| --- | --- | --- | --- | --- |
| 1 | Third | 22,900 | 2 | 2 |
| 2 | Third | 12,000 | 4 | 4 |
| 3 | Second | 37,700 | 3 | 0 |

Actual own seats were read per connection. Nine hand wins and six deal-in events do not establish competitive strength. South's aggressive risk preference remains unchanged.

All 315 submitted gameplay actions were server-confirmed. There were 95 assist changes: 94 confirmed and one Skip Calls enable explicitly observed still OFF after timeout. That attempt used native fallback and did not stop gameplay. This validates the verified-OFF fallback in this run; the two-frame recovery from unknown switch states was not exercised here. Both custom-room restarts worked after the room-number OCR correction.

Skip Calls and Auto Discard each enabled twice outside accepted Riichi. There were fourteen accepted-Riichi C enables and thirteen accepted-Riichi D enables. No late-small-gain Dama rejection was logged, so the new heuristic was not exercised by this batch.

Median decision-to-input latency was 1.377 seconds; 184 of 315 actions (58.4 percent) were within 1.5 seconds. Maximum was 6.764 seconds. Eleven submitted actions had assist attempts between their recorded decision and delivery, with median 3.282 seconds. The other 304 had median 1.370 seconds and maximum 3.507 seconds. The maximum-delay action included both Auto Win and Auto Kita setup. These groups describe journal ordering, not a randomized performance comparison.

First Auto Win enable after round start had median 2.34 seconds (31 hands); Auto Kita had median 4.40 seconds (30 hands). Kita setup was earlier than the previous batch's 6.04-second median, but overlap with pending gameplay still produced excessive outliers. There were 290 failed visual preflights, including 113 drawn-slot checks, 43 unavailable Skip checks, 29 unavailable Kita checks, and sixteen unavailable foreground-client checks.

Next development priority is to prevent optional R/K preparation from consuming a pending native action's latency budget. Retain switch-state verification, correct required disables and the fresh-board guards. No new game is needed before reviewing that scheduling path. No live input or agent launch was performed during this review, and no private session payload was published.
