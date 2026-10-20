# Automatic Result Buttons

`MahjongSoulAgent.bat` enables post-round Continue and Confirm handling alongside normal game input and automatic North extraction. The monitor remains read-only.

The handler is active only after a captured round or match ends and while the gameplay input controller is idle. It requires the foreground 1920x1080 game viewport, a verified AI room when that guard is enabled, visible result-screen context, and a unique lower-screen Continue or Confirm label. Windows English OCR reads the actual text bounds; there are no guessed result-button coordinates. Two screenshots must agree on label, position and stable button pixels. The board token and window geometry are rechecked before the native click.

Each result button is attempted once per round/label/position. Advancing game state confirms progression. It does not click Start, Play, Retry, room creation or queue buttons, and does not automatically enter another match. OCR absence, unknown text, animations, multiple matching labels or lost foreground focus produce no click. Delivery failures halt input rather than retry uncertain clicks.

The result recorder now continues capturing after network-state changes stop, so later Continue/Confirm screens are available for diagnosis. The initial implementation is covered by synthetic recognition/guard tests and a real Windows OCR smoke test. The round-score Confirm and final-results Confirm screens from session `20261020T104017-336368Z` now have actual OCR/pixel regression coverage. Live click validation remains pending after the fix.


Result reads preserve capture source identity and decode integrity but do not require gameplay freshness after an ended round. Gameplay decisions retain the original freshness guard. OCR transport uses UTF-8 and sanitizes control characters before JSON serialization. When stylized headings cannot be read, at least two displayed scores must match captured game scores to establish result context. Static label pixels are checked separately from the adjacent countdown.
