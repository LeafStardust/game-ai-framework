# Failed custom-room restart: focused room-number OCR

Session `20261023T123101-808869Z` used revision `e7c70bfa` and a five-game
limit. It counted only one completed match, so the budget was not the blocker.
The final room screen showed enabled Start, two AI opponents, and Room#96219.
Full-frame Windows OCR omitted that entire stylized heading. The required room
identity check consequently rejected the screen, and no Start attempt occurred.

Keep the room-identity requirement. When OCR finds Start, run a second read of
the same source frame's gold heading at three times its size, as black text on
white. Map the recognized word bounds back to source coordinates and retain all
existing format, AI roster, active-button, board, geometry and two-frame checks.
The OCR remains on the existing background worker. Result screens without Start
do not pay for another pass. Failed room-context verification now records a
bounded `room_start_withheld` diagnostic with the expected room and observed
heading words rather than silently returning forever.

Real Windows OCR on saved frame 0002983 now reads Room#96219. Offline replay
of that frame and later frame 0002990 through the actual ResultButtons handler,
using a fake mouse, produced one room_start_submitted at (1142,999). The full
roster/heading/button stability check passed across these distinct frames.
A small saved header fixture covers the original missing-heading case, focused
read and wrong-room rejection. This is replay validation, not a real Start click.
No agent was launched and no native input was sent during this fix.
