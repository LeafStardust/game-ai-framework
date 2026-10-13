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

## Limits

One later `.lq.Lobby.fetchAccountActivityData` response failed typed decoding:
`lq.ActivityShootData.level` is length-delimited on the current server, while
this reference schema declares a scalar uint32. Its original frame and decoding
error were retained. This was a lobby connection and did not interrupt game
state reconstruction. The reference JSON has not been altered to guess its new
meaning.

This test does not verify four-player play, concealed/added kan, reconnect
snapshots, special modes, or action execution. Kan and reconnect handling remain
covered by offline tests. No agent decisions or automatic game actions were sent.
