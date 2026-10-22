# Result-heading recognition follow-up

The first optimized-input session still needed OCR for six delivered result
clicks. Replaying those images showed that some Confirm label patches matched
exactly, but the separate result-heading patch changed with the board background
or shifted when East/South and repeat text changed. One screen was an Exhaustive
Draw banner, absent from the original fast templates. The final Match End heading
missed the original color threshold narrowly due to background pixels.

## Changes

Keep the existing strict Confirm-label distance. For the separate reviewed
heading, accept either the original color match or a matching letter-ink mask:
white/gold result text, at least sixteen reference text samples, at least 90%
intersection-over-union. This ignores changing background pixels while still
requiring the heading's spatial letter shape. New reviewed samples cover the
Exhaustive Draw banner and shifted East/South Repeat Counter headings, plus a
translucent Confirm variant over different tiles. Each includes source/hash.

OCR-derived centers can differ from reviewed centers by one pixel. Multiple
matching references to the same label/stage within four pixels now count as
agreement, rather than forcing OCR because their coordinates were not identical.
Different stages or clearly separated buttons still reject as ambiguous.

Exhaustive Draw has its own result stage. OCR stage classification now matches
actual Han/Fu tokens instead of treating the word Hand as Han. The fresh-frame
label and heading checks, state/foreground checks and two-click retry limit remain.
Unknown result layouts retain OCR. No blind coordinate clicks are introduced.

## Evidence and limitations

All six previously OCR-dependent delivered-button screenshots now pass fast
recognition without OCR, using actual screenshot-crop regressions. These are
reviewed development examples, not held-out recognition accuracy.

Full offline replay checked all 557 saved frames in session
`20261022T064356-902665Z`: zero result matches on 442 tracking frames, two
waiting-for-round frames and one frame without a state. Seventeen result frames
matched; other result-state frames include animations and non-button screens.
See [the replay artifact](RESULT_CONTEXT_REPLAY.json). Median static-frame
recognition including decode/read was about 57 ms; maximum about 103 ms on this
run. These are offline recognition times, not live click timings.

The reviewed repeated Pon-failure images 0000685 and 0003396 showed gameplay or
animation with no visible Pon label. Those guards correctly refused input;
no tile/call confidence threshold was relaxed to force a click. This review does
not claim every recognition retry in the session was unnecessary or fixed.

886 tests passed, one skipped. Continue remains OCR-backed until its own verified
layout is cached; this session did not contain a recorded Continue click. Next:
user-started South AI validation of result-stage advancement and remaining OCR
frequency. No game/agent process was started or gameplay input sent during this
work. User YAKU.md edits remain untouched.
