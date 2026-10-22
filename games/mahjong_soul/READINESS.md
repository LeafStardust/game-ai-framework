# Mahjong Soul validation status

As of October 22, 2026. Automatic input remains restricted to authenticated
rooms with only AI opponents. This document does not authorize ranked input.

| Check | Evidence | Remaining work |
| --- | --- | --- |
| Complete AI matches | Recorded completed three-player East/South games | Continue observing failures, not just placements |
| Legal action and Yaku scoring | Regression suite and recorded public decisions | Human-opponent playing strength is not measured |
| Focus/input recovery | Actual incident replay through real tile recognition | Verify an actual recoverable interruption in a running AI match |
| Same-step duplicate prevention | Controller attempt ledger and recovery tests | Keep checking runtime journal for duplicate or uncertain delivery |
| Settings overlay | Reviewed overlay now blocks hand verification and recovery | Other unreviewed overlays remain outside this recognition guarantee |
| AI-only, foreground and freshness gates | Actual replay matrix rejects missing verification, background and stale cases | These gates remain enabled |
| Auto Kita | Visually ON in recent live recordings | Exact client-versus-agent extraction attribution remains limited |
| Result controls | Confirm observed; reviewed fast paths replayed | Continue path and unknown layouts need live exposure |
| Input latency | Recent observed median 1.28 seconds after recommendation | Animation and OCR still add delay |

The recorded recovery matrix uses the actual failed attempt and later captured
boards from session `20261022T103714-684756Z`. Same original turn: stay blocked.
Later unobstructed ready turn: recover after real full-hand recognition, with no
click during recovery. Later Settings/quit overlay: remain paused even though
some hand pixels are visible. Each case is also tested with AI verification
removed, foreground missing and capture freshness rejected. No actual mouse
backend is invoked in these tests.

Next user action: restart `MahjongSoulAgent.bat`, start a three-player South AI
room, briefly switch away and return during ordinary play, then finish the match.
The journal will establish whether the interruption actually overlapped input
and exercised recovery; switching windows without an in-flight action does not
count as validation of uncertain-input recovery. Do not force repeated clicks or
start a ranked test to manufacture this condition. The developer did not launch
the game, run the live agent or send gameplay input for these checks.

## Historical foundation review (October 17, 2026)

The following is retained as historical evidence. Its implementation boundaries
were superseded by the current status above and subsequent linked reviews.


Reviewed 2026-10-17. Baseline and tile-efficiency policies are available in read-only shadow/evaluation mode. No policy is connected to native input and no autonomous playing loop is running.

| Area | Current evidence | Remaining boundary |
| --- | --- | --- |
| Steam reader | Own hand, public board, server operations, calls, wins, reconnect restoration and three/four-player state | Capture must be running before game entry; closed/incomplete state blocks execution |
| Consumer observation | Versioned independent snapshot, raw operations, absolute seats, connection, generation and exact board token | Normalized read-only intent interface is implemented; no policy or executor binding |
| Discard execution | Shared controller, native double-click, exact board/size/trigger guards, forbidden-discard checks and matching own server acknowledgement | Caller must visually bind the tile to its current screen slot |
| 1080p layouts | Common hand counts and action controls; two-tile drawn and post-call second-slot discards independently confirmed | First two-tile slot has visual evidence but no dedicated native run; exact offer guards still apply |
| Choice panels | Native two-choice Chi flow with explicitly observed choice ordering | Unseen combinations, multi-Pon and multi-kan choice panels remain blocked |
| 1200p layouts | Calibrated fourteen-tile layouts, post-call eleven-tile visual evidence and shared action-row mapping | Shorter hands and choice panels cannot inherit 1080p geometry; not every mapped control has a 1200p native run |
| Session control | One controller, attempted-step ledger, pending action, timeout/partial-delivery blocking | The eventual persistent runner must retain that controller and never restart it to retry uncertain input |

### Capture audit

The local 2026-10-17 capture review covered 3,127 frames and 952 distinct actions across eight rounds, with zero malformed rows, decode errors, schema warnings, step gaps, conflicting duplicates or historical game-state issues. Calls included 13 Pon, 19 Chi, one closed kan and one added kan across all players. The latest connection closed during the review: its final state is incomplete with `Game connection closed; awaiting restoration`. Therefore the audit's overall `coherent` flag is false despite the intact recorded action history. This is not a completed-match claim or evidence that live capture is currently ready.

### Next implementation boundary

The reader/input foundation is sufficient to begin the decision-interface stage. The read-only request/proposal interface is now implemented in [DECISIONS.md](DECISIONS.md), bound to connection, generation and board identity with current-offer validation. The policy-facing adapter and offline baseline replay evaluation are implemented. The persistent read-only shadow consumer is implemented with lifecycle and freshness tests. Its next live check is suggestions on newly arriving game state. Verified visual tile/action binding remains the execution boundary.

Automatic execution additionally requires a verified visual binding from each selected tile/action to the current screen. The reader hand array is not screen order. Neither sorting that array nor selecting a calibrated row alone establishes which tile occupies a slot. A future runtime must inspect that mapping, preserve red-five identity, use exact offer profiles, keep capture freshness checks and wait for server acknowledgement. Until those integrations exist, this is a functioning reader and guarded input toolkit rather than a complete playing agent.

Supporting evidence: [input](INPUT.md), [calibration review](CALIBRATION.md). Raw captures and screenshots remain local and ignored by Git.
