"""Post-round Continue/Confirm clicks from OCR and a fresh matching pixel observation.

Separate from gameplay proposals: only known result states and explicit labels
are accepted. Completed custom AI rooms can restart from a verified Start view.
"""
from concurrent.futures import ThreadPoolExecutor
import base64
import time
import json
import os
from pathlib import Path
import subprocess
import tempfile
import re
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.visual import decode_frame,distance,sample


def windows_words(png):
    decode_frame(png)  # Enforce the same physical viewport as native input.
    with tempfile.TemporaryDirectory(prefix="mahjong-result-") as directory:
        path=Path(directory)/"frame.png";path.write_bytes(png)
        result=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass",
                               "-File",str(Path(__file__).with_name("windows_ocr.ps1")),"-ImagePath",str(path)],
                              capture_output=True,text=True,encoding="utf-8",timeout=12,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        if result.returncode:raise ValueError("Result-button OCR unavailable: "+result.stderr.strip()[:200])
        return json.loads(result.stdout)["words"]


def result_button(words,scores=()):
    """Require a unique complete label in the lower portion of a result view."""
    context={re.sub(r"[^a-z0-9]","",w["text"].lower()) for w in words}
    score_values={str(n) for n in scores if type(n) is int}
    verified_scores=sum(re.sub(r"[^a-z0-9]","",w["text"].lower()) in score_values for w in words)>=2
    score_context=verified_scores or ("counter" in context and any(t.endswith("repeat") for t in context)) or (len(context & {"st","nd","rd","th","1st","2nd","3rd","4th"})>=2 and sum(t.isdigit() and len(t)>=4 for t in context)>=2)
    if not score_context and not any(t in {"han","fu","yakuman","points","score","scores","result","results","ranking","rank","1st","2nd","3rd","4th","exhaustive"}
               or re.fullmatch(r"[0-9]+(?:han|fu)",t) for t in context):
        raise ValueError("Result-screen context is not visible")
    matches=[]
    for word in words:
        label=re.sub(r"[^a-z]","",word["text"].lower())
        if label not in ("continue","confirm"):continue
        x,y,w,h=(word[k] for k in ("x","y","width","height"))
        if not (450<=x<=1800 and 600<=y<=1040 and 25<=w<=350 and 12<=h<=80):continue
        matches.append((label,round(x+w/2),round(y+h/2)))
    if len(matches)!=1:raise ValueError("No unique result Continue/Confirm label")
    return matches[0]


def heading_matches(actual,reference):
    """Match the reviewed heading ink independently of changing board pixels."""
    if distance(actual,reference)<=3:return True
    def ink(value):
        result=set()
        for i in range(0,len(value),3):
            r,g,b=value[i:i+3]
            if (r>120 and r>g*1.12 and g>b*1.2) or (min(r,g,b)>160 and max(r,g,b)-min(r,g,b)<55):
                result.add(i//3)
        return result
    expected=ink(reference);observed=ink(actual)
    return len(expected)>=16 and len(expected&observed)/len(expected|observed)>=.9


class ResultButtons:
    def __init__(self,ocr=windows_words):
        self.ocr=ocr;self.attempted=set();self.pending=None;self.deliveries={};self.restart_attempted=set()
        self.worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix="mahjong-result-ocr") if ocr is windows_words else None
        self.ocr_job=None;self.ocr_source=None
        data=json.loads(Path(__file__).with_name("result_samples.json").read_text())
        self.templates=data["templates"]

    def close(self):
        if self.worker is not None:self.worker.shutdown(wait=False,cancel_futures=True)

    def words(self,png,token,geometry):
        """OCR workers read pixels only; all state checks and input stay here."""
        self.ocr_source=png
        if self.worker is None:return self.ocr(png)
        if self.ocr_job is not None:
            future,source,old_token,old_geometry=self.ocr_job
            if not future.done():return None
            self.ocr_job=None
            words=future.result()
            if old_token==token and old_geometry==geometry:
                self.ocr_source=source
                return words
        self.ocr_job=(self.worker.submit(self.ocr,png),png,token,dict(geometry))
        return None

    def visual_button(self,png):
        rgb=decode_frame(png);matches=[]
        for row in self.templates:
            x,y=row["pixel"];cx,cy,w,h=row["context_bounds"]
            if (distance(sample(rgb,x,y,100,40),base64.b64decode(row["sample"]))<=3
                    and heading_matches(sample(rgb,cx,cy,w,h),base64.b64decode(row["context_sample"]))):
                matches.append((row["label"],x,y,row["stage"]))
        if not matches:return None
        # OCR centers can differ by a pixel from the reviewed center. Multiple
        # references to that same button are agreement, not two visible buttons.
        if (len({(m[0],m[3]) for m in matches})==1
                and max(m[1] for m in matches)-min(m[1] for m in matches)<=4
                and max(m[2] for m in matches)-min(m[2] for m in matches)<=4):return matches[0]
        return None

    def remember(self,png,words,label,x,y,stage):
        # Learn only from OCR-verified result text and a separate result heading.
        markers={"counter","han","fu","yakuman","score","scores","result","results","ranking","rank"}
        candidates=[w for w in words if re.sub(r"[^a-z]","",w["text"].lower()) in markers
                    and w["y"]<600 and 12<=w["height"]<=80 and 10<=w["width"]<=350]
        if not candidates:return
        word=candidates[0];cx=round(word["x"]+word["width"]/2);cy=round(word["y"]+word["height"]/2)
        w=max(25,round(word["width"]));h=max(20,round(word["height"]))
        rgb=decode_frame(png)
        context=sample(rgb,cx,cy,w,h);label_sample=sample(rgb,x,y,100,40)
        if max(context)-min(context)<20 or max(label_sample)-min(label_sample)<20:return
        self.templates.append({"label":label,"pixel":[x,y],"stage":stage,
            "sample":base64.b64encode(label_sample).decode(),
            "context_bounds":[cx,cy,w,h],"context_sample":base64.b64encode(context).decode()})
        self.templates=self.templates[-32:]

    @staticmethod
    def ocr_stage(words):
        text=" ".join(w["text"].lower() for w in words)
        if "exhaustive" in text and "draw" in text:return "exhaustive_draw"
        if "counter" in text:return "round_scores"
        tokens=[re.sub(r"[^a-z0-9]","",w["text"].lower()) for w in words]
        if any(re.fullmatch(r"[0-9]*(?:han|fu)",t) or t=="yakuman" for t in tokens):return "win_detail"
        return "match_results"

    @staticmethod
    def snapshot(owner):
        return owner._result_snapshot() if hasattr(owner,"_result_snapshot") else owner._current()

    def poll(self,owner):
        # Ordinary play must not invoke result-only source checks or OCR.
        reader=getattr(owner,"reader",None)
        if reader is not None and not self.pending:
            cached=reader.snapshot().get("state") or {}
            if cached.get("status") not in ("round_ended","match_ended"):return None
        report=self.snapshot(owner);state=report.get("state") or {}
        if state.get("status") not in ("round_ended","match_ended"):
            if self.pending:
                owner._record("result_button_confirmed",button=self.pending,confirmation="game_state_advanced")
                self.pending=None
            return None
        if owner.require_ai and (report.get("game_connection"),report.get("game_generation",0)) not in owner.ai_games:return None
        if owner.controller.snapshot()["status"]!="idle":return None
        geometry=owner.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"])!=(1920,1080):return None
        token=board_token(report)
        first=owner._frame(geometry,report,"result_preflight")
        if first is None:return None
        recognized=self.visual_button(first)
        method="template"
        if recognized is None:
            words=self.words(first,token,geometry)
            if words is None:return None
            try:button=result_button(words,state.get("scores",[]))
            except ValueError:
                from games.mahjong_soul.live.runtime.room_restart import restart_room
                return restart_room(self,owner,report,geometry,first,words,self.ocr_source)
            label,x,y=button;stage=self.ocr_stage(words);method="ocr"
            source=self.ocr_source
            self.remember(source,words,label,x,y,stage)
            if source!=first:
                current=self.visual_button(first)
                same=(current is not None and current[0]==label and current[3]==stage
                      and abs(current[1]-x)<=4 and abs(current[2]-y)<=4)
                if same:recognized=current
                if not same:
                    # An unknown heading may not be cacheable. Require both
                    # the label and central result panel to remain unchanged.
                    a=decode_frame(source);b=decode_frame(first)
                    if (distance(sample(a,x,y,100,40),sample(b,x,y,100,40))>1
                            or distance(sample(a,960,500,650,650),sample(b,960,500,650,650))>1):
                        owner._record("result_button_withheld",button=label,reason="async_ocr_screen_changed")
                        return None
        else:label,x,y,stage=recognized
        # Win detail and score transfer can share a Confirm position. Separate
        # stages; allow one delayed retry only after another full visual check.
        meta=state.get("round") or {}
        key=(report.get("game_connection"),report.get("game_generation",0),meta.get("chang"),meta.get("ju"),meta.get("ben"),stage,label,x//20,y//20)
        now=getattr(owner,"clock",time.monotonic)()
        count,last=self.deliveries.get(key,(0,float("-inf")))
        if count>=2 or (count and now-last<1.5):return None
        def reject(reason):
            owner._record("result_button_withheld",button=label,reason=reason)
            return None
        owner.sleep(.15)
        if owner.recorder.geometry()!=geometry:return reject("window_changed_after_ocr")
        if board_token(self.snapshot(owner))!=token:return reject("state_changed_after_ocr")
        second=owner._frame(geometry,report,"before_result_input")
        if second is None:return reject("fresh_frame_unavailable")
        if recognized is not None and self.visual_button(second)!=recognized:
            return reject("result_context_changed")
        # OCR establishes the label and position. Requiring the same label pixels
        # in a fresh frame validates that finding without another slow OCR run.
        if distance(sample(decode_frame(first),x,y,100,40),sample(decode_frame(second),x,y,100,40))>1:
            return reject("label_pixels_changed")
        if owner.recorder.geometry()!=geometry:return reject("window_changed_before_click")
        if board_token(self.snapshot(owner))!=token:return reject("state_changed_before_click")
        self.attempted.add(key);self.pending=label
        self.deliveries[key]=(count+1,getattr(owner,"clock",time.monotonic)())
        owner._record("result_button_attempt",button=label,pixel=[x,y],board_token=token,
                      stage=stage,recognition=method,attempt=count+1)
        try:owner.controller.backend.click(x/1919,y/1079,1920,1080)
        except Exception:
            owner.halted="Result button input failed; inspect before retry"
            raise
        owner._record("result_button_delivered",button=label)
        return {"kind":"status","reason":"result_button_submitted","button":label}
