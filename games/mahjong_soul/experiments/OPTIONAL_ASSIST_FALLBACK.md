# Optional assist timeout must not freeze native play

The latest run halted after an Auto Win enable attempt stayed unconfirmed for
three seconds. The saved sidebar independently reads Auto Win OFF. All thirty-
two submitted gameplay actions before the halt were server-confirmed. This was
an optional-assist halt, not a game-count stop or failed custom-room restart.
The recording does not establish why the original switch click was lost.

When Auto Win or Auto Kita enablement times out and a fresh reviewed sidebar
explicitly shows that switch OFF, stop trying that switch for the current hand
and continue with ordinary native win/extraction actions. Record
assist_native_fallback. A new hand allows normal preparation again. The uncertain
click itself is not repeated. Unknown switch states, failed delivery exceptions,
and unconfirmed Auto Discard/Skip Calls changes retain the original stop guard.
These restrictive controls could suppress or discard actions, so their unknown
state cannot be treated as a harmless optional assist failure.

Tests cover one delivered optional click followed by fresh OFF confirmation,
continued reconciliation without replay, next-hand setup and the retained
restrictive-toggle stop. Existing gameplay tests cover the native fallback
paths when observed Auto Win/Auto Discard is OFF. No agent was launched and no
native game input was sent during this fix. The first real fallback following a
lost assist click still needs live validation.
