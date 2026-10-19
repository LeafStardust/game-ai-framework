"""Threshold-gated Yakuman plans with visible-copy and remaining-draw checks."""
from itertools import combinations_with_replacement
from collections import Counter
from games.mahjong_soul.live.runtime.kan import tile_kind

ORPHANS={str(n)+s for s in "mps" for n in (1,9)}|{str(n)+"z" for n in range(1,8)}
GREEN={"2s","3s","4s","6s","8s","6z"}


def yakuman_targets(board,hand):
    opening=board["self"].get("opening_hand",[])
    counts=Counter(tile_kind(t) for t in opening);melds=next(p for p in board["players"] if p["is_self"])["melds"]
    fixed=[tile_kind(t) for m in melds for t in m["tiles"]];current=[tile_kind(t) for t in hand]
    live=Counter(tile_kind(t) for t in board["self"]["hand"]);live.update(fixed)
    visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    targets=[]
    def matches(values,name,suit):
        if name=="kokushi":return sum(values[t]>0 for t in ORPHANS)+int(any(values[t]>=2 for t in ORPHANS))
        if name=="nine_gates":
            base={str(n)+suit:(3 if n in (1,9) else 1) for n in range(1,10)}
            return sum(min(values[t],n) for t,n in base.items())+int(any(values[t]>n for t,n in base.items()))
        allowed={"all_honors":lambda t:t[1]=="z","all_terminals":lambda t:t[1]!="z" and t[0] in "19","all_green":lambda t:t in GREEN}[name]
        # A fourth copy in a quad does not fill an additional hand slot.
        return sum(min(n,3) for t,n in values.items() if allowed(t))
    def add(name,matched,allowed,closed=False,suit=None):
        current_matches=matches(live,name,suit)
        if max(matched,current_matches)<10 or closed and melds or not all(allowed(t) for t in fixed):return
        needed=_minimum_draws(name,suit,Counter(current),melds,visible)
        wall=board.get("wall_remaining")
        # Budget only own future draws; never assume opponents will feed calls.
        if needed is None or type(wall) is not int or needed>max(0,wall//board["player_count"]):return
        targets.append({"target_route":"yakuman_"+name,"target_yaku_han":13,"projected_han":13,
                        "route_cost":sum(not allowed(t) for t in current),"open_route":not closed,
                        "opening_matches":matched,"current_matches":current_matches,"qualification":"opening" if matched>=10 else "current",
                        "minimum_draws":needed,"yakuman_suit":suit})
    unique=sum(counts[t]>0 for t in ORPHANS);pair=any(counts[t]>=2 for t in ORPHANS)
    add("kokushi",unique+int(pair),lambda t:t in ORPHANS,True)
    add("all_honors",sum(n for t,n in counts.items() if t[1]=="z"),lambda t:t[1]=="z")
    add("all_terminals",sum(n for t,n in counts.items() if t[1]!="z" and t[0] in "19"),lambda t:t[1]!="z" and t[0] in "19")
    add("all_green",sum(n for t,n in counts.items() if t in GREEN),lambda t:t in GREEN)
    for suit in "mps":
        base={str(n)+suit:(3 if n in (1,9) else 1) for n in range(1,10)}
        matched=sum(min(counts[t],n) for t,n in base.items())+int(any(counts[t]>n for t,n in base.items()))
        add("nine_gates",matched,lambda t:t[1]==suit,True,suit)
    return targets


def _minimum_draws(name,suit,hand,melds,visible):
    """Cheapest complete template whose missing copies are still unseen."""
    def cost(required):
        if any(n>4 or max(0,n-hand[t])>max(0,4-visible[t]) for t,n in required.items()):return None
        return sum(max(0,n-hand[t]) for t,n in required.items())
    if name=="kokushi":
        base=Counter({t:1 for t in ORPHANS})
        templates=(base+Counter({t:1}) for t in sorted(ORPHANS))
    elif name=="nine_gates":
        base=Counter({str(n)+suit:3 if n in (1,9) else 1 for n in range(1,10)})
        templates=(base+Counter({str(n)+suit:1}) for n in range(1,10))
    else:
        allowed=sorted(GREEN if name=="all_green" else
                       {str(n)+"z" for n in range(1,8)} if name=="all_honors" else
                       {str(n)+s for s in "mps" for n in (1,9)})
        if any(m["type"]==0 and (name!="all_green" or sorted(tile_kind(t) for t in m["tiles"])!=["2s","3s","4s"]) for m in melds):return None
        groups=[Counter({t:3}) for t in allowed]
        if name=="all_green":groups.append(Counter({"2s":1,"3s":1,"4s":1}))
        fixed=Counter(tile_kind(t) for m in melds for t in m["tiles"])
        def candidates():
            for selection in combinations_with_replacement(range(len(groups)),4-len(melds)):
                base=Counter()
                for i in selection:base.update(groups[i])
                for head in allowed:
                    required=base+Counter({head:2})
                    if all(required[t]+fixed[t]<=4 for t in required):yield required
        templates=candidates()
    costs=[n for template in templates if (n:=cost(template)) is not None]
    return min(costs,default=None)
