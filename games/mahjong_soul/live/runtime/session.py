"""Durable, bounded local evidence for automatic play. Never injects input."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time


class SessionJournal:
    def __init__(self, root, *, max_bytes=2*1024**3):
        self.directory=Path(root)/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")
        self.directory.mkdir(parents=True,exist_ok=False)
        (self.directory/"frames").mkdir()
        self.stream=(self.directory/"events.jsonl").open("x",encoding="utf-8")
        self.current_key=None
        self.max_bytes=max_bytes;self.used=0;self.sequence=0;self.last_frame=None;self.last_digest=None
        self.summary={"version":1,"started":time.time(),"decisions":0,"inputs":0,"confirmations":0,"errors":0,"status":"running"}
        self.write("started")

    def write(self, kind, **data):
        self.sequence+=1
        row={"version":1,"sequence":self.sequence,"timestamp":time.time(),"monotonic":time.monotonic(),"kind":kind,**data}
        encoded=json.dumps(row,ensure_ascii=False,default=lambda x:asdict(x) if is_dataclass(x) else str(x))+"\n"
        cost=len(encoded.encode("utf-8"))
        if self.used+cost>self.max_bytes: raise OSError("Session recording limit reached; stopping input")
        self.stream.write(encoded);self.stream.flush();self.used+=cost
        if kind=="plan":self.current_key=data.get("attempt_key")
        if kind=="input_attempt":os.fsync(self.stream.fileno())
        if kind=="decision":self.summary["decisions"]+=1
        if kind=="input_attempt":self.summary["inputs"]+=1
        if kind=="confirmed":self.summary["confirmations"]+=1
        if kind in ("error","blocked"):self.summary["errors"]+=1
        self.summary.update(last_event=kind,last_sequence=self.sequence,last_frame=self.last_frame,last_timestamp=row["timestamp"])
        # events.jsonl is the durable source of truth. Updating this derived
        # convenience file in place avoids Windows indexer rename locks.
        (self.directory/"summary.json").write_text(json.dumps(self.summary,indent=2)+"\n",encoding="utf-8")
        return row

    def frame(self, png, *, report=None, geometry=None, phase="observe"):
        if png is None:return None
        digest=hashlib.sha256(png).hexdigest()
        if digest==self.last_digest:return self.last_frame
        if self.used+len(png)+8192>self.max_bytes:raise OSError("Session recording limit reached; stopping input")
        name=f"frames/{self.sequence+1:07d}.png"
        (self.directory/name).write_bytes(png);self.used+=len(png)
        self.last_digest=digest;self.last_frame=name
        self.write("frame",image=name,sha256=digest,phase=phase,geometry=geometry,report=report)
        return name

    def close(self, reason="stopped"):
        if self.stream.closed:return
        self.summary.update(status=reason,ended=time.time())
        try:self.write("stopped",reason=reason)
        finally:
            self.stream.close()
            (self.directory/"summary.json").write_text(json.dumps(self.summary,indent=2)+"\n",encoding="utf-8")


class RecordingMouse:
    """Journal before delivery; a journal failure cannot permit unrecorded input."""
    def __init__(self, backend, journal):self.backend,self.journal=backend,journal
    def _send(self,method,args):
        self.journal.write("input_attempt",method=method,coordinates=list(args),preceding_image=self.journal.last_frame,attempt_key=self.journal.current_key)
        try:getattr(self.backend,method)(*args)
        except Exception as error:
            self.journal.write("input_failure",method=method,error_type=type(error).__name__,reason=str(error))
            raise
        self.journal.write("input_delivered",method=method)
    def park(self,*args):
        self.journal.write("cursor_park",client_size=list(args))
        self.backend.park(*args)
    def click(self,*args):self._send("click",args)
    def double_click(self,*args):self._send("double_click",args)


class AgentLease:
    """OS-held lock; a crash releases it without clearing an input ledger."""
    def __init__(self,path):
        import os
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.stream=self.path.open("a+b")
        if self.path.stat().st_size==0:self.stream.write(b"0");self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close()
            raise ValueError("Another Mahjong agent is already running") from error
    def close(self):self.stream.close()


def prior_attempts(root):
    """Retain delivered/uncertain steps across restarts; never reconstruct pending input."""
    result=set()
    for path in Path(root).glob("*/events.jsonl"):
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:row=json.loads(line)
                except ValueError:continue  # Input is never sent after an incomplete log write.
                key=row.get("attempt_key")
                if row.get("kind")=="input_attempt" and isinstance(key,list) and len(key)==6:
                    if isinstance(key[0],str) and all(type(value) is int for value in key[1:]):result.add(tuple(key))
    return result
