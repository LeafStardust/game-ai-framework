"""Opening-only eligibility for supported structural Yakuman targets."""
from collections import Counter
from games.mahjong_soul.live.runtime.kan import tile_kind

ORPHANS={str(n)+s for s in "mps" for n in (1,9)}|{str(n)+"z" for n in range(1,8)}
GREEN={"2s","3s","4s","6s","8s","6z"}


def yakuman_targets(board,hand):
    opening=board["self"].get("opening_hand",[])
    if len(opening) not in (13,14):return []
    counts=Counter(tile_kind(t) for t in opening);melds=next(p for p in board["players"] if p["is_self"])["melds"]
    fixed=[tile_kind(t) for m in melds for t in m["tiles"]];current=[tile_kind(t) for t in hand]
    targets=[]
    def add(name,matched,allowed,closed=False,suit=None):
        if matched<10 or closed and melds or not all(allowed(t) for t in fixed):return
        targets.append({"target_route":"yakuman_"+name,"target_yaku_han":13,"projected_han":13,
                        "route_cost":sum(not allowed(t) for t in current),"open_route":not closed,
                        "opening_matches":matched,"yakuman_suit":suit})
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
