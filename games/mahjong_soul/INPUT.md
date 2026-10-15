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

## Serialized Chi menu opening

For a multi-choice offer, submit `calls.plan_chi_menu(report, offer_profile)`
through the shared controller. After taking a new screenshot of the open panel,
use `bind_chi_choices(report, panel_layout, visible_combinations)` to bind the
visually observed ordered combinations to calibrated geometry. Build a fresh
`plan_chi` for the desired combination and call
`controller.select_chi_combination(plan, report, enabled=True)`.

The menu and choice share one attempted game step. Other actions stay blocked
between them. A failed menu click cannot be followed by a choice click. The
choice must match the original menu, board and client size, and successful
confirmation still requires the exact live own meld. Opening a menu alone
never counts as a confirmed game action.

Fullscreen calibration at 1920x1080 verified the Chi-only button opening a
two-choice panel. The observed choices were `4p|5p` and `5p|7p`; selecting the
second produced own seat-1 `5p/7p/6p` Chi at step 27, sources `1/1/0`.
Reusable layouts are in `live/layouts/chi-offer.json` and
`live/layouts/chi-two-choices-fullscreen.json`. Geometry can be reused for the
same verified panel count, size and offer; actual tile order must be reobserved
each time. Calibration used computer-use; native Chi-menu delivery remains
unverified.

## Fullscreen Skip and eleven-tile hands

Native fullscreen Skip was verified on a Chi-only offer at step 50: the client
sent a cancellation request and the matching server response returned the
controller to idle. `live/layouts/skip-chi-offer.json` includes the tested
925x520 and 1920x1080 coordinates.

Agent-driven play also verified eleven-tile fullscreen hand layouts after a
call and after a draw. Their last slots differ: the post-call hand is continuous,
while the own draw is separated. Reusable profiles are
`discard-11-after-call-fullscreen.json` and `discard-11-draw-fullscreen.json`.
They remain tied to their reader event trigger and exact client dimensions.
These hand calibration clicks used computer-use; only Skip used the native
backend in this additional test.

## Native fullscreen open kan

Autonomous AI-room calibration reached a combined Pon/open-kan offer at
1920x1080. WindowsMouse clicked Kan through InputController; own seat-1 live
open kan at step 57 contained four `4p` tiles with sources `1/1/1/3`. Exact
confirmation returned the controller idle. A replacement draw followed.

`live/layouts/open-kan-offer.json` provides calibrated Kan coordinates for
`[3, 5]` offers at windowed and fullscreen sizes; it does not certify the
alternate Pon button. The subsequent eight-tile own-draw layout was exercised
with a computer-use discard and is saved as
`discard-8-draw-fullscreen.json`. Fullscreen concealed/added-kan, Pon, riichi
and win controls remain separate validation cases.

## Post-call discard restrictions

Discard planning treats the current type-1 operation's `combination` entries
as forbidden tile kinds, including red/ordinary-five equivalents. Unsupported
restriction encodings block planning. This guard also applies when the riichi
planner delegates to discard planning.

Autonomous fullscreen play verified native Chi `3m/4m/5m` at step 66. The
subsequent discard offer listed `2m` and `5m` as forbidden, with `2m` visibly
greyed out; an unrestricted `1s` was discarded instead. No blocked-tile click
was attempted. Native Chi used the reusable fullscreen Chi-offer profile.

## Automatic calibrated hand-layout selection

`layout.discard_profile(report, client_size)` chooses a unique bundled discard
profile by client size, hand count and last-action trigger. It does not interpolate
unknown sizes or reuse a post-call row for a separated draw. Missing or ambiguous
calibrations block planning. Five-tile fullscreen draw/post-call layouts were
also exercised during autonomous AI-room play and are now bundled.

This selects geometry only. The caller must still identify the actual visual
slot for the intended tile; reader hand order is not screen order. A matching
layout does not choose a discard or replace restriction checks.

## Initial dealer turn

The initial dealer hand has fourteen tiles but follows `ActionNewRound`, not
an own draw event. `discard-14-initial-fullscreen.json` explicitly covers that
1920x1080 layout. During autonomous play, native selection and confirmation
discarded the separated `7z` at step 1 after round-start step 0. The controller
returned idle. This calibration is not silently applied to unverified windowed
round-start layouts.

Fullscreen eight-tile post-call layout was visually checked after a second Chi in an AI room. The contiguous hand centers are 270 through 935 pixels at 95-pixel intervals; discarding the allowed 8m was confirmed by the following board update. This profile is distinct from the eight-tile draw layout, whose separated tile center is 963 pixels. Native execution of this particular post-call layout remains untested.

Native fullscreen Pon was confirmed in the combined Chi/Pon/Skip offer: Pon at (1020,835), exact operation types [2,3]. The reader confirmed own 8p triplet with sources [1,1,0] and the shared controller returned idle. The profile certifies only Pon in this offer context.

Native fullscreen Ron was confirmed on the final opponent discard in an AI round: the Ron-only offer [9] uses (1020,835). ActionHule confirmed own seat 1, winning tile 7p and non-tsumo win; the shared controller returned idle. This does not certify other win-button offer combinations.

Fullscreen Riichi [1,7] was verified at (1020,835) with the fourteen-tile own-draw layout. The native controller opened the menu and selected the visually highlighted 2p at (460,1000), showing the 7m wait preview. The calibration helper timed out during review delays before final confirmation; a computer-use click completed that selection. Reader evidence confirmed is_liqi on the 2p discard and subsequent own-seat liqi acceptance with failed=false. Full native end-to-end Riichi acceptance remains to be repeated; the production confirmation timeout was not changed.

The separate fullscreen Pon-only [3] offer was also natively confirmed at (1020,835): own 8m triplet, followed by the shared controller returning idle. This has its own profile rather than broadening the combined Chi/Pon profile.

Native fullscreen two-choice Chi was verified end to end through one shared controller. The Chi-only offer opened the panel; visual inspection showed left 1p|3p and right 3p|4p. Binding that observed ordering to the calibrated two-choice geometry and selecting the left choice produced the expected own Chi at the following step, with the controller returning idle. No combination order was inferred without inspecting the panel.

Native fullscreen added kan was verified for the own-turn [1,6] offer at (1020,835). Exact north (4z) was matched against the existing own Pon and concealed fourth tile; ActionAnGangAddGang type 2 confirmed the upgrade and the shared controller returned idle.

Fullscreen Riichi is now natively verified end to end: own-turn [1,7] menu at (1020,835), visually confirmed allowed discards [4p,6s], selection of the separated drawn 4p, and a second native click. The reader confirmed server acceptance at the following draw and the shared controller returned idle. This supersedes the earlier partial-native limitation for this calibrated offer. Generic discard lookup now excludes operation-specific hand layouts so Riichi geometry cannot make normal fourteen-tile draw selection ambiguous.

Native fullscreen closed kan was verified for the own-turn [1,4] offer at (1020,835). Four concealed 6s were checked against the server offer and own hand; ActionAnGangAddGang type 3 confirmed the kan, and the shared controller returned idle. This profile covers a single kan choice only.

Native fullscreen Tsumo was verified for the own-turn [1,8] offer at (1020,835). ActionHule confirmed own seat 3, exact winning draw 8m and zimo=true; the shared controller returned idle. The common fullscreen discard, Chi/menu choice, Pon, Skip, Riichi, single-choice kan and win paths now have live native confirmation in their documented offer contexts. Unseen combined offers, multiple kan choices and uncalibrated client sizes remain blocked.

1920x1200 support: profile_for_viewport builds candidate coordinates within an explicitly observed physical viewport; candidates remain verified=false until inspected. No letterboxing is inferred from dimensions alone. Fourteen-tile round-start and own-draw hand coordinates were visually validated at this size, including the separated tile. Native white-dragon selection and confirmation at (1532,1060) produced the exact discard and returned the controller to idle. These two discard variants are automatically selected by current client size. Other hand counts and action-button profiles remain blocked at 1920x1200 until individually inspected; this is not blanket arbitrary-resize support.

1920x1200 shared action row: native Pon at (1020,895) confirmed own 9m triplet and returned the controller idle. Pon and Skip visually retain their horizontal positions and share the +60px vertical offset. That shared-row transform is now applied to the existing exact-context Chi, Pon, Skip, kan, Riichi and win profiles, with validation_basis metadata identifying the derivation. These other controls were not each executed at 1920x1200; their original 1920x1080 verification and the observed shared-row mapping are the basis. The eleven-tile post-call hand was also visually checked. Choice panels and unobserved shorter hand geometries are excluded from this row mapping. This supersedes the earlier blanket block on action buttons at this size.
