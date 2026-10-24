# Room roster OCR and expired decision retry

The latest four-game run completed one match and remained in the custom room.
Full-frame OCR intermittently omitted an AI name, Start, or the room heading.
The focused heading pass alone was therefore insufficient. A separate
high-contrast pass now isolates white AI nameplate text and dark Start lettering
from animated portraits/backgrounds, then the existing heading pass verifies
room identity. All format, roster count, enabled-button, current-board, geometry
and fresh second-frame checks remain. Existing fixtures reproduce a missing
AI label without publishing another live-session snapshot.

Offline replay of two distinct saved frames from the failed room, using real
Windows OCR and a fake mouse, produced one room_start_submitted. No game or
agent was launched and no native input was sent during development.

All 132 submitted gameplay actions were confirmed, but two decision attempts
were rejected without diagnostic text. Those rejects occurred roughly 2.6 and
3.2 seconds after the preceding game event. The old logs cannot establish the
exact ValueError; replaying each saved board yields a legal discard. Do not
claim that every missed input has been explained or fixed.

Previously any policy rejection marked the board permanently considered.
Automatic play now allows one new decision request after the specific request-
expiry error. Full legality, freshness and native visual checks still apply;
it neither reuses an expired proposal nor retries a delivered mouse action.
A second expiry remains rejected, policy crashes are not retried, and ordinary
read-only monitor behavior remains unchanged. Rejection events now include
exception text for diagnosis. Tests cover a fresh successful retry and the
bounded repeated-expiry case. Live validation is still needed.

C/D behavior is unchanged: C skips calls, D forces drawn-tile discard, and
accepted Riichi currently enables both. C adds little after Riichi because
ordinary calls are already disallowed; D avoids redundant discard decisions.
A provisional closed plan or open Tenpai is not an unconditional hand lock.
