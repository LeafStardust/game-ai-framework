"""Canonical standard Yaku scoring with four-player and sanma payments.

Exact tiles, winning tile, open/closed melds, wind context and verified event
flags go to MahjongRepository's complete-hand evaluator. No partial-shape Han
is awarded here. Optional local Yaku remain disabled.
"""
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.scores import ScoresCalculator
from mahjong.hand_calculating.hand_config import HandConfig,OptionalRules
from mahjong.meld import Meld
from agents.mahjong_soul.efficiency import INDEX
from games.mahjong_soul.live.runtime.kan import tile_kind
from agents.mahjong_soul.yaku_catalog import catalog

YAKU_BY_ID={y["id"]:y for y in catalog()}

FLAGS={"ippatsu":"is_ippatsu","rinshan":"is_rinshan","chankan":"is_chankan",
       "haitei":"is_haitei","houtei":"is_houtei","double_riichi":"is_daburu_riichi",
       "tenhou":"is_tenhou","chiihou":"is_chiihou","nagashi_mangan":"is_nagashi_mangan"}


def allocate(groups):
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


def score_hand(hand,win,*,melds=(),doras=(),ura=(),seat_wind=0,round_wind=0,riichi=False,tsumo=False,
               context=None,open_tanyao=True,honba=0,riichi_sticks=0,player_count=4,norths=0,tsumo_loss=True):
    """hand excludes the winning tile and includes only concealed tiles."""
    context=context or {}
    if player_count not in (3,4) or type(norths) is not int or not 0<=norths<=4:raise ValueError("Invalid sanma scoring context")
    if player_count==4 and norths:raise ValueError("North extraction is sanma-only")
    if player_count==3 and any(tile_kind(t)[1]=="m" and tile_kind(t)[0] not in "19" for t in list(hand)+[win]+[t for m in melds for t in m["tiles"]]):
        return {"legal":False,"reason":"Removed sanma Man tile"}
    if player_count==3 and any(m["type"]==0 for m in melds):return {"legal":False,"reason":"Chi is unavailable in sanma"}
    def indicator(t):
        # The evaluator uses the four-player Man cycle. 8 Man encodes 9 Man
        # Dora without adding a removed tile to the actual hand.
        kind=tile_kind(t)
        if player_count==3 and kind[1]=="m":
            if kind not in ("1m","9m"):raise ValueError("Removed sanma indicator")
            if kind=="1m":kind="8m"
        return INDEX[kind]*4+1
    if set(context)-set(FLAGS):raise ValueError("Unknown scoring context")
    if any(type(v) is not bool for v in context.values()):raise ValueError("Scoring flags must be bool")
    if seat_wind not in range(4) or round_wind not in range(4):raise ValueError("Invalid Wind context")
    groups=[list(m["tiles"]) for m in melds]+[list(hand),[win]]
    if norths+sum(t=="4z" for g in groups for t in g)>4:return {"legal":False,"reason":"Too many North tiles including extraction"}
    try:
        if len(hand)!=13-3*len(melds):raise ValueError("Concealed hand length does not match melds")
        for m in melds:
            code=m["type"];kinds=sorted(tile_kind(t) for t in m["tiles"])
            if code not in (0,1,2,3) or len(kinds)!=(3 if code in (0,1) else 4):raise ValueError("Invalid meld")
            if code==0:
                if kinds[0][1]=="z" or len({t[1] for t in kinds})!=1 or [int(t[0]) for t in kinds]!=list(range(int(kinds[0][0]),int(kinds[0][0])+3)):raise ValueError("Invalid Chi")
            elif len(set(kinds))!=1:raise ValueError("Invalid triplet/quad")
        allocated=allocate(groups)
    except (ValueError,KeyError) as error:return {"legal":False,"reason":str(error)}
    fixed=[Meld(meld_type={0:Meld.CHI,1:Meld.PON,2:Meld.KAN,3:Meld.KAN}[m["type"]],tiles=t,opened=m["type"]!=3)
           for m,t in zip(melds,allocated)]
    config=HandConfig(is_tsumo=tsumo,is_riichi=riichi,player_wind=27+seat_wind,round_wind=27+round_wind,
                      tsumi_number=honba,kyoutaku_number=riichi_sticks,
                      options=OptionalRules(has_open_tanyao=open_tanyao,has_aka_dora=True),
                      **{arg:context.get(key,False) for key,arg in FLAGS.items()})
    response=HandCalculator.estimate_hand_value([t for g in allocated for t in g],allocated[-1][0],melds=fixed,
                    dora_indicators=[indicator(t) for t in doras],
                    ura_dora_indicators=[indicator(t) for t in ura],config=config)
    if response.error:return {"legal":False,"reason":response.error}
    opened=any(m["type"]!=3 for m in melds);lookup=YAKU_BY_ID
    details=[]
    for y in response.yaku:
        entry=lookup.get(y.yaku_id)
        if entry is None:raise ValueError("Nonstandard Yaku escaped configured evaluator")
        details.append({"key":entry["key"],"name":entry["name"],"han":y.han_open if opened else y.han_closed,
                        "yakuman":y.is_yakuman,"bonus":entry["bonus"]})
    cost=dict(response.cost)
    han=response.han
    if norths and not any(y["yakuman"] for y in details):
        bonus=norths*(1+sum(tile_kind(t)=="3z" for t in doras)+sum(tile_kind(t)=="3z" for t in ura if riichi))
        han+=bonus
        details.append({"key":"north_dora","name":"North Dora","han":bonus,"yakuman":False,"bonus":True})
        cost=dict(ScoresCalculator.calculate_scores(han,response.fu,config))
    if player_count==3 and tsumo and not tsumo_loss:
        missing=cost["additional"]
        split=((missing+199)//200)*100
        cost["main"]+=split;cost["additional"]+=split
    additional_payers=player_count-2
    points=cost["main"]+(additional_payers*cost["additional"] if tsumo else 0)
    bonus_points=cost.get("main_bonus",0)+(additional_payers*cost.get("additional_bonus",0) if tsumo else 0)
    cost["total"]=points+bonus_points+cost.get("kyoutaku_bonus",0)
    yakuman_multiplier=sum(y["han"]//13 for y in details if y["yakuman"])
    basic=response.fu*2**(han+2)
    limit=("yakuman" if yakuman_multiplier else "counted_yakuman" if han>=13 else "sanbaiman" if han>=11 else
           "baiman" if han>=8 else "haneman" if han>=6 else "mangan" if han>=5 or basic>=2000 else "ordinary")
    return {"legal":True,"limit":limit,"points":points,"han":han,"fu":response.fu,"yaku":[y["name"] for y in details],
            "yaku_details":details,"yakuman_multiplier":yakuman_multiplier,
            "bonus_han":sum(y["han"] for y in details if y["bonus"]),"payments":dict(cost),
            "points_with_honba":points+bonus_points,"riichi_sticks":riichi_sticks*1000}


def score_offered_win(board,action):
    """Evaluate a current offered win with event-proven context, never future flags."""
    from agents.mahjong_soul.attack_value import own_player
    own=own_player(board);hand=list(board["self"]["hand"]);tsumo=action["kind"]=="tsumo"
    if tsumo:hand.remove(action["tile"])
    context=dict(board["self"].get("scoring_context",{}).get("win",{}))
    riichi=own["riichi"] in ("accepted","declared")
    if not riichi:context.pop("ippatsu",None);context.pop("double_riichi",None)
    return score_hand(hand,action["tile"],melds=own["melds"],doras=board["dora_indicators"],
             seat_wind=(board["self_seat"]-board["round"]["ju"])%board["player_count"],round_wind=board["round"]["chang"],
             riichi=riichi,tsumo=tsumo,context=context,open_tanyao=board.get("rules",{}).get("open_tanyao") is True,
             honba=board["round"].get("ben",0),riichi_sticks=board["round"].get("liqibang",0),
             player_count=board["player_count"],norths=own.get("norths",0),tsumo_loss=board.get("rules",{}).get("tsumo_loss",True))


def nagashi_eligible(board):
    own=next(p for p in board["players"] if p["is_self"])
    river=own["discards"]
    return bool(river) and all(d.get("called") is False and (tile_kind(d["tile"])[1]=="z" or tile_kind(d["tile"])[0] in "19") for d in river)
