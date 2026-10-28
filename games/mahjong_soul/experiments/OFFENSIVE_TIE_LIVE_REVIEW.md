# Offensive-tie live batch review ? October 28, 2026

Reviewed the three-game batch on e541135e. All three completed, both custom-room restarts worked and the configured limit stopped the worker normally. No fatal block, gameplay input failure, policy rejection or withheld retry was recorded. All 309 submitted gameplay actions were confirmed.

| Game | Placement | Own final score | Hand wins | Deal-in events |
| --- | --- | --- | --- | --- |
| 1 | Second | 32,100 | 2 | 2 |
| 2 | Second | 27,900 | 4 | 3 |
| 3 | Third | -12,400 | 2 | 4 |

Own seats were resolved per connection. Eight hand wins and nine deal-in events highlight that decision quality remains unresolved. Mechanical reliability and an exact-tie improvement do not establish competitive strength or acceptable long-run win rate.

Seventy-six of 77 assist changes confirmed. An Auto Discard enable became unconfirmed, then complete switch-state recovery occurred 1.160 seconds later and gameplay resumed. The uncertain toggle is not counted as a confirmed enable. No manual restart was required by the recorded failure.

Median initial decision-to-input latency was 1.287 seconds. 193 of 309 actions (62.5 percent) were within 1.5 seconds. Maximum was 3.245 seconds. These are not end-to-end completion latencies and still fail the target of consistently finishing input within one-to-one-and-a-half seconds.

## Decision-change validation

Fifteen decisions recorded a discard already in every current Riichi declarer's river. Replay with the original previous route and round memory, once with the new tie-break disabled and once enabled, found five changed actions. Each retained identical Shanten, projected Han, ukeire and route cost. This validates the intended limited selection behavior; it does not demonstrate that any game result improved.

Only two open-Kan offers were observed. One was rejected because it did not secure Yaku; the other was two Shanten and rejected as too far from winning. There was no own-draw Tenpai Kan offer, so that separate path remains unvalidated live. Do not conflate these recorded rejections with failure to read the offer.

Next strategic priority is detailed review of the nine deal-in events and their preceding hand/value/wait choices, while preserving South's explicit attack-first and always-push preference. Do not quietly introduce a defensive policy or tune against revealed opponent concealed hands. No special live hand is needed before the offline review. No agent was launched and no private session payload was published.
