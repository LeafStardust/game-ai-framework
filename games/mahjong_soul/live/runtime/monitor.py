"""Display current game state while following the latest local capture file."""

import argparse
import json
from pathlib import Path
import sys
import time

from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.reader import GameReader


class CaptureTail:
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.pending = b""
        self.bad_rows = 0
        self.reset = False

    def read(self):
        self.reset = False
        if not self.path.exists():
            return []
        if self.path.stat().st_size < self.offset:
            self.offset = 0
            self.pending = b""
            self.reset = True
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            chunk = stream.read()
            self.offset = stream.tell()
        lines = (self.pending + chunk).split(b"\n")
        self.pending = lines.pop()
        rows = []
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or not (all(key in row for key in ("connection", "raw_base64", "direction")) or (row.get("event") == "connection_closed" and "connection" in row)):
                    raise ValueError("Invalid capture row")
                rows.append(row)
            except (ValueError, UnicodeError):
                self.bad_rows += 1
        return rows


def render(summary, path=None, bad_rows=0):
    lines = ["MAHJONG SOUL READER", f"Capture: {path or 'none yet'}",
             f"Frames: {summary['frames']} | Game actions: {sum(summary['actions'].values())} | Decode errors: {sum(item['count'] for item in summary['decode_errors'])} | Schema warnings: {sum(item['count'] for item in summary['schema_warnings'])} | Malformed rows: {bad_rows}"]
    state = summary["state"]
    if not state:
        lines.append("Waiting for a game connection / round start.")
    else:
        lines.extend([f"Status: {state['status']} | Connection: {'open' if summary['connection_open'] else 'closed'} | Players: {state['player_count']} | Own seat: {state['seat']} | Step: {state['step']}",
                      f"Round: {state['round']} | Last actor: {state['turn']} | Wall: {state['left_tile_count']}",
                      "Hand: " + " ".join(state['hand']), "Dora indicators: " + " ".join(state['doras'])])
        for seat in range(state['player_count']):
            score = state['scores'][seat] if seat < len(state['scores']) else "?"
            river = " ".join(item['tile'] + ("*" if item.get('called') else "") + ("R" if item.get('riichi') else "") for item in state['discards'][seat])
            melds = " | ".join(" ".join(item.get('tiles', [])) for item in state['melds'][seat])
            lines.extend([f"Seat {seat}: score {score} | Norths {state['norths'][seat]} | Riichi {state['riichi'][seat]}", f"  Discards: {river or '-'}", f"  Melds: {melds or '-'}"])
        lines.append(f"Drawn tile: {state['drawn_tile'] or '-'} | Furiten: {state['furiten']}")
        operation = state['operations'] or {}
        labels = {1: 'discard', 2: 'chi', 3: 'pon', 5: 'open kan', 6: 'added kan', 7: 'riichi', 8: 'tsumo', 9: 'ron', 11: 'extract north'}
        choices = [labels.get(item['type'], 'type ' + str(item['type'])) + (":" + "/".join(item.get('combination', [])) if item.get('combination') else "") for item in operation.get('operation_list', [])]
        lines.append(f"Operations for seat {operation.get('seat', '?')}: " + (", ".join(choices) or "none"))
        lines.append("Visible tile counts: " + ", ".join(f"{tile}:{count}" for tile, count in state["visible_tile_counts"].items()) + ("" if state["visibility_complete"] else " (incomplete / lower bound)"))
        if state['issues']:
            lines.append("State issues: " + "; ".join(state['issues']))
    if summary['decode_errors']:
        lines.append("Decode diagnostics: " + "; ".join(f"{item['method']}: {item['error']} ({item['count']})" for item in summary['decode_errors']))
    if summary["schema_warnings"]:
        lines.append("Opaque lobby diagnostics: " + "; ".join(f"{item['method']}: {item['warning']} ({item['count']})" for item in summary["schema_warnings"]))
    lines.append("Tiles: m=characters, p=circles, s=bamboo, z=honors; 0=red five. * = called discard; R = riichi discard.")
    return "\n".join(lines)


def main():
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="Follow one capture; default is newest capture-*.jsonl")
    parser.add_argument("--schema", default=str(root / "liqi-reference.json"))
    parser.add_argument("--seat", type=int, choices=range(4))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print a structured summary")
    args = parser.parse_args()
    schema = LiqiSchema.load(args.schema)
    reader = GameReader(schema, args.seat)
    tail = None
    last_display = None
    try:
        while True:
            candidates = list((root / "logs/mahjong_soul").glob("capture-*.jsonl"))
            path = Path(args.file).resolve() if args.file else max(candidates, key=lambda item: item.stat().st_mtime_ns) if candidates else None
            if path and (tail is None or tail.path != path):
                tail = CaptureTail(path)
                reader = GameReader(schema, args.seat)
            if tail:
                rows = tail.read()
                if tail.reset:
                    reader = GameReader(schema, args.seat)
                for row in rows:
                    try:
                        reader.consume(row)
                    except (ValueError, KeyError, TypeError):
                        tail.bad_rows += 1
            summary = reader.snapshot()
            display = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else render(summary, path, tail.bad_rows if tail else 0)
            if display != last_display:
                if sys.stdout.isatty() and not args.once and not args.json:
                    print("\033[2J\033[H", end="")
                print(display, flush=True)
                last_display = display
            if args.once:
                return 0
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
