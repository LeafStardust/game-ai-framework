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
    try:
        return subprocess.call(command, cwd=root)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
