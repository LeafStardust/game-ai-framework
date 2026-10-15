# Passive calibration recording

Start the existing network capture first, open Steam Mahjong Soul, then run from this worktree:

```powershell
.\.venv\Scripts\python.exe -m games.mahjong_soul.live.runtime.calibration
```

Play normally. You do not need to announce each prompt. The recorder saves changing client screenshots, client size/origin, reader hand and available operations, left-click positions, and nearby own action confirmations. It follows the newest capture file automatically. Historical frames bootstrap the reader but are not emitted as new actions.

Recordings stay in ignored `logs/mahjong_soul/calibration/<session>/`. `events.jsonl` references PNG screenshots and candidate click IDs. Raw network frames, account identifiers and authentication payloads are not copied. Nothing is uploaded or added to Git. Screenshots are client-area screen captures: overlays within the game rectangle may appear.

The recorder sends no clicks, never changes the foreground window and never installs a hook. It pauses screenshots when the game is not foreground, is minimized, is partly off screen, or the reader is not ready. Click sampling runs in a separate thread every 5 ms while screenshots are sampled every 250 ms. Very brief clicks, UI transitions or scheduler stalls can still be missed. Missing, stale or moved-window pre-click images are explicitly marked unavailable. Server-event correlation is a review aid, not proof that a particular button was clicked. Menu opening, tile selection and Skip may have no corresponding game action; their screenshots/clicks are retained without inventing confirmation.

The default run ends after one hour or at a 1 GiB session limit. Stop with Ctrl+C. Options: `--duration 600`, `--max-mb 512`, `--file <capture.jsonl>`, `--output <directory>`. Each run creates a new session and does not overwrite previous recordings. A full or exhausted output limit stops the recorder rather than deleting evidence.

Recorded examples must be inspected before a layout is marked verified. The recorder does not automatically choose tiles, certify coordinates or enable profiles. Multi-choice panels can be collected while you interact normally; slower visible panels give more complete evidence.
