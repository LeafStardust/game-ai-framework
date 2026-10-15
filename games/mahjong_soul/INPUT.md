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
using a fake mouse. Native discard delivery is verified below. An earlier computer-use UI test verified
a discard at a 925x520 client size: the first click selected/raised the drawn
`5m`, and a second click discarded it, confirmed by live seat-0 action step 11.
The local 14-tile profile remains under ignored logs. Native call-button delivery and remaining controls need further live verification.

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
exact contributed tiles, red-five identity, and source seats. Keep a shared input coordinator when integrating executors;
these primitives do not prevent another executor instance from sending input.

Live UI calibration also verified leftmost `2m` discard at step 51 and a
single-choice `9s` Pon at step 56. The Pon-only button layout differs from offers
with multiple action buttons. Discard profiles must match the last-event trigger:
an equal hand count after draw and after call does not imply equal positions.
The call UI tests used the computer-use plugin, with decoded live game events
as confirmation. Native discard delivery was subsequently verified below.

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
choice panel. Native call-button delivery, combined button offers, and other choice-panel layouts remain unverified.

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
Multi-choice Pon, kan, and riichi/win/pass execution remain outstanding. Native
discard delivery and shared input coordination are verified below. No decision
policy is connected.

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

The discard CLI uses this controller. The subsequent native input test below
verified the full controller/backend discard flow.

## Native backend validation

On 2026-10-14, the repository WindowsMouse backend and InputController were
verified in a fresh four-player Steam AI room at 925x520 client size. Native
selection raised the separated drawn `4m` at seat 3, step 7. After screenshot
verification, a native confirmation click produced live own discard at step 8
and returned the controller to idle. The computer-use plugin supplied screenshots
only; both mouse clicks were sent by the repository backend. This verifies this
window/layout and two-click flow, not every DPI/window size or action button.

Pon planning also checks the latest known uncalled opponent discard. Matching
only normalized tile kinds is insufficient: red-five contribution and source
identity must match exactly, as in the Chi path.

## Skip input

`skip.plan_skip(report, profile)` supports declining a visible call offer. A
profile uses `stage: "call_offer"`, the full ordered `operation_types`, and a
normalized `skip` point. A choice-panel profile cannot act as an offer profile.
Planning accepts Chi/Pon/open-kan/ron operation codes only when the exact offer
layout is visually verified; the current live evidence covers Chi-only offers.

Submit Skip through `InputController`. In addition to game events, feed each
decoded RPC using `observe_message(connection, decoded, from_client)`. Confirmation
requires the newly observed client `inputChiPengGang` cancellation request and
its matching successful server response on the same connection and request ID.
A later draw is not sufficient. Error replies block the controller.

The reader clears operations only after successful acknowledgement of the
current step's cancellation. Delayed acknowledgement cannot clear a later
action's operations. A live Chi-only Skip at step 34 sent
`cancel_operation=true`, received the successful matching response (request 78),
and advanced to own draw at step 35. The click used computer-use; native Skip
delivery remains unverified. Kan, riichi and win input still need calibration.

## Riichi input

`riichi.plan_riichi(report, profile, visual_slot, tile)` requires the exact tile
in the server's type-7 discard list, a calibrated hand layout, the full ordered
operation types, and a normalized `riichi` button point. Use the shared controller:

1. Submit the plan to open the riichi selection mode.
2. Visually verify the highlighted allowed tiles and rebuild a fresh plan. Call
   `select_riichi_discard(plan, report, visible_allowed_tiles, enabled=True)`.
3. Verify the selected tile visually and use `confirm_selection` if required
   by the observed two-click mode.
4. Feed live events until an exact own discard marked `is_liqi`/`is_wliqi` is
   followed by successful server `liqi` acceptance.

Ordinary discard confirmation does not complete riichi input. Wrong tiles,
plain discards, failed declarations, stale boards and partial delivery block
the controller. The highlighted tile set must match the offer including red
fives; screen order need not match the server list. Opening the mode has no
dedicated network event, so visual verification is required.

Live calibration at 925x520 offered `7s` and `6s`. The riichi button opened
highlighted-discard mode. The own `6s` declaration was captured at step 84, and
server acceptance at step 85 reported seat 1 score 24,000 and one riichi stick.
An initial click on the unoffered `3s` slot sent no declaration; the implemented
planner rejects that tile before clicking. Calibration clicks used computer-use;
native riichi delivery remains unverified. Next controls are kan and win.

## Concealed kan input

`kan.plan_concealed_kan(report, profile)` supports one server-offered concealed
kan (operation type 4). It requires the four exact contributed tiles in the own
hand, including red-five identities. A verified profile uses `stage: "call_offer"`,
the complete ordered `operation_types`, `client_size`, and a normalized `kan` point.
Submit the plan through `InputController`; the usual expiry, duplicate, overlap,
foreground and client-size checks apply.

Confirmation requires a later own live `ActionAnGangAddGang` with concealed-kan
event type 3 and the expected tile kind. The event identifies one tile kind,
not the four-tile red composition; the planner checks those contributions before
input and the reader removes the actual own tiles. A replacement draw alone,
added-kan type, mismatched kind or restored action cannot confirm the click.

Live validation at 925x520 offered `[discard, concealed kan]`, with one combination
`6p|6p|6p|6p`. One Kan-button click produced own seat-2 concealed kan at step 35,
then replacement draw `1s` at step 36 with a second dora indicator. These calibration
clicks used computer-use. Native concealed-kan delivery remains unverified.
Multiple kan candidates, open/added kan, and combined offers with other buttons
require further calibration. Profiles still reject changed client sizes; resize,
maximize and fullscreen layout support remains outstanding.

## Combined Chi/Pon offer

At 925x520 the combined `[2, 3]` offer places Chi left of Pon and Skip. Its
Chi coordinate differs from a Chi-only offer, even when the combination count
is one. Profiles must retain the complete ordered `operation_types: [2, 3]`
and independently calibrated `chi`, `pon`, and `skip` points. Existing planners
reject a Chi-only or Pon-only profile against this combined offer.

The observed live offer contained Chi `7s|8s` and Pon `9s|9s` on a discarded
`9s`. Clicking the shifted Chi button produced own seat-2 `7s/8s/9s` Chi at
step 43, with sources `2/2/1`. The Pon and Skip positions were visually mapped
in this offer; only the shifted Chi button was clicked in this validation.
Regression tests cover distinct target points and shared-controller overlap
prevention. Native combined-offer delivery remains unverified.

## Win input

`win.plan_win(report, profile, kind="tsumo")` requires the own win operation and
a known own winning draw. `kind="ron"` requires the current known uncalled
opponent discard; robbing-kan contexts remain unsupported. Profiles use
`stage: "call_offer"`, complete ordered `operation_types`, `client_size`, and
a `tsumo` or `ron` point. Submit through `InputController`.

Confirmation requires a later live `ActionHule` containing the own seat, exact
winning tile including red-five identity, and matching self-draw/ron flag. A
round end or another player's win alone cannot confirm the action. Ron matching
can find the own winner among multiple results; multiple-winner handling has
offline coverage only.

Live Tsumo calibration at 925x520 offered `[discard, tsumo]`. One button click
produced own seat-2 `9p` self-draw at step 83, with final scores
22,600 / 27,100 / 38,000 / 12,300. The UI test used computer-use; native Tsumo
delivery remained unverified in that test; native Ron is verified below. No decision policy is connected.

## Native Ron validation

On 2026-10-15 a live Ron-only offer (operation `[9]`) at own seat 2 concerned
opponent seat 3's uncalled `7m` discard, step 87. A verified 925x520 Ron profile
was passed to `plan_win(..., "ron")` and the shared controller. The repository's
WindowsMouse backend clicked Ron once. Live `ActionHule` step 88 reported own
seat 2, `zimo=false`, and `hu_tile=7m`, with final scores
22,600 / 27,100 / 39,800 / 10,500. Exact confirmation returned the controller
to idle. Computer-use supplied the initial screenshot only, not the click.

This verifies native single-button Ron on an ordinary discard. Robbing kan,
combined Ron/call buttons, and native Tsumo remain outside this live validation.
Open/added-kan input and resize/fullscreen layout handling remain outstanding.

## Open kan input

`kan.plan_open_kan(report, profile)` requires one server type-5 combination,
three exact contributed own tiles, and the latest known uncalled opponent
discard of the same kind. A verified `call_offer` profile must match the full
ordered offer types and supply the `kan` point. Multiple combinations remain
blocked until their choice panel is calibrated.

Submit through the shared controller. Confirmation requires own live
`ActionChiPengGang` type 2 with all four exact tiles and their source seats.
Red fives are not interchangeable with ordinary fives. Pon, concealed/added kan,
wrong source assignments, and restored actions cannot confirm open kan.

Live calibration at 925x520 offered `[3, 5]` (Pon and open kan) on a seat-1 `2p`
discard. Clicking Kan produced own seat-2 open kan at step 114, with four `2p`
tiles and sources `2/2/2/1`. Replacement draw `7s` followed at step 115.
The click used computer-use; native open-kan delivery remains unverified.
Added kan and resize/fullscreen support remain outstanding.

## Added kan input

`kan.plan_added_kan(report, profile)` requires a single type-6 offer with four
exact tiles, one matching own three-tile Pon, and the exact fourth tile in the
own hand. Multiset subtraction identifies the added tile, preserving red-five
identity. An existing kan, a missing or ambiguous Pon, inconsistent composition,
or multiple candidates blocks planning. Use a verified `call_offer` profile
with the full ordered operation types and normalized `kan` point.

Through the shared controller, confirmation requires a later own live
`ActionAnGangAddGang` type 2 naming the exact added tile. A concealed-kan event,
a normalized substitute for a red five, or a restored action cannot confirm it.
Unknown red-five encodings remain blocked pending live evidence.

Live calibration at 925x520 offered `[1, 6]` (discard and added kan), upgrading
a `9s` Pon. The Kan click produced own seat-1 upgrade at step 33 followed by an
`8m` replacement draw at step 34, with no reader issues. Calibration used
computer-use; native added-kan delivery and multi-candidate panels remain
unverified. Resize/fullscreen handling remains a separate outstanding task.

## Window size variants and fullscreen

Coordinates remain relative to the current game client origin. Moving the
window between actions requires no recalibration. The backend now reads
physical client geometry using `WindowsMouse.client_geometry()` and rechecks it
immediately before sending input. A move or resize during click preparation
blocks that attempt. Minimized windows are explicitly rejected.

Use `layout.profile_for_size(profile, (width, height))` before planning. Each
verified `size_variants` entry supplies its exact target dimensions and every
coordinate field present in the base profile. Unknown sizes, duplicate variants,
unverified variants, and missing coordinates are rejected. No interpolation or
aspect-ratio guessing is used. Board/action context remains checked by planners.

A reusable profile at `live/layouts/discard-14-draw.json` covers the observed
14-tile hand after an own draw at 925x520 and fullscreen 1920x1080. On
2026-10-15 the native backend selected and confirmed the separated `3z` tile
using the fullscreen variant; the reader confirmed discard step 4 and the shared
controller returned idle. Both clicks came from the repository backend.

The discard CLI selects a verified variant from actual client geometry when
executing. Dry-run `--client-size WIDTH HEIGHT` selects a target explicitly.
Call/choice/riichi profiles, other hand layouts, other fullscreen resolutions,
and maximized client sizes still need their own verified variants. Fullscreen
validation of this discard layout does not certify every control at that size.
