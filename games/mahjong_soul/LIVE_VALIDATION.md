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

## Combined Chi/Pon UI calibration (2026-10-15)

A combined Chi/Pon offer at own seat 2 showed a shifted Chi button, followed by
Pon and Skip. Clicking Chi on `7s|8s` produced live `7s/8s/9s` Chi at step 43
with contributions from seats `2/2/1`. The alternate Pon combination was `9s|9s`.
Only the Chi button was clicked; the other two positions were visually mapped.
The client remained 925x520 and clicks used computer-use.

## Tsumo UI calibration (2026-10-15)

The own seat-2 prompt offered operations `[1, 8]` (discard and tsumo). Clicking
Tsumo produced live `ActionHule` step 83 with own `zimo=true`, winning tile `9p`,
and scores 22,600 / 27,100 / 38,000 / 12,300. This verifies the Tsumo button at
925x520 through computer-use; native win clicks and live Ron remain unverified.

## Native Ron input (2026-10-15)

A Ron-only offer at own absolute seat 2 followed seat 3's `7m` discard at step
87. The repository's native WindowsMouse backend clicked the calibrated Ron
button through InputController. Live ActionHule step 88 confirmed own
`zimo=false`, winning tile `7m`, and final scores
22,600 / 27,100 / 39,800 / 10,500. The controller returned idle with one attempt.
The client was 925x520. This validates ordinary-discard native Ron; robbing kan
and combined Ron offers remain unverified.

## Open-kan UI calibration (2026-10-15)

A combined Pon/Kan offer (types 3 and 5) followed seat 1's `2p` discard at step
113. One Kan click produced own seat-2 open kan at step 114: four `2p` with
sources `2/2/2/1`. Replacement draw `7s` followed at step 115. This verifies
the single-choice combined Pon/Kan layout at 925x520 through computer-use.
Native open-kan delivery and multiple-choice kan panels remain unverified.

## Added-kan UI calibration (2026-10-15)

An own seat-1 `[1, 6]` offer contained `9s|9s|9s|9s` while the existing own Pon
contained three `9s`. A single Kan click produced added-kan event type 2 at
step 33, followed by replacement draw `8m` at step 34. The reader remained ready
without issues. The UI was 925x520 and clicks used computer-use; native added-kan
delivery and multi-candidate selection remain unverified.

## Native fullscreen discard (2026-10-15)

The game was already fullscreen at 1920x1080. The 14-tile own-draw layout was
compared with the 925x520 windowed calibration and given explicit fullscreen
coordinates. Native selection raised the separated `3z` tile, verified by a
screenshot. Native confirmation produced live discard step 4 and returned the
controller idle. Both clicks used WindowsMouse, with InputController retaining
the pending action across visual inspection. The game stayed fullscreen.

Only this hand layout is live-verified at fullscreen size. Other action buttons,
choice panels, maximized sizes, and other resolutions remain unverified.

## Fullscreen Chi menu (2026-10-15)

During agent-driven AI-room calibration, a Chi-only offer at 1920x1080 opened
a two-choice panel (`4p|5p`, `5p|7p`). Clicking the second choice produced own
seat-1 Chi at step 27, tiles `5p/7p/6p`, sources `1/1/0`. Both menu opening and
choice selection used computer-use. The reader reported no issues.

## Native fullscreen Skip (2026-10-15)

After continued autonomous AI-room play, a Chi-only offer at step 50 was skipped
using WindowsMouse and the shared controller at 1920x1080. The cancellation
request and matching successful response (request 930) confirmed the action,
returning the controller to idle after one attempt. Eleven-tile post-call and
own-draw layouts were also exercised through computer-use discards.

## Native fullscreen open kan (2026-10-15)

During autonomous AI-room play, a combined Pon/Kan offer produced own seat-1
open `4p` kan at step 57, sources `1/1/1/3`, through the repository's native
backend and shared controller. Exact confirmation returned idle after one
attempt. A replacement draw followed; the subsequent eight-tile draw layout
was exercised via a computer-use discard. The client remained 1920x1080.

## Native fullscreen Chi and post-call restrictions (2026-10-15)

A single-choice Chi on `5m` used WindowsMouse and InputController at 1920x1080.
Own seat-1 `3m/4m/5m` Chi was confirmed at step 66, sources `1/1/0`. The next
discard operation prohibited `2m` and `5m`; the UI greyed out `2m`. An allowed
`1s` discard continued calibration. The input planner now enforces these
restrictions before sending any click.
