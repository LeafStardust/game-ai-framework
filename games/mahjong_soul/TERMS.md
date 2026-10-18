# Reading Mahjong Soul suggestions

Default terminal output now shows just a readable action, such as **Discard South Wind**. Use `--json` only if you want the detailed fields described below.

In JSON output, look at `action` first. For example:

```json
{"kind": "discard", "tile": "2z"}
```

This means **discard South Wind**. The terminal suggests actions; you perform them manually.

## Tile codes

A tile code is a number followed by its suit letter.

| Ending | Suit | Example |
| --- | --- | --- |
| `m` | Manzu / 萬 Characters | `3m` = Three of Characters |
| `p` | Pinzu / Circles | `7p` = Seven of Circles |
| `s` | Souzu / Bamboo  | `1s` = One of Bamboo |
| `z` | Honors: Winds and Dragons | `2z` = South Wind |

### All numbered tiles

| Rank | Characters | Circles | Bamboo |
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
| **Red Five** | **`0m`** | **`0p`** | **`0s`** |

`0` means a **Red Five**, not a zero tile. `0p` and `5p` are different physical tiles; follow the exact code in the suggestion. Both count as five of circles when forming sets.

### All Honor Tiles

| Code | Tile | Common face |
| --- | --- | --- |
| `1z` | East Wind | Black 東 |
| `2z` | South Wind | Black 南 |
| `3z` | West Wind | Black 西 |
| `4z` | North Wind | Black 北 |
| `5z` | White Dragon | Blank Face |
| `6z` | Green Dragon | Green 發 |
| `7z` | Red Dragon | Red 中 |

There is no `0z`, `8z` or `9z`. The Red Dragon (`7z`) is an Honor Tile; a Red Five (`0m`, `0p`, `0s`) is a numbered bonus tile.

## Suggested actions

| `action.kind` | Meaning |
| --- | --- |
| `discard` | Discard the exact tile in `action.tile`. |
| `skip` | Decline the current call/win offer using Skip. |
| `chi` | Call the previous player's discard to make a three-tile Sequence. |
| `pon` | Call a discard to make three matching tile kinds. |
| `closed_kan` | Declare four matching tiles held in your Concealed Hand. |
| `open_kan` | Call a discard to combine with three matching tiles in your hand. |
| `added_kan` | Add a fourth matching tile to an existing Pon. |
| `riichi` | Declare Riichi, then discard the specified offered tile. |
| `tsumo` | Claim a win on your own draw. |
| `ron` | Claim a win on another player's tile. |

The current **EfficiencyPolicy** suggests discards, server-offered Riichi, Skip and offered wins. It does not yet choose Chi, Pon or Kan. Their names are included here because the decision interface supports them.

`combination` strings such as `0p|5p` list exact tiles contributed from your hand. The `|` separates tiles. `called_tile` is the opponent's tile being claimed; `source_seat` is that opponent's absolute seat index, not a screen position.

## Analysis terms

| Field / term | Meaning |
| --- | --- |
| **Shanten** | Distance from a ready hand. Lower is better: `0` = Tenpai (ready), `1` = one Shanten, and so on. `-1` describes a complete tile structure. It does not by itself prove a legal win with Yaku. |
| `analysis.shanten` | Shanten **after the suggested discard**. A value of `4` means four Shanten, not four tiles left in your hand. |
| **Tenpai** | A hand whose tile structure can be completed by a winning tile; actual win legality still depends on the rules. |
| **Ukeire** | Unseen copies of tile kinds that improve the hand's Shanten. Higher is better when comparing discards with the same Shanten. |
| `analysis.ukeire` | Total unseen improving copies after the suggested discard. It is a count, not a percentage. |
| `improving_tiles` | The tile kinds that lower Shanten when drawn, with their unseen copy counts. |
| `unseen` | Four copies minus currently visible copies of that tile kind. Unseen tiles may be in opponents' hands or the Dead Wall; they are not guaranteed to be drawable. |
| **Meld / set** | A Sequence, Triplet or Kan that forms part of the hand. |
| **Yaku** | A qualifying scoring pattern needed to win; tile efficiency alone does not check whether a future hand will have one. |
| **Dora** | Bonus tiles that increase hand value. Dora alone is not a Yaku. |

For structural analysis, a Red Five and Ordinary Five share one tile kind. Improving tile lists therefore use `5m`, `5p` and `5s` to include the remaining red/ordinary copies together.

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

Read this as: **discard South Wind; the resulting hand is four Shanten with 37 unseen improving copies in total**. The sample improving list above is shortened: its `1m` entry says three unseen copies of one of characters improve the hand.

The policy first minimizes Shanten, then maximizes Ukeire, then preserves Red Fives on equal efficiency. It currently does not evaluate opponent danger, hand value or future Yaku.

## Other terminal fields

| Field | Meaning |
| --- | --- |
| `kind: "suggestion"` | A newly proposed action for this board. |
| `mode: "shadow"` | Advice only; the program is not playing for you. |
| `executable: false` | The suggestion is not an authorized mouse command. Perform the action manually. |
| `policy` | The policy producing the suggestion, currently `EfficiencyPolicy`. |
| `board_token` | An identifier for the exact game state. You can normally ignore it. |
| `generation` | A reader game-authentication counter used to distinguish game sessions. |
| `step` | Server action Sequence number within the round, not your turn count. |
| `version` | Output format version. |
| `round.chang` | Round wind: `0` = East, `1` = South, `2` = West, `3` = North. |
| `round.ju` | Hand number starting at zero: `0` = hand 1, `1` = hand 2, etc. |
| `round.ben` | Honba / continuation counter. |
| `round.liqibang` | Riichi sticks currently on the table. |

For example, `chang: 1, ju: 2, ben: 1` means **South 3 with one Honba**.

With `--verbose`, diagnostic statuses may also appear:

| `reason` | Meaning |
| --- | --- |
| `board_already_considered` | A suggestion or decision attempt already occurred for this exact board; waiting for change. |
| `stale_game_capture` | No sufficiently recent game-connection frame; suggestions pause until fresh data arrives. |
| `waiting_for_own_offer` | No action offer for you right now. |
| `waiting_for_game_connection` | Waiting for a captured game connection. |
| `waiting_for_ready_board` | Reader data is not yet complete enough to propose an action. |
| `decision_rejected` | A policy result could not be validated; no action was sent. |

Readable terminal examples: **Discard 1 Man**, **Discard 2 Pin**, **Discard 3 Sou**, **Discard Red 5 Pin**. **Riichi, then discard 6 Pin** means press the Riichi button and then discard the six of circles. Internal JSON tile codes remain `1m`, `2p`, `3s`, `0p`, etc.

**PlaybookPolicy** adds basic value-aware tie-breaks and defense. A **Genbutsu** tile is a tile kind already discarded by the specific threatening opponent; it is not a blanket safety claim against all players. **Fold Mode** prioritizes available known-safe evidence when the hand is far from ready. The balanced playbook can decline Riichi while an opponent is threatening Riichi.
