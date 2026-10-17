"""Run Mahjong Soul capture with worktree-local schema, logs and certificates."""

import argparse
from datetime import datetime
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

from games.mahjong_soul.live.external.schema import LiqiSchema


def main(argv=None, *, run=None):
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--output", help="JSONL output; defaults to a new timestamped capture")
    parser.add_argument("--schema", default=str(root / "liqi-reference.json"))
    parser.add_argument("--raw-only", action="store_true", help="Record envelopes without typed decoding")
    parser.add_argument("--seat", type=int, choices=range(4), help="Own absolute seat, 0-3")
    parser.add_argument("--action-encoding", choices=("xor", "plain"), default="xor")
    parser.add_argument("--process", help="Capture just this process name or PID using local mode")
    parser.add_argument("--hosts", default="mahjongsoul.com,maj-soul.com,majsoul.com,yo-star.com")
    parser.add_argument("--confdir", help="Proxy config/certificate directory; defaults to this worktree")
    parser.add_argument("--check", action="store_true", help="Validate dependencies/schema without starting capture")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if args.process is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+", args.process):
        parser.error("process must be one explicit name or PID; lists and exclusions are unsupported")
    if importlib.util.find_spec("mitmproxy") is None:
        parser.error("Run MahjongSoulSetup.bat to install capture dependencies in this worktree")
    schema = None
    if not args.raw_only:
        schema = Path(args.schema).resolve()
        try:
            loaded = LiqiSchema.load(schema)
            if "lq.ActionPrototype" not in loaded.types:
                raise ValueError("schema lacks lq.ActionPrototype")
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(f"Cannot load schema: {error}")
    output = Path(args.output).resolve() if args.output else root / "logs/mahjong_soul" / ("capture-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".jsonl")
    confdir = Path(args.confdir).resolve() if args.confdir else root / "logs/mahjong_soul/proxy"
    command = [sys.executable, "-c", "from mitmproxy.tools.main import mitmdump; mitmdump()",
               "--listen-host", "127.0.0.1", "--listen-port", str(args.port),
               "--mode", "local:" + args.process if args.process else "regular",
               "-s", str(root / "games/mahjong_soul/live/external/capture.py"),
               "--set", "flow_detail=0",
               "--set", f"confdir={confdir}",
               "--set", f"mahjong_capture_output={output}",
               "--set", f"mahjong_capture_hosts={args.hosts}",
               "--set", f"mahjong_action_encoding={args.action_encoding}"]
    if schema:
        command.extend(["--set", f"mahjong_capture_schema={schema}"])
    if args.seat is not None:
        command.extend(["--set", f"mahjong_capture_seat={args.seat}"])
    print(f"Capture mode: {'process ' + args.process if args.process else 'regular proxy on 127.0.0.1:' + str(args.port)}", flush=True)
    print(f"Schema: {schema or 'raw envelopes only'}", flush=True)
    print(f"Output: {output}", flush=True)
    print(f"Proxy certificate: {confdir / 'mitmproxy-ca-cert.cer'}", flush=True)
    if args.check:
        print("Dependency and schema checks passed. Live routing/TLS are not checked.")
        return 0
    try:
        return (run or subprocess.call)(command, cwd=root)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
