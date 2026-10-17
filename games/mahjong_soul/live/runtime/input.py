"""Guarded single-click or explicit double-click discard execution; no retries."""

from dataclasses import dataclass, replace, field
import hashlib
import json
import re
import time


def board_token(report):
    return hashlib.sha256(json.dumps([report.get("game_connection"), report.get("game_generation", 0), report.get("state")],
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
    double_click: bool = field(default=False, kw_only=True)


def plan_discard(report, profile, slot, tile, *, now=None):
    """Slot is a visually verified index, never the reader hand-list index."""
    if not report.get("state_ready"):
        raise ValueError("Reader is not ready")
    state = report["state"]
    operation = state.get("operations") or {}
    choices = [choice for choice in operation.get("operation_list", []) if choice.get("type") == 1]
    if operation.get("seat") != state["seat"] or len(choices) != 1:
        raise ValueError("No unambiguous own discard operation")
    restrictions = choices[0].get("combination", [])
    if not isinstance(restrictions, list) or any(
            not isinstance(value, str) or not re.fullmatch(r"(?:[0-9][mps]|[1-7]z)", value) for value in restrictions):
        raise ValueError("Unsupported discard restriction encoding")
    def kind(value):
        return "5" + value[1:] if value.startswith("0") else value
    if kind(tile) in {kind(value) for value in restrictions}:
        raise ValueError("Tile is forbidden by the current discard operation")
    if tile not in state["hand"]:
        raise ValueError("Expected tile is not in the own hand")
    if profile.get("version") != 1 or profile.get("verified") is not True:
        raise ValueError("Layout has not been calibrated and verified")
    if profile.get("trigger") != (report.get("last_event") or {}).get("name"):
        raise ValueError("Layout action context does not match")
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
        if plan.double_click:
            self.backend.double_click(plan.x, plan.y, plan.width, plan.height)
        else:
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
    parser.add_argument("--double-click", action="store_true", help="Send the selection and discard together as one native action")
    parser.add_argument("--expected-token", help="Require the visually inspected board token before executing")
    parser.add_argument("--execute", action="store_true", help="Send one real click; default is dry run")
    parser.add_argument("--client-size", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"), help="Dry-run target size; execution reads actual client geometry")
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
        from games.mahjong_soul.live.runtime.layout import profile_for_size
        mouse = None
        if args.execute:
            from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
            mouse = WindowsMouse()
            geometry = mouse.client_geometry()
            target_size = [geometry["width"], geometry["height"]]
        else:
            target_size = args.client_size or profile["client_size"]
        profile = profile_for_size(profile, target_size)
        plan = replace(plan_discard(reader.snapshot(), profile, args.slot, args.tile), double_click=args.double_click)
        if args.execute and args.double_click and not args.expected_token:
            parser.error("Double-click execution requires --expected-token")
        if args.expected_token and plan.token != args.expected_token:
            parser.error("Observed board changed; no input")
        if not args.execute:
            print(json.dumps({"dry_run": True, "step": plan.step, "tile": plan.tile,
                              "slot": args.slot, "client_size": [plan.width, plan.height],
                              "point": [plan.x, plan.y], "token": plan.token, "double_click": plan.double_click}))
            return 0
        # Require a recently appended live row, not merely an open saved socket.
        if args.double_click:
            deadline = time.monotonic() + 15
            while time.time() - Path(args.capture).stat().st_mtime > 2 and time.monotonic() < deadline:
                time.sleep(.05)
            for row in tail.read():
                reader.consume(row)
            if tail.bad_rows or tail.pending or tail.reset:
                parser.error("Capture incomplete or reset; no input")
            if board_token(reader.snapshot()) != args.expected_token:
                parser.error("Observed board changed; no input")
            plan = replace(plan_discard(reader.snapshot(), profile, args.slot, args.tile), double_click=True)
        if not 0 <= time.time() - Path(args.capture).stat().st_mtime <= 2:
            parser.error("Capture is not fresh; wait for the next action and rebuild the plan")
        from games.mahjong_soul.live.runtime.controller import InputController
        executor = InputController(mouse)
        for row in tail.read():
            reader.consume(row)
        if tail.bad_rows or tail.pending:
            parser.error("Capture changed to malformed or unfinished rows")
        executor.submit(plan, reader.snapshot(), enabled=True)
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
