"""Bounded ready-hand checks for reversible client C/D preferences."""
from collections import Counter
from copy import deepcopy
from functools import lru_cache
import json
import time
from agents.mahjong_soul.ready_commit import committed_ready,kan_possible
from agents.mahjong_soul.attack_value import own_player,tenpai_value
from agents.mahjong_soul.efficiency import counts34,shanten,KINDS,tile_supply
from games.mahjong_soul.live.runtime.kan import tile_kind


def ready_lock(board,action):
    required={"players","self","self_seat","round","visible_tile_counts","dora_indicators","player_count"}
    if not required<=board.keys():return {}
    own=own_player(board)
    if board.get("lobby",{}).get("match_length")!="south" and any(p.get("riichi") in ("accepted","declared") for p in board["players"] if not p.get("is_self")):return {}
    if action.get("kind") not in ("discard",):return {}
    after=deepcopy(board);hand=after["self"]["hand"];fixed=len(own["melds"])
    if len(hand)==14-3*fixed:
        tile=action.get("tile")
        if tile not in hand:return {}
        hand.remove(tile);own_player(after)["discards"].append({"tile":tile})
    if len(hand)!=13-3*fixed or shanten(counts34(hand),fixed)!=0:return {}
    # Only scoring context used by the evaluator enters the bounded cache.
    reduced={k:after[k] for k in required}
    reduced["rules"]=after.get("rules",{})
    reduced["lobby"]=after.get("lobby",{})
    reduced["players"]=[own_player(after)]
    try:return dict(_check(json.dumps(reduced,sort_keys=True)))
    except (ValueError,KeyError,StopIteration):return {}


def improves(profile,base,speed_first=False):
    if not profile or profile["ron_blocked"]:return False
    for mode in ("dama","tsumo"):
        points=mode+"_points";copies=mode+"_ukeire"
        fields=(copies,points) if speed_first else (points,copies)
        if tuple(round(profile[k],6) for k in fields)>tuple(round(base[k],6) for k in fields):return True
    return False


@lru_cache(maxsize=256)
def _check(encoded):
    board=json.loads(encoded);own=own_player(board);hand=board["self"]["hand"]
    base=tenpai_value(board,hand)
    if not base or base["ron_blocked"] or not base["dama_ukeire"]:return {}
    speed_first=board.get("lobby",{}).get("match_length")=="east"
    if kan_possible(board):
        return {"skip_calls":False,"auto_discard":False,"reason":"keep_kan_available"}
    if committed_ready(board,base):
        return {"skip_calls":True,"auto_discard":True,"reason":"committed_open_tenpai",
                "ron_points":base["dama_points"],"live_waits":base["dama_ukeire"]}
    deadline=time.perf_counter()+.12
    counts=Counter(tile_kind(t) for t in hand)
    visible=Counter()
    for t,n in board["visible_tile_counts"].items():visible[tile_kind(t)]+=n
    def allowed(tile):return max(0,tile_supply(board,tile)-visible[tile])
    # Kan can bring another draw/Dora. Do not suppress it without a model of
    # that uncertainty; explicit native policy keeps those choices available.
    if any(n>=4 or n>=3 and allowed(t) for t,n in counts.items()):return {}
    if any(m["type"]==1 and (counts[tile_kind(m["tiles"][0])] or allowed(tile_kind(m["tiles"][0]))) for m in own["melds"]):return {}
    calls=[]
    for tile,n in counts.items():
        if n>=2 and allowed(tile):calls.append((tile,[tile,tile],1))
    if board["player_count"]==4:
        for suit in "mps":
            for start in range(1,8):
                group=[str(n)+suit for n in range(start,start+3)]
                for called in group:
                    need=list(group);need.remove(called)
                    if allowed(called) and not (Counter(need)-counts):calls.append((called,need,0))
    checked=0
    for called,need,typ in calls:
        if time.perf_counter()>deadline:return {}
        after=deepcopy(board);remaining=after["self"]["hand"]
        for kind in need:remaining.remove(next(t for t in remaining if tile_kind(t)==kind))
        own_player(after)["melds"].append({"type":typ,"tiles":need+[called]})
        after["visible_tile_counts"][called]=after["visible_tile_counts"].get(called,0)+1
        for discard in set(remaining):
            if tile_kind(discard)==called:continue
            if time.perf_counter()>deadline:return {}
            post=list(remaining);post.remove(discard)
            profile=tenpai_value(after,post,discard=discard);checked+=1
            if improves(profile,base,speed_first):return {"skip_calls":False,"auto_discard":False,"reason":"call_can_improve_ready_hand"}
    result={"skip_calls":True,"auto_discard":False,"reason":"no_ready_hand_call_improvement","checked_calls":checked}
    # Non-Riichi D is restricted to open hands with no beneficial calls.
    # Closed hands keep the option to declare Riichi or develop their value.
    if not any(m["type"]!=3 for m in own["melds"]):return result
    draws=[tile for tile in KINDS if allowed(tile)]
    # A red five can improve value even when replacing a normal five leaves
    # the shape unchanged. Model it conservatively whenever that kind remains.
    draws += ["0"+tile[1] for tile in draws if tile[0]=="5" and tile[1]!="z"]
    for draw in draws:
        if time.perf_counter()>deadline:return {}
        after=deepcopy(board);after["self"]["hand"].append(draw)
        after["visible_tile_counts"][draw]=after["visible_tile_counts"].get(draw,0)+1
        holding=after["self"]["hand"]
        if shanten(counts34(holding),len(own["melds"]))==-1:continue
        unchanged=tenpai_value(after,hand,discard=draw)
        for discard in set(holding):
            if discard==draw:continue
            if time.perf_counter()>deadline:return {}
            post=list(holding);post.remove(discard)
            if improves(tenpai_value(after,post,discard=discard),unchanged or base,speed_first):return result
    result.update(auto_discard=True,reason="open_tenpai_no_one_draw_improvement")
    return result
