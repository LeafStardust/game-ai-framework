"""Explicit riichi menu, allowed discard selection, and server acceptance."""

from dataclasses import dataclass
from collections import Counter
import time
from games.mahjong_soul.live.runtime.input import DiscardPlan, DiscardExecutor, plan_discard, board_token


@dataclass(frozen=True)
class RiichiPlan(DiscardPlan):
    button_x: float
    button_y: float
    allowed_tiles: tuple


def plan_riichi(report, profile, slot, tile, *, now=None):
    operation = (report.get("state") or {}).get("operations") or {}
    choices = [item for item in operation.get("operation_list", []) if item.get("type") == 7]
    if len(choices) != 1 or tile not in choices[0].get("combination", []):
        raise ValueError("Tile is not an offered riichi discard")
    if profile.get("operation_types") != [item.get("type") for item in operation.get("operation_list", [])]:
        raise ValueError("Riichi button layout does not match the offer")
    base = plan_discard(report, profile, slot, tile, now=now)
    x, y = profile["riichi"]
    if not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid riichi button coordinates")
    return RiichiPlan(**base.__dict__, button_x=x, button_y=y,
                      allowed_tiles=tuple(dict.fromkeys(choices[0]["combination"])))


class RiichiExecutor(DiscardExecutor):
    def __init__(self, backend):
        super().__init__(backend)
        self.phase = None
        self.declaration_step = None
        self.failed = False

    def execute(self, plan, report, *, enabled=False, now=None):
        if not enabled or self.pending is not None or plan.token in self.attempted:
            raise ValueError("Riichi disabled, pending, or already attempted")
        self._check(plan, report, now)
        self.attempted.add(plan.token)
        self.pending = plan
        self.phase = "menu_clicked"
        self.declaration_step = None
        self.failed = False
        self.selection_possible = False
        self.backend.click(plan.button_x, plan.button_y, plan.width, plan.height)

    @staticmethod
    def _check(plan, report, now):
        if (time.monotonic() if now is None else now) >= plan.expires:
            raise ValueError("Riichi plan expired")
        if not report.get("state_ready") or board_token(report) != plan.token:
            raise ValueError("Board changed")

    def select_discard(self, plan, report, visible_allowed_tiles, *, enabled=False, now=None):
        if not enabled or self.phase != "menu_clicked" or self.pending is None:
            raise ValueError("No riichi selection menu to act on")
        self._check(plan, report, now)
        if plan != self.pending and (plan.token, plan.tile, plan.x, plan.y, plan.allowed_tiles, plan.button_x, plan.button_y) != (
                self.pending.token, self.pending.tile, self.pending.x, self.pending.y, self.pending.allowed_tiles, self.pending.button_x, self.pending.button_y):
            raise ValueError("Riichi selection does not match the original plan")
        if Counter(visible_allowed_tiles) != Counter(plan.allowed_tiles):
            raise ValueError("Visible riichi discards do not match the server offer")
        self.phase = "tile_selection_attempted"
        if plan.double_click:
            self.backend.double_click(plan.x,plan.y,plan.width,plan.height)
            self.phase = "awaiting_declaration"
            self.selection_possible = False
        else:
            self.backend.click(plan.x, plan.y, plan.width, plan.height)
            self.phase = "tile_selected"
            self.selection_possible = True

    def observe(self, connection, event):
        plan = self.pending
        if plan is None or connection != plan.connection or event.get("source") != "live":
            return False
        data = event.get("data", {})
        step = event.get("step", -1)
        if (event.get("name") == "ActionDiscardTile" and step > plan.step
                and data.get("seat", 0) == plan.seat and data.get("tile") == plan.tile
                and (data.get("is_liqi") is True or data.get("is_wliqi") is True)):
            self.declaration_step = step
            self.phase = "awaiting_acceptance"
            self.selection_possible = False
        # A Ron on the declaration discard ends the hand before Riichi can be
        # accepted. This resolves the attempted input without calling it accepted.
        if self.declaration_step is not None and event.get("name")=="ActionHule" and step>=self.declaration_step:
            winners=data.get("hules",[])
            if winners and all(w.get("seat",0)!=plan.seat and w.get("zimo",False) is False
                               and w.get("hu_tile")==plan.tile for w in winners):
                self.pending=None
                self.phase="interrupted_by_ron"
                return True
        failed = data.get("failed_liqi")
        if self.declaration_step is not None and step >= self.declaration_step:
            if isinstance(failed, dict) and failed and failed.get("seat", 0) == plan.seat:
                self.failed = True
            accepted = data.get("liqi")
            if isinstance(accepted, dict) and accepted and accepted.get("seat", 0) == plan.seat and accepted.get("failed") is True:
                self.failed = True
            if isinstance(accepted, dict) and accepted and accepted.get("seat", 0) == plan.seat and not self.failed:
                self.pending = None
                self.phase = "accepted"
                return True
        return False
