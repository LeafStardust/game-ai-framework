# Reading Mahjong Soul suggestions

Look at `action` first. For example:

```json
{"kind": "discard", "tile": "2z"}
```

This means **discard South wind**. The terminal suggests actions; you perform them manually.

## Tile codes

A tile code is a number followed by its suit letter.

| Ending | Suit | Example |
| --- | --- | --- |
| `m` | Characters / manzu ? numbered tiles with the ? character | `3m` = three of characters |
| `p` | Circles / dots / pinzu | `7p` = seven of circles |
| `s` | Bamboo / souzu ? the one often looks like a bird | `1s` = one of bamboo |
| `z` | Honors: winds and dragons | `2z` = South wind |

### All numbered tiles

| Rank | Characters | Circles / dots | Bamboo |
| --- | --- | --- | --- |
| One | `1m` | `1p` | `1s` |
| Two | `2m` | `2p` | `2s` |
| Three | `3m` | `3p` | `3s` |
| Four | `4m` | `4p` | `4s` |
| Five | `5m` | `5p` | `5s` |
| Six | `6m` | `6p` | `6s` |
| Seven | `7m` | `7p` | `7s` |
| Eight | `8m` | `8p` | `8s` |
| Nine | `9m` | `9p` | `9s` |
| **Red five** | **`0m`** | **`0p`** | **`0s`** |

`0` means a **red five**, not a zero tile. `0p` and `5p` are different physical tiles; follow the exact code in the suggestion. Both count as five of circles when forming sets.

### All honor tiles

| Code | Tile | Common face |
| --- | --- | --- |
| `1z` | East wind | ? |
| `2z` | South wind | ? |
| `3z` | West wind | ? |
| `4z` | North wind | ? |
| `5z` | White dragon | Blank white face in Mahjong Soul |
| `6z` | Green dragon | ? |
| `7z` | Red dragon | ? |

There is no `0z`, `8z` or `9z`. The red dragon (`7z`) is an honor tile; a red five (`0m`, `0p`, `0s`) is a numbered bonus tile.

## Suggested actions

| `action.kind` | Meaning |
| --- | --- |
| `discard` | Discard the exact tile in `action.tile`. |
| `skip` | Decline the current call/win offer using Skip. |
| `chi` | Call the previous player's discard to make a three-tile sequence. |
| `pon` | Call a discard to make three matching tile kinds. |
| `closed_kan` | Declare four matching tiles held in your concealed hand. |
| `open_kan` | Call a discard to combine with three matching tiles in your hand. |
| `added_kan` | Add a fourth matching tile to an existing Pon. |
| `riichi` | Declare Riichi, then discard the specified offered tile. |
| `tsumo` | Claim a win on your own draw. |
| `ron` | Claim a win on another player's tile. |

The current **EfficiencyPolicy** suggests discards, Skip and offered wins. It does not yet choose Chi, Pon, kan or Riichi. Their names are included here because the decision interface supports them.

`combination` strings such as `0p|5p` list exact tiles contributed from your hand. The `|` separates tiles. `called_tile` is the opponent's tile being claimed; `source_seat` is that opponent's absolute seat index, not a screen position.

## Analysis terms

| Field / term | Meaning |
| --- | --- |
| **Shanten** | Distance from a ready hand. Lower is better: `0` = tenpai (ready), `1` = one shanten, and so on. `-1` describes a complete tile structure. It does not by itself prove a legal win with yaku. |
| `analysis.shanten` | Shanten **after the suggested discard**. A value of `4` means four shanten, not four tiles left in your hand. |
| **Tenpai** | A hand whose tile structure can be completed by a winning tile; actual win legality still depends on the rules. |
| **Ukeire** | Unseen copies of tile kinds that improve the hand's shanten. Higher is better when comparing discards with the same shanten. |
| `analysis.ukeire` | Total unseen improving copies after the suggested discard. It is a count, not a percentage. |
| `improving_tiles` | The tile kinds that lower shanten when drawn, with their unseen copy counts. |
| `unseen` | Four copies minus currently visible copies of that tile kind. Unseen tiles may be in opponents' hands or the dead wall; they are not guaranteed to be drawable. |
| **Meld / set** | A sequence, triplet or kan that forms part of the hand. |
| **Yaku** | A qualifying scoring pattern needed to win; tile efficiency alone does not check whether a future hand will have one. |
| **Dora** | Bonus tiles that increase hand value. Dora alone is not a yaku. |

For structural analysis, a red five and ordinary five share one tile kind. Improving tile lists therefore use `5m`, `5p` and `5s` to include the remaining red/ordinary copies together.

### Example

```json
{
  "action": {"kind": "discard", "tile": "2z"},
  "analysis": {
    "shanten": 4,
    "ukeire": 37,
    "improving_tiles": [{"tile": "1m", "unseen": 3}]
  }
}
```

Read this as: **discard South wind; the resulting hand is four shanten with 37 unseen improving copies in total**. The sample improving list above is shortened: its `1m` entry says three unseen copies of one of characters improve the hand.

The policy first minimizes shanten, then maximizes ukeire, then preserves red fives on equal efficiency. It currently does not evaluate opponent danger, hand value or future yaku.

## Other terminal fields

| Field | Meaning |
| --- | --- |
| `kind: "suggestion"` | A newly proposed action for this board. |
| `mode: "shadow"` | Advice only; the program is not playing for you. |
| `executable: false` | The suggestion is not an authorized mouse command. Perform the action manually. |
| `policy` | The policy producing the suggestion, currently `EfficiencyPolicy`. |
| `board_token` | An identifier for the exact game state. You can normally ignore it. |
| `generation` | A reader game-authentication counter used to distinguish game sessions. |
| `step` | Server action sequence number within the round, not your turn count. |
| `version` | Output format version. |
| `round.chang` | Round wind: `0` = East, `1` = South, `2` = West, `3` = North. |
| `round.ju` | Hand number starting at zero: `0` = hand 1, `1` = hand 2, etc. |
| `round.ben` | Honba / continuation counter. |
| `round.liqibang` | Riichi sticks currently on the table. |

For example, `chang: 1, ju: 2, ben: 1` means **South 3 with one honba**.

With `--verbose`, diagnostic statuses may also appear:

| `reason` | Meaning |
| --- | --- |
| `board_already_considered` | A suggestion or decision attempt already occurred for this exact board; waiting for change. |
| `stale_game_capture` | No sufficiently recent game-connection frame; suggestions pause until fresh data arrives. |
| `waiting_for_own_offer` | No action offer for you right now. |
| `waiting_for_game_connection` | Waiting for a captured game connection. |
| `waiting_for_ready_board` | Reader data is not yet complete enough to propose an action. |
| `decision_rejected` | A policy result could not be validated; no action was sent. |
