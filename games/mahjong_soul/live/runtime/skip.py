"""Skip a visible call offer and confirm its correlated cancellation RPC."""

from dataclasses import dataclass
import time
from games.mahjong_soul.live.runtime.input import board_token


@dataclass(frozen=True)
class SkipPlan:
    token: str
    connection: str
    step: int
    seat: int
    x: float
    y: float
    width: int
    height: int
    expires: float


def plan_skip(report, profile, *, now=None):
    state = report.get("state") or {}
    operation = state.get("operations") or {}
    types = [item.get("type") for item in operation.get("operation_list", [])]
    if not report.get("state_ready") or operation.get("seat") != state.get("seat") or not types or any(t not in (2, 3, 5, 9) for t in types):
        raise ValueError("No supported own call offer to skip")
    if profile.get("version") != 1 or profile.get("verified") is not True or profile.get("stage") != "call_offer" or profile.get("operation_types") != types:
        raise ValueError("Skip layout is not verified for this offer")
    width, height = profile["client_size"]
    x, y = profile["skip"]
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or not 0 < x < 1 or not 0 < y < 1:
        raise ValueError("Invalid skip coordinates")
    return SkipPlan(board_token(report), report["game_connection"], state["step"], state["seat"], x, y, width, height,
                    (time.monotonic() if now is None else now) + 2)


class SkipExecutor:
    def __init__(self, backend):
        self.backend = backend
        self.pending = None
        self.attempted = set()
        self.request_id = None
        self.failed = False

    def execute(self, plan, report, *, enabled=False, now=None):
        if not enabled or self.pending is not None or plan.token in self.attempted:
            raise ValueError("Skip disabled, pending, or already attempted")
        if (time.monotonic() if now is None else now) >= plan.expires:
            raise ValueError("Skip plan expired")
        if not report.get("state_ready") or board_token(report) != plan.token:
            raise ValueError("Board changed")
        self.attempted.add(plan.token)
        self.pending = plan
        self.request_id = None
        self.failed = False
        self.backend.click(plan.x, plan.y, plan.width, plan.height)

    def observe(self, connection, event):
        return False  # Later game actions alone cannot prove the skip was accepted.

    def observe_message(self, connection, decoded, from_client):
        if not self.pending or connection != self.pending.connection or decoded.get("method") != ".lq.FastTest.inputChiPengGang":
            return False
        request_id = decoded.get("request_id")
        if decoded.get("kind") == "request" and from_client and decoded.get("data", {}).get("cancel_operation") is True:
            if self.request_id is None and type(request_id) is int:
                self.request_id = request_id
        elif decoded.get("kind") == "response" and not from_client and self.request_id is not None and request_id == self.request_id:
            if decoded.get("data", {}).get("error", {}).get("code", 0):
                self.failed = True
            else:
                self.pending = None
                return True
        return False
