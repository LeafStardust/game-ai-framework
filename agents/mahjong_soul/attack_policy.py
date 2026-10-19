"""Four-player attack decisions with value, yaku, calls and relative danger."""
from collections import Counter
import math
from copy import deepcopy
from agents.mahjong_soul.efficiency import counts34,shanten,rank_discards,KINDS
from agents.mahjong_soul.attack_value import yaku_routes,tenpai_value,own_player,yaku_potential
from agents.mahjong_soul.attack_defense import threats,danger
from agents.mahjong_soul.attack_routes import project_attack,known_bonus,route_progress
from games.mahjong_soul.playbook.features import discard_features
from games.mahjong_soul.live.runtime.kan import tile_kind


def enrich(board,options,settings=None):
    settings=settings or {"han_weight":20,"shanten_cost":18,"route_cost_weight":4,"ukeire_weight":2.5}
    opponents=threats(board)
    for option in options:
        tile=option["action"]["tile"];hand=list(board["self"]["hand"]);hand.remove(tile)
        option.update(discard_features(board,tile));option.update(yaku_routes(board,hand));option.update(danger(board,tile,opponents))
        option["yaku_potential"]=yaku_potential(board,hand)
        before=Counter(tile_kind(t) for t in board["self"]["hand"])
        option["pair_break_loss"]=int(not own_player(board)["melds"] and sum(n>=2 for n in before.values())>=5 and before[tile_kind(tile)]==2)
        option["value_han"]=option["retained_bonus"]+option["route_han"]
        option.update(project_attack(board,hand,option["retained_bonus"],preferred=settings.get("preferred_plan")))
        # An open hand must progress toward its scoring route, not toward
        # a faster sequence shape that has no Yaku.
        option["shape_shanten"]=option["shanten"]
        targets=[]
        for target in project_attack(board,hand,option["retained_bonus"],all_targets=True):
            if option["opened"] and not target["open_route"]:continue
            distance,improving=route_progress(board,hand,target)
            targets.append((target,distance,improving))
        if not targets:
            targets=[(option,8,[])]
        nearest=min(item[1] for item in targets)
        # Value competes between routes that can actually win equally soon.
        # Do not advertise generic one-Shanten speed for a three-Shanten flush.
        practical=[item for item in targets if item[1]==nearest]
        target,distance,improving=max(practical or targets,key=lambda item:(
            item[0]["projected_han"]*settings["han_weight"]-item[1]*settings["shanten_cost"]-item[0]["route_cost"]*settings["route_cost_weight"]
            +math.sqrt(sum(t["unseen"] for t in item[2]))*settings["ukeire_weight"]
            +(6 if settings.get("preferred_plan")== (item[0]["target_route"],item[0].get("target_suit") or item[0].get("yakuman_suit")) else 0),-item[1]))
        option.update(target);option["shanten"]=distance;option["improving_tiles"]=improving
        option["ukeire"]=sum(t["unseen"] for t in improving)
        option["push_value_estimate"]=option["value_han"]+int(not option["opened"])+max(0,max(option["yaku_potential"].values(),default=0)-option["route_han"])
        operations=(board.get("available_operations") or {}).get("operation_list",[])
        option["riichi_offered"]=any(o.get("type")==7 and tile in o.get("combination",[]) for o in operations)
        option["wait_value"]=tenpai_value(board,hand,discard=tile) if option["shanten"]==0 and option["improving_tiles"] else None
        profile=option["wait_value"]
        if profile:
            from agents.mahjong_soul.attack_value import scored_han
            option["target_han_estimate"]=option["projected_han"]
            option["projected_han"]=scored_han(profile,option["riichi_offered"])
        option["effective_ukeire"]=(max(profile["dama_ukeire"],profile["tsumo_ukeire"]) if profile and option["has_open_meld"] else option["ukeire"])
    return options


def attack_utility(option,settings):
    profile=option.get("wait_value")
    points=0
    if profile:
        points=max(profile["dama_points"] if profile["dama_ukeire"] else 0,
                   profile["riichi_points"] if option.get("riichi_offered") else 0,
                   profile["tsumo_points"] if profile["tsumo_ukeire"] else 0)
    return (option["projected_han"]*settings["han_weight"]
            -option["shanten"]*settings["shanten_cost"]
            -option["route_cost"]*settings["route_cost_weight"]
            +math.sqrt(max(0,option["effective_ukeire"]))*settings["ukeire_weight"]
            +min(20,points/1000)
            +(6 if settings.get("preferred_plan")== (option.get("target_route"),option.get("target_suit") or option.get("yakuman_suit")) else 0))


def offensive(board,options,value):
    distance=min(o["shanten"] for o in options)
    if distance==0 and not any(o["effective_ukeire"]>0 for o in options if o["shanten"]==0):
        productive=[o["shanten"] for o in options if o["effective_ukeire"]>0]
        if productive:distance=min(productive)
    maximum=max(o["effective_ukeire"] for o in options if o["shanten"]==distance)
    candidates=[o for o in options if o["shanten"]==distance and o["effective_ukeire"]>=max(maximum-value["max_ukeire_sacrifice"],math.ceil(maximum*value.get("minimum_ukeire_fraction",0)))
                and (o["effective_ukeire"]>0 or maximum==0)]
    best_han=max(o["projected_han"] for o in candidates)
    wall=board.get("wall_remaining")
    if value.get("allow_value_rebuild",True) and type(wall) is int and wall>=value["value_rebuild_min_wall"]:
        candidates += [o for o in options if o["shanten"]==distance+1 and o["effective_ukeire"]>0
                       and o["projected_han"]>=best_han+value["value_rebuild_han_gain"]]
    return max(candidates,key=lambda o:(attack_utility(o,value),-o["shanten"],o["effective_ukeire"],
                                       -o["dora_loss"],-o["pair_break_loss"],
                                       not o["action"]["tile"].startswith("0"),
                                       o["action"]["tile"]==board["self"].get("drawn_tile"),o["action"]["tile"]))


def may_push(option,opponents,wall,settings):
    if settings.get("always_push") or not opponents:return True
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


def _call_options(request,book,ranker,diagnostics=None,value=None):
    value=value or book.thresholds_for("D1")
    board=request["observation"]["board"];own=own_player(board);hand=board["self"]["hand"]
    fixed=len(own["melds"]);baseline=shanten(counts34(hand),fixed)
    opponents=threats(board);settings=book.strategy["calls"];candidates=[]
    before_value=tenpai_value(board,hand) if baseline==0 else None
    before_target=project_attack(board,hand,known_bonus(board,hand),preferred=value.get("preferred_plan"))
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
        options=enrich(simulated,ranker(synthetic),value)
        viable=[];rejections=Counter()
        for option in options:
            profile=option["wait_value"]
            credible=(option["open_yaku"] or option["open_route"] and option["route_cost"]<=settings["max_route_cost"])
            reason=None
            if str(before_target["target_route"]).startswith("yakuman_") and option["target_route"]!=before_target["target_route"]:
                reason="abandons_qualified_yakuman"
            elif not credible:reason="no_reachable_open_yaku"
            elif option["shanten"]>settings["max_shanten"]:reason="too_far_from_win"
            elif profile and (profile["dama_ukeire"]==0 or profile["permanent_furiten"]):reason="no_legal_ron_wait"
            elif option["projected_han"]<settings["minimum_han"] and not (settings.get("allow_cheap_tenpai",True) and profile and profile["dama_ukeire"]>=settings["cheap_tenpai_waits"]):reason="low_value_open_hand"
            elif option["shanten"]>baseline:
                wall=board.get("wall_remaining")
                if (option["shanten"]>baseline+1 or option["projected_han"]<before_target["projected_han"]+2
                        or type(wall) is not int or wall<24):reason="call_loses_progress"
            elif option["shanten"]==baseline:
                enables_ron=(profile and before_value and before_value["dama_ukeire"]==0 and profile["dama_ukeire"]>0)
                value_gain=(option["projected_han"]>before_target["projected_han"] or option["route_cost"]<before_target["route_cost"]
                            or option["projected_han"]>=settings["minimum_han"]
                            and option["projected_han"]>=before_target["projected_han"]-1
                            and option["route_cost"]<=3)
                if not enables_ron and not value_gain:reason="no_progress_or_value_gain"
            if not reason and option["shanten"]==baseline:
                before_draws=draw_ukeire(board,hand,fixed)
                enables_ron=profile and before_value and before_value["dama_ukeire"]==0 and profile["dama_ukeire"]>0
                if not enables_ron and option["effective_ukeire"]<math.ceil(before_draws*settings.get("minimum_ukeire_fraction",0)):
                    reason="call_reduces_winning_chances"
            if reason:rejections[reason]+=1;continue
            if before_value and before_value["dama_ukeire"]>0 and profile and profile["dama_points"]<before_value["dama_points"]:
                rejections["reduces_ready_hand_value"]+=1;continue
            if (before_value and before_value["dama_ukeire"]>0 and profile
                    and profile["dama_points"]<=before_value["dama_points"]
                    and profile["dama_ukeire"]<=before_value["dama_ukeire"]
                    and profile["tsumo_points"]<=before_value["tsumo_points"]
                    and profile["tsumo_ukeire"]<=before_value["tsumo_ukeire"]):
                rejections["no_ready_hand_improvement"]+=1;continue
            viable.append(option)
        if diagnostics is not None:
            diagnostics.append({"action":deepcopy(action),"accepted":bool(viable),"baseline_shanten":baseline,
                                "best_shanten":min(o["shanten"] for o in options),
                                "best_projected_han":max(o["projected_han"] for o in options),"rejections":dict(rejections)})
        if viable:
            best=offensive(simulated,viable,value)
            candidates.append((action,best))
    if not candidates:return None
    return max(candidates,key=lambda x:(attack_utility(x[1],value),-x[1]["shanten"],x[1]["effective_ukeire"],str(x[0])))


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
    if (threats(board) and settings.get("avoid_kan_under_threat",True)) or own["riichi"] in ("declared","accepted"):return None
    wall=board.get("wall_remaining")
    if type(wall) is not int or wall<settings["kan_min_wall"]:return None
    hand=board["self"]["hand"];fixed=len(own["melds"])
    if any(t["target_route"] in ("yakuman_kokushi","yakuman_nine_gates") for t in project_attack(board,hand,all_targets=True)):return None
    baseline=best["shanten"] if best else shanten(counts34(hand),fixed)
    candidates=[]
    for action in request["actions"]:
        if action["kind"] not in ("closed_kan","added_kan","open_kan"):continue
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
        target=project_attack(new,remaining,retained)
        if route["opened"] and (not target["open_route"] or target["route_cost"]>settings["max_route_cost"]
                                or target["projected_han"]<settings["kan_min_han"]):continue
        if not route["opened"] and sum(n>=2 for n in Counter(tile_kind(t) for t in hand).values())>=5:continue
        candidates.append((action,target["projected_han"],-target["route_cost"],draw_ukeire(new,remaining,len(melds))))
    return max(candidates,key=lambda c:(c[1],c[2],c[3],str(c[0])))[0] if candidates else None


def choose_attack(owner,request,book,ranker=rank_discards):
    board=request["observation"]["board"];actions=request["actions"];call_notes=[]
    from agents.mahjong_soul.hand_plan import begin,remember
    previous_plan=begin(owner,request)
    value=book.thresholds_for("D1");value["preferred_plan"]=previous_plan
    def finish(action,mode,option=None,**detail):
        owner.last_analysis={"board_token":request["board_token"],"playbook":book.name,"playbook_version":book.version,"style":"atk","mode":mode,"call_evaluations":deepcopy(call_notes),**detail}
        owner.last_analysis["hand_plan"]=remember(owner,option)
        if option:
            owner.last_analysis.update({k:deepcopy(option[k]) for k in ("shanten","ukeire","effective_ukeire","value_han","push_value_estimate","routes","yaku_potential","danger","danger_by_seat","wait_value","improving_tiles","target_route","projected_han","route_cost")})
            owner.last_analysis["retained_value_proxy"]=option["value_han"]
        return deepcopy(action)
    wins=[a for a in actions if a["kind"] in ("ron","tsumo")]
    if wins:return finish(wins[0],"win")
    opponents=threats(board);wall=board.get("wall_remaining")
    if not any(a["kind"]=="discard" for a in actions):
        call=_call_options(request,book,ranker,call_notes,value)
        if call:return finish(call[0],"call",call[1],post_call_discard=call[1]["action"])
        kan=_kan_option(request,book)
        if kan:return finish(kan,"kan")
        return finish(next(a for a in actions if a["kind"]=="skip"),"skip")
    options=enrich(board,ranker(request),value);best=offensive(board,options,value)
    settings=book.thresholds_for("D2")
    if opponents and not settings.get("always_push"):
        alternatives=[o for o in options if o["shanten"]==best["shanten"]
                      and o["effective_ukeire"]>=best["effective_ukeire"]-book.thresholds_for("D1")["max_ukeire_sacrifice"]
                      and may_push(o,opponents,wall,settings)]
        if alternatives:best=offensive(board,alternatives,value)
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
            best=offensive(board,candidates,value);chosen=offered[best["action"]["tile"]]
    if chosen["kind"]=="discard":
        kan=_kan_option(request,book,best)
        if kan:return finish(kan,"kan",best)
    return finish(chosen,"attack_push" if opponents and push else "value_attack",best)
