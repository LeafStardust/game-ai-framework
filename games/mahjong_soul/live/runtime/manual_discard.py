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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--tile", required=True)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    reader = GameReader(LiqiSchema.load(root / "liqi-reference.json"))
    tail = CaptureTail(args.capture)
    def refresh():
        for row in tail.read():
            reader.consume(row)
        if tail.bad_rows or tail.pending or tail.reset:
            raise ValueError("Capture incomplete or reset; no input")
        return reader.snapshot()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    report = refresh()
    plan = plan_discard(report, profile, args.slot, args.tile)
    if not args.execute:
        print(json.dumps({"dry_run": True, "step": plan.step, "tile": plan.tile}))
        return 0
    # Wait briefly for a heartbeat; never make stale evidence appear fresh.
    deadline = time.monotonic()+15
    while time.time()-args.capture.stat().st_mtime > 2:
        if time.monotonic() >= deadline:
            raise ValueError("Capture is stale; no input")
        time.sleep(.05)
    from games.mahjong_soul.live.runtime.windows_input import WindowsMouse
    controller = InputController(WindowsMouse(), confirmation_timeout=300)
    report = refresh()
    plan = plan_discard(report, profile, args.slot, args.tile)
    ticket = root / "logs/mahjong_soul" / ("confirm-"+uuid.uuid4().hex+".json")
    controller.submit(plan, report, enabled=True)
    print(json.dumps({"selection_sent": True, "step": plan.step, "ticket": str(ticket),
                      "confirmation": {"token": plan.token, "tile": plan.tile}}), flush=True)
    deadline = time.monotonic()+295
    while time.monotonic() < deadline:
        report = refresh()
        if board_token(report) != plan.token or controller.update(report)["status"] == "blocked":
            raise ValueError("Board changed or input became uncertain; no confirmation or retry")
        if confirmation_matches(ticket, plan) and time.time()-args.capture.stat().st_mtime <= 2:
            fresh = plan_discard(report, profile, args.slot, args.tile)
            controller.confirm_selection(fresh, report, args.tile, enabled=True)
            break
        time.sleep(.05)
    else:
        raise ValueError("Visual confirmation timed out; no retry")
    deadline = time.monotonic()+5
    while time.monotonic() < deadline:
        for row in tail.read():
            result = reader.consume(row)
            for event in result.get("liqi", {}).get("events", []):
                if controller.observe(row["connection"], event):
                    print(json.dumps({"confirmed": True, "step": event.get("step"),
                                      "tile": args.tile}), flush=True)
                    return 0
        if tail.bad_rows or tail.pending or tail.reset:
            raise ValueError("Capture incomplete or reset; no retry")
        time.sleep(.02)
    raise ValueError("No server confirmation; no retry")


if __name__ == "__main__":
    raise SystemExit(main())
