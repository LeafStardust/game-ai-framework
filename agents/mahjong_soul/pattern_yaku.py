"""Constrained normal-Yaku development; final Han always comes from scoring.

Mandatory melds/pair consume disjoint tiles. The residual shape is evaluated
with explicit fixed groups; open melds cannot supply concealed-only patterns.
"""
from collections import Counter
from functools import lru_cache
from itertools import combinations,combinations_with_replacement
from agents.mahjong_soul.efficiency import KINDS,INDEX,counts34
from games.mahjong_soul.live.runtime.kan import tile_kind


def _meld_key(m):return (m["type"],tuple(sorted(tile_kind(t) for t in m["tiles"])))


@lru_cache(maxsize=40000)
def _distance(counts,fixed,groups,pair,mode,blocked_heads,concealed_required):
    from agents.mahjong_soul.attack_routes import _regular_distance
    if mode=="honroto_pairs":
        if fixed:return 8
        usable=[n for t,n in zip(KINDS,counts) if t[1]=="z" or t[0] in "19"]
        return 6-sum(n>=2 for n in usable)+max(0,7-sum(n>0 for n in usable))
    remaining=list(counts);unused=list(fixed);needed=[]
    for group in groups:
        found=next((m for m in unused if (not concealed_required or m[0]==3) and
                    (tuple(sorted(m[1][:3]))==group)),None)
        if found:unused.remove(found)
        else:needed.append(group)
    total_fixed=len(fixed)+len(needed)
    if total_fixed>4:return 8
    # Exposed groups must fit the route's group restriction.
    for code,tiles in fixed:
        outside=lambda t:t[1]=="z" or t[0] in "19"
        terminal=lambda t:t[1]!="z" and t[0] in "19"
        if mode=="pinfu":return 8
        if mode in ("outside","honroto") and not any(outside(t) for t in tiles):return 8
        if mode=="junchan" and (any(t[1]=="z" for t in tiles) or not any(terminal(t) for t in tiles)):return 8
        if mode=="honroto" and code==0:return 8
    required=Counter(t for group in needed for t in group)
    if pair:required[pair]+=2
    full_required=Counter(t for _,tiles in fixed for t in tiles)+required
    if any(n>4 for n in full_required.values()):return 8
    missing=0
    for tile,n in required.items():
        i=INDEX[tile];missing+=max(0,n-remaining[i]);remaining[i]=max(0,remaining[i]-n)
    return _regular_distance(tuple(remaining),total_fixed,mode,bool(pair),blocked_heads)+missing


def pattern_distance(board,hand,target):
    own=next(p for p in board["players"] if p["is_self"])
    return _distance(counts34(hand),tuple(_meld_key(m) for m in own["melds"]),target["pattern_groups"],
                     target["pattern_pair"],target["pattern_mode"],target["blocked_heads"],target["concealed_required"])


def pattern_progress(board,hand,target):
    distance=pattern_distance(board,hand,target);visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    counts=Counter(tile_kind(t) for t in hand);improving=[]
    for tile in KINDS:
        if visible[tile]>=4 or counts[tile]>=4:continue
        if pattern_distance(board,hand+[tile],target)<distance:
            improving.append({"tile":tile,"unseen":4-visible[tile]})
    return distance,improving



def _retained_bonus(board,hand,target):
    """Count bonus tiles that fit reserved groups and conservative residual groups.

    An isolated Dora cannot survive when three mandatory concealed triplets,
    an exposed sequence and the best available pair already consume the hand.
    """
    from agents.mahjong_soul.attack_routes import known_bonus
    from games.mahjong_soul.playbook.features import value_honors
    own=next(p for p in board["players"] if p["is_self"])
    remaining=list(hand);kept=[];unused=[_meld_key(m) for m in own["melds"]];needed=[]
    for group in target["pattern_groups"]:
        found=next((m for m in unused if (not target["concealed_required"] or m[0]==3) and tuple(sorted(m[1][:3]))==group),None)
        if found:unused.remove(found)
        else:needed.append(group)
    def take(group):
        for kind in group:
            matches=[t for t in remaining if tile_kind(t)==kind]
            if matches:
                tile=max(matches,key=lambda t:t.startswith("0"));remaining.remove(tile);kept.append(tile)
    for group in needed:take(group)
    pair=target["pattern_pair"];mode=target["pattern_mode"]
    if pair:take([pair]*2)
    free=max(0,4-len(own["melds"])-len(needed))
    if mode=="honroto_pairs":
        candidates={tile_kind(t) for t in remaining if t[1]=="z" or tile_kind(t)[0] in "19"}
        for kind in sorted(candidates,key=lambda t:sum(tile_kind(x)==t for x in remaining),reverse=True)[:7]:take([kind]*2)
        return known_bonus(board,kept)
    for _ in range(free):
        counts=Counter(tile_kind(t) for t in remaining);groups=[]
        for t,n in counts.items():
            if n>=3 and mode!="pinfu" and (mode not in ("outside","honroto","junchan") or t[0] in "19" or mode!="junchan" and t[1]=="z"):
                groups.append([t]*3)
        if mode!="honroto":
            for suit in "mps":
                for start in range(1,8):
                    group=[str(n)+suit for n in range(start,start+3)]
                    if mode in ("outside","junchan") and start not in (1,7):continue
                    if all(counts[t] for t in group):groups.append(group)
        if not groups:break
        def group_bonus(group):
            trial=list(remaining);selected=[]
            for kind in group:
                t=max((t for t in trial if tile_kind(t)==kind),key=lambda t:t.startswith("0"));trial.remove(t);selected.append(t)
            return known_bonus(board,selected)
        take(max(groups,key=group_bonus))
    if not pair:
        counts=Counter(tile_kind(t) for t in remaining)
        candidates=[t for t in counts if not (mode=="pinfu" and t in value_honors(board))
                    and (mode not in ("outside","honroto","junchan") or t[0] in "19" or mode!="junchan" and t[1]=="z")]
        if candidates:take([max(candidates,key=lambda t:(min(2,counts[t]),known_bonus(board,[x for x in remaining if tile_kind(x)==t][:2])))]*2)
    return known_bonus(board,kept)

def pattern_targets(board,hand,bonus):
    from games.mahjong_soul.playbook.features import value_honors
    own=next(p for p in board["players"] if p["is_self"]);melds=own["melds"]
    opened=any(m["type"]!=3 for m in melds);counts=Counter(tile_kind(t) for t in hand)
    all_counts=counts+Counter(tile_kind(t) for m in melds for t in m["tiles"])
    honors=value_honors(board)
    visible=Counter()
    for tile,n in board["visible_tile_counts"].items():visible[tile_kind(tile)]+=n
    results=[]
    def add(name,han,groups=(),pair=None,mode="any",closed=False,concealed=False,extra=0):
        if closed and opened:return
        groups=tuple(tuple(sorted(g)) for g in groups)
        required=Counter(t for g in groups for t in g)
        if pair:required[pair]+=2
        missing=sum(max(0,n-all_counts[t]) for t,n in required.items())
        if missing>3 or any(n>all_counts[t]+max(0,4-visible[t]) for t,n in required.items()):return
        honor_units=[v for t,v in honors.items() if all_counts[t]>=3 and t!=pair]
        if mode in ("pinfu","junchan"):honor_units=[]
        compatible_honors=sum(sorted(honor_units,reverse=True)[:max(0,4-len(groups))])
        blocked=tuple(INDEX[t] for t in honors) if mode=="pinfu" else ()
        target={"target_route":name,"target_yaku_han":han+extra+compatible_honors,
                "projected_han":han+extra+compatible_honors+bonus+int(not opened),"route_cost":missing,
                "open_route":not closed,"pattern_groups":groups,"pattern_pair":pair,"pattern_mode":mode,
                "blocked_heads":blocked,"concealed_required":concealed}
        target["projected_han"]=han+extra+compatible_honors+min(bonus,_retained_bonus(board,hand,target))+int(not opened)
        distance=pattern_distance(board,hand,target)
        if distance>3:return
        target["pattern_shanten"]=distance
        # Alternative decompositions of the same Yaku are compared by actual
        # route distance, not by summing their advertised Han.
        results.append(target)
    sequences=[tuple(str(n)+s for n in range(start,start+3)) for s in "mps" for start in range(1,8)]
    if not opened:
        add("pinfu",1,mode="pinfu",closed=True)
        for seq in sequences:
            add("iipeikou",1,(seq,seq),closed=True)
        # Two pairs of identical sequences (distinct decompositions supported).
        near=[seq for seq in sequences if sum(min(counts[t],2) for t in seq)>=4]
        for a,b in combinations_with_replacement(near,2):add("ryanpeikou",3,(a,a,b,b),closed=True)
    for start in range(1,8):add("sanshoku",1 if opened else 2,
                              [tuple(str(n)+s for n in range(start,start+3)) for s in "mps"])
    for s in "mps":add("ittsu",1 if opened else 2,[tuple(str(n)+s for n in range(start,start+3)) for start in (1,4,7)])
    for n in range(1,10):add("sanshoku_doukou",2,[tuple([str(n)+s]*3) for s in "mps"])
    candidates=[t for t,n in all_counts.items() if n>=2]
    for chosen in combinations(candidates,3):add("sanankou",2,[tuple([t]*3) for t in chosen],concealed=True)
    dragons=("5z","6z","7z")
    for pair in dragons:
        groups=[tuple([t]*3) for t in dragons if t!=pair]
        # The two required Dragon triplets supply two Yakuhai Han; avoid
        # counting those triplets twice when already present.
        add("shousangen",2,groups,pair,extra=2-sum(1 for t in dragons if t!=pair and all_counts[t]>=3))
    # Chanta needs both a sequence and an honor; reserve an honor pair unless
    # an exposed honor triplet already establishes the honor requirement.
    honor_fixed=any(m["tiles"][0][1]=="z" for m in melds)
    outer=[seq for seq in sequences if seq[0][0] in "17"]
    for seq in outer:
        if honor_fixed:add("chanta",1 if opened else 2,[seq],mode="outside")
        else:
            for honor in (t for t in KINDS if t[1]=="z" and all_counts[t]>=1):
                add("chanta",1 if opened else 2,[seq],pair=honor,mode="outside")
        if not honor_fixed:
            for honor in (t for t in KINDS if t[1]=="z" and all_counts[t]>=2):
                add("chanta",1 if opened else 2,[seq,tuple([honor]*3)],mode="outside")
        add("junchan",2 if opened else 3,[seq],mode="junchan")
    if not melds:add("honroutou_pairs",4,mode="honroto_pairs",closed=True)
    add("honroutou",4,mode="honroto")  # Triplet form necessarily also Toitoi.
    if sum(m["type"] in (2,3) for m in melds)>=3:add("sankantsu",2)
    return results
