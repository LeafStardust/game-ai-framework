# Room restart rejected numeric-only header and animated decoration

The latest run used the three-game limit but completed only one match. All 140
submitted gameplay actions were confirmed; no input block or game-limit stop
prevented restart. The room Start handler withheld the visible custom room.

The focused header OCR returned the correct number without its stylized Room#
prefix. Accept a unique four-to-six-digit word only inside the expected numeric
header region and with an independent Room heading from the full-frame read.
Map it back to source coordinates; the existing exact expected-room comparison
still rejects a different number. This is interpretation of recognized digits,
not substitution of the authenticated room ID when OCR fails.

A replay then found a second blocker: animation beside the heading changed the
old broad header rectangle by mean RGB distance 1.203, above its threshold of
one, although roster, format and Start regions were unchanged. Compare the
recognized header's text bounds instead. Every pixel within the recognized
number/heading, each AI text crop, format panel and Start still receives the
same stability check. A regression changes surrounding decoration without
changing text, and separately verifies changed header pixels are rejected.

Real Windows OCR plus two distinct saved frames from the failed room now
produce one room_start_submitted through the real handler and a fake mouse.
The original replay failed before these two changes. No private session fixtures
were added; unit tests use existing cropped fixtures and synthetic room numbers.
No game or agent was launched and no native input was sent. Actual restart
still needs validation after the user reloads the launcher.
