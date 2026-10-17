"""One native discard calibration session with explicit visual confirmation.

Keeps the original controller alive; no stdin, retries or executor reconstruction.
"""
import argparse
import json
from pathlib import Path
import time
import uuid

from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.monitor import CaptureTail
from games.mahjong_soul.live.runtime.reader import GameReader
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import plan_discard, board_token


def confirmation_matches(path, plan):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return value == {"token": plan.token, "tile": plan.tile}



class ManualDiscardSession:
    """Retain one controller through selection, review and server acknowledgement."""
    def __init__(self, backend, profile, slot, tile, ticket, *, review_timeout=295,
                 server_timeout=5):
        if review_timeout <= 0 or server_timeout <= 0:
            raise ValueError("Timeouts must be positive")
        self.controller = InputController(backend, confirmation_timeout=review_timeout+server_timeout)
        self.profile, self.slot, self.tile = profile, slot, tile
        self.ticket = Path(ticket)
        self.review_timeout, self.server_timeout = review_timeout, server_timeout
        self.phase = "new"
        self.plan = None
        self.deadline = None

    def start(self, report, *, fresh, now, expected_token=None):
        if self.phase != "new":
            raise ValueError("Session already started; no retry")
        self.phase = "failed"  # Any partial delivery is terminal for this session.
        if self.ticket.exists():
            raise ValueError("Confirmation ticket already exists")
        if not fresh:
            raise ValueError("Capture is stale; no input")
        if not report.get("connection_open"):
            raise ValueError("Game connection is closed")
        if expected_token is not None and board_token(report) != expected_token:
            raise ValueError("Observed board changed; no input")
        self.plan = plan_discard(report, self.profile, self.slot, self.tile, now=now)
        self.controller.submit(self.plan, report, enabled=True, now=now)
        self.deadline = now+self.review_timeout
        self.phase = "review"
        return {"selection_sent": True, "step": self.plan.step, "ticket": str(self.ticket),
                "confirmation": {"token": self.plan.token, "tile": self.tile}}

    def tick(self, report, events=(), *, fresh, now):
        if self.phase == "complete":
            return {"confirmed": True, "tile": self.tile}
        if self.phase not in {"review", "server"}:
            raise ValueError("Session is not active; no retry")
        try:
            if now >= self.deadline:
                raise ValueError("Confirmation timed out; no retry")
            for connection, event in events:
                matched = self.controller.observe(connection, event, now=now)
                if matched:
                    if self.phase != "server":
                        raise ValueError("Discard occurred before native confirmation; not a native success")
                    self.phase = "complete"
                    return {"confirmed": True, "step": event.get("step"), "tile": self.tile}
            if self.controller.update(report, now=now)["status"] == "blocked":
                raise ValueError("Controller blocked; no retry")
            if board_token(report) != self.plan.token:
                raise ValueError("Board changed; no retry")
            if (self.phase == "review" and fresh
                    and confirmation_matches(self.ticket, self.plan)):
                plan = plan_discard(report, self.profile, self.slot, self.tile, now=now)
                self.controller.confirm_selection(plan, report, self.tile, enabled=True, now=now)
                self.phase = "server"
                self.deadline = now+self.server_timeout
                return {"confirmation_sent": True, "tile": self.tile}
            return {"phase": self.phase}
        except Exception:
            self.phase = "failed"
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--tile", required=True)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-token", help="Board token from a dry run on the visually inspected turn")
    args = parser.parse_args()
    if args.execute and not args.expected_token:
        parser.error("--execute requires --expected-token from the inspected board")
    root = Path(__file__).resolve().parents[4]
    reader = GameReader(LiqiSchema.load(root / "liqi-reference.json"))
    tail = CaptureTail(args.capture)
    def refresh():
        events = []
        for row in tail.read():
            result = reader.consume(row)
            events.extend((row["connection"], e) for e in result.get("liqi", {}).get("events", []))
        if tail.bad_rows or tail.pending or tail.reset:
            raise ValueError("Capture incomplete or reset; no input")
        return reader.snapshot(), events
    def fresh():
        return 0 <= time.time()-args.capture.stat().st_mtime <= 2
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    report, _ = refresh()
    plan = plan_discard(report, profile, args.slot, args.tile)
    if not args.execute:
        print(json.dumps({"dry_run": True, "step": plan.step, "tile": plan.tile, "token": plan.token}))
        return 0
    deadline = time.monotonic()+15
    while not fresh():
        if time.monotonic() >= deadline:
            raise ValueError("Capture is stale; no input")
        time.sleep(.05)
    from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
    ticket = root / "logs/mahjong_soul" / ("confirm-"+uuid.uuid4().hex+".json")
    session = ManualDiscardSession(WindowsMouse(), profile, args.slot, args.tile, ticket)
    report, _ = refresh()
    print(json.dumps(session.start(report, fresh=fresh(), now=time.monotonic(), expected_token=args.expected_token)), flush=True)
    while True:
        report, events = refresh()
        result = session.tick(report, events, fresh=fresh(), now=time.monotonic())
        if result.get("confirmed") or result.get("confirmation_sent"):
            print(json.dumps(result), flush=True)
        if result.get("confirmed"):
            return 0
        time.sleep(.02)


if __name__ == "__main__":
    raise SystemExit(main())
