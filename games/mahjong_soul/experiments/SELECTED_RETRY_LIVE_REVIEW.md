# Selected-retry live validation ? October 27, 2026

Reviewed the three-game batch on b090cb6e. All three completed, both custom-room restarts worked and the game limit stopped the worker normally. No fatal stop, blocked state or policy rejection was recorded. All 220 submitted gameplay actions and all 54 assist changes were confirmed.

| Game | Placement | Own final score | Hand wins | Deal-in events |
| --- | --- | --- | --- | --- |
| 1 | First | 50,000 | 3 | 0 |
| 2 | Third | -400 | 1 | 2 |
| 3 | Third | 20,500 | 3 | 1 |

Own seat was resolved per connection. Seven hand wins and three deal-in events do not establish policy strength. The poor second/third placements remain decision-quality concerns despite improved mechanical reliability.

An opening dealer-hand discard left a tile selected and timed out. The existing eligible single retry was planned and delivered once, with the matching server discard confirmed 0.064 seconds after retry delivery. No retry_withheld entries were recorded, compared with 84 in the previous batch. This validates recovery for the observed selected-slot case, not every possible selected-tile layout.

Median decision-to-input latency was 1.271 seconds; 137 of 220 actions (62.3 percent) were within 1.5 seconds. Maximum was 3.278 seconds. Input-latency entries measure initial delivery, not timeout-plus-retry completion; the successful retry must therefore be assessed separately. Timing still does not consistently meet the one-to-one-and-a-half-second goal.

Two concealed Kan proposals were selected and confirmed at two Shanten and one Shanten. An open Kan was explicitly rejected for lacking secured Yaku. No Tenpai Kan opportunity occurred, so the committed-Tenpai Kan path remains unvalidated live. Do not represent these ordinary Kan actions as validation of that separate case.

One assist-preparation check reported capture temporarily stale/incomplete; it did not halt the run. No assist failure or recovery was needed. Future work should prioritize offline decision-quality review of the losing games while retaining the successful retry and restart behavior. No new game or agent was started during analysis, and no private session payload was published.
