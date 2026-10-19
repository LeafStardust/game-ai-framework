# Standard Four-Player Yaku and Scoring

The agent uses `agents/mahjong_soul/scoring.py` as its complete-hand authority. It wraps the pinned `mahjong==2.0.0` evaluator and supplies exact tiles, the winning tile, meld openness, Winds, indicators and verified event context. The table is backed by `yaku_catalog.py`; every entry has a positive complete-hand regression.

## Conditions and values

A dash means the Yaku is unavailable with an open hand. Yakuman hands are labeled Yakuman. Wind variants are listed separately to make seat/round stacking explicit.

| Key | Yaku | Japanese | Open | Closed | Condition |
|---|---|---|---:|---:|---|
| `tsumo` | Menzen Tsumo | 門前清自摸和 | - | 1 Han | Closed hand won by self-draw. |
| `riichi` | Riichi | 立直 | - | 1 Han | Legal closed-hand Riichi declaration. |
| `ippatsu` | Ippatsu | 一発 | - | 1 Han | Riichi win within the uninterrupted first turn after declaration. |
| `chankan` | Chankan | 槍槓 | 1 Han | 1 Han | Win by robbing a Kan. |
| `rinshan` | Rinshan Kaihou | 嶺上開花 | 1 Han | 1 Han | Self-draw win on a Kan replacement tile. |
| `haitei` | Haitei Raoyue | 海底摸月 | 1 Han | 1 Han | Self-draw win on the last live-wall tile; not a Kan replacement. |
| `houtei` | Houtei Raoyui | 河底撈魚 | 1 Han | 1 Han | Ron on the discard after the last live-wall draw. |
| `daburu_riichi` | Double Riichi | ダブル立直 | - | 2 Han | Riichi on the first discard before any interrupting call. |
| `nagashi_mangan` | Nagashi Mangan | 流し満貫 | 5 Han | 5 Han | Exhaustive-draw award: every own discard is an uncalled terminal or honor. |
| `pinfu` | Pinfu | 平和 | - | 1 Han | Closed four-sequence hand, non-value pair and two-sided winning wait. |
| `tanyao` | Tanyao | 断么九 | 1 Han | 1 Han | Only suited ranks 2 through 8; open form requires Kuitan. |
| `iipeiko` | Iipeiko | 一盃口 | - | 1 Han | Closed hand containing two identical sequences. |
| `haku` | Yakuhai (haku) | 役牌・白 | 1 Han | 1 Han | Triplet/quad of the corresponding Dragon. |
| `hatsu` | Yakuhai (hatsu) | 役牌・發 | 1 Han | 1 Han | Triplet/quad of the corresponding Dragon. |
| `chun` | Yakuhai (chun) | 役牌・中 | 1 Han | 1 Han | Triplet/quad of the corresponding Dragon. |
| `seat_wind_east` | Yakuhai (seat wind east) | 自風牌・東 | 1 Han | 1 Han | Triplet/quad of the player's current seat Wind. |
| `seat_wind_south` | Yakuhai (seat wind south) | 自風牌・南 | 1 Han | 1 Han | Triplet/quad of the player's current seat Wind. |
| `seat_wind_west` | Yakuhai (seat wind west) | 自風牌・西 | 1 Han | 1 Han | Triplet/quad of the player's current seat Wind. |
| `seat_wind_north` | Yakuhai (seat wind north) | 自風牌・北 | 1 Han | 1 Han | Triplet/quad of the player's current seat Wind. |
| `round_wind_east` | Yakuhai (round wind east) | 場風牌・東 | 1 Han | 1 Han | Triplet/quad of the current round Wind. |
| `round_wind_south` | Yakuhai (round wind south) | 場風牌・南 | 1 Han | 1 Han | Triplet/quad of the current round Wind. |
| `round_wind_west` | Yakuhai (round wind west) | 場風牌・西 | 1 Han | 1 Han | Triplet/quad of the current round Wind. |
| `round_wind_north` | Yakuhai (round wind north) | 場風牌・北 | 1 Han | 1 Han | Triplet/quad of the current round Wind. |
| `sanshoku` | Sanshoku Doujun | 三色同順 | 1 Han | 2 Han | Same sequence ranks in all three suits. |
| `ittsu` | Ittsu | 一気通貫 | 1 Han | 2 Han | 123, 456 and 789 sequences in one suit. |
| `chantai` | Chantai | 混全帯么九 | 1 Han | 2 Han | Every group and pair contains a terminal or honor; at least one sequence and honor. |
| `honroto` | Honroutou | 混老頭 | 2 Han | 2 Han | Only terminals and honors; triplet or seven-pairs form. |
| `toitoi` | Toitoi | 対々和 | 2 Han | 2 Han | Four triplets/quads and a pair. |
| `sanankou` | San Ankou | 三暗刻 | 2 Han | 2 Han | Three concealed triplets/quads; Ron-completed triplet is not concealed. |
| `sankantsu` | San Kantsu | 三槓子 | 2 Han | 2 Han | Three declared quads. |
| `sanshoku_douko` | Sanshoku Doukou | 三色同刻 | 2 Han | 2 Han | Same-rank triplets/quads in all three suits. |
| `chiitoitsu` | Chiitoitsu | 七対子 | - | 2 Han | Seven distinct pairs; a quad is not two pairs. |
| `shosangen` | Shou Sangen | 小三元 | 2 Han | 2 Han | Two Dragon triplets/quads and a pair of the third Dragon. |
| `honitsu` | Honitsu | 混一色 | 2 Han | 3 Han | Exactly one suit plus honors. |
| `junchan` | Junchan | 純全帯么九 | 2 Han | 3 Han | Every group and pair contains a suited terminal; at least one sequence; no honors. |
| `ryanpeiko` | Ryanpeikou | 二盃口 | - | 3 Han | Closed four-sequence hand with two pairs of identical sequences. |
| `chinitsu` | Chinitsu | 清一色 | 5 Han | 6 Han | Exactly one suit, no honors. |
| `kokushi` | Kokushi Musou | 国士無双 | - | Yakuman | One of each of the thirteen terminal/honor kinds and one duplicate. |
| `chuuren_poutou` | Chuuren Poutou | 九蓮宝燈 | - | Yakuman | Closed 1112345678999 plus one extra tile, all in one suit. |
| `suuankou` | Suu Ankou | 四暗刻 | - | Yakuman | Four concealed triplets/quads, usually completed by self-draw. |
| `daisangen` | Daisangen | 大三元 | Yakuman | Yakuman | Triplet/quad of every Dragon. |
| `shosuushi` | Shousuushii | 小四喜 | Yakuman | Yakuman | Three Wind triplets/quads and a pair of the fourth Wind. |
| `ryuisou` | Ryuuiisou | 緑一色 | Yakuman | Yakuman | Only 2,3,4,6,8 Sou and Green Dragon. |
| `suukantsu` | Suu Kantsu | 四槓子 | Yakuman | Yakuman | Four declared quads. |
| `tsuisou` | Tsuu Iisou | 字一色 | Yakuman | Yakuman | Only honors. |
| `chinroto` | Chinroutou | 清老頭 | Yakuman | Yakuman | Only suited terminals. |
| `daisuushi` | Dai Suushii | 大四喜 | Yakuman | Yakuman | Triplet/quad of all four Winds. |
| `daburu_kokushi` | Kokushi Musou Juusanmen Matchi | 国士無双十三面待ち | - | Yakuman | Kokushi won from the thirteen-sided wait. |
| `suuankou_tanki` | Suu Ankou Tanki | 四暗刻単騎 | - | Yakuman | Four concealed triplets/quads won on the pair wait. |
| `daburu_chuuren_poutou` | Daburu Chuuren Poutou | 純正九蓮宝燈 | - | Yakuman | Nine Gates won from the pure nine-sided wait. |
| `tenhou` | Tenhou | 天和 | - | Yakuman | Dealer wins on the initial dealt hand. |
| `chiihou` | Chiihou | 地和 | - | Yakuman | Non-dealer wins on the first draw before any interrupting call. |
| `dora` | Dora | ドラ | 1 Han | 1 Han | Indicator-derived bonus Han; cannot supply the required Yaku. |
| `aka_dora` | Aka Dora | 赤ドラ | 1 Han | 1 Han | Red Five bonus Han; cannot supply the required Yaku. |
| `ura_dora` | Ura Dora | 裏ドラ | - | 1 Han | Revealed Ura indicators after Riichi; never assume hidden indicators. |

## Exact value, stacking and legal wins

The scorer chooses a legal scoring decomposition and returns Han, Fu, each applied Yaku, separate bonus Han, Ron/Tsumo payments, Honba and Riichi-stick awards. It applies open/closed Han reductions, mutually exclusive Yaku and stacked/double Yakuman. Counted Yakuman is a score limit, not an extra shape Yaku. Dora, Red Fives and Ura Dora never satisfy the required Yaku by themselves. Ura indicators are counted only if explicitly supplied after Riichi; hidden Ura and future Ippatsu are never invented.

Ordinary score limits are Mangan, Haneman, Baiman, Sanbaiman and Counted Yakuman. The configured standard profile allows open Tanyao when confirmed by the room, Red Fives and double/stacked Yakuman, uses no Kiriage, and caps counted hands at one Yakuman. Optional local Yaku such as Open Riichi, Renhou and Daisharin are excluded. Different event-room/local-rule formats require a separate explicit rules profile.

## Development and capture context

Normal structural targets cover Riichi, Tanyao, Yakuhai, Pinfu, Iipeikou, Ryanpeikou, both Sanshoku forms, Ittsu, Chanta, Junchan, Toitoi, Sanankou, Shousangen, Honroutou (triplet and Seven Pairs forms), Chiitoitsu and both flushes. Required groups and pairs reserve disjoint tiles. Fixed open groups cannot supply concealed-only patterns. Three Quads is credited only after the quads actually exist; the agent does not assume it will draw new quads. Target Han is still a partial-hand estimate; the complete-hand scorer supersedes it at Tenpai.

The reader tracks Double Riichi, Ippatsu, Kan replacement draws, robbed Kan, last draws/discards and uninterrupted first turns. A reconnect with incomplete history does not invent event bonuses. Robbed-Kan Ron requires the captured Kan source, exact tile and matching live offer. The dealer initial 14-tile hand can identify a Tenhou offer. Nagashi eligibility is a river condition, not permission to claim a normal incomplete hand.

All standard Yakuman are recognized by complete-hand scoring, including Four Concealed Triplets, Three Big Dragons, Four Winds and Four Quads. Deliberate Yakuman pursuit remains subject to the existing opening-only 10-tile gate and its supported target set; complete scoring coverage is not a claim of equally developed search for every Yakuman. Situation Yaku are not freely added to a future hand just to advertise more Han.

## Validation and scope

Regression cases cover every table entry, open/closed reductions, illegal and Dora-only hands, Fu/payments, counted versus actual Yakuman, simultaneous Yakuman, contextual exclusivity, first-turn wins and robbed-Kan offers. This establishes winning-condition/scoring coverage; it does not establish a win rate or replace a full expected-value search. Terminal output remains the recommended action. Detailed scoring is recorded in `win_value` and per-wait analysis.

References: [MahjongRepository evaluator](https://github.com/MahjongRepository/mahjong), [configuration documentation](https://mahjongrepository.github.io/mahjong/modules/hand_calculating/hand_config.html). The user-provided Yaku reference was used as the requested standard-Yaku scope.
