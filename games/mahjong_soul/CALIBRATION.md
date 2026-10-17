# Passive calibration recording

Start the existing network capture first, open Steam Mahjong Soul, then run from this worktree:

```powershell
.\.venv\Scripts\python.exe -m games.mahjong_soul.live.runtime.calibration
```

Play normally. You do not need to announce each prompt. The recorder saves changing client screenshots, client size/origin, reader hand and available operations, left-click positions, and nearby own action confirmations. It follows the newest capture file automatically. Historical frames bootstrap the reader but are not emitted as new actions.

Recordings stay in ignored `logs/mahjong_soul/calibration/<session>/`. `events.jsonl` references PNG screenshots and candidate click IDs. Raw network frames, account identifiers and authentication payloads are not copied. Nothing is uploaded or added to Git. Screenshots are client-area screen captures: overlays within the game rectangle may appear.

The recorder sends no clicks, never changes the foreground window and never installs a hook. It pauses screenshots when the game is not foreground, is minimized, is partly off screen, or the reader is not ready. Click sampling runs in a separate thread every 5 ms while screenshots are sampled every 250 ms when an action is available. The latest full-resolution PNG stays in memory; the recorder saves a frame on a new board/geometry, at five-second animation checkpoints, and when a fresh pre-click image is needed. Intermediate animations are not all retained. Very brief clicks, UI transitions or scheduler stalls can still be missed. Missing, stale or moved-window pre-click images are explicitly marked unavailable. Server-event correlation is a review aid, not proof that a particular button was clicked. Menu opening, tile selection and Skip may have no corresponding game action; their screenshots/clicks are retained without inventing confirmation.

The default run ends after one hour or at a 1 GiB session limit. Stop with Ctrl+C. Options: `--duration 600`, `--max-mb 512`, `--file <capture.jsonl>`, `--output <directory>`. Each run creates a new session and does not overwrite previous recordings. A full or exhausted output limit stops the recorder rather than deleting evidence.

Recorded examples must be inspected before a layout is marked verified. The recorder does not automatically choose tiles, certify coordinates or enable profiles. Multi-choice panels can be collected while you interact normally; slower visible panels give more complete evidence.

Live smoke validation confirmed readable 1920x1080 game PNGs, player click records and own-action candidate correlations while playing normally. Identical recaptured screens refresh evidence timestamps without writing duplicate images. Missing correlations remain explicitly unconfirmed.

## Recording review: 2026-10-16

Reviewed local session `20261016-181251-573310`: 357 frame records, 33 clicks and 26 own-action records. Every recorded client geometry is 1920x1080. The replacement session `20261016-182056-719819` currently contains no events; starting a recorder alone does not establish additional coverage.

- Riichi: two declared discards are present. `frame-000044.png` visibly shows Riichi tile selection; the associated click has a fresh preceding image and the subsequent server action declares Riichi. The second declaration has candidate clicks but lacks fresh preceding images.
- Chi: three single-combination offers are recorded. `frame-000198.png` visibly shows Chi and Skip. No own Chi action follows in this recording, so this is visual offer evidence, not a newly verified execution.
- Wins: one own Tsumo and one own Ron are confirmed by server events, but neither has correlated click evidence. Examined win-context frames show transitions rather than stable actionable buttons. Do not promote button layouts from those confirmations alone.
- No Pon, kan or multiple-combination Chi offers are present. This session adds no evidence for their layouts or shorter post-call hands, and no evidence for 1920x1200.

No layout profile was changed by this review. Existing previously verified profiles remain the execution baseline. Raw screenshots and event logs remain local and ignored by Git.

The first session exhausted its 1 GiB cap after only a few minutes: animated full-client PNGs dominate storage. Longer unattended collection needs improved storage efficiency; the current recorder must not be described as guaranteeing a full hour of evidence. Missing evidence is not a reason to request another match until that limitation is addressed.


## Storage improvement validation

Replaying the recorded 1920x1080 session with sparse persistence reduced saved PNGs from 357 to 42 and PNG bytes from 1,072,733,372 to 125,286,123 (88.3%). This is a replay measurement, not a promise about every match or a new live input test. Full resolution and PNG encoding are unchanged. Fresh click evidence is saved from the sampled buffer before writing its click record; stale or geometrically mismatched images remain unavailable. The 1 GiB cap still applies, and reaching it now stops cleanly with the evidence directory printed.


## Improved recorder live validation: 2026-10-16

Reviewed session `20261016-183751-482320`, covering 10:42:24 through 10:51:12 UTC. It contains 138 full-resolution 1920x1080 frame records (415,079,742 PNG bytes, about 396 MiB), 265 click records and 83 own-action records. The session remained below its 1 GiB cap. These are live totals; the 88.3% reduction above is a separate replay comparison.

The own actions comprise 72 ordinary discards, three Riichi discards, four Pon calls and four wins (two Tsumo, two Ron). Of all clicks, 49 have fresh preceding images; 71 actions have candidate click IDs. Multiple clicks may correspond to a single action, and candidates remain review evidence rather than execution certification.

Visually reviewed examples:

| Local frame | Observation | Supported conclusion |
| --- | --- | --- |
| `frame-000011.png` | Pon and Skip visible; click 10 at (1020, 815), followed by own 8m Pon | Readable offer, fresh click evidence and matching server call |
| `frame-000182.png` | Riichi selection with the selected 3p and other tiles greyed; click 181 and subsequent Riichi discard | Selection-stage evidence; the menu-opening click has no fresh image |
| `frame-000354.png` | Single-combination Chi and Skip visible | Visual offer evidence; no own Chi call in this session |
| `frame-000117.png` | Four exposed melds and one visible concealed tile during a self-draw transition | Short-hand state captured, but not a stable two-slot discard layout |
| `frame-000190.png` | Ron-context transition with a wait preview | Does not establish stable Ron button coordinates |
| `frame-000402.png` | Tsumo-context transition before a stable prompt | Does not establish stable Tsumo button coordinates |

The reader also recorded two-tile hands after the fourth Pon and on subsequent draws. Those contexts are useful evidence for the remaining two-tile discard layouts, but no new profile is enabled from transitional frames. There are no kan or multiple-combination Chi offers in this session, and no 1920x1200 frames.

This completes live validation of sparse screenshot persistence and fresh click-image saving. It does not establish complete click coverage: rapid transitions and clicks without fresh images are still explicitly unavailable. No further special play session is required for this recorder milestone. Next development work is reviewing stable short-hand evidence and preserving exact-context guards for any additional layout profiles; the decision pipeline remains unconnected.


## Two-tile discard layout review

Added separate 1920x1080 two-tile profiles for `ActionChiPengGang` and `ActionDealTile`. In session `20261016-183751-482320`, frames 108/110 show the post-call 3p and 4p slots; candidate clicks 107/109 have fresh image evidence and are followed by the own 4p discard at step 110. Frames 111/113 show the draw-separated 3p and 9s slots; click 112 has fresh image evidence and is followed by the own 9s discard at step 118.

Safe interior points are (269, 1000) for the first slot, (365, 1000) for the post-call second slot, and (394, 1000) for the drawn second slot. Both ordinary and raised/selected tile bounds contain those points. Profile verification is based on inspected images and manual click/server evidence, not a new native executor run. Slot indices still require visual tile identity; reader hand order must not be treated as screen order. Exact size/trigger guards and discard restrictions continue to apply. No 1920x1200 variant was inferred.


## Native two-tile selection test: 2026-10-17

Capture from the previous day was closed when the test began. Restarting process-scoped capture restored the current four-player AI room, own seat 1, including its two-tile hand. No game restart was needed. A first attempt against the expired 2m turn was rejected before input; another attempt was rejected by the capture freshness guard. With fresh capture and a current 8m/7p hand at step 136, the shared native controller clicked the second draw slot at (394, 1000). A fresh screenshot showed the 7p raised and selected.

The turn then expired before the explicit confirmation stage; rebuilding the confirmation plan rejected the missing own discard operation and sent no confirmation click. This verifies native selection of the second drawn slot only. It does not establish a confirmed native discard, the first slot, or the post-call profile. Keep the current hand untouched immediately after requesting a test; capture readiness must be checked before preparing another live opportunity.


A subsequent native selection test on the South 1 hand at step 86 selected 4p correctly in the drawn second slot. The local test harness used the controller's five-second default confirmation deadline; it expired during the separate visual observation before the explicit confirmation could be submitted. No confirmation click was sent, and this is not a completed discard test. The local interactive harness now uses the existing configurable 60-second confirmation deadline to accommodate human review, retaining fresh-plan, same-board and no-retry checks. Production defaults are unchanged. The selected tile must be manually discarded before another native attempt on a newer board.


## Persistent manual discard runner

Use `python -m games.mahjong_soul.live.runtime.manual_discard --capture <capture.jsonl> --profile <layout.json> --slot <visual-index> --tile <tile>` for a dry run. Add `--execute` only after visually identifying the current tile and slot. The runner sends one selection, prints a unique local confirmation-ticket path and the exact token/tile JSON it expects, and keeps its original controller alive without stdin or terminal focus. After a fresh screenshot verifies the raised tile, write that JSON to the printed ticket path. The runner requires unchanged board state, fresh capture and a newly built plan before the second click; it then waits for the matching server discard. Ticket contents are a human visual attestation, not automatic visual recognition.

The interactive runner allows up to 295 seconds for review using a 300-second controller deadline. Game expiry or any board change aborts it earlier. It never reconstructs pending executor internals or retries a failed action. Production controller defaults remain five seconds. Regression tests cover delayed confirmation with a fresh plan, rejection of an expired plan, and exact token/tile ticket matching. The earlier local harness selected 1m at South 3 step 76 but expired before its confirmation arrived; that attempt remains unconfirmed.


## Confirmation runner offline acceptance

The runner now uses a testable `ManualDiscardSession` that owns one controller from start through server acknowledgement. Its cross-process regression starts a child with stdin closed, sends confirmation through the unique ticket file, and checks exactly two fake mouse clicks and a matching live action acknowledgement. Additional complete-session tests cover a 140-second review delay, stale/wrong/malformed tickets, stale capture, changed boards, manual discards before confirmation, closed connections, incomplete state, initial and second-click delivery failures, review expiry, missing server acknowledgement and duplicate requests. Failures are terminal within that session; no executor internals are reconstructed.

Dry runs now print the observed board token. Execution additionally requires `--expected-token <token>` from that inspected turn, and refuses to select if the board changed during preparation. Both planned clicks still use fresh plans and the native backend's foreground/client-size checks. These are offline tests with a fake mouse, not proof of a successful live native discard. No further game preparation was requested during this repair.


## Native double-click confirmed: 2026-10-17

The native two-tile drawn-slot discard completed successfully in the existing four-player AI room at 1920x1080. The inspected hand was 7p/2p, own seat 1, South 3 with one continuation, action step 124. The double-click executor targeted the second drawn slot at (394, 1000), and the shared controller received the matching own `ActionDiscardTile` for 2p at step 125. The CLI returned `{"confirmed": true, "tile": "2p", "step": 125}`. No screenshot review or ticket was needed between clicks.

An initial invocation was blocked before input because running the input module with `-m` constructed a `__main__.DiscardPlan` while the shared controller registered the canonical imported class. The CLI now constructs its plans through the canonical module import; a subprocess regression verifies plan dispatch before any fake or native input. Only the second drawn slot was executed in this live test. The first slot and post-call two-tile profile retain their previous visual/manual evidence.
