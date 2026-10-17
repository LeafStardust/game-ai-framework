"""Four-player attack decisions with value, yaku, calls and relative danger."""
from collections import Counter
from copy import deepcopy
from agents.mahjong_soul.efficiency import counts34,shanten,rank_discards,KINDS
from agents.mahjong_soul.attack_value import yaku_routes,tenpai_value,own_player,yaku_potential
from agents.mahjong_soul.attack_defense import threats,danger
from games.mahjong_soul.playbook.features import discard_features
from games.mahjong_soul.live.runtime.kan import tile_kind


def enrich(board,options):
    opponents=threats(board)
    for option in options:
        tile=option["action"]["tile"];hand=list(board["self"]["hand"]);hand.remove(tile)
        option.update(discard_features(board,tile));option.update(yaku_routes(board,hand));option.update(danger(board,tile,opponents))
        option["yaku_potential"]=yaku_potential(board,hand)
        before=Counter(tile_kind(t) for t in board["self"]["hand"])
        option["pair_break_loss"]=int(not own_player(board)["melds"] and sum(n>=2 for n in before.values())>=5 and before[tile_kind(tile)]==2)
        option["value_han"]=option["retained_bonus"]+option["route_han"]
        option["push_value_estimate"]=option["value_han"]+int(not option["opened"])+max(0,max(option["yaku_potential"].values(),default=0)-option["route_han"])
        operations=(board.get("available_operations") or {}).get("operation_list",[])
        option["riichi_offered"]=any(o.get("type")==7 and tile in o.get("combination",[]) for o in operations)
        option["wait_value"]=tenpai_value(board,hand,discard=tile) if option["shanten"]==0 and option["improving_tiles"] else None
        profile=option["wait_value"]
        option["effective_ukeire"]=(max(profile["dama_ukeire"],profile["tsumo_ukeire"]) if profile and option["has_open_meld"] else option["ukeire"])
    return options


def offensive(board,options,value):
    distance=min(o["shanten"] for o in options)
    if distance==0 and not any(o["effective_ukeire"]>0 for o in options if o["shanten"]==0):
        productive=[o["shanten"] for o in options if o["effective_ukeire"]>0]
        if productive:distance=min(productive)
    maximum=max(o["effective_ukeire"] for o in options if o["shanten"]==distance)
    candidates=[o for o in options if o["shanten"]==distance and o["effective_ukeire"]>=maximum-value["max_ukeire_sacrifice"]]
    for option in candidates:
        option["value_loss"]=(option["dora_loss"]*value["dora_loss_weight"]+option["yakuhai_pair_loss"]*value["yakuhai_pair_loss_weight"]
                              +option["yakuhai_triplet_loss"]*value["yakuhai_triplet_loss_weight"]+option["pair_break_loss"]*value["pair_break_weight"])
    def scoring_credit(option):
        profile=option["wait_value"]
        points=max(profile["dama_points"] if profile["dama_ukeire"] else 0,
                   profile["riichi_points"] if option["riichi_offered"] else 0) if profile else 0
        return min(6,points/value["points_per_ukeire"])+max(option["yaku_potential"].values(),default=0)*value["potential_weight"]
    return min(candidates,key=lambda o:(-o["effective_ukeire"]+o["value_loss"]*value["ukeire_per_value"]-o["route_han"]-scoring_credit(o),
                                      o["danger"],-o["value_han"],o["action"]["tile"].startswith("0"),
                                      o["action"]["tile"]!=board["self"].get("drawn_tile"),o["action"]["tile"]))


def may_push(option,opponents,wall,settings):
    if not opponents:return True
    if len(opponents)!=1 or type(wall) is not int or wall<(4 if option["shanten"]==0 else settings["push_min_wall"]):return False
    if option["shanten"]>settings["push_max_shanten"] or option["danger"]>settings["push_max_danger"]:return False
    if option["opened"] and not option["open_yaku"]:return False
    value=option["push_value_estimate"]
    profile=option["wait_value"]
    if option["shanten"]==0:
        if profile and profile["ron_blocked"]:return False
        points=(max(profile["dama_points"] if profile["dama_ukeire"] else 0,
                    profile["riichi_points"] if option["riichi_offered"] else 0) if profile else None)
        return option["effective_ukeire"]>=2 and (points is None or points>=2000)
    if value<settings["push_value_floor"]:return False
    if option["shanten"]==2:
        return value>=settings["distant_push_han"] and option["ukeire"]>=settings["distant_push_ukeire"] and wall>=settings["distant_push_wall"]
    return True


def _call_options(request,book,ranker):
    board=request["observation"]["board"];own=own_player(board);hand=board["self"]["hand"]
    fixed=len(own["melds"]);baseline=shanten(counts34(hand),fixed)
    opponents=threats(board);settings=book.strategy["calls"];candidates=[]
    before_value=tenpai_value(board,hand) if baseline==0 else None
    pairs=sum(n>=2 for n in Counter(tile_kind(t) for t in hand).values())
    for action in request["actions"]:
        if action["kind"] not in ("chi","pon"):continue
        simulated=deepcopy(board);remaining=simulated["self"]["hand"]
        for tile in action["combination"].split("|"):remaining.remove(tile)
        meld={"type":0 if action["kind"]=="chi" else 1,"tiles":action["combination"].split("|")+[action["called_tile"]]}
        own_player(simulated)["melds"].append(meld)
        forbidden={tile_kind(action["called_tile"])}
        if action["kind"]=="chi":
            ranks=sorted(int(tile_kind(t)[0]) for t in meld["tiles"]);called=int(tile_kind(action["called_tile"])[0]);suit=action["called_tile"][1]
            if called==ranks[0] and ranks[-1]<9:forbidden.add(str(ranks[-1]+1)+suit)
            if called==ranks[-1] and ranks[0]>1:forbidden.add(str(ranks[0]-1)+suit)
        discards=[{"kind":"discard","tile":t} for t in sorted(set(remaining)) if tile_kind(t) not in forbidden]
        if not discards:continue
        synthetic={"observation":{"board":simulated},"actions":discards}
        options=enrich(simulated,ranker(synthetic))
        viable=[]
        for option in options:
            if not option["open_yaku"] or option["shanten"]>settings["max_shanten"]:continue
            profile=option["wait_value"]
            enables_ron=(baseline==option["shanten"]==0 and before_value and before_value["dama_ukeire"]==0
                         and profile and profile["dama_ukeire"]>=3 and profile["dama_points"]>=2000
                         and option["value_han"]>=settings["minimum_han"])
            if option["shanten"]>=baseline and not enables_ron:continue
            if profile and (profile["dama_ukeire"]==0 or profile["permanent_furiten"]):continue
            if option["value_han"]<settings["minimum_han"] and not (profile and profile["dama_ukeire"]>=settings["cheap_tenpai_waits"]):continue
            if not own["melds"] and pairs>=5 and option["value_han"]<4:continue
            if opponents and not (option["shanten"]==0 and may_push(option,opponents,board.get("wall_remaining"),book.thresholds_for("D2"))):continue
            viable.append(option)
        if viable:
            best=offensive(simulated,viable,book.thresholds_for("D1"))
            candidates.append((action,best))
    if not candidates:return None
    return min(candidates,key=lambda x:(x[1]["shanten"],-x[1]["effective_ukeire"],x[1]["danger"],-x[1]["value_han"],str(x[0])))


def draw_ukeire(board,hand,fixed):
    counts=list(counts34(hand));distance=shanten(tuple(counts),fixed);visible=Counter()
    for tile,n in board["visible_tile_counts"].items():visible[tile_kind(tile)]+=n
    total=0
    for index,tile in enumerate(KINDS):
        remaining=4-visible[tile]
        if remaining<=0 or counts[index]>=4:continue
        counts[index]+=1
        if shanten(tuple(counts),fixed)<distance:total+=remaining
        counts[index]-=1
    return total


def _kan_option(request,book,best=None):
    board=request["observation"]["board"];own=own_player(board);settings=book.strategy["calls"]
    if threats(board) or own["riichi"] in ("declared","accepted"):return None
    wall=board.get("wall_remaining")
    if type(wall) is not int or wall<settings["kan_min_wall"]:return None
    hand=board["self"]["hand"];fixed=len(own["melds"])
    baseline=best["shanten"] if best else shanten(counts34(hand),fixed)
    for action in request["actions"]:
        if action["kind"] not in ("closed_kan","added_kan","open_kan"):continue
        if action["kind"]=="open_kan" and not any(m["type"]!=3 for m in own["melds"]):continue
        new=deepcopy(board);remaining=new["self"]["hand"];melds=own_player(new)["melds"]
        contribution=action["combination"].split("|")
        if action["kind"]=="added_kan":
            matching=next(m for m in melds if m["type"]==1 and tile_kind(m["tiles"][0])==tile_kind(contribution[0]))
            extra=list((Counter(contribution)-Counter(matching["tiles"])).elements())
            if len(extra)!=1:continue
            remaining.remove(extra[0]);matching.update(type=2,tiles=contribution)
        else:
            for tile in contribution:remaining.remove(tile)
            melds.append({"type":3 if action["kind"]=="closed_kan" else 2,
                          "tiles":contribution+([action["called_tile"]] if action["kind"]=="open_kan" else [])})
        if shanten(counts34(remaining),len(melds))>baseline:continue
        before_ukeire=best["ukeire"] if best else draw_ukeire(board,hand,fixed)
        if draw_ukeire(board,remaining,len(melds))<before_ukeire-settings["kan_ukeire_loss"]:continue
        before_score=best["wait_value"] if best else tenpai_value(board,hand) if baseline==0 else None
        after_score=tenpai_value(new,remaining) if shanten(counts34(remaining),len(melds))==0 else None
        if before_score and after_score and max(after_score["dama_points"],after_score["riichi_points"])<max(before_score["dama_points"],before_score["riichi_points"]):continue
        route=yaku_routes(new,remaining)
        # Avoid increasing dora exposure for a cheap open hand, or breaking a
        # closed special-hand route. Unknown replacement tiles add no value.
        retained=sum(t.startswith("0") for t in remaining)+sum(t.startswith("0") for m in melds for t in m["tiles"])
        from games.mahjong_soul.playbook.features import dora_kind
        doras=Counter(dora_kind(t,4) for t in board["dora_indicators"])
        retained+=sum(doras[tile_kind(t)] for t in remaining+[t for m in melds for t in m["tiles"]])
        if route["opened"] and (not route["open_yaku"] or retained+route["route_han"]<settings["kan_min_han"]):continue
        if not route["opened"] and sum(n>=2 for n in Counter(tile_kind(t) for t in hand).values())>=5:continue
        return action
    return None


def choose_attack(owner,request,book,ranker=rank_discards):
    board=request["observation"]["board"];actions=request["actions"]
    def finish(action,mode,option=None,**detail):
        owner.last_analysis={"board_token":request["board_token"],"playbook":book.name,"playbook_version":book.version,"style":"atk","mode":mode,**detail}
        if option:
            owner.last_analysis.update({k:deepcopy(option[k]) for k in ("shanten","ukeire","effective_ukeire","value_han","push_value_estimate","routes","yaku_potential","danger","danger_by_seat","wait_value","improving_tiles")})
            owner.last_analysis["retained_value_proxy"]=option["value_han"]
        return deepcopy(action)
    wins=[a for a in actions if a["kind"] in ("ron","tsumo")]
    if wins:return finish(wins[0],"win")
    opponents=threats(board);wall=board.get("wall_remaining")
    if not any(a["kind"]=="discard" for a in actions):
        call=_call_options(request,book,ranker)
        if call:return finish(call[0],"call",call[1],post_call_discard=call[1]["action"])
        kan=_kan_option(request,book)
        if kan:return finish(kan,"kan")
        return finish(next(a for a in actions if a["kind"]=="skip"),"skip")
    options=enrich(board,ranker(request));best=offensive(board,options,book.thresholds_for("D1"))
    settings=book.thresholds_for("D2")
    if opponents:
        alternatives=[o for o in options if o["shanten"]==best["shanten"]
                      and o["effective_ukeire"]>=best["effective_ukeire"]-book.thresholds_for("D1")["max_ukeire_sacrifice"]
                      and may_push(o,opponents,wall,settings)]
        if alternatives:best=offensive(board,alternatives,book.thresholds_for("D1"))
    push=may_push(best,opponents,wall,settings)
    fold=bool(opponents and not push)
    if fold:
        best=min(options,key=lambda o:(o["danger"],o["total_danger"],o["shanten"],-o["effective_ukeire"],-o["value_han"],o["action"]["tile"]))
        return finish(best["action"],"fold",best)
    chosen=best["action"];riichi=book.thresholds_for("D3")
    offered={a["tile"]:a for a in actions if a["kind"]=="riichi"}
    candidates=[]
    closed=not any(m["type"]!=3 for m in own_player(board)["melds"])
    if (offered and closed and riichi["enabled"] and (riichi["allow_furiten"] or board["self"].get("furiten") is False)
            and (not opponents or riichi["allow_under_riichi_threat"]) and len(opponents)<=riichi["max_threats"]
            and type(wall) is int and wall>=riichi["minimum_wall"]):
        minimum=riichi["minimum_ukeire_under_threat"] if opponents else riichi["minimum_ukeire"]
        for option in options:
            if option["action"]["tile"] not in offered or option["shanten"]!=0 or option["ukeire"]<minimum:continue
            profile=option["wait_value"]
            if profile and ((profile["permanent_furiten"] and not riichi["allow_furiten"]) or profile["riichi_ukeire"]<minimum):continue
            if opponents and not may_push(option,opponents,wall,settings):continue
            existing=best["wait_value"]
            if (profile and existing and existing["dama_ukeire"]>=riichi["dama_min_waits"]
                    and existing["dama_points"]>=riichi["dama_min_points"]
                    and profile["riichi_points"]<existing["dama_points"]*riichi["dama_gain_ratio"]):continue
            if profile and profile["dama_ukeire"]>=riichi["dama_min_waits"] and profile["dama_points"]>=riichi["dama_min_points"] and profile["riichi_points"]<profile["dama_points"]*riichi["dama_gain_ratio"]:continue
            candidates.append(option)
        if candidates:
            best=offensive(board,candidates,book.thresholds_for("D1"));chosen=offered[best["action"]["tile"]]
    if chosen["kind"]=="discard":
        kan=_kan_option(request,book,best)
        if kan:return finish(kan,"kan",best)
    return finish(chosen,"attack_push" if opponents and push else "efficiency",best)
