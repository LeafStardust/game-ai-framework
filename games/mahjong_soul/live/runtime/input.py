"""Guarded, single-click discard execution. No policy or automatic retries."""

from dataclasses import dataclass
import hashlib
import json
import time


def board_token(report):
    return hashlib.sha256(json.dumps([report.get("game_connection"), report.get("state")],
                                    sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class DiscardPlan:
    token: str
    connection: str
    step: int
    seat: int
    tile: str
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_discard(report, profile, slot, tile, *, now=None):
    """Slot is a visually verified index, never the reader hand-list index."""
    if not report.get("state_ready"):
        raise ValueError("Reader is not ready")
    state = report["state"]
    operation = state.get("operations") or {}
    if operation.get("seat") != state["seat"] or not any(
            choice.get("type") == 1 for choice in operation.get("operation_list", [])):
        raise ValueError("No own discard operation")
    if tile not in state["hand"]:
        raise ValueError("Expected tile is not in the own hand")
    if profile.get("version") != 1 or profile.get("verified") is not True:
        raise ValueError("Layout has not been calibrated and verified")
    if profile.get("hand_count") != len(state["hand"]):
        raise ValueError("Hand layout does not match")
    width, height = profile["client_size"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError("Invalid client size")
    slots = profile["slots"]
    if len(slots) != len(state["hand"]) or type(slot) is not int or not 0 <= slot < len(slots):
        raise ValueError("Invalid visual slot")
    x, y = slots[slot]
    if not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Click must be inside the client area")
    return DiscardPlan(board_token(report), report["game_connection"], state["step"],
                       state["seat"], tile, x, y, width, height,
                       (time.monotonic() if now is None else now) + 2.0)


class DiscardExecutor:
    def __init__(self, backend):
        self.backend = backend
        self.pending = None
        self.attempted = set()

    def execute(self, plan, current_report, *, enabled=False, now=None):
        if not enabled:
            raise ValueError("Real input is disabled")
        if self.pending is not None:
            raise ValueError("Previous click is awaiting confirmation")
        if plan.token in self.attempted:
            raise ValueError("This board has already had a click attempt")
        if (time.monotonic() if now is None else now) >= plan.expires:
            raise ValueError("Click plan expired")
        if not current_report.get("state_ready") or board_token(current_report) != plan.token:
            raise ValueError("Board changed; rebuild the plan")
        # Record attempts before input: partial delivery must never be retried.
        self.attempted.add(plan.token)
        self.pending = plan
        self.backend.click(plan.x, plan.y, plan.width, plan.height)

    def observe(self, connection, event):
        """Confirm only a matching live discard, not a restored historical action."""
        plan = self.pending
        if plan is None or connection != plan.connection or event.get("source") != "live":
            return False
        data = event.get("data", {})
        confirmed = (event.get("name") == "ActionDiscardTile"
                     and event.get("step", -1) > plan.step
                     and data.get("seat", 0) == plan.seat and data.get("tile") == plan.tile)
        if confirmed:
            self.pending = None
        return confirmed
