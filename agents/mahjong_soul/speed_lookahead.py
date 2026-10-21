"""Bounded closed-hand development experiments; no hidden tile information."""
from functools import lru_cache
from agents.mahjong_soul.efficiency import KINDS,counts34,shanten,tile_supply
from games.mahjong_soul.live.runtime.kan import tile_kind


@lru_cache(maxsize=20000)
def _quality(after,visible,pool,river,improving):
    weighted=0;weight=0
    for draw,copies in improving:
        hand=list(after);hand[draw]+=1;seen=list(visible);seen[draw]+=1
        best=0
        for discard,n in enumerate(hand):
            if not n:continue
            hand[discard]-=1
            if shanten(tuple(hand))==0:
                waits=[]
                for next_draw,supply in enumerate(pool):
                    remaining=supply-seen[next_draw]
                    if remaining<=0 or hand[next_draw]>=4:continue
                    hand[next_draw]+=1
                    complete=shanten(tuple(hand))==-1
                    hand[next_draw]-=1
                    if complete:waits.append((next_draw,remaining))
                # Furiten is based on all structural waits, even exhausted ones.
                furiten=False
                for old in set(river)|{discard}:
                    if hand[old]>=4:continue
                    hand[old]+=1;complete=shanten(tuple(hand))==-1;hand[old]-=1
                    if complete:furiten=True;break
                copies_available=sum(count for _,count in waits)
                # Prefer waits supporting both Ron and Tsumo over Tsumo only.
                best=max(best,copies_available*(1 if furiten else 2))
            hand[discard]+=1
        weighted+=copies*best;weight+=copies
    return weighted/weight if weight else 0


def next_wait_quality(board,option):
    """Expected next-step wait-copy proxy, conditional on a useful next draw.

    Applicable only to closed one-Shanten hands. Immediate Shanten and Ukeire
    are never sacrificed. This is not a calibrated win probability.
    """
    own=next(p for p in board["players"] if p["seat"]==board["self_seat"])
    if own["melds"] or own.get("riichi") in ("declared","accepted") or option["shanten"]!=1:return 0
    hand=list(board["self"]["hand"]);discard=option["action"]["tile"];hand.remove(discard)
    after=counts34(hand)
    if shanten(after)!=1:return 0
    visible=[0]*34
    for t,n in board["visible_tile_counts"].items():visible[KINDS.index(tile_kind(t))]+=n
    pool=tuple(tile_supply(board,t) for t in KINDS)
    draws=tuple((KINDS.index(tile_kind(t["tile"])),t["unseen"]) for t in option["improving_tiles"] if t["unseen"]>0)
    river=tuple(sorted({KINDS.index(tile_kind(d["tile"])) for d in own["discards"]}|{KINDS.index(tile_kind(discard))}))
    return _quality(after,tuple(visible),pool,river,draws)


@lru_cache(maxsize=12000)
def _development(after,visible,pool,distance):
    total=0
    for draw,supply in enumerate(pool):
        copies=supply-visible[draw]
        if copies<=0 or after[draw]>=4:continue
        hand=list(after);hand[draw]+=1
        if shanten(tuple(hand))>=distance:continue
        seen=list(visible);seen[draw]+=1;best=0
        for discard,n in enumerate(hand):
            if not n:continue
            hand[discard]-=1
            if shanten(tuple(hand))==distance-1:
                improving=0
                for future,supply2 in enumerate(pool):
                    remaining=supply2-seen[future]
                    if remaining<=0 or hand[future]>=4:continue
                    hand[future]+=1
                    if shanten(tuple(hand))<distance-1:improving+=remaining
                    hand[future]-=1
                best=max(best,improving)
            hand[discard]+=1
        total+=copies*best
    return total


def development_quality(board,option):
    """Public-copy-weighted two-stage progress proxy for closed 2/3-Shanten."""
    own=next(p for p in board["players"] if p["seat"]==board["self_seat"])
    distance=option["shanten"]
    if own["melds"] or own.get("riichi") in ("declared","accepted") or distance not in (2,3):return 0
    hand=list(board["self"]["hand"]);hand.remove(option["action"]["tile"]);after=counts34(hand)
    if shanten(after)!=distance:return 0
    visible=[0]*34
    for t,n in board["visible_tile_counts"].items():visible[KINDS.index(tile_kind(t))]+=n
    return _development(after,tuple(visible),tuple(tile_supply(board,t) for t in KINDS),distance)
