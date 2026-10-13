"""Start a loopback-only capture proxy for the Steam client."""

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--output", default="logs/mahjong_soul/capture.jsonl")
    parser.add_argument("--schema", help="Client protobufjs liqi.json schema")
    parser.add_argument("--seat", type=int, choices=range(4), help="Own absolute seat, 0-3")
    parser.add_argument("--action-encoding", choices=("xor", "plain"), default="xor")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if importlib.util.find_spec("mitmproxy") is None:
        parser.error("Install capture dependencies: py -m pip install -r games/mahjong_soul/setup/requirements.txt")
    root = Path(__file__).resolve().parents[3]
    addon = root / "games/mahjong_soul/live/external/capture.py"
    # Use the installed entry point via a Python shim, preserving this interpreter.
    command = [sys.executable, "-c", "from mitmproxy.tools.main import mitmdump; mitmdump()",
               "--listen-host", "127.0.0.1", "--listen-port", str(args.port),
               "-s", str(addon), "--set",
               f"mahjong_capture_output={Path(args.output).resolve()}"]
    if args.schema:
        if not Path(args.schema).is_file():
            parser.error("schema file does not exist")
        command.extend(["--set", f"mahjong_capture_schema={Path(args.schema).resolve()}"])
    if args.seat is not None:
        command.extend(["--set", f"mahjong_capture_seat={args.seat}"])
    command.extend(["--set", f"mahjong_action_encoding={args.action_encoding}"])
    try:
        return subprocess.call(command, cwd=root)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
