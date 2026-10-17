"""Known-tile yaku routes and conservative tenpai values; no hidden bonuses."""
from collections import Counter
from functools import lru_cache
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig,OptionalRules
from mahjong.meld import Meld
from agents.mahjong_soul.efficiency import counts34,shanten,KINDS,INDEX
from games.mahjong_soul.live.runtime.kan import tile_kind
from games.mahjong_soul.playbook.features import value_honors


def own_player(board):return next(p for p in board["players"] if p["is_self"])


def yaku_routes(board,hand, melds=None):
    melds=own_player(board)["melds"] if melds is None else melds
    tiles=list(hand)+[t for m in melds for t in m["tiles"]]
    counts=Counter(tile_kind(t) for t in tiles)
    opened=any(m["type"]!=3 for m in melds)
    honors=value_honors(board)
    routes={"yakuhai":sum(units for t,units in honors.items() if counts[t]>=3)}
    if tiles and all(t[1]!="z" and 2<=int(tile_kind(t)[0])<=8 for t in tiles):
        if not opened or board.get("rules",{}).get("open_tanyao") is True:routes["tanyao"]=1
    suits={t[1] for t in tiles if t[1]!="z"}
    if len(suits)==1:
        if any(t[1]=="z" for t in tiles):routes["honitsu"]=2 if opened else 3
        else:routes["chinitsu"]=5 if opened else 6
    concealed=Counter(tile_kind(t) for t in hand)
    if len(melds)>=3 and all(m["type"]!=0 for m in melds) and len(concealed)<=2:
        routes["toitoi"]=2
    routes={k:v for k,v in routes.items() if v}
    # These routes describe the retained tiles, not speculative extra han.
    return {"routes":routes,"route_han":sum(routes.values()),"open_yaku":bool(routes),"opened":opened}


def _allocate(groups):
    used=set();result=[]
    for group in groups:
        converted=[]
        for tile in group:
            index=INDEX[tile_kind(tile)]
            offsets=[0] if tile.startswith("0") else ([1,2,3] if index in (4,13,22) else [0,1,2,3])
            candidates=[index*4+n for n in offsets if index*4+n not in used]
            if not candidates:raise ValueError("Impossible exact tile copies")
            value=candidates[0];used.add(value);converted.append(value)
        result.append(converted)
    return result


@lru_cache(maxsize=12000)
def _score(hand,meld_data,win,doras,seat_wind,round_wind,riichi,tsumo,open_tanyao):
    groups=[list(m[1]) for m in meld_data]+[list(hand),[win]]
    try:allocated=_allocate(groups)
    except ValueError:return None
    melds=[Meld(meld_type={0:Meld.CHI,1:Meld.PON,2:Meld.KAN,3:Meld.KAN}[code],tiles=tiles,opened=code!=3)
           for (code,_),tiles in zip(meld_data,allocated)]
    config=HandConfig(is_tsumo=tsumo,is_riichi=riichi,player_wind=27+seat_wind,round_wind=27+round_wind,
                      options=OptionalRules(has_open_tanyao=open_tanyao,has_aka_dora=True))
    indicators=[INDEX[tile_kind(t)]*4+1 for t in doras]
    response=HandCalculator.estimate_hand_value([t for g in allocated for t in g],allocated[-1][0],melds=melds,
                                               dora_indicators=indicators,config=config)
    if response.error:return None
    cost=response.cost
    points=cost["main"]+(2*cost["additional"] if tsumo else 0)
    return {"points":points,"han":response.han,"fu":response.fu,"yaku":[y.name for y in response.yaku]}


def tenpai_value(board,hand,*,discard=None):
    own=own_player(board);melds=own["melds"];fixed=len(melds)
    counts=counts34(hand)
    if shanten(counts,fixed)!=0:return None
    opened=any(m["type"]!=3 for m in melds)
    meld_data=tuple((m["type"],tuple(sorted(m["tiles"]))) for m in melds)
    fixed_counts=Counter(tile_kind(t) for m in melds for t in m["tiles"])
    visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    river={tile_kind(d["tile"]) for d in own["discards"]}
    if discard:river.add(tile_kind(discard))
    wait_data=[]
    seat_wind=(board["self_seat"]-board["round"]["ju"])%4
    round_wind=board["round"]["chang"]
    for index,kind in enumerate(KINDS):
        if counts[index]+fixed_counts[kind]>=4:continue
        trial=list(counts);trial[index]+=1
        if shanten(tuple(trial),fixed)!=-1:continue
        variants=[kind]+(["0"+kind[1]] if kind[0]=="5" and kind[1]!="z" else [])
        values={}
        for mode in ("dama","riichi","tsumo"):
            if mode=="riichi" and opened:continue
            scored=[]
            for tile in variants:
                result=_score(tuple(sorted(hand)),meld_data,tile,tuple(board["dora_indicators"]),seat_wind,round_wind,
                              mode=="riichi" or own["riichi"] in ("declared","accepted"),mode=="tsumo",
                              board.get("rules",{}).get("open_tanyao") is True)
                if result:scored.append(result)
            if scored:
                selected=min(scored,key=lambda x:x["points"])
                values[mode]={**selected,"yaku":list(selected["yaku"])}
        wait_data.append({"tile":kind,"unseen":max(0,4-visible[kind]),"values":values})
    permanent=any(w["tile"] in river for w in wait_data)
    def weighted(mode):
        eligible=[w for w in wait_data if mode in w["values"] and w["unseen"]>0]
        copies=sum(w["unseen"] for w in eligible)
        return (sum(w["unseen"]*w["values"][mode]["points"] for w in eligible)/copies if copies else 0),copies
    dama,dama_ukeire=weighted("dama");riichi,riichi_ukeire=weighted("riichi");tsumo,tsumo_ukeire=weighted("tsumo")
    ron_blocked=permanent or board["self"].get("furiten") is True
    return {"waits":wait_data,"permanent_furiten":permanent,"ron_blocked":ron_blocked,"unseen_waits":sum(w["unseen"] for w in wait_data),
            "dama_points":dama,"dama_ukeire":0 if ron_blocked else dama_ukeire,"riichi_points":riichi,
            "riichi_ukeire":riichi_ukeire,"tsumo_points":tsumo,"tsumo_ukeire":tsumo_ukeire,
            "known_han":max((v["han"] for w in wait_data for v in w["values"].values()),default=0)}



def yaku_potential(board,hand):
    own=own_player(board);melds=own["melds"];opened=any(m["type"]!=3 for m in melds)
    counts=Counter(tile_kind(t) for t in hand+[t for m in melds for t in m["tiles"]])
    potential={}
    for start in range(1,8):
        if all(all(counts[str(n)+suit] for n in range(start,start+3)) for suit in "mps"):
            potential["sanshoku"]=1 if opened else 2
    if any(all(counts[str(n)+suit] for n in range(1,10)) for suit in "mps"):
        potential["ittsu"]=1 if opened else 2
    if not opened and any(all(counts[str(n)+suit]>=2 for n in range(start,start+3)) for suit in "mps" for start in range(1,8)):
        potential["iipeikou"]=1
    if not melds and sum(n>=2 for n in counts.values())>=5:potential["chiitoitsu"]=2
    orphans={"1m","9m","1p","9p","1s","9s"}|{str(n)+"z" for n in range(1,8)}
    if not melds and set(counts)<=orphans and len(counts)>=11:potential["kokushi"]=13
    return potential
