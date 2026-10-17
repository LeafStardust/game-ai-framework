"""Follow Steam capture and emit policy suggestions only. Never sends input."""
import argparse
import json
import math
from pathlib import Path
import time

from agents.mahjong_soul.evaluate import decide
from agents.mahjong_soul.policy import BaselinePolicy, make_policy
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.monitor import CaptureTail
from games.mahjong_soul.live.runtime.reader import GameReader


def status(reason):
    return {"version":1,"kind":"status","mode":"shadow","executable":False,"reason":reason}


class ShadowFollower:
    def __init__(self, schema, *, file=None, directory=None, policy=None,
                 max_age=2, clock=time.monotonic, wall_clock=time.time):
        if type(max_age) not in (int,float) or not math.isfinite(max_age) or max_age <= 0:
            raise ValueError("Capture freshness age must be finite and positive")
        self.schema, self.file = schema, Path(file) if file is not None else None
        self.directory = Path(directory) if directory is not None else None
        if self.file is None and self.directory is None: raise ValueError("Capture location required")
        self.policy = BaselinePolicy() if policy is None else policy
        self.max_age, self.clock, self.wall_clock = max_age, clock, wall_clock
        self.path = None; self.identity = None; self.tail = None; self.reader = None
        self.frame_times = {}; self.fault = False; self.seen = set()

    def _select(self):
        if self.file is not None: return self.file if self.file.is_file() else None
        paths = list(self.directory.glob("capture-*.jsonl"))
        return max(paths, key=lambda p:p.stat().st_mtime_ns) if paths else None

    def _drain(self):
        previous_bad_rows = self.tail.bad_rows
        rows = self.tail.read()
        if self.tail.reset:
            self.reader = GameReader(self.schema); self.frame_times.clear(); self.fault = False
            self.tail.bad_rows -= previous_bad_rows
        if self.tail.bad_rows:
            self.fault = True
        for row in rows:
            try:
                self.reader.consume(row)
            except (ValueError, KeyError, TypeError):
                self.fault = True
                continue
            timestamp = row.get("timestamp")
            if (row.get("event") is None and type(timestamp) in (int,float)
                    and math.isfinite(timestamp)):
                self.frame_times[row["connection"]] = timestamp
        return self.reader.snapshot()

    def _fresh(self, report):
        stamp = self.frame_times.get(report.get("game_connection"))
        return stamp is not None and 0 <= self.wall_clock()-stamp <= self.max_age

    def _current(self):
        info = self.path.stat()
        if self._select() != self.path or (info.st_dev, info.st_ino) != self.identity:
            raise ValueError("Capture changed during policy evaluation")
        report = self._drain()
        if self.fault or self.tail.pending or not self._fresh(report):
            raise ValueError("Capture became stale or incomplete during policy evaluation")
        return report

    def poll(self):
        path = self._select()
        if path is None: return status("waiting_for_capture")
        info = path.stat()
        identity = (info.st_dev, info.st_ino)
        if path != self.path or identity != self.identity:
            self.identity = identity
            self.path = path; self.tail = CaptureTail(path); self.reader = GameReader(self.schema)
            self.frame_times.clear(); self.fault = False
            report = self._drain()
            # Bootstrap is historical context, never a new suggestion.
            self.seen.add(board_token(report))
            return status("capture_bootstrapped")
        report = self._drain()
        if self.tail.reset:
            self.seen.add(board_token(report))
            return status("capture_reset_bootstrapped")
        if self.fault: return status("malformed_capture_blocked")
        if self.tail.pending: return status("waiting_for_complete_row")
        state = report.get("state") or {}
        if not report.get("connection_open"): return status("waiting_for_game_connection")
        if not report.get("state_ready"): return status("waiting_for_ready_board")
        if not self._fresh(report): return status("stale_game_capture")
        operation = state.get("operations") or {}
        if operation.get("seat") != state.get("seat") or not operation.get("operation_list"):
            return status("waiting_for_own_offer")
        token = board_token(report)
        if token in self.seen: return status("board_already_considered")
        self.seen.add(token)  # Policy failures do not trigger repeated calls on the same board.
        try:
            validated = decide(self.policy, report, self._current, clock=self.clock)
        except Exception as error:
            return {**status("decision_rejected"),"error_type":type(error).__name__,"board_token":token}
        analysis = getattr(self.policy, "last_analysis", None)
        detail = {"analysis":analysis} if analysis and analysis.get("board_token") == token else {}
        return {**detail,"version":1,"kind":"suggestion","mode":"shadow","executable":False,
                "policy":type(self.policy).__name__,"board_token":token,
                "generation":report.get("game_generation",0),"step":state.get("step"),
                "round":state.get("round"),"action":validated["action"]}



def tile_label(tile):
    honors = {"1z":"East Wind", "2z":"South Wind", "3z":"West Wind", "4z":"North Wind",
              "5z":"White dragon", "6z":"Green dragon", "7z":"Red dragon"}
    if tile in honors: return honors[tile]
    suit = {"m":"Man", "p":"Pin", "s":"Sou"}[tile[1]]
    return "Red 5 " + suit if tile[0] == "0" else tile[0]+" "+suit


def format_suggestion(event):
    action = event["action"]
    labels = {"discard":"Discard", "skip":"Skip", "chi":"Chi", "pon":"Pon",
              "closed_kan":"Closed kan", "open_kan":"Open kan", "added_kan":"Added kan",
              "riichi":"Riichi, then discard", "tsumo":"Tsumo", "ron":"Ron"}
    label = labels.get(action["kind"], action["kind"])
    if action.get("tile"): return label + " " + tile_label(action["tile"])
    if action.get("combination"):
        label += " " + " + ".join(tile_label(t) for t in action["combination"].split("|"))
        if action.get("called_tile"): label += " with " + tile_label(action["called_tile"])
    return label


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="One capture; defaults to newest local capture")
    parser.add_argument("--policy", choices=["baseline","efficiency","playbook"], default="playbook")
    parser.add_argument("--schema", type=Path, default=root / "liqi-reference.json")
    parser.add_argument("--max-age", type=float, default=2)
    parser.add_argument("--interval", type=float, default=.2)
    parser.add_argument("--duration", type=float, help="Optional bounded run in seconds")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Print full suggestion JSON instead of a readable action")
    parser.add_argument("--verbose", action="store_true", help="Include diagnostic status lines")
    parser.add_argument("--once", action="store_true", help="Bootstrap smoke check; add --verbose to show status")
    args = parser.parse_args()
    if (not math.isfinite(args.interval) or args.interval < .05
            or args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0)):
        parser.error("Interval must be at least .05 seconds and duration must be finite and positive")
    follower = ShadowFollower(LiqiSchema.load(args.schema), file=args.file,
                              directory=root / "logs/mahjong_soul", max_age=args.max_age, policy=make_policy(args.policy))
    start = time.monotonic(); previous = None
    try:
        while args.duration is None or time.monotonic()-start < args.duration:
            event = follower.poll()
            encoded = json.dumps(event, sort_keys=True)
            if (event.get("kind") == "suggestion" or args.verbose) and encoded != previous:
                output = encoded if args.json_output else (format_suggestion(event) if event.get("kind") == "suggestion" else event["reason"])
                print(output, flush=True); previous = encoded
            if args.once: break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
