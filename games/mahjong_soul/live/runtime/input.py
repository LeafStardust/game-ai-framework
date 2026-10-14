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
        self.selection_possible = False
        self.selection_confirmed = set()

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
        self.selection_possible = False
        self.backend.click(plan.x, plan.y, plan.width, plan.height)
        self.selection_possible = True

    def confirm_selection(self, plan, current_report, selected_tile, *, enabled=False, now=None):
        """One explicit second click after a fresh visual selection check.

        Rebuild the plan after observing the selected tile so expiry still applies.
        This is never called on a timeout alone or after partial input failure.
        """
        pending = self.pending
        if not enabled or pending is None or not self.selection_possible:
            raise ValueError("No delivered selection click to confirm")
        if plan.token in self.selection_confirmed:
            raise ValueError("Selection confirmation already attempted")
        if (plan.token, plan.tile, plan.x, plan.y, plan.width, plan.height) != (
                pending.token, pending.tile, pending.x, pending.y, pending.width, pending.height):
            raise ValueError("Selection plan does not match the first click")
        if selected_tile != plan.tile:
            raise ValueError("Visually selected tile does not match")
        if (time.monotonic() if now is None else now) >= plan.expires:
            raise ValueError("Click plan expired")
        if not current_report.get("state_ready") or board_token(current_report) != plan.token:
            raise ValueError("Board changed; cannot confirm selection")
        self.selection_confirmed.add(plan.token)
        self.selection_possible = False
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


def main():
    """Inspect a click plan or explicitly send one against a current live capture."""
    import argparse
    from pathlib import Path
    from games.mahjong_soul.live.external.schema import LiqiSchema
    from games.mahjong_soul.live.runtime.monitor import CaptureTail
    from games.mahjong_soul.live.runtime.reader import GameReader

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--tile", required=True)
    parser.add_argument("--execute", action="store_true", help="Send one real click; default is dry run")
    parser.add_argument("--schema", default=str(Path(__file__).resolve().parents[4] / "liqi-reference.json"))
    args = parser.parse_args()
    reader = GameReader(LiqiSchema.load(args.schema))
    tail = CaptureTail(args.capture)
    for row in tail.read():
        reader.consume(row)
    if tail.bad_rows or tail.pending:
        parser.error("Capture contains malformed or unfinished rows")
    try:
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
        plan = plan_discard(reader.snapshot(), profile, args.slot, args.tile)
        if not args.execute:
            print(json.dumps({"dry_run": True, "step": plan.step, "tile": plan.tile,
                              "slot": args.slot, "client_size": [plan.width, plan.height],
                              "point": [plan.x, plan.y]}))
            return 0
        # Require a recently appended live row, not merely an open saved socket.
        if time.time() - Path(args.capture).stat().st_mtime > 2:
            parser.error("Capture is not fresh; wait for the next action and rebuild the plan")
        from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
        executor = DiscardExecutor(WindowsMouse())
        for row in tail.read():
            reader.consume(row)
        if tail.bad_rows or tail.pending:
            parser.error("Capture changed to malformed or unfinished rows")
        executor.execute(plan, reader.snapshot(), enabled=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            for row in tail.read():
                result = reader.consume(row)
                for event in result.get("liqi", {}).get("events", []):
                    if executor.observe(row["connection"], event):
                        print(json.dumps({"confirmed": True, "tile": plan.tile, "step": event["step"]}))
                        return 0
            time.sleep(0.05)
        print(json.dumps({"confirmed": False, "error": "No matching discard received; inspect the game and do not retry"}))
        return 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
