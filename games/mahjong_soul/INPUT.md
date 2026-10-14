# Steam mouse input

The first input milestone implements guarded single-click discards. The reader
continues capturing game data; no decision policy is connected. Chi/pon/kan,
riichi, win and pass buttons still need visual calibration and multi-stage
handling. No coordinates are enabled by default.

## Calibrated layout

A profile is a local JSON object with `version: 1`, `verified: true`,
`client_size: [width, height]`, `hand_count`, and `slots: [[x, y], ...]`.
Coordinates are fractions inside the game client area, not the whole desktop.
Each slot must be verified visually for that exact hand layout and window size,
including the separated drawn tile. Profiles belong under ignored
`logs/mahjong_soul/`; do not mark guessed coordinates verified. Recalibrate after
a resolution, UI scale, hand arrangement, or layout change. Window movement is
handled by translating the current client origin.

The reader hand array is not guaranteed to match screen sorting. The caller
must identify the visual slot and its exact tile (including red-five identity)
from the current screen. The planner checks tile membership, not visual
recognition. It does not map hand-array indices to screen positions.

## Executor interface

```python
from games.mahjong_soul.live.runtime.input import plan_discard, DiscardExecutor
from games.mahjong_soul.live.runtime.windows_input import WindowsMouse

executor = DiscardExecutor(WindowsMouse())
plan = plan_discard(reader.snapshot(), verified_profile, visual_slot, exact_tile)
# Drain live capture rows again immediately before sending input.
executor.execute(plan, reader.snapshot(), enabled=True)
# Feed decoded live events as they arrive:
confirmed = executor.observe(connection_id, decoded_event)
```

Real input requires explicit `enabled=True`. A plan expires after two seconds,
requires a ready board and an own discard operation, and is bound to the board
and connection that produced it. Always consume the live capture to its current
end before planning/executing; saved captures are for dry-run tests only. Plan
expiry does not establish that an old capture itself is fresh.

The Windows backend verifies the foreground process is
`Jantama_MahjongSoul.exe`, requires the calibrated client size, applies per-monitor
DPI coordinates, and sends a mouse move followed by left press/release. It never
activates another window. Foreground and state checks reduce races but cannot
make OS input and network state atomic. Keep the game foreground during execution.

A successful OS input call means only that input was delivered. Confirmation
requires a later live `ActionDiscardTile` for the same connection, own seat and
exact tile. Restored historical actions cannot confirm clicks. Each board gets
one attempt, and pending clicks block subsequent input. A failed or unconfirmed
click is never automatically repeated. Stop and inspect before resuming; retain
the executor instance so attempted-board protection is not lost.

## Validation and next step

Unit tests cover stale boards, expired plans, operation/seat checks, unverified
layouts, exact red-five confirmation, repeat prevention, and partial input errors
using a fake mouse. The native backend has not yet been live-tested and no click
was sent during development. Next: calibrate and verify one discard in a Steam
AI room, then extend the same confirmation flow to call/choice panels.

Win32 references: [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
and [MOUSEINPUT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput).
