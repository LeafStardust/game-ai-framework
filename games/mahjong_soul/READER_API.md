# Game reader interface

Run capture and the terminal reader from the Mahjong worktree using
`MahjongSoulCapture.bat --process Jantama_MahjongSoul.exe` and
`MahjongSoulReader.bat` in separate terminals. Capture must begin before game
entry to infer your absolute seat. These tools read traffic and send no game actions.

## Python consumer

```python
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.reader import GameReader

reader = GameReader(LiqiSchema.load("liqi-reference.json"))
# Feed complete JSONL capture rows in recorded order, including control rows.
reader.consume(capture_row)
report = reader.snapshot()
if report["state_ready"]:
    board = report["state"]
    hand = board["hand"]
    operations = board["operations"]
```

`consume(row)` returns diagnostics and the state for that row's connection.
`snapshot()` returns the selected game's state, which is the interface consumers
should use when lobby and game traffic are interleaved. Snapshots are independent
copies; changing them does not change the reader. A single consumer should feed
rows sequentially; the reader is not designed for concurrent mutation.

`state_ready` requires an open selected connection, tracking status, known own
seat, no state issues, and complete visible-tile counts. It is false before a
round, after a round or match ends, after disconnect, and for uncertain state.
It indicates board readiness, not permission to act or that an operation is
available. Check `operations` separately; an empty or absent operation provides
no action opportunity. This reader sends no input.

`state.rules.open_tanyao` is `true`, `false`, or `null` (unknown), decoded from the authenticated room's numeric `GameDetailRule.shiduan` flag. It persists across round resets and is copied into the consumer observation. Reauthentication replaces it; a missing rule is not assumed enabled.

## Report and board fields

| Field | Meaning |
| --- | --- |
| `state` | Board dictionary, or null before any game is selected |
| `game_generation` | Per-connection authentication generation for input identity; increases on each auth reply |
| `game_connection`, `connection_open` | Selected socket identity and current lifecycle |
| `frames`, `actions`, `closed_connections` | Accumulated counters for this reader instance |
| `last_event` | Last selected-game action name and step, or null |
| `decode_errors` | Strict decoding failures, with method and occurrence count |
| `schema_warnings` | Unsupported lobby payloads retained as opaque data |
| `state.status`, `state.issues` | Lifecycle and reasons state cannot be trusted |
| `state.seat`, `state.player_count` | Absolute own seat and three/four-player table size |
| `state.hand`, `state.drawn_tile` | Own tiles and latest own drawn tile |
| `state.discards`, `state.melds`, `state.norths` | Seat-indexed visible board |
| `state.scores`, `state.round`, `state.doras` | Scores, wind/dealer/repeat/sticks, dora indicators |
| `state.turn`, `state.left_tile_count` | Last actor and reported remaining wall |
| `state.operations` | Latest server-provided operation payload; may be null |
| `state.riichi`, `state.furiten` | Tracked declarations and server-provided furiten |
| `state.visible_tile_counts`, `state.visibility_complete` | Normalized visible copies and completeness |

Tile notation uses `m`, `p`, `s`, and `z`; `0m/0p/0s` are red fives. Visible counts
normalize reds to ordinary fives. Opponent concealed hands remain unknown. A
called river tile is counted in its meld only. Unknown snapshot river flags
produce lower-bound counts and block readiness. Concealed kan tile kind is
known while an opponent's red-five composition can remain unknown.

Statuses are `waiting_for_round`, `tracking`, `incomplete`, `round_ended`, and
`match_ended`. A new round or successful restoration can recover incomplete
tracking; cumulative diagnostics remain in the report. A closed game's last
board stays available for display but never reports ready. New authentication
clears the old board before the next round.

For direct byte ingestion, use
`read(connection, content, from_client, is_text=False)` and
`close_connection(connection)` instead of JSONL rows. Keep connection IDs unique
per socket, preserve direction, and deliver closure notifications.

## Validation boundary

Live Steam AI tests verified three/four-player play, chi/pon, concealed kan,
exhaustive draw, score settlements, restart/new-game reset, and match end.
Added/open kan and reconnect restoration are tested offline but remain
unverified live. Special modes are outside the current verified scope.
See [live evidence](LIVE_VALIDATION.md) and [capture commands](README.md).

## Observation adapter

```python
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot

observation = observation_from_snapshot(reader.snapshot())
if observation["ready"]:
    hand = observation["board"]["self"]["hand"]
```

Version 1 observations contain `ready`, `status`, `issues`, `source`, and `board`.
Before any game, `board` is null and status is `waiting_for_game`. Source records
the selected connection, open/closed status, step, and last event. The board
contains the own hand/drawn tile/furiten, seat-indexed public player information,
round, wall, dora, visible counts, and unchanged server `available_operations`.
Missing scores remain null; opponent concealed hands are omitted. Seat indices
remain absolute, with `is_self` identifying the human seat. Unknown operation
codes and combination strings are preserved. Returned objects are independent
copies. The adapter selects no actions, expands no legal-action set, and sends
no commands. The decision pipeline has not been implemented.
