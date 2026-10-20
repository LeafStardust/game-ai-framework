"""Reconcile reviewed client assists, with observed-state confirmation."""
import base64
import json
from pathlib import Path
from games.mahjong_soul.live.runtime.visual import decode_frame,sample,distance
from games.mahjong_soul.live.runtime.input import board_token


class AssistButtons:
    def __init__(self):
        self.profile=json.loads(Path(__file__).with_name("assist_samples.json").read_text())
        self.pending=None;self.observed={};self.last_scan=float("-inf");self.failed=False

    def read(self,png):
        rgb=decode_frame(png);states={}
        for key,row in self.profile["rows"].items():
            y=row["y"]
            if distance(sample(rgb,164,y,150,34),base64.b64decode(row["label"]))>7:
                return None
            color=[sum(rgb[(yy*1920+xx)*3+c] for yy in range(y-3,y+4) for xx in range(57,64))/49 for c in range(3)]
            scores={name:sum(abs(a-b) for a,b in zip(color,self.profile[name]))/3 for name in ("on","off")}
            choice=min(scores,key=scores.get)
            if scores[choice]>18:return None
            states[key]=choice=="on"
        return states

    def poll(self,owner,desired):
        if self.failed:return None
        if owner.clock()-self.last_scan<.5:return None
        self.last_scan=owner.clock()
        report=owner._current();state=report.get("state") or {}
        if state.get("status")!="tracking" or state.get("player_count")!=3:return None
        if owner.require_ai and (report.get("game_connection"),report.get("game_generation",0)) not in owner.ai_games:return None
        if owner.controller.snapshot()["status"]!="idle":return None
        geometry=owner.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"])!=(1920,1080):return None
        first=owner._frame(geometry,report,"assist_preflight")
        if first is None:return None
        states=self.read(first)
        if self.pending:
            key,target,deadline=self.pending
            if (key=="panel" and states is not None) or (states is not None and states.get(key)==target):
                owner._record("assist_confirmed",control=key,enabled=target);self.pending=None
            elif owner.clock()>deadline:
                owner._record("assist_unconfirmed",control=key,enabled=target)
                self.failed=True;self.pending=None
                owner.halted="Assist switch outcome unconfirmed; inspect switches before restarting"
                return {"kind":"blocked","reason":owner.halted}
            else:return {"kind":"status","reason":"awaiting_assist_confirmation"}
        if states is None:
            self.observed={}
            if distance(sample(decode_frame(first),40,833,40,40),base64.b64decode(self.profile["collapsed_arrow"]))>5:return None
            key,target,x,y="panel",True,40,833
        else:
            self.observed=states
            # Disable irreversible automatic discards first when unlocking.
            keys=("auto_discard","skip_calls","auto_kita","auto_win")
            key=next((k for k in keys if states[k]!=desired[k]),None)
            if key is None:return None
            target=desired[key];x,y=60,self.profile["rows"][key]["y"]
        token=board_token(report);owner.sleep(.1)
        if owner.recorder.geometry()!=geometry or board_token(owner._current())!=token:return None
        second=owner._frame(geometry,report,"before_assist_input")
        if second is None:return None
        if states is not None:
            if self.read(second)!=states:return None
        elif distance(sample(decode_frame(second),40,833,40,40),sample(decode_frame(first),40,833,40,40))>1:return None
        if owner.recorder.geometry()!=geometry or board_token(owner._current())!=token:return None
        self.pending=key,target,owner.clock()+3
        owner._record("assist_attempt",control=key,enabled=target,pixel=[x,y])
        try:owner.controller.backend.click(x/1919,y/1079,1920,1080)
        except Exception:
            self.failed=True;owner.halted="Assist input failed; inspect before restarting"
            raise
        owner._record("assist_delivered",control=key,enabled=target)
        return {"kind":"status","reason":"assist_submitted"}
