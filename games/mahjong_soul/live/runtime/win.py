"""Guarded win buttons with exact winner, tile and win-type confirmation."""

from dataclasses import dataclass
import time
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.calls import PonExecutor


@dataclass(frozen=True)
class WinPlan:
    token: str
    connection: str
    step: int
    seat: int
    tile: str
    zimo: bool
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_win(report, profile, kind="tsumo", *, now=None):
    if kind not in ("tsumo", "ron"):
        raise ValueError("Unsupported win type")
    state = report.get("state") or {}
    operation = state.get("operations") or {}
    types = [item.get("type") for item in operation.get("operation_list", [])]
    code = 8 if kind == "tsumo" else 9
    if not report.get("state_ready") or operation.get("seat") != state.get("seat") or types.count(code) != 1:
        raise ValueError("No own matching win operation")
    if kind == "tsumo":
        tile = state.get("drawn_tile")
        if not tile or tile not in state.get("hand", []):
            raise ValueError("Own winning draw is unknown")
    else:
        source = state.get("turn")
        if (not isinstance(source, int) or not 0 <= source < state["player_count"] or source == state["seat"]
                or (report.get("last_event") or {}).get("name") != "ActionDiscardTile"):
            raise ValueError("Ron source discard is unknown")
        river = state["discards"][source]
        if not river or river[-1].get("called") is not False:
            raise ValueError("Ron source discard is uncertain")
        tile = river[-1]["tile"]
    if (profile.get("version") != 1 or profile.get("verified") is not True
            or profile.get("stage") != "call_offer" or profile.get("operation_types") != types):
        raise ValueError("Win button layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = profile[kind]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid win coordinates")
    return WinPlan(board_token(report), report["game_connection"], state["step"], state["seat"], tile, kind == "tsumo",
                   x, y, width, height, (time.monotonic() if now is None else now) + 2)


class WinExecutor(PonExecutor):
    def observe(self, connection, event):
        plan = self.pending
        if (not plan or connection != plan.connection or event.get("source") != "live"
                or event.get("name") != "ActionHule" or event.get("step", -1) <= plan.step):
            return False
        for winner in event.get("data", {}).get("hules", []):
            if (winner.get("seat", 0) == plan.seat and winner.get("zimo", False) is plan.zimo
                    and winner.get("hu_tile") == plan.tile):
                self.pending = None
                return True
        return False
