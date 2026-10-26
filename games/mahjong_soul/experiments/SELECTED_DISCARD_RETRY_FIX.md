# Selected discard retry fix ? October 26, 2026

The three-game batch on 6a7337df finished first at 44,800, third at 8,100 and second at 30,100. Four hand wins and two deal-in events were recorded. Both custom-room restarts worked; all 240 submitted gameplay actions eventually matched server confirmations. One Skip Calls disable became unconfirmed and recovered after approximately 1.07 seconds. Median decision-to-input latency was 1.302 seconds; maximum 7.069 seconds. These submission-to-event confirmations do not prove each original click immediately succeeded.

The available Kan cases did not exercise the committed-Tenpai fix: the accepted added Kan was one Shanten, and the concealed-Kan offers were three Shanten. Do not claim Tenpai Kan is live-validated from this run.

## Actual retry stall

An opening dealer-hand discard selected South but did not produce an immediate discard event. The server hand still contained all fourteen tiles, and the client showed South lifted at the original last-slot position. The timeout retry verifier kept sampling the unselected baseline, causing 84 withheld retries. A matching server discard arrived roughly 28 seconds after original delivery; the log alone cannot establish whether that eventual action came from the original input, user action or client behavior.

The original pending tile was South; the initial reader drawn_tile field referred to another tile. Therefore recovery is bound to the original pending plan's coordinates, not an assumption that the last slot always equals drawn_tile.

For an eligible same-board, same-tile ordinary discard retry only, locate the exact original plan point in the current calibrated slot list. At that slot, recognition may additionally inspect the reviewed 48-pixel selected lift. Exact tile confidence and margin remain unchanged; disagreement with other successful alignment samples is rejected. The complete recognized hand must still match the reader. Both independent frames must pass normal stability checks, followed by foreground, geometry and board-token checks. Native click coordinates and the controller's existing one-retry limit are unchanged.

Normal initial decisions cannot use the selected-lift exception. Different pending tiles, boards and slot coordinates do not authorize it. The change neither increases the retry count nor blindly repeats a click when the visible hand disagrees.

Validation: the actual saved selected-hand frame recognizes South with the unchanged confidence thresholds. Two separate saved frames pass the complete retry-plan path with a fake mouse, exactly one initial fake delivery and one permitted retry, then matching server confirmation. Synthetic regressions cover scoped eligibility, disagreement rejection and original-slot binding. No real input, game or agent launch was performed. No private image or hand snapshot was published.

Next: restart the worker to load the fix and use the normal user-started three-game run. Selected tiles outside this reviewed lift and unverified game layouts remain withheld rather than guessed.
