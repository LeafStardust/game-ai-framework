# Three-game North-handling review

Reviewed the completed October 25, 2026 three-game batch on revision `73f36bde` using the local journal. No new live input or agent launch was performed.

| Game | Placement | Agent final score | Hand wins | Deal-ins |
| --- | --- | --- | --- | --- |
| 1 | First | 42,500 | 3 | 1 |
| 2 | Third | 18,900 | 3 | 2 |
| 3 | Second | 30,800 | 3 | 2 |

The agent's seat differs between games; placements above use the captured own seat, not a fixed score-list index. All three completed, two custom-room restarts were delivered, and the configured game limit stopped the worker normally.

## Delivery and assists

All 279 submitted gameplay actions were server-confirmed. All 79 assist changes were confirmed. There were no recorded input failures or indefinite halts. One proposal was rejected after the client extracted North and changed the board during evaluation; a fresh decision followed on the replacement draw. Rejecting the obsolete proposal was correct.

Skip Calls enabled twice outside accepted Riichi; Auto Discard enabled once outside accepted Riichi. Both also enabled for all eleven accepted Riichi commitments. This establishes that the new open-ready path can reach the actual switches, although this small sample does not establish optimal toggle usage.

Auto Win enabled 27 times, with median first-enable delay 2.30 seconds after a new round. Auto Kita enabled 26 times, with median first-enable delay 4.19 seconds. These include round animation and setup time and are not pure click delivery timings. Kita setup is substantially earlier than the previous batch's 45.65-second median, but still not instantaneous.

Twenty-four post-result Confirm transitions and both custom-room Start transitions were confirmed. There were 56 result-button attempts: attempts alone are not distinct completed transitions.

## North and calls

Twelve policy decisions selected Kita. Twelve further decisions retained useful North because extraction increased Shanten by one; the comparison was recorded in the journal. Actual own North-extraction events totalled thirteen, including client-driven extractions. The policy selected nine Pon actions and no Kan actions in this run. No Kan decision was available here to validate the revised Kan acceptance behavior.

## Remaining latency issue

Median recorded decision-to-input latency was 1.425 seconds; 153 of 279 actions (54.8 percent) met 1.5 seconds. Maximum was 4.384 seconds. This is not the requested consistent one-to-one-and-a-half-second behavior.

Grouping actions by whether visual preflight failed since their decision: 76 without such retries had median 1.013 seconds and maximum 1.366 seconds; 203 with retries had median 1.660 seconds and maximum 4.384 seconds. This grouping is descriptive, not a causal benchmark. The journal recorded 363 failed visual preflights, including animation, ambiguous tile samples, and unavailable buttons. Most recovered before a submitted action; confirmed submissions alone do not prove that every transient offer was acted on before it disappeared.

Next development priority is offline replay of saved frames around repeated ambiguous drawn-tile checks and call-button availability. Preserve full-hand verification, fresh-board guards and exact switch-state checks; do not loosen recognition thresholds merely to improve timing. No additional game is needed before that investigation. This batch verifies execution and North diagnostics, not competitive strength or an optimal policy.
