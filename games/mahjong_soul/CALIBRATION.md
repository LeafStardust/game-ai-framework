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

Live smoke validation confirmed readable 1920x1080 game PNGs, player click records and own-action candidate correlations while playing normally. Identical recaptured screens refresh evidence timestamps without writing duplicate images. Missing correlations remain explicitly unconfirmed.

## Recording review: 2026-10-16

Reviewed local session `20261016-181251-573310`: 357 frame records, 33 clicks and 26 own-action records. Every recorded client geometry is 1920x1080. The replacement session `20261016-182056-719819` currently contains no events; starting a recorder alone does not establish additional coverage.

- Riichi: two declared discards are present. `frame-000044.png` visibly shows Riichi tile selection; the associated click has a fresh preceding image and the subsequent server action declares Riichi. The second declaration has candidate clicks but lacks fresh preceding images.
- Chi: three single-combination offers are recorded. `frame-000198.png` visibly shows Chi and Skip. No own Chi action follows in this recording, so this is visual offer evidence, not a newly verified execution.
- Wins: one own Tsumo and one own Ron are confirmed by server events, but neither has correlated click evidence. Examined win-context frames show transitions rather than stable actionable buttons. Do not promote button layouts from those confirmations alone.
- No Pon, kan or multiple-combination Chi offers are present. This session adds no evidence for their layouts or shorter post-call hands, and no evidence for 1920x1200.

No layout profile was changed by this review. Existing previously verified profiles remain the execution baseline. Raw screenshots and event logs remain local and ignored by Git.

The first session exhausted its 1 GiB cap after only a few minutes: animated full-client PNGs dominate storage. Longer unattended collection needs improved storage efficiency; the current recorder must not be described as guaranteeing a full hour of evidence. Missing evidence is not a reason to request another match until that limitation is addressed.
