"""Decode a saved capture into a new JSONL file without a running game."""

import argparse
import base64
import json
from pathlib import Path

from games.mahjong_soul.live.external.capture import CaptureWriter
from games.mahjong_soul.live.external.schema import LiqiSchema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seat", type=int, choices=range(4))
    parser.add_argument("--action-encoding", choices=("xor", "plain"), default="xor")
    args = parser.parse_args()
    source, output = Path(args.capture).resolve(), Path(args.output).resolve()
    if source == output or output.exists():
        parser.error("output must be a new file distinct from the capture")
    writer = CaptureWriter(output, LiqiSchema.load(args.schema), args.seat, args.action_encoding)
    count, errors, closures = 0, 0, 0
    with source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("Capture row must be an object")
                if not isinstance(row.get("connection"), str) or not row["connection"]:
                    raise ValueError("Invalid capture connection")
                if row.get("event") == "connection_closed":
                    writer.close_connection(row["connection"], row.get("timestamp"))
                    closures += 1
                    continue
                if row.get("event"):
                    raise ValueError("Unknown capture control event")
                if row["direction"] not in ("client", "server"):
                    raise ValueError("Invalid capture direction")
                record = writer.record(connection=row["connection"], host=row["host"],
                                       content=base64.b64decode(row["raw_base64"], validate=True),
                                       from_client=row["direction"] == "client",
                                       timestamp=row["timestamp"], is_text=row.get("is_text", False))
            except (ValueError, KeyError, TypeError) as error:
                parser.error(f"Invalid capture row {line_number}: {error}")
            count += 1
            errors += "decode_error" in record
    print(f"Decoded {count} frames; {errors} decode errors; {closures} connection closures. Output: {output}")


if __name__ == "__main__":
    main()
