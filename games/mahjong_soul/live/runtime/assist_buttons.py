"""Reconcile reviewed client assists, with observed-state confirmation."""
import base64
import json
from pathlib import Path
from games.mahjong_soul.live.runtime.visual import decode_frame,sample,distance
from games.mahjong_soul.live.runtime.input import board_token


class AssistButtons:
    def __init__(self):
        self.profile=json.loads(Path(__file__).with_name("assist_samples.json").read_text())
        self.unavailable=set();self.context=None
        self.layout=None;self.pending=None;self.observed={};self.last_scan=float("-inf");self.failed=False
        self.last_recovery_scan=float("-inf")

    def collapsed(self,rgb):
        states={}
        for key,row in self.profile["collapsed"].items():
            foreground=set();green=set()
            for dy in range(48):
                for dx in range(37):
                    x,y=21+dx,row["y"]-24+dy
                    r,g,b=rgb[(y*1920+x)*3:(y*1920+x)*3+3];index=dy*37+dx
                    if g>65 and g>r*1.4 and g>b*1.2:
                        foreground.add(index);green.add(index)
                    elif r>48 and g>60 and b>75 and max(r,g,b)-min(r,g,b)<65:foreground.add(index)
            variants=[set(row["mask"]),*(set(mask) for mask in row.get("alternates",[]))]
            expected=max(variants,key=lambda mask:len(foreground & mask)/len(foreground | mask))
            if len(foreground & expected)/len(foreground | expected)<.8:return None
            ratio=len(green & expected)/len(expected)
            if .1<ratio<.9:return None
            states[key]=ratio>=.9
        return states

    def read(self,png):
        rgb=decode_frame(png)
        collapsed=self.collapsed(rgb)
        if collapsed is not None:
            self.layout="collapsed"
            return collapsed
        self.layout="expanded"
        states={}
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

    @staticmethod
    def guard(report,key):
        state=report.get("state") or {}
        # Opponents' unrelated discards must not starve sidebar preparation.
        # Our hand, round, connection and declarations still bind the action.
        return (report.get("game_connection"),report.get("game_generation",0),report.get("connection_open"),state.get("status"),
                tuple(sorted((state.get("round") or {}).items())),
                tuple(sorted(state.get("hand",[]))),tuple(state.get("riichi",[])),tuple(state.get("doras",[])))

    def recover(self,owner):
        """Re-observe an uncertain toggle; never click or assume its outcome."""
        if not self.failed or owner.clock()-self.last_recovery_scan<.5:return False
        self.last_recovery_scan=owner.clock()
        def current_report():
            try:return owner._current()
            except ValueError:
                if not hasattr(owner,"_result_snapshot"):raise
                report=owner._result_snapshot()
                if (report.get("state") or {}).get("status") not in ("round_ended","match_ended"):raise
                return report
        report=current_report();state=report.get("state") or {}
        if state.get("status") not in ("tracking","round_ended","match_ended") or state.get("player_count")!=3:return False
        if owner.controller.snapshot()["status"]!="idle":return False
        if owner.require_ai and (report.get("game_connection"),report.get("game_generation",0)) not in owner.ai_games:return False
        geometry=owner.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"])!=(1920,1080):return False
        token=self.guard(report,None)
        first=owner._frame(geometry,report,"assist_recovery")
        states=self.read(first) if first is not None else None
        if states is None:return False
        layout=self.layout;owner.sleep(.1)
        if owner.recorder.geometry()!=geometry or self.guard(current_report(),None)!=token:return False
        second=owner._frame(geometry,report,"assist_recovery_confirmation")
        current=self.read(second) if second is not None else None
        if current!=states or self.layout!=layout:return False
        if owner.recorder.geometry()!=geometry or self.guard(current_report(),None)!=token:return False
        self.pending=None;self.observed=current;self.failed=False;self.last_scan=float("-inf")
        owner._record("assist_recovered",observed=current,confirmation="two_fresh_matching_frames")
        return True

    def poll(self,owner,desired,*,prepare_optional=True):
        if self.failed:return None
        def permitted(key):
            return prepare_optional or desired[key] is False
        mismatch=bool(self.observed) and any(self.observed.get(k)!=desired[k] for k in desired if k not in self.unavailable
                                            and permitted(k))
        if owner.clock()-self.last_scan<(.1 if self.pending or mismatch else .5):
            return {"kind":"status","reason":"awaiting_assist_setup"} if mismatch else None
        self.last_scan=owner.clock()
        report=owner._current();state=report.get("state") or {}
        if state.get("status")!="tracking" or state.get("player_count")!=3:return None
        meta=state.get("round") or {}
        context=(report.get("game_connection"),report.get("game_generation",0),meta.get("chang"),meta.get("ju"),meta.get("ben"))
        if context!=self.context:
            if self.context is not None and self.pending and self.pending[0] in ("auto_win","auto_kita"):
                owner._record("assist_retired",control=self.pending[0],enabled=self.pending[1],reason="new_hand")
                self.pending=None
            self.context=context;self.unavailable.clear();self.observed={}
        if owner.require_ai and (report.get("game_connection"),report.get("game_generation",0)) not in owner.ai_games:return None
        if owner.controller.snapshot()["status"]!="idle":return None
        geometry=owner.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"])!=(1920,1080):return None
        captured=owner.clock()
        first=owner._frame(geometry,report,"assist_preflight")
        if first is None:return None
        states=self.read(first)
        if self.pending:
            key,target,deadline=self.pending
            if states is not None and states.get(key)==target:
                owner._record("assist_confirmed",control=key,enabled=target);self.pending=None
            elif (states is not None and desired.get(key)!=target
                  and states.get(key)==desired.get(key)):
                # A hand can finish before the clicked Riichi assist is visible.
                # Resolve from a fresh observed state, never replay the old click.
                owner._record("assist_superseded",control=key,enabled=target,
                              observed=states[key],desired=desired[key])
                self.pending=None
            elif owner.clock()>deadline:
                owner._record("assist_unconfirmed",control=key,enabled=target)
                if key in ("auto_win","auto_kita","skip_calls","auto_discard") and target is True and states is not None and states.get(key) is False:
                    # A fresh observation proves the optional automatic switch
                    # stayed OFF. Native policy actions remain available.
                    # Do not replay the uncertain click within this hand.
                    self.unavailable.add(key);self.pending=None;self.observed=states
                    owner._record("assist_native_fallback",control=key,reason="verified_off_after_timeout")
                    return None
                self.failed=True;self.pending=None
                owner.halted="Assist switch outcome unconfirmed; automatically rechecking switch states"
                return {"kind":"status","reason":"waiting_for_assist_recovery"}
            else:
                if (not prepare_optional and key in ("auto_win","auto_kita") and target is True
                        and states is not None and states.get(key) is False):
                    self.observed=states
                    return None
                return {"kind":"status","reason":"awaiting_assist_confirmation"}
        if states is None:
            self.observed={}
            return None
        self.observed=states
        layout=self.layout
        # Disable irreversible automatic discards first when unlocking.
        order=("auto_discard","skip_calls","auto_win","auto_kita")
        keys=tuple(k for k in order if states[k] and not desired[k])+tuple(
            k for k in ("auto_win","auto_kita","skip_calls","auto_discard") if not states[k] or desired[k])
        key=next((k for k in keys if k not in self.unavailable and states[k]!=desired[k]
                  and permitted(k)),None)
        if key is None:
            owner.assist_frame=(first,geometry,board_token(report),captured)
            return None
        target=desired[key]
        x,y=(40,self.profile["collapsed"][key]["y"]) if layout=="collapsed" else (60,self.profile["rows"][key]["y"])
        token=self.guard(report,key);owner.sleep(.1)
        if owner.recorder.geometry()!=geometry or self.guard(owner._current(),key)!=token:return None
        second=owner._frame(geometry,report,"before_assist_input")
        if second is None:return None
        if self.read(second)!=states or self.layout!=layout:return None
        current=owner._current()
        if owner.recorder.geometry()!=geometry or self.guard(current,key)!=token:return None
        if key in ("skip_calls","auto_discard"):
            if hasattr(owner,"_assist_target_allowed"):
                if not owner._assist_target_allowed(current,key,target):return None
            elif board_token(current)!=board_token(report):return None
        self.pending=key,target,owner.clock()+3
        owner._record("assist_attempt",control=key,enabled=target,pixel=[x,y])
        try:owner.controller.backend.click(x/1919,y/1079,1920,1080)
        except Exception:
            self.failed=True;owner.halted="Assist input failed; inspect before restarting"
            raise
        owner._record("assist_delivered",control=key,enabled=target)
        # The click backend already waits for release consumption. Read its
        # outcome immediately instead of adding a half-second polling wait.
        if owner.recorder.geometry()==geometry and self.guard(owner._current(),key)==token:
            after=owner._frame(geometry,report,"assist_confirmation")
            current=self.read(after) if after is not None else None
            if current is not None and current.get(key)==target:
                owner._record("assist_confirmed",control=key,enabled=target)
                self.pending=None;self.observed=current
                if all(current[k]==desired[k] for k in keys):return None
        return {"kind":"status","reason":"assist_submitted"}
