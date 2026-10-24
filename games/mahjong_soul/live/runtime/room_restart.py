"""Restart the same completed custom AI room from a fresh verified Start view."""
import re
import math
from games.mahjong_soul.live.runtime.visual import decode_frame
from games.mahjong_soul.live.runtime.input import board_token


def room_start(words,lobby):
    count=lobby.get("player_count");room=lobby.get("room_id")
    if count not in (3,4) or not room or lobby.get("ai") is not True:return None
    if lobby.get("unsupported_rules"):return None
    def compact(w):return re.sub(r"[^a-z0-9#]","",w["text"].lower())
    headers=[w for w in words if compact(w)=="room#"+str(room) and 500<w["x"]<1300 and w["y"]<150]
    formats=[w for w in words if compact(w)==str(count)+"player" and w["x"]>1550 and 150<w["y"]<250]
    length={"east":"onewind","south":"twowind"}.get(lobby.get("match_length"))
    if not any(compact(w)==length and w["x"]>1550 and 220<w["y"]<270 for w in words):return None
    bots=[]
    for word in words:
        if compact(word) not in ("ai","al") or not (0<word["x"]<1550 and 780<word["y"]<930):continue
        # Windows OCR splits '(Normal)' into several tokens and reads I as l.
        if any(compact(w).startswith(("normal","norma","easy","hard"))
               and 0<w["x"]-word["x"]<100 and abs(w["y"]-word["y"])<12 for w in words):
            bots.append(word)
    if len(headers)!=1 or len(formats)!=1 or len(bots)!=count-1:return None
    if len({round(w["x"]/80) for w in bots})!=count-1:return None
    starts=[w for w in words if compact(w)=="start" and 600<w["x"]<1500 and 900<w["y"]<1040
            and 40<w["width"]<300 and 15<w["height"]<90]
    if len(starts)!=1:return None
    word=starts[0]
    return round(word["x"]+word["width"]/2),round(word["y"]+word["height"]/2)


def unchanged_room(a,b,x,y,words):
    """Compare every pixel in text/control regions, including the full roster."""
    a=decode_frame(a);b=decode_frame(b)
    headers=[w for w in words if w["text"].lower().startswith("room#") and 500<w["x"]<1300 and w["y"]<150]
    regions=[(1600,175,280,120),(x-100,y-35,200,70)]
    regions.extend((math.floor(w["x"]),math.floor(w["y"]),
                    math.ceil(w["x"]+w["width"])-math.floor(w["x"]),
                    math.ceil(w["y"]+w["height"])-math.floor(w["y"])) for w in headers)
    regions.extend((w["x"],w["y"],w["width"],w["height"]) for w in words
                   if 0<w["x"]<1550 and 780<w["y"]<930)
    for left,top,width,height in regions:
        total=0
        for row in range(top,top+height):
            start=(row*1920+left)*3;end=start+width*3
            total+=sum(abs(u-v) for u,v in zip(a[start:end],b[start:end]))
        if total>width*height*3:return False
    return True


def restart_room(buttons,owner,report,geometry,first,words,source):
    state=report.get("state") or {};lobby=state.get("lobby") or {}
    if state.get("status")!="match_ended" or lobby.get("identified") is not True:return None
    # Match authentication alone is insufficient: the visible current roster
    # must independently contain only AI opponents in the same custom room.
    if (report.get("game_connection"),report.get("game_generation",0)) not in owner.ai_games:return None
    found=room_start(words,lobby)
    if found is None:
        context=(lobby.get("room_id"),tuple(w["text"] for w in words if w["y"]<150))
        if getattr(buttons,"restart_rejection",None)!=context:
            owner._record("room_start_withheld",reason="room_header_format_or_ai_roster_not_verified",
                          room_id=lobby.get("room_id"),header_words=list(context[1]))
            buttons.restart_rejection=context
        return None
    key=(report.get("game_connection"),report.get("game_generation",0),lobby["room_id"])
    if key in buttons.restart_attempted:return None
    x,y=found;token=board_token(report)
    # An inactive/grey Start label is not authorization to click it.
    from games.mahjong_soul.live.runtime.visual import sample
    face=sample(decode_frame(first),x,y,240,70)
    gold=sum(r>150 and g>80 and b<150 and r>g*1.15 for r,g,b in zip(face[0::3],face[1::3],face[2::3]))
    if gold<len(face)//3*.35:return None
    if source!=first and not unchanged_room(source,first,x,y,words):return None
    owner.sleep(.15)
    if owner.recorder.geometry()!=geometry or board_token(buttons.snapshot(owner))!=token:return None
    second=owner._frame(geometry,report,"before_room_start")
    if second is None or not unchanged_room(first,second,x,y,words):return None
    if owner.recorder.geometry()!=geometry or board_token(buttons.snapshot(owner))!=token:return None
    buttons.restart_attempted.add(key)
    owner._record("room_start_attempt",room_id=lobby["room_id"],pixel=[x,y],board_token=token)
    try:owner.controller.backend.click(x/1919,y/1079,1920,1080)
    except Exception:
        owner.halted="Room Start input failed; inspect before restarting"
        raise
    buttons.pending="start"
    owner._record("room_start_delivered",room_id=lobby["room_id"])
    return {"kind":"status","reason":"room_start_submitted"}
