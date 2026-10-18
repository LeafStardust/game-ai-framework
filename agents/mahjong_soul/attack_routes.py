"""Reachable offensive targets, not promised Han or hidden-tile expectations."""
from collections import Counter
from agents.mahjong_soul.attack_value import own_player
from games.mahjong_soul.live.runtime.kan import tile_kind
from games.mahjong_soul.playbook.features import value_honors,dora_kind


def known_bonus(board,hand):
    doras=Counter(dora_kind(t,board["player_count"]) for t in board["dora_indicators"])
    all_tiles=list(hand)+[t for m in own_player(board)["melds"] for t in m["tiles"]]
    return sum(doras[tile_kind(t)]+int(t.startswith("0")) for t in all_tiles)


def project_attack(board,hand,bonus=0):
    own=own_player(board);melds=own["melds"]
    opened=any(m["type"]!=3 for m in melds)
    kinds=[tile_kind(t) for t in hand]
    fixed=[tile_kind(t) for m in melds for t in m["tiles"]]
    counts=Counter(kinds+fixed);concealed=Counter(kinds)
    visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    honors=value_honors(board)
    secured=sum(units for t,units in honors.items() if counts[t]>=3)
    room=max(0,4-len(melds)-sum(n>=3 for n in concealed.values()))
    pairs=sorted(((t,units) for t,units in honors.items() if concealed[t]==2 and visible[t]<4),
                 key=lambda item:(-item[1],item[0]))[:room]
    targets=[]
    def add(name,han,cost,open_route=True,future_riichi=True,compatible=None):
        if han<=0:return
        # Future Riichi is explicitly projected only for a closed hand. It is
        # never presented as scored/secured Han or added to open-hand targets.
        route_bonus=bonus if compatible is None else min(bonus,known_bonus(board,[t for t in hand if compatible(tile_kind(t))]))
        targets.append({"target_route":name,"target_yaku_han":han,
                        "projected_han":han+route_bonus+(0 if opened or not future_riichi else 1),
                        "route_cost":cost,"open_route":open_route})
    if secured:add("yakuhai",secured,0)
    if pairs:add("yakuhai",secured+sum(units for _,units in pairs),len(pairs))
    if not opened:add("riichi",1,0,False,False)
    simple=lambda t:t[1]!="z" and 2<=int(t[0])<=8
    if (not opened or board.get("rules",{}).get("open_tanyao") is True) and all(simple(t) for t in fixed):
        outsiders=sum(not simple(t) for t in kinds)
        if outsiders<=3:add("tanyao",1,outsiders,compatible=simple)
    for suit in "mps":
        if all(t[1] in (suit,"z") for t in fixed):
            suit_count=sum(t[1]==suit for t in kinds+fixed)
            outsiders=sum(t[1] not in (suit,"z") for t in kinds)
            if suit_count>=6 and outsiders<=4:
                add("honitsu",(2 if opened else 3)+secured+sum(u for _,u in pairs),outsiders+len(pairs),compatible=lambda t:t[1] in (suit,"z"))
        if all(t[1]==suit for t in fixed):
            outsiders=sum(t[1]!=suit for t in kinds)
            if sum(t[1]==suit for t in kinds+fixed)>=8 and outsiders<=3:
                add("chinitsu",5 if opened else 6,outsiders,compatible=lambda t:t[1]==suit)
    if all(m["type"]!=0 for m in melds):
        pairs_ready=sum(n>=2 for n in concealed.values())+len(melds)
        if pairs_ready>=3:
            # Do not chase a pair-to-triplet conversion when all copies are
            # visible; a remaining pair can still be the final head.
            convertible=sum(n>=3 or n==2 and visible[t]<4 for t,n in concealed.items())+len(melds)
            if convertible>=3:
                add("toitoi",2+secured+sum(u for _,u in pairs),max(0,4-convertible)+sum(n==2 for n in concealed.values())*.5)
    if not melds:
        n_pairs=sum(n>=2 for n in concealed.values())
        if n_pairs>=4:add("chiitoitsu",2,max(0,7-n_pairs),False)
    # A target with fewer tile replacements is more credible than an equally
    # valuable remote shape. This is a planning heuristic, not an EV model.
    if not targets:return {"target_route":None,"target_yaku_han":0,"projected_han":bonus,"route_cost":99,"open_route":False}
    return max(targets,key=lambda r:(r["projected_han"]-r["route_cost"]*.6,-r["route_cost"],r["target_route"]))
