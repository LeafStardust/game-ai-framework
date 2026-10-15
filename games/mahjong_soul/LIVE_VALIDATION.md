# Steam live capture validation

Date: 2026-10-14 (Asia/Kuala_Lumpur).

## Observed test

Steam executable: `Jantama_MahjongSoul.exe`. A three-player room against AI
players, captured using process-scoped mitmproxy local mode. The Windows helper
ran with administrator approval, and the worktree's generated CA was trusted
in the user's Current User root certificate store with explicit approval.

The client used numeric IPv4 and IPv6 gateway addresses. Capture now accepts IP
hosts only when local mode targets one explicit process name or PID; hostname
filtering remains in effect for regular proxy mode.

## Game sequence and replay

All 77 game actions were decoded, with steps 0 through 76 contiguous:

| Action | Count |
| --- | ---: |
| ActionMJStart | 1 |
| ActionNewRound | 1 |
| ActionBaBei | 4 |
| ActionDealTile | 37 |
| ActionDiscardTile | 33 |
| ActionHule | 1 |

The last game event ended the round. Offline replay with the current tracker
produced three seats, no game-state issues, final scores of 47,000 / 29,000 /
29,000, and north extraction counts of 2 / 1 / 1. Seat inference identified the
user as absolute seat 0. Three-player round scores now size rivers, meld arrays,
and north counts to three rather than retaining a phantom fourth seat.

Raw captures and replay files remain local under ignored `logs/mahjong_soul/`.
They are not committed. The test capture and redirector were stopped afterward;
the game process remained running.

## Four-player validation and restart

A subsequent four-player AI room identified the human as absolute seat 2. Its
first two rounds ended with 149 and 87 contiguous actions; a third round had
82 contiguous actions before the client was closed. Four pons and two chis
verified contributed-tile removal and called-discard marking. The room could
not be rejoined, so this attempt did not validate live restoration.

After restarting Steam Mahjong Soul, a fresh four-player AI match completed:

| Round (wind, dealer, repeat) | Actions | End | Scores by absolute seat |
| --- | ---: | --- | --- |
| 0, 0, 0 | 147 | Exhaustive draw | 25,500 / 23,500 / 23,500 / 26,500 |
| 0, 0, 1 | 39 | Win | 25,500 / 30,000 / 23,500 / 21,000 |
| 0, 1, 0 | 124 | Win | 24,500 / 28,000 / 27,500 / 20,000 |
| 0, 2, 0 | 131 | Win | 36,500 / 28,000 / 27,500 / 8,000 |
| 0, 3, 0 | 144 | Win | 34,500 / 36,000 / 25,500 / 4,000 |

All 685 actions were contiguous within their rounds, with no conflicting
duplicates, game decoding errors, or historical state issues. The match included
ten pons, five chis, and one concealed kan. Exhaustive-draw score settlement and
final `match_ended` status were verified. Fresh authentication reset the old board.

## Limits

The current server exposes lobby activity fields and an RPC absent from the
reference schema. Those payloads remain opaque with explicit schema warnings;
request/response correlation and original bytes are retained. Game decoding
remains strict. The reference JSON has not been altered to guess field meanings.

Live added/open kan, reconnect restoration, special modes, and action execution
remain unverified. Offline tests cover kan variants and restoration. No agent
decisions or automatic game actions were sent. Raw captures remain local in
ignored logs; only this sanitized report is committed.

## Native input validation

A fresh four-player AI room verified repository-native mouse selection and
confirmation through the shared controller. Own absolute seat 3 selected the
drawn `4m` from step 7, then discarded it at step 8 after visual selection
verification. The controller received the matching live event and returned idle.
The client was 925x520. This was an explicit input test; no decision policy was
connected. Screenshots came from computer-use, while both clicks came from the
repository Windows backend.

## Concealed-kan input calibration (2026-10-15)

In a four-player AI room, absolute seat 2 was offered a concealed `6p` kan.
One UI button click produced `ActionAnGangAddGang` step 35 (type 3, `6p`), followed
by replacement draw `1s` at step 36 and dora indicators `3p` and `9s`. The reader
remained ready without issues. This verifies the single-choice Kan UI at 925x520;
native Kan delivery and multiple-candidate panels remain unverified.
