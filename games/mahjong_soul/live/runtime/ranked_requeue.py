"""Budget-bound ranked One More Game clicks from actual result-screen labels."""
import re
import time
from games.mahjong_soul.live.runtime.game_access import input_game_verified
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.visual import decode_frame,sample,distance
from games.mahjong_soul.live.runtime.ranked_end import final_ranked_screen,insufficient_copper,queue_active


def one_more_game(words,scores=()):
    from games.mahjong_soul.live.runtime.result_buttons import result_context
    if not result_context(words,scores):return None
    if any(re.sub(r"[^a-z]","",w["text"].lower()) in ("cancel","cancelmatch","matching","matchmaking") for w in words):return None
    candidates=[]
    lower=[w for w in words if 450<=w.get("x",0)<=1800 and 600<=w.get("y",0)<=1040
           and 12<=w.get("height",0)<=80 and 5<=w.get("width",0)<=500]
    for first in lower:
        line=sorted([w for w in lower if abs((w["y"]+w["height"]/2)-(first["y"]+first["height"]/2))<=12],key=lambda w:w["x"])
        start=line.index(first)
        for size in (1,2,3):
            group=line[start:start+size]
            if len(group)!=size:continue
            if any(b["x"]-(a["x"]+a["width"])>60 or b["x"]<a["x"]+a["width"]-3 for a,b in zip(group,group[1:])):continue
            if "".join(re.sub(r"[^a-z]","",w["text"].lower()) for w in group)!="onemoregame":continue
            left=min(w["x"] for w in group);right=max(w["x"]+w["width"] for w in group)
            top=min(w["y"] for w in group);bottom=max(w["y"]+w["height"] for w in group)
            if 40<=right-left<=500 and bottom<=1080:
                candidates.append((round((left+right)/2),round((top+bottom)/2)))
    candidates=set(candidates)
    return next(iter(candidates)) if len(candidates)==1 else None


def requeue_ranked(buttons,owner,report,geometry,first,words,source):
    state=report.get("state") or {};budget=getattr(owner,"game_budget",None)
    if (state.get("status")!="match_ended" or not (state.get("lobby") or {}).get("ranked")
            or not input_game_verified(owner,report) or budget is None):return None
    key=(report.get("game_connection"),report.get("game_generation",0))
    if key not in budget.completed:return None
    more=one_more_game(words,state.get("scores",[]))
    copper=insufficient_copper(words)
    end=final_ranked_screen(words,state.get("scores",[]))
    if not copper and key in buttons.ranked_deliveries and buttons.pending=="one_more_game" and queue_active(words):
        return {"kind":"status","reason":"waiting_for_ranked_match"}
    point=copper or more or end
    if point is None:
        buttons.ranked_end_wait.pop(key,None)
        if key in buttons.ranked_deliveries and buttons.pending=="one_more_game":
            return {"kind":"status","reason":"waiting_for_ranked_match"}
        return None
    count,last=buttons.ranked_deliveries.get(key,(0,float("-inf")))
    now=getattr(owner,"clock",time.monotonic)()
    exhausted=count>=2 and now-last>=8
    if more and not copper and not budget.done and (count and now-last<3 or count>=2 and not exhausted):
        return {"kind":"status","reason":"waiting_for_ranked_match"}
    x,y=point;token=board_token(report)
    def withheld(reason):
        buttons.ranked_end_wait.pop(key,None)
        owner._record("ranked_requeue_withheld",reason=reason)
        return {"kind":"status","reason":"waiting_for_stable_ranked_results"}
    def stable(a,b):
        return (distance(sample(a,x,y,100,40),sample(b,x,y,100,40))<=1
                and distance(sample(a,960,500,650,650),sample(b,960,500,650,650))<=1)
    rgb=decode_frame(first)
    if source!=first and not stable(decode_frame(source),rgb):return withheld("ocr_source_changed")
    owner.sleep(.15)
    current=buttons.snapshot(owner)
    if owner.recorder.geometry()!=geometry or board_token(current)!=token or key not in budget.completed:return withheld("state_window_or_budget_changed")
    second=owner._frame(geometry,current,"ranked_end_screen" if budget.done else "before_ranked_requeue")
    if second is None or not stable(rgb,decode_frame(second)):return withheld("result_pixels_changed")
    current=buttons.snapshot(owner)
    if hasattr(owner,"_game_limit"):
        finished=owner._game_limit()
        if finished is not None:return finished
    if (owner.recorder.geometry()!=geometry or board_token(current)!=token
            or not input_game_verified(owner,current) or key not in budget.completed):return withheld("final_verification_changed")
    if budget.done:
        if hasattr(owner,"_finish_at_end_screen"):return owner._finish_at_end_screen(current)
        return {"kind":"finished","reason":"game_limit_reached","completed":len(budget.completed),"limit":budget.limit}
    reason="insufficient_copper" if copper else "ranked_requeue_unconfirmed" if exhausted else None
    if more is None and not copper:
        since=buttons.ranked_end_wait.setdefault(key,now)
        if now-since<8:return {"kind":"status","reason":"waiting_for_ranked_continuation_button"}
        reason="ranked_continuation_unavailable"
    if reason:
        owner._record("ranked_continuation_stopped",reason=reason,completed=len(budget.completed),limit=budget.limit)
        if hasattr(owner,"_stop_ranked_continuation"):return owner._stop_ranked_continuation(current,reason)
        return {"kind":"finished","reason":reason,"completed":len(budget.completed),"limit":budget.limit}
    buttons.ranked_end_wait.pop(key,None)
    buttons.ranked_deliveries[key]=(count+1,getattr(owner,"clock",time.monotonic)())
    owner._record("ranked_requeue_attempt",pixel=[x,y],completed=len(budget.completed),limit=budget.limit,attempt=count+1)
    owner.controller.backend.click(x/1919,y/1079,1920,1080)
    buttons.pending="one_more_game"
    owner._record("ranked_requeue_delivered",completed=len(budget.completed),limit=budget.limit)
    return {"kind":"status","reason":"ranked_requeue_submitted"}
