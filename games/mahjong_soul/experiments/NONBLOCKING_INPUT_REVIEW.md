# Correct missed win Confirm and remove input-loop blocking

Session `20261023T053456-266792Z` reproduces the report. Frame 0000212 shows
a visible win-detail Confirm at timestamp 1792733868.883. The next result-button
attempt was 1792733875.823, on the score-transfer screen: about 6.94 seconds later.
The win-detail button was not handled promptly merely because later Confirm
clicks were logged. Thirteen delivered result clicks do not prove that every
result screen was clicked. The gameplay recommendation-to-submit median was
1.571 seconds, maximum 5.376, across 120 confirmed submissions. Successful
visual preflight alone had median 0.649 seconds.

## Fixes

The old win-detail context rectangle included a changing Dora indicator tile.
Its button-label patch actually matched exactly, but the context failed. Narrow
the reviewed context to the stable Dora heading only. The recorded missed win
screen now matches without OCR; the screenshot crop is a regression fixture.

Windows OCR now runs on a single background worker for production. Result polling
never waits on an unfinished OCR future. It keeps checking fast visual templates
while OCR is busy. The worker reads saved pixels and produces words only; it has
no controller or mouse reference. A result is usable only for the same board token
and geometry. Before any input, verify its label and heading against the current
frame; an uncacheable layout instead requires unchanged label and central panel.
The ordinary distinct second frame, source/window checks and stable-label test
remain. Old-board OCR results are discarded. Shutdown cancels queued OCR tasks;
a running read-only OCR subprocess retains its existing twelve-second timeout.
Unknown layouts can still need one OCR pass, but that work no longer blocks the
agent's main polling loop.

When all client-assist switches already match their desired state, retain that
captured frame for immediate action preflight. Reuse only within 250 milliseconds
of capture start, at identical geometry and board token, and consume it once.
The full hand recognition still runs, followed by a separately captured second
frame after the existing stability delay. Stale, moved or other-board frames are
not reused. This removes one duplicate capture/PNG operation where eligible;
it does not remove the second screenshot or guess tile positions from the reader.

## Why monitor output is earlier

The server event can arrive before the draw animation finishes. The read-only
monitor can immediately print a recommendation from that event. Native input
must wait for a usable visual tile/button mapping; failed animation checks can
still delay it. The fixes remove avoidable blocking and duplicate work, not this
necessary distinction. Mouse press/release timing and strategy remain unchanged.

913 tests passed, one skipped. New cases cover non-blocking pending OCR, stale
OCR discard, fresh-frame reuse, stale/wrong-token rejection, and the actual missed
win Confirm. This is offline verification, not a new measured live latency gain.
No game/agent process was launched and no gameplay input sent during development.
Next user-started AI match should expose `preflight_frame_reused`, Confirm stage
attempts and actual recommendation-to-submission timing in the journal.
