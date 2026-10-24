"""Four-player attack decisions with value, yaku, calls and relative danger."""
from agents.mahjong_soul.efficiency import tile_supply
from collections import Counter
import math
from copy import deepcopy
from agents.mahjong_soul.efficiency import counts34,shanten,rank_discards,KINDS
from agents.mahjong_soul.attack_value import yaku_routes,tenpai_value,own_player,yaku_potential
from agents.mahjong_soul.attack_defense import threats,danger
from agents.mahjong_soul.ready_commit import committed_ready
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
            if settings.get("speed_first") and str(target["target_route"]).startswith("yakuman_"):continue
            if option["opened"] and not target["open_route"]:continue
            if "pattern_shanten" in target and targets and target["pattern_shanten"]>min(item[1] for item in targets):continue
            distance,improving=route_progress(board,hand,target)
            targets.append((target,distance,improving))
        if not targets:
            targets=[(option,8,[])]
        option["pair_route_comparison"]=[{"route":target["target_route"],"shanten":distance,
             "ukeire":sum(t["unseen"] for t in improving),"projected_han":target["projected_han"]}
             for target,distance,improving in targets if target["target_route"] in ("chiitoitsu","toitoi")]
        nearest=min(item[1] for item in targets)
        # Value competes between routes that can actually win equally soon.
        # Do not advertise generic one-Shanten speed for a three-Shanten flush.
        practical=[item for item in targets if item[1]==nearest]
        if settings.get("speed_first"):
            target,distance,improving=max(practical or targets,key=lambda item:(sum(t["unseen"] for t in item[2]),item[0]["projected_han"]))
        else:
            target,distance,improving=max(practical or targets,key=lambda item:(
            credible_han(item[0],settings)*settings["han_weight"]-item[1]*settings["shanten_cost"]-item[0]["route_cost"]*settings["route_cost_weight"]
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
            # Complete-hand scoring supersedes the partial target's restricted
            # wait set. Riichi can legalize additional waits outside that Yaku.
            option["target_route_cost_estimate"]=option["route_cost"]
            option["route_cost"]=0
            modes={"tsumo"}
            if not profile["ron_blocked"]:modes.add("dama")
            if option["riichi_offered"] and not profile["ron_blocked"]:modes.add("riichi")
            option["improving_tiles"]=[{"tile":w["tile"],"unseen":w["unseen"]}
                                       for w in profile["waits"] if w["unseen"]>0 and modes.intersection(w["values"])]
            option["ukeire"]=sum(w["unseen"] for w in option["improving_tiles"])
        option["effective_ukeire"]=(max(profile["dama_ukeire"],profile["tsumo_ukeire"]) if profile and option["has_open_meld"] else option["ukeire"])
    return options


def credible_han(option,settings):
    """Discount uncompleted target value, never a scored winning hand.

    Route cost measures replacements still needed for the claimed Yaku. This
    is a bounded planning heuristic, not an expected score or probability.
    """
    han=option["projected_han"]
    discount=settings.get("route_value_discount",0)
    if option.get("wait_value") or not discount:return han
    return han/(1+max(0,option.get("route_cost",0))*discount)


def attack_utility(option,settings):
    profile=option.get("wait_value")
    points=0
    if profile:
        points=max(profile["dama_points"] if profile["dama_ukeire"] else 0,
                   profile["riichi_points"] if option.get("riichi_offered") else 0,
                   profile["tsumo_points"] if profile["tsumo_ukeire"] else 0)
    return (credible_han(option,settings)*settings["han_weight"]
            -option["shanten"]*settings["shanten_cost"]
            -option["route_cost"]*settings["route_cost_weight"]
            +math.sqrt(max(0,option["effective_ukeire"]))*settings["ukeire_weight"]
            +min(20,points/1000)
            +(6 if settings.get("preferred_plan")== (option.get("target_route"),option.get("target_suit") or option.get("yakuman_suit")) else 0))


def offensive(board,options,value):
    if value.get("speed_first"):
        if value.get("early_development"):
            nearest=min(o["shanten"] for o in options)
            own=own_player(board)
            if nearest in (2,3) and not own["melds"]:
                maximum=max(o["effective_ukeire"] for o in options if o["shanten"]==nearest)
                shortlist=sorted([o for o in options if o["shanten"]==nearest and o["effective_ukeire"]>=max(1,maximum-2)],key=lambda o:(o["effective_ukeire"],-o.get("danger",0),o["projected_han"]),reverse=True)[:3]
                if shortlist:
                    from agents.mahjong_soul.speed_lookahead import development_quality
                    return max(shortlist,key=lambda o:(development_quality(board,o),o["effective_ukeire"],-o.get("danger",0),-o.get("total_danger",0),o["projected_han"]))
        if value.get("two_draw_progress"):
            nearest=min(o["shanten"] for o in options)
            own=own_player(board)
            if nearest==1 and not own["melds"] and own["riichi"] not in ("declared","accepted"):
                maximum=max(o["effective_ukeire"] for o in options if o["shanten"]==nearest)
                shortlist=[o for o in options if o["shanten"]==nearest and o["effective_ukeire"]>=max(1,maximum-2)]
                if shortlist:
                    from agents.mahjong_soul.speed_lookahead import next_wait_quality
                    return max(shortlist,key=lambda o:(next_wait_quality(board,o)*o["effective_ukeire"],o["effective_ukeire"],-o.get("danger",0),-o.get("total_danger",0),o["projected_han"]))
        if value.get("next_wait_tiebreak"):
            nearest=min(o["shanten"] for o in options)
            copies=max(o["effective_ukeire"] for o in options if o["shanten"]==nearest)
            tied=[o for o in options if o["shanten"]==nearest and o["effective_ukeire"]==copies]
            if len(tied)>1 and nearest==1 and all(o["action"]["tile"] in board["self"]["hand"] for o in tied):
                from agents.mahjong_soul.speed_lookahead import next_wait_quality
                for option in tied:option["next_wait_quality"]=next_wait_quality(board,option)
        if value.get("discard_completion"):
            from agents.mahjong_soul.discard_completion import choose_completion_discard
            key=lambda o:(-o["shanten"],o["effective_ukeire"],o.get("next_wait_quality",0),-o.get("danger",0),-o.get("total_danger",0),o["projected_han"],attack_utility(o,value))
            return choose_completion_discard(board,options,key)
        return max(options,key=lambda o:(-o["shanten"],o["effective_ukeire"],o.get("next_wait_quality",0),-o.get("danger",0),
                                         -o.get("total_danger",0),o["projected_han"],attack_utility(o,value)))
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
    key=lambda o:(attack_utility(o,value),-o["shanten"],o["effective_ukeire"],
                  -o["dora_loss"],-o["pair_break_loss"],
                  not o["action"]["tile"].startswith("0"),
                  o["action"]["tile"]==board["self"].get("drawn_tile"),o["action"]["tile"])
    if value.get("attack_completion"):
        from agents.mahjong_soul.discard_completion import choose_attack_completion_discard
        return choose_attack_completion_discard(board,candidates,key)
    return max(candidates,key=key)


def may_push(option,opponents,wall,settings):
    if settings.get("always_push") or not opponents:return True
    if len(opponents)!=1 or type(wall) is not int or wall<(4 if option["shanten"]==0 else settings["push_min_wall"]):return False
    profile=option["wait_value"]
    limit=settings["push_max_danger"]
    # Offline candidate only unless a playbook explicitly enables it. Require
    # real available Ron waits, rather than a shape-only Tenpai projection.
    if (option["shanten"]==0 and profile and not profile["ron_blocked"]
            and profile["dama_ukeire"]>=settings.get("ready_push_min_ukeire",3)):
        limit=max(limit,settings.get("ready_push_max_danger",limit))
    if option["shanten"]>settings["push_max_shanten"] or option["danger"]>limit:return False
    # A pair wait may acquire its Yaku only when the winning tile arrives.
    # For East Speed, exact legal Ron scoring can prove that ready route;
    # partial-hand Yaku flags cannot. Keep every danger/value/wall gate below.
    scored_ready=(settings.get("allow_scored_ready_yaku",False)
                  and option["shanten"]==0 and profile
                  and not profile["ron_blocked"] and profile["dama_ukeire"]>0)
    if option["opened"] and not option["open_yaku"] and not scored_ready:return False
    value=option["push_value_estimate"]
    if option["shanten"]==0:
        if profile and profile["ron_blocked"]:return False
        points=(max(profile["dama_points"] if profile["dama_ukeire"] else 0,
                    profile["riichi_points"] if option["riichi_offered"] else 0) if profile else None)
        return option["effective_ukeire"]>=2 and (points is None or points>=settings.get("ready_push_min_points",2000))
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
    if committed_ready(board,before_value):return None
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
        nearest=min(o["shanten"] for o in options)
        for option in options:
            profile=option["wait_value"]
            credible=(option["open_yaku"] or option["open_route"] and option["route_cost"]<=settings["max_route_cost"])
            reason=None
            if option["shanten"]>nearest:reason="slower_than_post_call_plan"
            elif not credible:reason="no_reachable_open_yaku"
            elif option["shanten"]>settings["max_shanten"]:reason="too_far_from_win"
            elif (settings.get("unsecured_opening_min_ukeire",0)>0
                  and baseline==2 and option["shanten"]==1 and not option["open_yaku"]
                  and not any(m["type"]!=3 for m in own["melds"])
                  and option["effective_ukeire"]<settings["unsecured_opening_min_ukeire"]):
                reason="narrow_unsecured_opening"
            elif profile and (profile["dama_ukeire"]==0 or profile["permanent_furiten"]):reason="no_legal_ron_wait"
            elif option["projected_han"]<settings["minimum_han"] and not (
                    settings.get("allow_cheap_tenpai",True) and profile and profile["dama_ukeire"]>=settings["cheap_tenpai_waits"]
                    or any(m["type"]!=3 for m in own["melds"]) and not yaku_routes(board,hand)["open_yaku"]
                    and option["shanten"]==0 and profile and not profile["ron_blocked"]
                    and profile["dama_ukeire"]>=3):reason="low_value_open_hand"
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
                if not value.get("speed_first") and not enables_ron and not value_gain:reason="no_progress_or_value_gain"
            if not reason and option["shanten"]==baseline:
                before_draws=draw_ukeire(board,hand,fixed)
                enables_ron=profile and before_value and before_value["dama_ukeire"]==0 and profile["dama_ukeire"]>0
                if not enables_ron and option["effective_ukeire"]<math.ceil(before_draws*settings.get("minimum_ukeire_fraction",0)):
                    reason="call_reduces_winning_chances"
            if not reason and value.get("speed_first"):
                if option["shanten"]>baseline:reason="call_loses_speed"
                elif opponents and not may_push(option,opponents,board.get("wall_remaining"),book.thresholds_for("D2")):reason="call_requires_unsafe_push"
            if not reason and value.get("speed_first") and option["shanten"]==baseline:
                enables_ron=profile and before_value and before_value["dama_ukeire"]==0 and profile["dama_ukeire"]>0
                if not enables_ron and option["effective_ukeire"]<=draw_ukeire(board,hand,fixed):reason="no_speed_gain"
            if reason:rejections[reason]+=1;continue
            if not value.get("speed_first") and before_value and before_value["dama_ukeire"]>0 and profile and profile["dama_points"]<before_value["dama_points"]:
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
    if value.get("speed_first"):
        key=lambda x:(-x[1]["shanten"],x[1]["effective_ukeire"],-x[1]["danger"],x[1]["projected_han"])
        if settings.get("completion_opening_guard",False):
            from agents.mahjong_soul.completion_call_guard import guard_opening
            return guard_opening(board,sorted(candidates,key=key,reverse=True),diagnostics)
        return max(candidates,key=key)
    return max(candidates,key=lambda x:(attack_utility(x[1],value),-x[1]["shanten"],x[1]["effective_ukeire"],str(x[0])))


def draw_ukeire(board,hand,fixed):
    counts=list(counts34(hand));distance=shanten(tuple(counts),fixed);visible=Counter()
    for tile,n in board["visible_tile_counts"].items():visible[tile_kind(tile)]+=n
    total=0
    for index,tile in enumerate(KINDS):
        remaining=tile_supply(board,tile)-visible[tile]
        if remaining<=0 or counts[index]>=4:continue
        counts[index]+=1
        if shanten(tuple(counts),fixed)<distance:total+=remaining
        counts[index]-=1
    return total


def _kan_option(request,book,best=None,diagnostics=None):
    board=request["observation"]["board"];own=own_player(board);settings=book.strategy["calls"]
    if (threats(board) and settings.get("avoid_kan_under_threat",True)) or own["riichi"] in ("declared","accepted"):return None
    wall=board.get("wall_remaining")
    if type(wall) is not int or wall<settings["kan_min_wall"]:return None
    hand=board["self"]["hand"];fixed=len(own["melds"])
    if any(t["target_route"] in ("yakuman_kokushi","yakuman_nine_gates") for t in project_attack(board,hand,all_targets=True)):return None
    baseline=best["shanten"] if best else shanten(counts34(hand),fixed)
    if committed_ready(board,best.get("wait_value") if best else tenpai_value(board,hand) if baseline==0 else None):return None
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
        if action["kind"]=="open_kan" and baseline>1:
            if diagnostics is not None:diagnostics.append({"action":deepcopy(action),"accepted":False,"reason":"open_kan_too_far_from_win","shanten":baseline})
            continue
        if shanten(counts34(remaining),len(melds))>baseline:continue
        before_ukeire=best["ukeire"] if best else draw_ukeire(board,hand,fixed)
        if draw_ukeire(new,remaining,len(melds))<before_ukeire-settings["kan_ukeire_loss"]:continue
        before_score=best["wait_value"] if best else tenpai_value(board,hand) if baseline==0 else None
        after_score=tenpai_value(new,remaining) if shanten(counts34(remaining),len(melds))==0 else None
        if before_score and after_score and max(after_score["dama_points"],after_score["riichi_points"])<max(before_score["dama_points"],before_score["riichi_points"]):continue
        route=yaku_routes(new,remaining)
        if action["kind"]=="open_kan" and not route["open_yaku"] and not (after_score and after_score["dama_ukeire"]>0):
            if diagnostics is not None:diagnostics.append({"action":deepcopy(action),"accepted":False,"reason":"open_kan_has_no_secured_yaku"})
            continue
        # Avoid increasing dora exposure for a cheap open hand, or breaking a
        # closed special-hand route. Unknown replacement tiles add no value.
        retained=sum(t.startswith("0") for t in remaining)+sum(t.startswith("0") for m in melds for t in m["tiles"])
        from games.mahjong_soul.playbook.features import dora_kind
        doras=Counter(dora_kind(t,board["player_count"]) for t in board["dora_indicators"])
        retained+=sum(doras[tile_kind(t)] for t in remaining+[t for m in melds for t in m["tiles"]])
        target=project_attack(new,remaining,retained)
        if route["opened"] and (not target["open_route"] or target["route_cost"]>settings["max_route_cost"]
                                or target["projected_han"]<settings["kan_min_han"]):continue
        if not route["opened"] and sum(n>=2 for n in Counter(tile_kind(t) for t in hand).values())>=5:continue
        candidates.append((action,target["projected_han"],-target["route_cost"],draw_ukeire(new,remaining,len(melds))))
    return max(candidates,key=lambda c:(c[1],c[2],c[3],str(c[0])))[0] if candidates else None


def choose_attack(owner,request,book,ranker=rank_discards):
    board=request["observation"]["board"];actions=request["actions"];call_notes=[];kan_notes=[]
    from agents.mahjong_soul.hand_plan import begin,remember
    previous_plan=begin(owner,request)
    discard_notes=[]
    north_notes={}
    value=book.thresholds_for("D1");value["preferred_plan"]=previous_plan
    def finish(action,mode,option=None,**detail):
        owner.last_analysis={"board_token":request["board_token"],"playbook":book.name,"playbook_version":book.version,"style":"speed" if value.get("speed_first") else "atk","mode":mode,"call_evaluations":deepcopy(call_notes),"kan_evaluations":deepcopy(kan_notes),"discard_evaluations":deepcopy(discard_notes),"north_evaluation":deepcopy(north_notes),**detail}
        owner.last_analysis["hand_plan"]=remember(owner,option)
        from agents.mahjong_soul.scoring import nagashi_eligible
        owner.last_analysis["nagashi_candidate"]=nagashi_eligible(board)
        if option:
            owner.last_analysis.update({k:deepcopy(option[k]) for k in ("shanten","ukeire","effective_ukeire","value_han","push_value_estimate","routes","yaku_potential","danger","danger_by_seat","wait_value","improving_tiles","target_route","projected_han","route_cost")})
            owner.last_analysis["retained_value_proxy"]=option["value_han"]
            owner.last_analysis["pair_route_comparison"]=deepcopy(option.get("pair_route_comparison",[]))
            if "completion_baseline_action" in option:
                owner.last_analysis["completion_baseline_action"]=deepcopy(option["completion_baseline_action"])
            if "completion_objective" in option:
                owner.last_analysis["completion_objective"]=option["completion_objective"]
        return deepcopy(action)
    wins=[a for a in actions if a["kind"] in ("ron","tsumo")]
    if wins:
        from agents.mahjong_soul.scoring import score_offered_win
        return finish(wins[0],"win",win_value=score_offered_win(board,wins[0]))
    north=next((a for a in actions if a["kind"]=="extract_north"),None)
    if north:
        from agents.mahjong_soul.north_choice import north_choice
        choice=north_choice(request)
        north_notes.update(choice)
        if choice["extract"]:return finish(north,"north_extraction")
    opponents=threats(board);wall=board.get("wall_remaining")
    if not any(a["kind"]=="discard" for a in actions):
        call=_call_options(request,book,ranker,call_notes,value)
        if call:return finish(call[0],"call",call[1],post_call_discard=call[1]["action"])
        kan=_kan_option(request,book,diagnostics=kan_notes)
        if kan:return finish(kan,"kan")
        return finish(next(a for a in actions if a["kind"]=="skip"),"skip")
    draw=board["self"].get("drawn_tile")
    discard_draw=next((a for a in actions if a.get("kind")=="discard" and a.get("tile")==draw),None)
    if discard_draw and draw in board["self"]["hand"] and any(m["type"]!=3 for m in own_player(board)["melds"]):
        retained=list(board["self"]["hand"]);retained.remove(draw)
        ready=tenpai_value(board,retained,discard=draw)
        if committed_ready(board,ready):
            return finish(discard_draw,"committed_open_tenpai",shanten=0,wait_value=ready,
                          effective_ukeire=ready["dama_ukeire"],projected_han=ready["known_han"])
    options=enrich(board,ranker(request),value);best=offensive(board,options,value)
    # Detailed recordings explain alternatives; terminal rendering stays action-only.
    discard_notes=[{k:deepcopy(o.get(k)) for k in ("action","target_route","projected_han","shanten","effective_ukeire","route_cost","wait_value")} |
                   {"utility":attack_utility(o,value)} |
                   ({"completion_estimate":deepcopy(o["completion_estimate"])} if "completion_estimate" in o else {}) for o in options]
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
    # Kokushi already scores Yakuman without a declaration. Keep the chosen
    # ready hand flexible and avoid paying a deposit or advertising its wait.
    def kokushi_ready(option):
        profile=option.get("wait_value") or {}
        return any(v.get("legal") and any(y.get("key") in ("kokushi","daburu_kokushi")
                   for y in v.get("yaku_details",[]))
                   for w in profile.get("waits",[]) for v in [w.get("values",{}).get("dama",{})])
    chosen=best["action"];riichi=book.thresholds_for("D3")
    offered={a["tile"]:a for a in actions if a["kind"]=="riichi"}
    candidates=[]
    closed=not any(m["type"]!=3 for m in own_player(board)["melds"])
    if (offered and closed and not kokushi_ready(best) and riichi["enabled"] and (riichi["allow_furiten"] or board["self"].get("furiten") is False)
            and (not opponents or riichi["allow_under_riichi_threat"]) and len(opponents)<=riichi["max_threats"]
            and type(wall) is int and wall>=riichi["minimum_wall"]):
        minimum=riichi["minimum_ukeire_under_threat"] if opponents else riichi["minimum_ukeire"]
        for option in options:
            if option["action"]["tile"] not in offered or option["shanten"]!=0 or option["ukeire"]<minimum:continue
            if kokushi_ready(option):continue
            profile=option["wait_value"]
            if profile and ((profile["permanent_furiten"] and not riichi["allow_furiten"]) or profile["riichi_ukeire"]<minimum):continue
            if opponents and not may_push(option,opponents,wall,settings):continue
            if value.get("riichi_speed_first") and option["effective_ukeire"]<best["effective_ukeire"]:continue
            existing=best["wait_value"]
            if (profile and existing and existing["dama_ukeire"]>=riichi["dama_min_waits"]
                    and existing["dama_points"]>=riichi["dama_min_points"]
                    and profile["riichi_points"]<existing["dama_points"]*riichi["dama_gain_ratio"]):continue
            if profile and profile["dama_ukeire"]>=riichi["dama_min_waits"] and profile["dama_points"]>=riichi["dama_min_points"] and profile["riichi_points"]<profile["dama_points"]*riichi["dama_gain_ratio"]:continue
            candidates.append(option)
        if candidates:
            best=offensive(board,candidates,value);chosen=offered[best["action"]["tile"]]
    if chosen["kind"]=="discard":
        kan=_kan_option(request,book,best,diagnostics=kan_notes)
        if kan:return finish(kan,"kan",best)
    return finish(chosen,"attack_push" if opponents and push else "value_attack",best)
