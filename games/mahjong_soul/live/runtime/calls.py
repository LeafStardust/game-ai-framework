"""Guarded one-choice Pon button; ambiguous choice panels are unsupported."""

from dataclasses import dataclass
import time
from games.mahjong_soul.live.runtime.input import board_token


@dataclass(frozen=True)
class PonPlan:
    token: str
    connection: str
    step: int
    seat: int
    tile_kind: str
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_pon(report, profile, *, now=None):
    if not report.get("state_ready"):
        raise ValueError("Reader is not ready")
    state = report["state"]
    operation = state.get("operations") or {}
    choices = [item for item in operation.get("operation_list", []) if item.get("type") == 3]
    if operation.get("seat") != state["seat"] or len(choices) != 1:
        raise ValueError("No own Pon operation")
    combinations = choices[0].get("combination", [])
    if len(combinations) != 1:
        raise ValueError("Pon choice panel requires explicit mapping")
    tiles = combinations[0].split("|")
    def kind(tile):
        return "5" + tile[1:] if tile.startswith("0") else tile
    if len(tiles) != 2 or kind(tiles[0]) != kind(tiles[1]):
        raise ValueError("Unsupported Pon combination")
    hand = list(state["hand"])
    for tile in tiles:
        if tile not in hand:
            raise ValueError("Pon contribution is missing from hand")
        hand.remove(tile)
    if (profile.get("version") != 1 or profile.get("verified") is not True
            or profile.get("operation_types") != [item.get("type") for item in operation["operation_list"]]):
        raise ValueError("Call-button layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = profile["pon"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid call-button coordinates")
    return PonPlan(board_token(report), report["game_connection"], state["step"], state["seat"],
                   kind(tiles[0]), x, y, width, height,
                   (time.monotonic() if now is None else now) + 2)


class PonExecutor:
    def __init__(self, backend):
        self.backend = backend
        self.pending = None
        self.attempted = set()

    def execute(self, plan, report, *, enabled=False, now=None):
        if not enabled or self.pending is not None or plan.token in self.attempted:
            raise ValueError("Pon input disabled, pending, or already attempted")
        if (time.monotonic() if now is None else now) >= plan.expires:
            raise ValueError("Pon plan expired")
        if not report.get("state_ready") or board_token(report) != plan.token:
            raise ValueError("Board changed")
        self.attempted.add(plan.token)
        self.pending = plan
        self.backend.click(plan.x, plan.y, plan.width, plan.height)

    def observe(self, connection, event):
        plan = self.pending
        data = event.get("data", {})
        tiles = data.get("tiles", [])
        kinds = ["5" + tile[1:] if tile.startswith("0") else tile for tile in tiles]
        if (plan and connection == plan.connection and event.get("source") == "live"
                and event.get("name") == "ActionChiPengGang" and event.get("step", -1) > plan.step
                and data.get("seat", 0) == plan.seat and data.get("type", 0) == 1
                and kinds == [plan.tile_kind] * 3):
            self.pending = None
            return True
        return False
