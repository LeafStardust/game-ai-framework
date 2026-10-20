"""Verified Kita click, confirmed only by own live North extraction."""
import time
from dataclasses import dataclass
from games.mahjong_soul.live.runtime.skip import SkipPlan
from games.mahjong_soul.live.runtime.calls import PonExecutor
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.decision import offered_actions


@dataclass(frozen=True)
class NorthPlan(SkipPlan):
    pass


def plan_north(report,profile,*,now=None):
    if {"kind":"extract_north","tile":"4z"} not in offered_actions(report):raise ValueError("No verified North-extraction offer")
    state=report["state"];types=[o["type"] for o in state["operations"]["operation_list"]]
    if (profile.get("version")!=1 or profile.get("verified") is not True or profile.get("stage")!="call_offer"
            or profile.get("operation_types")!=types or profile.get("client_size")!=[1920,1080]):
        raise ValueError("North layout is not verified for this offer")
    x,y=profile["extract_north"]
    if not 0<x<1 or not 0<y<1:raise ValueError("Invalid North coordinates")
    return NorthPlan(board_token(report),report["game_connection"],state["step"],state["seat"],x,y,1920,1080,
                     (time.monotonic() if now is None else now)+2)


class NorthExecutor(PonExecutor):
    def observe(self,connection,event):
        plan=self.pending;data=event.get("data",{})
        if (not plan or connection!=plan.connection or event.get("source")!="live"
                or event.get("name")!="ActionBaBei" or event.get("step",-1)<=plan.step
                or data.get("seat",0)!=plan.seat):return False
        self.pending=None
        return True
