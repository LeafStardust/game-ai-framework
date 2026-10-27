"""Relative visible danger rankings, not deal-in probabilities."""
from collections import Counter
from games.mahjong_soul.live.runtime.kan import tile_kind
from games.mahjong_soul.playbook.features import dora_kind,value_honors


def threats(board):
    result=[]
    for player in board["players"]:
        if player["is_self"]:continue
        kind=None
        if player["riichi"] in ("declared","accepted"):kind="riichi"
        else:
            opened=[m for m in player["melds"] if m["type"]!=3]
            exposed=Counter(tile_kind(t) for m in opened for t in m["tiles"])
            context=dict(board,self_seat=player["seat"])
            yaku=any(exposed[t]>=3 for t in value_honors(context))
            bonus=sum(exposed[dora_kind(d,board["player_count"])] for d in board["dora_indicators"])
            bonus+=sum(t.startswith("0") for m in opened for t in m["tiles"])
            if len(opened)>=3 and (yaku or bonus>=3):kind="open_hand"
        if kind:result.append({**player,"threat_kind":kind})
    return result


def danger(board,tile,opponents):
    tile=tile_kind(tile);visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    dora={dora_kind(d,board["player_count"]) for d in board["dora_indicators"]};scores=[]
    for player in opponents:
        river={tile_kind(d["tile"]) for d in player["discards"]}
        if tile in river: risk=0
        elif tile[1]=="z" and visible[tile]>=4:risk=0 if player["melds"] else 5
        elif tile[1]=="z":risk={1:70,2:45,3:20}.get(visible[tile],80)
        else:
            rank=int(tile[0]);suit=tile[1];risk=55 if rank in (1,9) else 75 if rank in (2,8) else 90
            checks=[str(n)+suit in river for n in (rank-3,rank+3) if 1<=n<=9]
            if checks and all(checks):risk*=.65
            elif any(checks):risk*=.85
            walls=sum(visible[str(n)+suit]>=4 for n in (rank-1,rank+1) if 1<=n<=9)
            risk*=.5 if walls==2 else .8 if walls else 1
            if tile in dora:risk+=12
        scores.append({"seat":player["seat"],"risk":round(risk,2),"threat_kind":player["threat_kind"]})
    return {"danger":max((x["risk"] for x in scores),default=0),"total_danger":sum(x["risk"] for x in scores),"danger_by_seat":scores}


def riichi_genbutsu(board,tile):
    """True only when every current Riichi declarer discarded this kind."""
    opponents=[p for p in board.get("players",[]) if not p.get("is_self")
               and p.get("riichi") in ("declared","accepted")]
    kind=tile_kind(tile)
    return bool(opponents) and all(kind in {tile_kind(d["tile"]) for d in p.get("discards",[])}
                                   for p in opponents)
