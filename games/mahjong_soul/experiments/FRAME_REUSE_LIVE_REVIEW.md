# Frame-reuse live batch review ? October 26, 2026

Reviewed the three-game batch on aa0891f4. All three completed, both custom-room restarts worked, and the configured limit stopped the worker normally. No fatal block or gameplay input failure was recorded. All 312 submitted gameplay actions were server-confirmed.

| Game | Placement | Own final score | Hand wins | Deal-in events |
| --- | --- | --- | --- | --- |
| 1 | First | 69,500 | 6 | 2 |
| 2 | Third | 14,600 | 0 | 3 |
| 3 | First | 77,900 | 4 | 2 |

Own seat was resolved per connection. Ten hand wins and seven deal-in events show continued aggressive risk, not proven long-run strength. Do not infer competitive readiness from two first places in this small AI batch.

One Skip Calls enable became unconfirmed. Two matching fresh frames recovered all-OFF switch states after 1.140 seconds; the follower resumed without user intervention. Eighty-three of 84 assist attempts were confirmed, and the remaining uncertain attempt was resolved through recovery rather than counted as a successful toggle.

Median decision-to-input latency was 1.326 seconds, versus 1.457 seconds previously. 179 of 312 actions (57.4 percent) were within 1.5 seconds, versus 50.6 percent previously. Maximum was 3.363 seconds versus 3.775 previously. Different hands and rendering conditions mean this is observational evidence, not a controlled speed benchmark.

There were 476 first-frame reuses, of which 54 were older than the former 250 ms limit. Those 54 checks exercised the expanded window and avoided a redundant first capture; the required separate fresh second observation remained active. Reuse age median was 0.219 seconds.

There were 525 failed preflights. New diagnostics distinguish client switch state: twenty of 36 unavailable Kita checks occurred with Auto Kita last observed ON; sixteen occurred with it OFF. Eighty-five of 86 unavailable Skip checks occurred with Skip Calls OFF. Therefore client automation explains some Kita waits but does not explain most Skip visibility failures. Remaining frequent checks involved the drawn slot (171), moving UI (41), and post-call animation guard (27). These counts are retries, not distinct missed turns.

Skip Calls and Auto Discard each enabled five times outside accepted Riichi. Auto Discard disabled twice outside Riichi. The late-small-gain Riichi heuristic was not exercised. The policy selected eleven Pon and three added Kan proposals in addition to discards, wins, skips, Kita and Riichi.

Next priority is focused offline review of Skip visibility timing and the remaining drawn/post-call animations. Keep the current reuse change, automatic recovery and restart behavior. No new game is needed before that review. No agent or game was started during analysis, and no private session data was published.
