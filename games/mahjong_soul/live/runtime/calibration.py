"""Passive calibration evidence recorder. Never sends input or enables profiles."""
import argparse
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import queue
import threading

from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.monitor import CaptureTail
from games.mahjong_soul.live.runtime.reader import GameReader
from games.mahjong_soul.live.runtime.input import board_token


def context(report):
    state = report.get("state") or {}
    return {"board_token": board_token(report), "generation": report.get("game_generation", 0),
            "step": state.get("step"), "seat": state.get("seat"),
            "round": deepcopy(state.get("round")), "hand": list(state.get("hand", [])),
            "operations": deepcopy(state.get("operations")),
            "last_event": deepcopy(report.get("last_event"))}


class EvidenceRecorder:
    def __init__(self, directory, max_bytes=1024**3):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.stream = (self.directory / "events.jsonl").open("x", encoding="utf-8")
        self.max_bytes = max_bytes
        self.used = 0
        self.sequence = 0
        self.last_key = None
        self.last_image = None
        self.clicks = deque(maxlen=100)

    def write(self, kind, **data):
        row = {"kind": kind, "utc": datetime.now(timezone.utc).isoformat(), **data}
        encoded = json.dumps(row, ensure_ascii=False) + "\n"
        self.used += len(encoded.encode("utf-8"))
        if self.used > self.max_bytes:
            raise RuntimeError("Recording size limit reached")
        self.stream.write(encoded)
        self.stream.flush()

    def frame(self, report, geometry, png, now):
        ctx = context(report)
        digest = hashlib.sha256(png).hexdigest()
        key = (ctx["board_token"], json.dumps(geometry, sort_keys=True), digest)
        if key == self.last_key:
            return self.last_image
        if self.used + len(png) > self.max_bytes:
            raise RuntimeError("Recording size limit reached")
        self.sequence += 1
        name = f"frame-{self.sequence:06d}.png"
        (self.directory / name).write_bytes(png)
        self.used += len(png)
        self.last_key = key
        self.last_image = {"file": name, "monotonic": now, "context": ctx, "geometry": dict(geometry)}
        self.write("frame", image=name, geometry=geometry, context=ctx)
        return self.last_image

    def click(self, report, geometry, x, y, now):
        self.sequence += 1
        click_id = self.sequence
        ctx = context(report)
        frame = self.last_image
        fresh = bool(frame and 0 <= now - frame["monotonic"] <= .75
                     and frame["context"]["board_token"] == ctx["board_token"]
                     and frame["geometry"] == geometry)
        item = {"id": click_id, "monotonic": now, "context": ctx}
        self.clicks.append(item)
        self.write("click", id=click_id, context=ctx, geometry=geometry,
                   pixel=[x, y], normalized=[x / (geometry["width"]-1), y / (geometry["height"]-1)],
                   preceding_image=frame["file"] if fresh else None,
                   needs_review=True)

    def action(self, report, connection, event, now):
        state = report.get("state") or {}
        data = event.get("data") or {}
        if connection != report.get("game_connection") or event.get("source") != "live":
            return
        name = event.get("name")
        own = data.get("seat", 0) == state.get("seat")
        winners = [w for w in data.get("hules", []) if w.get("seat", 0) == state.get("seat")]
        if not ((name in {"ActionDiscardTile", "ActionChiPengGang", "ActionAnGangAddGang"} and own)
                or (name == "ActionHule" and winners)):
            return
        # Correlation is evidence, never proof of a particular button or layout.
        candidates = [c["id"] for c in self.clicks if 0 <= now-c["monotonic"] <= 8
                      and c["context"]["generation"] == report.get("game_generation", 0)
                      and c["context"]["round"] == state.get("round")
                      and c["context"]["step"] == event.get("step", -1)-1]
        safe = {k: data[k] for k in ("seat", "tile", "tiles", "type", "froms", "is_liqi", "is_wliqi") if k in data}
        if winners:
            safe["winners"] = [{k: w.get(k) for k in ("seat", "hu_tile", "zimo")} for w in winners]
        self.write("action", name=name, step=event.get("step"), data=safe,
                   candidate_click_ids=candidates, needs_review=True)
        self.clicks.clear()

    def close(self):
        self.stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[4]
    parser.add_argument("--file", type=Path, help="Capture JSONL; defaults to newest capture")
    parser.add_argument("--schema", type=Path, default=root / "liqi-reference.json")
    parser.add_argument("--output", type=Path, default=root / "logs/mahjong_soul/calibration")
    parser.add_argument("--duration", type=float, default=3600)
    parser.add_argument("--max-mb", type=int, default=1024)
    args = parser.parse_args()
    if args.duration <= 0 or args.max_mb <= 0:
        parser.error("Duration and size limit must be positive")
    from games.mahjong_soul.live.runtime.windows_recording import WindowsRecorder
    backend = WindowsRecorder()
    schema = LiqiSchema.load(args.schema)
    reader = GameReader(schema)
    tail = None
    session = args.output / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    recorder = EvidenceRecorder(session, args.max_mb * 1024**2)
    print(f"Recording locally to {session}. Play normally; Ctrl+C stops.", flush=True)
    start = time.monotonic(); next_frame = 0
    samples = queue.Queue(maxsize=1000)
    stop = threading.Event()
    latest = [None]
    def sample_clicks():
        while not stop.is_set():
            sampled = backend.poll()
            current = latest[0]
            if sampled and sampled[1] and current:
                geometry, _, x, y = sampled
                try: samples.put_nowait((current, geometry, x, y, time.monotonic()))
                except queue.Full: pass  # Missing evidence never enables a layout.
            stop.wait(.005)
    worker = threading.Thread(target=sample_clicks, daemon=True)
    worker.start()
    try:
        while time.monotonic()-start < args.duration:
            paths = list((root / "logs/mahjong_soul").glob("capture-*.jsonl"))
            path = args.file or (max(paths, key=lambda p:p.stat().st_mtime_ns) if paths else None)
            if path and (tail is None or tail.path != path):
                tail = CaptureTail(path); reader = GameReader(schema)
                for row in tail.read(): reader.consume(row)  # Bootstrap, do not label historical actions.
                recorder.clicks.clear(); recorder.last_image = None
            while True:
                try:
                    current, geometry, x, y, clicked_at = samples.get_nowait()
                except queue.Empty: break
                recorder.click(current, geometry, x, y, clicked_at)
            if tail:
                rows = tail.read()
                if tail.reset:
                    reader = GameReader(schema); recorder.clicks.clear(); recorder.last_image = None
                for row in rows:
                    result = reader.consume(row)
                    for event in result.get("liqi", {}).get("events", []):
                        recorder.action(reader.snapshot(), row["connection"], event, time.monotonic())
            report = reader.snapshot()
            now = time.monotonic()
            latest[0] = report if report.get("state_ready") and report.get("connection_open") else None
            # Main-thread polling is read-only; the dedicated sampler tracks edges.
            sampled = backend.geometry()
            if sampled and latest[0]:
                geometry = sampled
                if now >= next_frame:
                    image = backend.frame(geometry)
                    if image: recorder.frame(report, geometry, image, time.monotonic())
                    next_frame = now + .25
            else:
                recorder.last_image = None
            time.sleep(.01)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set(); worker.join(timeout=2)
        recorder.close()
    print("Recorder stopped.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
