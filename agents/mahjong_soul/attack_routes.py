"""Reachable offensive targets, not promised Han or hidden-tile expectations."""
from collections import Counter
from functools import lru_cache
from agents.mahjong_soul.efficiency import KINDS,counts34
from agents.mahjong_soul.attack_value import own_player
from games.mahjong_soul.live.runtime.kan import tile_kind
from games.mahjong_soul.playbook.features import value_honors,dora_kind


def known_bonus(board,hand):
    doras=Counter(dora_kind(t,board["player_count"]) for t in board["dora_indicators"])
    all_tiles=list(hand)+[t for m in own_player(board)["melds"] for t in m["tiles"]]
    return sum(doras[tile_kind(t)]+int(t.startswith("0")) for t in all_tiles)


def project_attack(board,hand,bonus=0,*,all_targets=False):
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
    from agents.mahjong_soul.yakuman import yakuman_targets
    targets=yakuman_targets(board,hand)
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
    if all_targets:return targets
    if not targets:return {"target_route":None,"target_yaku_han":0,"projected_han":bonus,"route_cost":99,"open_route":False}
    return max(targets,key=lambda r:(r["projected_han"]-r["route_cost"]*.6,-r["route_cost"],r["target_route"]))


@lru_cache(maxsize=12000)
def _toitoi_distance(counts,fixed):
    """Missing draws minus one for four distinct triplets and a distinct pair."""
    available=[i for i,t in enumerate(KINDS) if t not in fixed]
    needed=4-len(fixed)
    return min(max(0,2-counts[head])+sum(sorted(max(0,3-counts[i])
               for i in available if i!=head)[:needed])-1 for head in available)


def toitoi_progress(board,hand):
    """Count only draws that advance the all-triplets winning shape."""
    melds=own_player(board)["melds"]
    if any(m["type"]==0 for m in melds):raise ValueError("Chi cannot form Toitoi")
    fixed=tuple(sorted(tile_kind(m["tiles"][0]) for m in melds))
    counts=list(counts34(hand));distance=_toitoi_distance(tuple(counts),fixed)
    visible=Counter()
    for tile,n in board["visible_tile_counts"].items():visible[tile_kind(tile)]+=n
    improving=[]
    for i,tile in enumerate(KINDS):
        unseen=max(0,4-visible[tile])
        if not unseen or counts[i]>=4 or tile in fixed:continue
        counts[i]+=1
        if _toitoi_distance(tuple(counts),fixed)<distance:
            improving.append({"tile":tile,"unseen":unseen})
        counts[i]-=1
    return distance,improving


@lru_cache(maxsize=50000)
def _regular_distance(counts,fixed):
    """Standard shape distance with explicit fixed melds and missing tiles.

    Unlike length-inferred library Shanten, route-incompatible tiles may be
    removed without accidentally treating their empty slots as open melds.
    """
    def search(values,melds,tatsu,pair):
        i=next((i for i,n in enumerate(values) if n),None)
        if i is None:return 8-2*(fixed+melds)-min(tatsu,4-fixed-melds)-pair
        best=8
        def take(indices,dm=0,dt=0,dp=0):
            nonlocal best
            new=list(values)
            for j in indices:new[j]-=1
            best=min(best,search(tuple(new),melds+dm,tatsu+dt,pair+dp))
        take([i])
        if melds+fixed<4:
            if values[i]>=3:take([i]*3,dm=1)
            if i<27 and i%9<=6 and values[i+1] and values[i+2]:take([i,i+1,i+2],dm=1)
        if values[i]>=2:
            if not pair:take([i,i],dp=1)
            if tatsu<4-fixed-melds:take([i,i],dt=1)
        if tatsu<4-fixed-melds and i<27:
            if i%9<=7 and values[i+1]:take([i,i+1],dt=1)
            if i%9<=6 and values[i+2]:take([i,i+2],dt=1)
        return best
    return search(counts,0,0,0)


def route_progress(board,hand,target):
    """Measure only shape development compatible with the selected open Yaku."""
    route=target["target_route"]
    if route in ("yakuman_kokushi","yakuman_nine_gates"):
        from agents.mahjong_soul.yakuman import ORPHANS
        counts=Counter(tile_kind(t) for t in hand)
        def special_distance(values):
            if route=="yakuman_kokushi":return 13-sum(values[t]>0 for t in ORPHANS)-int(any(values[t]>=2 for t in ORPHANS))
            base={str(n)+target["yakuman_suit"]:(3 if n in (1,9) else 1) for n in range(1,10)}
            retained=sum(min(values[t],n) for t,n in base.items())+int(any(values[t]>n for t,n in base.items()))
            return 13-retained
        distance=special_distance(counts);visible=Counter()
        for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
        improving=[]
        for tile in KINDS:
            if visible[tile]>=4:continue
            trial=counts.copy();trial[tile]+=1
            if special_distance(trial)<distance:improving.append({"tile":tile,"unseen":4-visible[tile]})
        return distance,improving
    if route=="toitoi":return toitoi_progress(board,hand)
    melds=own_player(board)["melds"];fixed=len(melds)
    counts=counts34(hand);visible=Counter()
    for tile,n in board["visible_tile_counts"].items():visible[tile_kind(tile)]+=n
    if route in ("honitsu","chinitsu"):
        all_tiles=hand+[t for m in melds for t in m["tiles"]]
        suits=[s for s in "mps" if all(tile_kind(t)[1] in ((s,"z") if route=="honitsu" else (s,)) for m in melds for t in m["tiles"])]
        suit=max(suits,key=lambda s:sum(tile_kind(t)[1]==s for t in all_tiles))
        allowed=lambda t:t[1]==suit or route=="honitsu" and t[1]=="z"
    elif route=="yakuman_all_honors":allowed=lambda t:t[1]=="z"
    elif route=="yakuman_all_terminals":allowed=lambda t:t[1]!="z" and t[0] in "19"
    elif route=="yakuman_all_green":
        from agents.mahjong_soul.yakuman import GREEN
        allowed=lambda t:t in GREEN
    elif route=="tanyao":allowed=lambda t:t[1]!="z" and 2<=int(t[0])<=8
    else:allowed=lambda t:True
    def distance(values):
        filtered=tuple(n if allowed(t) else 0 for t,n in zip(KINDS,values))
        if route=="yakuhai":
            choices=[]
            for t in value_honors(board):
                i=KINDS.index(t)
                if values[i]<2 or visible[t]>=4:continue
                remaining=list(filtered);missing=max(0,3-remaining[i]);remaining[i]=max(0,remaining[i]-3)
                choices.append(_regular_distance(tuple(remaining),fixed+1)+missing)
            return min(choices,default=8)
        return _regular_distance(filtered,fixed)
    baseline=distance(counts);improving=[]
    for i,tile in enumerate(KINDS):
        unseen=max(0,4-visible[tile])
        if not unseen or counts[i]>=4 or not allowed(tile):continue
        draw=list(counts);draw[i]+=1
        if distance(tuple(draw))<baseline:improving.append({"tile":tile,"unseen":unseen})
    return baseline,improving
