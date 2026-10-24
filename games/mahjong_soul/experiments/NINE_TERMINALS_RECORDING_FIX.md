# Nine Terminals stall and multi-game recording exhaustion

Session `20261024T040250-275703Z` completed two of four requested matches,
clicked room Start twice, and authenticated three AI games. All 175 submitted
gameplay actions received server confirmation. Its terminal error was
`Session recording limit reached; stopping input`: the bounded 2 GiB recording
was exhausted during game three. No Start failure caused this stop.

There was a separate decision stall in that game. Saved frame 0009415 shows
normal discard, Kita and Nine Terminals Draw offers (server types 1, 11, 10).
The decision normalizer did not recognize type 10 and rejected the whole offer.
Type 10 is now accepted only as an optional abort alongside a normal discard,
with empty combinations. It is not selected as an abort action. The policy can
continue with its normal legal discard or North extraction. Unknown codes,
duplicate codes and malformed abort encodings remain rejected. A synthetic
legal opening hand reproduces the operation combination without copying private
session identifiers, room details or account data into the repository.

Recording now rotates oldest screenshot files within the current session when
space is needed. It retains the complete events journal and most recent image,
records removed image paths in frames_pruned events, and keeps record-before-
input fsync behavior. No earlier sessions are touched. Logs may therefore refer
to older images explicitly removed by retention. A budget too small for retained
metadata/current evidence, file deletion failure or disk error still stops input;
the code never bypasses recording to keep clicking. Screenshot retention is
bounded rather than multiplying the storage allowance by requested game count.

Tests cover continued fake input after rotation, exact journal sequence order,
current-image retention and the Nine Terminals operation combination. No
existing user recordings were deleted during development. No agent was started
and no native input was sent. The next user-started run must validate continued
native play across this offer and long-run screenshot rotation.
