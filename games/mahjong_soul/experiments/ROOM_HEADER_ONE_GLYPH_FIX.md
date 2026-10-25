# Room-header 1/J OCR correction

The October 25 batch completed its first game of three but did not return to gameplay. All 92 submitted gameplay actions and 24 assist changes were confirmed. The worker was still running, with an idle controller and no halt, repeatedly withholding room Start because the room heading could not be verified.

The full-screen and enlarged OCR reads rendered different occurrences of the stylized digit 1 as J. Start, the same three-player South format and the two AI opponents were otherwise recognized. A digits-only crop experiment failed to produce reliable text and was not implemented.

Add a narrow fallback for complete Room# headings containing only four-to-six digits and J. Normalize J to 1 only when independent full-screen and enlarged heading reads agree on the complete normalized numeric identifier. Neither read receives the authenticated expected room ID. The existing room_start check then requires exact equality with that ID, verified AI roster, format, enabled gold Start button, stable header/roster/button pixels across fresh frames, unchanged board and geometry, and remaining game budget.

Other letters are rejected. Disagreeing OCR views are rejected. Normal numeric OCR behavior is unchanged. The correction does not blindly click Start, relax AI-room requirements or replay an already attempted uncertain Start.

Offline validation of the actual saved failed screen now verifies Start. Two separate saved room frames passed the restart delivery path with exactly one fake-backend click and zero real input. Synthetic regressions cover view agreement, disagreement, unknown letters and changed room identity. No private session fixture or screenshot was committed. No agent or game was launched.

Next: restart the worker to load the change and run the normal three-game batch. The code-level replay validates this observed failure; live restart delivery still needs confirmation.
