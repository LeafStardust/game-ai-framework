"""Post-round Continue/Confirm clicks from OCR and a fresh matching pixel observation.

Separate from gameplay proposals: only known result states and explicit labels
are accepted. No menus, room joins, purchases or new matches are selected.
"""
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


class ResultButtons:
    def __init__(self,ocr=windows_words):
        self.ocr=ocr;self.attempted=set();self.pending=None

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
        words=self.ocr(first)
        try:button=result_button(words,state.get("scores",[]))
        except ValueError:
            return None
        label,x,y=button
        # One click per label/position/round; no repeated click during animation.
        meta=state.get("round") or {}
        key=(report.get("game_connection"),report.get("game_generation",0),meta.get("chang"),meta.get("ju"),meta.get("ben"),label,x//20,y//20)
        if key in self.attempted:return None
        def reject(reason):
            owner._record("result_button_withheld",button=label,reason=reason)
            return None
        owner.sleep(.15)
        if owner.recorder.geometry()!=geometry:return reject("window_changed_after_ocr")
        if board_token(self.snapshot(owner))!=token:return reject("state_changed_after_ocr")
        second=owner._frame(geometry,report,"before_result_input")
        if second is None:return reject("fresh_frame_unavailable")
        # OCR establishes the label and position. Requiring the same label pixels
        # in a fresh frame validates that finding without another slow OCR run.
        if distance(sample(decode_frame(first),x,y,100,40),sample(decode_frame(second),x,y,100,40))>1:
            return reject("label_pixels_changed")
        if owner.recorder.geometry()!=geometry:return reject("window_changed_before_click")
        if board_token(self.snapshot(owner))!=token:return reject("state_changed_before_click")
        self.attempted.add(key);self.pending=label
        owner._record("result_button_attempt",button=label,pixel=[x,y],board_token=token)
        try:owner.controller.backend.click(x/1919,y/1079,1920,1080)
        except Exception:
            owner.halted="Result button input failed; inspect before retry"
            raise
        owner._record("result_button_delivered",button=label)
        return {"kind":"status","reason":"result_button_submitted","button":label}
