# Automatic Result Buttons

`MahjongSoulAgent.bat` enables post-round Continue and Confirm handling alongside normal game input and automatic North extraction. The monitor remains read-only.

The handler is active only after a captured round or match ends and while the gameplay input controller is idle. It requires the foreground 1920x1080 game viewport, an authenticated AI room or ranked match when the lobby guard is enabled, visible result-screen context, and a unique lower-screen Continue or Confirm label. Windows English OCR reads the actual text bounds; there are no guessed result-button coordinates. OCR identifies the label and position once; a fresh second screenshot must preserve the same static label pixels. This avoids a second OCR subprocess delaying the click. The board token and window geometry are rechecked before the native click.

Each result button is attempted once per round/label/position. Advancing game state confirms progression. After a completed match, it can click Start in the same custom AI room, as described below. It does not create rooms or select ranked queues. OCR absence, unknown text, animations, multiple matching labels or lost foreground focus produce no click. Delivery failures halt input rather than retry uncertain clicks.

The result recorder now continues capturing after network-state changes stop, so later Continue/Confirm screens are available for diagnosis. The initial implementation is covered by synthetic recognition/guard tests and a real Windows OCR smoke test. The round-score Confirm and final-results Confirm screens from session `20261020T104017-336368Z` now have actual OCR/pixel regression coverage. Live click validation remains pending after the fix. Result scans run at most every half second, and detected buttons withheld by later frame, state or window checks are recorded as `result_button_withheld` with the reason. These diagnostics do not appear in the recommendation terminal.


Result reads preserve capture source identity and decode integrity but do not require gameplay freshness after an ended round. Gameplay decisions retain the original freshness guard. OCR transport uses UTF-8 and sanitizes control characters before JSON serialization. When stylized headings cannot be read, at least two displayed scores must match captured game scores to establish result context. Static label pixels are checked separately from the adjacent countdown.

## Restart a custom AI room

The normal agent launcher also restarts a completed custom room when its Start
screen is visible. The monitor remains read-only. No additional launcher is needed.

Room restart requires the preceding authenticated AI match to be ended, the
controller idle, and the same room number and three/four-player East/South format
visible in fresh English OCR. The visible roster must contain exactly the expected
number of AI opponents, and Start must be unique and gold/enabled. Room text,
format, each roster text crop and the button are checked again in a distinct
screenshot; geometry and board identity are rechecked before delivery.

Only one Start click is delivered per completed game connection/generation/room.
There is no blind retry if loading takes time. A new authenticated game permits
the next restart after that game ends. A delivery failure halts input. Restart
attempts, deliveries and the preceding screenshot are recorded. A changed room,
human opponent, missing OCR, inactive button, stale screen or background window
prevents a click. The three-player South screen is covered by a real recording;
four-player and East recognition use the same strict text checks but still need
live coverage. No game was started by the coding assistant during implementation.

## Limit the run to X games

Run `.\MahjongSoulAgent.bat 5` to play five completed matches, restarting the
verified custom AI room between them. Replace `5` with any positive integer.
With no number, automatic play remains unlimited until stopped manually.

Each match counts once, including a match already in progress when the agent
attaches. Individual rounds, reconnects, repeated final-state messages and a
previously finished match found in capture history do not count. When X is
reached, the automatic worker exits immediately at the match-end event; it does
not click final result controls or start game X+1. The existing package supervisor
then performs its normal capture cleanup. There is no extra BAT file.
The agent still needs the game open in the supported foreground viewport, with
an active AI match or the same previously verified custom room available.
