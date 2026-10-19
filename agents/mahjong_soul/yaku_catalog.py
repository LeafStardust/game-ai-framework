"""Standard four-player Yaku metadata; engine conditions are the single authority."""
from mahjong.hand_calculating.yaku_config import YakuConfig

# These optional/local variants are not standard Mahjong Soul Yaku.
LOCAL={"open_riichi","daburu_open_riichi","renhou","renhou_yakuman","daisharin","daichisei","sashikomi","paarenchan"}
BONUS={"dora","aka_dora","ura_dora"}
SITUATIONAL={"tsumo","riichi","ippatsu","chankan","rinshan","haitei","houtei","daburu_riichi","tenhou","chiihou","nagashi_mangan"}
CONDITIONS={
 "tsumo":"Closed hand won by self-draw.","riichi":"Legal closed-hand Riichi declaration.",
 "ippatsu":"Riichi win within the uninterrupted first turn after declaration.",
 "chankan":"Win by robbing a Kan.","rinshan":"Self-draw win on a Kan replacement tile.",
 "haitei":"Self-draw win on the last live-wall tile; not a Kan replacement.",
 "houtei":"Ron on the discard after the last live-wall draw.",
 "daburu_riichi":"Riichi on the first discard before any interrupting call.",
 "nagashi_mangan":"Exhaustive-draw award: every own discard is an uncalled terminal or honor.",
 "pinfu":"Closed four-sequence hand, non-value pair and two-sided winning wait.",
 "tanyao":"Only suited ranks 2 through 8; open form requires Kuitan.",
 "iipeiko":"Closed hand containing two identical sequences.",
 "sanshoku":"Same sequence ranks in all three suits.","ittsu":"123, 456 and 789 sequences in one suit.",
 "chantai":"Every group and pair contains a terminal or honor; at least one sequence and honor.",
 "honroto":"Only terminals and honors; triplet or seven-pairs form.",
 "toitoi":"Four triplets/quads and a pair.","sanankou":"Three concealed triplets/quads; Ron-completed triplet is not concealed.",
 "sankantsu":"Three declared quads.","sanshoku_douko":"Same-rank triplets/quads in all three suits.",
 "chiitoitsu":"Seven distinct pairs; a quad is not two pairs.",
 "shosangen":"Two Dragon triplets/quads and a pair of the third Dragon.",
 "honitsu":"Exactly one suit plus honors.","junchan":"Every group and pair contains a suited terminal; at least one sequence; no honors.",
 "ryanpeiko":"Closed four-sequence hand with two pairs of identical sequences.","chinitsu":"Exactly one suit, no honors.",
 "kokushi":"One of each of the thirteen terminal/honor kinds and one duplicate.",
 "daburu_kokushi":"Kokushi won from the thirteen-sided wait.",
 "chuuren_poutou":"Closed 1112345678999 plus one extra tile, all in one suit.",
 "daburu_chuuren_poutou":"Nine Gates won from the pure nine-sided wait.",
 "suuankou":"Four concealed triplets/quads, usually completed by self-draw.",
 "suuankou_tanki":"Four concealed triplets/quads won on the pair wait.",
 "daisangen":"Triplet/quad of every Dragon.","shosuushi":"Three Wind triplets/quads and a pair of the fourth Wind.",
 "daisuushi":"Triplet/quad of all four Winds.","ryuisou":"Only 2,3,4,6,8 Sou and Green Dragon.",
 "suukantsu":"Four declared quads.","tsuisou":"Only honors.","chinroto":"Only suited terminals.",
 "tenhou":"Dealer wins on the initial dealt hand.","chiihou":"Non-dealer wins on the first draw before any interrupting call.",
 "dora":"Indicator-derived bonus Han; cannot supply the required Yaku.",
 "aka_dora":"Red Five bonus Han; cannot supply the required Yaku.",
 "ura_dora":"Revealed Ura indicators after Riichi; never assume hidden indicators."
}


def catalog():
    entries=[]
    for key,yaku in vars(YakuConfig()).items():
        if key in LOCAL:continue
        condition=CONDITIONS.get(key)
        if key in {"haku","hatsu","chun"}:condition="Triplet/quad of the corresponding Dragon."
        if key.startswith("seat_wind_"):condition="Triplet/quad of the player's current seat Wind."
        if key.startswith("round_wind_"):condition="Triplet/quad of the current round Wind."
        if condition is None:raise ValueError("Missing Yaku condition: "+key)
        entries.append({"key":key,"id":yaku.yaku_id,"name":yaku.name,"closed_han":yaku.han_closed,
                        "open_han":yaku.han_open,"yakuman":yaku.is_yakuman,"bonus":key in BONUS,
                        "category":"bonus" if key in BONUS else "situational" if key in SITUATIONAL else "shape",
                        "condition":condition})
    return entries
