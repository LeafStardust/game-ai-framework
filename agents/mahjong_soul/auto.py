"""Playbook-driven, opt-in 1080p native discards and calibrated Skip."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import time

from agents.mahjong_soul.policy import make_policy
from agents.mahjong_soul.shadow import ShadowFollower, format_suggestion
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import board_token, plan_discard
from games.mahjong_soul.live.runtime.layout import discard_profile, profile_for_size
from games.mahjong_soul.live.runtime.skip import plan_skip
from games.mahjong_soul.live.runtime.visual import TileVision, distance


class AutoFollower(ShadowFollower):
    def __init__(self, schema, *, controller, recorder, vision, enabled=False,
                 sleep=time.sleep, **kwargs):
        super().__init__(schema, **kwargs)
        self.controller, self.recorder, self.vision = controller, recorder, vision
        self.enabled, self.sleep = enabled, sleep
        self.halted = None
        self.source = None
        self.candidate = None
        self.candidate_until = None

    def _consume(self, row):
        result = super()._consume(row)
        decoded = (result or {}).get("liqi")
        if decoded:
            connection = row["connection"]
            for event in decoded.get("events", []):
                self.controller.observe(connection,event,now=self.clock())
            self.controller.observe_message(connection,decoded,row["direction"]=="client",now=self.clock())
        return result

    def _skip_profile(self, report):
        path = Path(__file__).resolve().parents[2]/"games/mahjong_soul/live/layouts/skip-chi-offer.json"
        return profile_for_size(json.loads(path.read_text(encoding="utf-8")),(1920,1080))

    def _plan(self, event):
        report = self._current()
        if board_token(report) != event["board_token"]: raise ValueError("Board changed before visual check")
        geometry = self.recorder.geometry()
        if not geometry or (geometry["width"],geometry["height"]) != (1920,1080):
            raise ValueError("Foreground Mahjong client must be 1920x1080")
        action = event["action"]
        if action["kind"] == "discard": profile = discard_profile(report,(1920,1080))
        else: profile = self._skip_profile(report)
        first = self.recorder.frame(geometry)
        if first is None: raise ValueError("Cannot capture Mahjong client")
        if action["kind"] == "discard":
            tiles, samples = self.vision.hand(first,profile,report["state"]["hand"])
        else:
            # Check offer compatibility before any input or visual assumption.
            plan_skip(report,profile,now=self.clock())
            samples = [self.vision.skip_visible(first,profile)]
        self.sleep(.1)
        if self.recorder.geometry() != geometry: raise ValueError("Game window moved during verification")
        second = self.recorder.frame(geometry)
        if second is None: raise ValueError("Cannot recheck Mahjong client")
        if action["kind"] == "discard":
            current_tiles, current_samples = self.vision.hand(second,profile,report["state"]["hand"])
            if current_tiles != tiles: raise ValueError("Visible hand changed")
        else: current_samples = [self.vision.skip_visible(second,profile)]
        if any(distance(a,b)>1 for a,b in zip(samples,current_samples)):
            raise ValueError("Game UI is still moving")
        current = self._current()
        if board_token(current) != event["board_token"]: raise ValueError("Board changed during visual check")
        if self.recorder.geometry() != geometry: raise ValueError("Game window moved after verification")
        if action["kind"] == "discard":
            plan = replace(plan_discard(current,profile,tiles.index(action["tile"]),action["tile"],now=self.clock()),double_click=True)
        else: plan = plan_skip(current,profile,now=self.clock())
        return plan,current

    def poll(self):
        if self.halted: return {"kind":"blocked","reason":self.halted}
        event = super().poll()
        if self.path is not None:
            source = (self.path,self.identity)
            if self.source is not None and (source != self.source or self.tail.reset):
                self.halted = "Capture source reset; restart after inspecting the game"
                return {"kind":"blocked","reason":self.halted}
            self.source = source
            snapshot = self.controller.update(self.reader.snapshot(),now=self.clock())
            if snapshot["status"] == "blocked":
                self.halted = snapshot["reason"]
                return {"kind":"blocked","reason":self.halted}
            if snapshot["status"] == "awaiting_confirmation":
                return {"kind":"status","reason":"awaiting_confirmation"}
        if not self.enabled: return event
        if event.get("kind") == "suggestion":
            self.candidate = event
            self.candidate_until = self.clock()+2
        elif self.candidate is not None:
            if board_token(self.reader.snapshot()) != self.candidate["board_token"]:
                self.candidate = None
                return event
            event = self.candidate
        else: return event
        if event["action"]["kind"] not in ("discard","skip"):
            self.candidate = None
            return {**event,"kind":"manual","reason":"Action requires manual input"}
        try:
            plan,report = self._plan(event)
            self.controller.submit(plan,report,enabled=True,now=self.clock())
        except (ValueError,OSError) as error:
            if self.controller.snapshot()["status"] != "idle": self.halted = str(error)
            if not self.halted and self.clock() < self.candidate_until:
                return {"kind":"status","reason":"waiting_for_stable_visuals"}
            self.candidate = None
            return {**event,"kind":"blocked" if self.halted else "manual","reason":str(error)}
        self.candidate = None
        return {**event,"kind":"submitted","mode":"auto","executable":True}


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true",help="Enable mouse input; AI room testing")
    parser.add_argument("--playstyle",choices=["balanced","atk"],default="atk")
    parser.add_argument("--file",type=Path)
    parser.add_argument("--duration",type=float)
    parser.add_argument("--once",action="store_true")
    args = parser.parse_args()
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration<=0): parser.error("Duration must be positive and finite")
    recorder = vision = None
    # Dry mode never initializes Windows input or screen capture.
    if args.execute:
        from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
        from games.mahjong_soul.live.runtime.windows_recording import WindowsRecorder
        recorder = WindowsRecorder(); vision = TileVision(); backend = WindowsMouse()
    else: backend = None
    follower = AutoFollower(LiqiSchema.load(root/"liqi-reference.json"),
        file=args.file,directory=root/"logs/mahjong_soul",policy=make_policy("playbook",args.playstyle),
        controller=InputController(backend),recorder=recorder,vision=vision,enabled=args.execute)
    print("Automatic discards/Skip enabled. Other actions require manual input. Ctrl+C stops." if args.execute else "Suggestions only; mouse input disabled.",flush=True)
    start=time.monotonic(); previous=None
    try:
        while args.duration is None or time.monotonic()-start<args.duration:
            event=follower.poll()
            kind=event.get("kind")
            if kind in ("suggestion","submitted","manual","blocked"):
                line=(format_suggestion(event)+(" [sent; awaiting confirmation]" if kind=="submitted" else "") if "action" in event else "Stopped")
                if kind in ("manual","blocked"): line += ": "+event["reason"]
                identity=(kind,event.get("board_token"),event.get("reason"))
                if identity != previous: print(line,flush=True);previous=identity
            if kind=="blocked" or args.once: break
            time.sleep(.1)
    except KeyboardInterrupt: pass
    return 1 if follower.halted else 0


if __name__=="__main__": raise SystemExit(main())
