# Reader and input readiness

Reviewed 2026-10-17. No decision policy is connected and no autonomous play loop is running.

| Area | Current evidence | Remaining boundary |
| --- | --- | --- |
| Steam reader | Own hand, public board, server operations, calls, wins, reconnect restoration and three/four-player state | Capture must be running before game entry; closed/incomplete state blocks execution |
| Consumer observation | Versioned independent snapshot, raw operations, absolute seats, connection, generation and exact board token | Operations are not yet a normalized decision/action interface |
| Discard execution | Shared controller, native double-click, exact board/size/trigger guards, forbidden-discard checks and matching own server acknowledgement | Caller must visually bind the tile to its current screen slot |
| 1080p layouts | Common hand counts and action controls; two-tile drawn and post-call second-slot discards independently confirmed | First two-tile slot has visual evidence but no dedicated native run; exact offer guards still apply |
| Choice panels | Native two-choice Chi flow with explicitly observed choice ordering | Unseen combinations, multi-Pon and multi-kan choice panels remain blocked |
| 1200p layouts | Calibrated fourteen-tile layouts, post-call eleven-tile visual evidence and shared action-row mapping | Shorter hands and choice panels cannot inherit 1080p geometry; not every mapped control has a 1200p native run |
| Session control | One controller, attempted-step ledger, pending action, timeout/partial-delivery blocking | The eventual persistent runner must retain that controller and never restart it to retry uncertain input |

## Capture audit

The local 2026-10-17 capture review covered 3,127 frames and 952 distinct actions across eight rounds, with zero malformed rows, decode errors, schema warnings, step gaps, conflicting duplicates or historical game-state issues. Calls included 13 Pon, 19 Chi, one closed kan and one added kan across all players. The latest connection closed during the review: its final state is incomplete with `Game connection closed; awaiting restoration`. Therefore the audit's overall `coherent` flag is false despite the intact recorded action history. This is not a completed-match claim or evidence that live capture is currently ready.

## Next implementation boundary

The reader/input foundation is sufficient to begin the decision-interface stage. The first work there should be a read-only, versioned decision request bound to the observation's connection, generation and board token, followed by strict validation of proposed actions against current operations. No mouse input is needed for that work.

Automatic execution additionally requires a verified visual binding from each selected tile/action to the current screen. The reader hand array is not screen order. Neither sorting that array nor selecting a calibrated row alone establishes which tile occupies a slot. A future runtime must inspect that mapping, preserve red-five identity, use exact offer profiles, keep capture freshness checks and wait for server acknowledgement. Until those integrations exist, this is a functioning reader and guarded input toolkit rather than a complete playing agent.

Supporting evidence: [input](INPUT.md), [calibration review](CALIBRATION.md). Raw captures and screenshots remain local and ignored by Git.
