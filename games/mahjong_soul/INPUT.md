# Steam mouse input

The first input milestone implements guarded discard selection and confirmation. The reader
continues capturing game data; no decision policy is connected. Chi/pon/kan,
riichi, win and pass buttons still need visual calibration and multi-stage
handling. No coordinates are enabled by default.

## Calibrated layout

A profile is a local JSON object with `version: 1`, `verified: true`,
`client_size: [width, height]`, `hand_count`, `trigger` (the reader last-event name), and `slots: [[x, y], ...]`.
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
one initial attempt, and pending clicks block subsequent ordinary input. A failed or unconfirmed
click is never automatically repeated. Stop and inspect before resuming; retain
the executor instance so attempted-board protection is not lost.

## Validation and next step

Unit tests cover stale boards, expired plans, operation/seat checks, unverified
layouts, exact red-five confirmation, repeat prevention, and partial input errors
using a fake mouse. The native backend has not yet delivered a live click. A computer-use UI test verified
a discard at a 925x520 client size: the first click selected/raised the drawn
`5m`, and a second click discarded it, confirmed by live seat-0 action step 11.
The local 14-tile profile remains under ignored logs. Next: verify the native
backend and extend the confirmation flow to call/choice panels.

Win32 references: [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
and [MOUSEINPUT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput).

## Selected-tile confirmation

For the observed two-click UI mode, take a fresh screenshot after the first
click and verify the intended tile is selected. Re-read current capture rows,
rebuild the same plan, then call
`executor.confirm_selection(plan, report, selected_tile, enabled=True)`. It
permits one confirmation click only, requires the same board/tile/coordinates,
and rejects partial-input failures. Never invoke it just because no discard
arrived. A selected tile is a visual UI state; the network reader cannot prove
selection.

A command-line dry-run helper is available:

```powershell
.\.venv\Scripts\python.exe -m games.mahjong_soul.live.runtime.input --capture path/to/live.jsonl --profile path/to/layout.json --slot 13 --tile 5m
```

`--execute` opts into one native click and waits five seconds for confirmation.
It requires a capture modified within two seconds and never automatically sends
a selection-confirmation click. Held turns may fail that conservative freshness
check; the screenshot-aware consumer interface above is the appropriate path
for explicit selection handling.

## Pon input

`calls.plan_pon(report, profile)` and `calls.PonExecutor(backend)` support a
single server-provided Pon combination. Profiles contain `version: 1`,
`verified: true`, `client_size`, `operation_types` matching the full offer order,
and a normalized `pon` point. Multiple red-five combinations are rejected until
their choice panel is calibrated. Confirmation requires a live own Pon with the
expected tile kind. Keep a shared input coordinator when integrating executors;
these primitives do not prevent another executor instance from sending input.

Live UI calibration also verified leftmost `2m` discard at step 51 and a
single-choice `9s` Pon at step 56. The Pon-only button layout differs from offers
with multiple action buttons. Discard profiles must match the last-event trigger:
an equal hand count after draw and after call does not imply equal positions.
The native backend remains unverified for delivery; the UI tests used the
computer-use plugin, with decoded live game events as confirmation.

## Chi input

`calls.plan_chi(report, profile)` and `calls.ChiExecutor(backend)` support a single
Chi combination. Profiles use a `chi` point and the full `operation_types` offer
order, following the same layout guards as Pon. Planning requires a known uncalled
discard from the previous seat and the two exact contributed own tiles.
Confirmation checks the resulting sequence, exact red-five identity, and tile
source seats. Multiple combinations require an explicitly observed and calibrated choice panel.

The live 925x520 Chi-only offer was clicked at the same button location as the
Pon-only offer and immediately produced own `5s/6s/7s` Chi at step 80, with
contributions from seats `0/0/3`. There was one combination and no intermediate
choice panel. Native backend delivery, combined button offers, and other choice-panel layouts remain unverified.

## Multi-choice Chi panel

For an already open panel, use
`plan_chi(report, profile, combination="4m|0m", visible_combinations=observed_order)`.
The profile must have `stage: "chi_choices"`, the exact ordered `combinations`,
and one normalized `choice_points` coordinate per combination. Both the saved
profile and the currently visually observed order must match the server offer.
Do not supply the server list as a substitute for screen observation. A stale
profile, reordered choices, missing points, or absent selected combination blocks
input. `ChiExecutor` then clicks the selected point once and requires the exact
meld, including red-five identity and source seats, as confirmation.

A live three-choice panel showed `2m|4m`, `4m|0m`, and `4m|5m` from left to right.
Selecting the middle group produced `4m/0m/3m` at own seat 0, step 89, with sources
`0/0/3`. That validates this 925x520 layout and red/ordinary-five distinction.
The user opened the panel before calibration; automatic menu opening has not
been live-verified. Two-choice panels and other UI scales need separate profiles.
Multi-choice Pon, kan, riichi/win/pass execution, native backend delivery, and a
shared input coordinator remain outstanding. No decision policy is connected.

## Shared input controller

Use one `controller.InputController(backend)` instance for the game session.
Submit all discard/Pon/Chi plans through `submit(plan, report, enabled=True)`;
do not also send input through independent executors. The controller serializes
submissions, allows one pending action, and reserves attempted game steps across
all action types. Keys include connection, reader game generation, round and step
so a new round or authenticated game may restart step numbering.

```python
from games.mahjong_soul.live.runtime.controller import InputController

controller = InputController(backend, confirmation_timeout=5)
controller.submit(plan, reader.snapshot(), enabled=True)
# For each decoded event, before updating from the resulting board:
controller.observe(connection_id, event)
controller.update(reader.snapshot())
```

Call `update` periodically even with no new rows. Wrong own actions, confirmation
timeouts, partial delivery, a closed/new connection or unready state block input.
Late confirmations cannot silently unlock a timed-out controller. A successful
matching event clears the pending action, allowing a plan at the next game step.
The controller never retries or chooses another action.

Discard selection uses the same controller's `confirm_selection` method after a
fresh screenshot and rebuilt plan. Set a confirmation timeout long enough for
the consumer's visual inspection; the default five seconds is intended for an
automated local consumer, not slow manual calibration.

Blocked recovery is explicit: `recover(report, visually_verified=True)` requires
a newer ready board after visual inspection. It sends no input and retains
attempt history. It cannot unlock the same attempted round/step. A new round or
authenticated game can reset step numbers. Retain the controller for the session;
creating another instance loses its in-memory duplicate ledger.

The discard CLI now uses this controller. Native backend delivery still needs a
live test; no additional real input was sent for controller validation.

## Native backend validation

On 2026-10-14, the repository WindowsMouse backend and InputController were
verified in a fresh four-player Steam AI room at 925x520 client size. Native
selection raised the separated drawn `4m` at seat 3, step 7. After screenshot
verification, a native confirmation click produced live own discard at step 8
and returned the controller to idle. The computer-use plugin supplied screenshots
only; both mouse clicks were sent by the repository backend. This verifies this
window/layout and two-click flow, not every DPI/window size or action button.
