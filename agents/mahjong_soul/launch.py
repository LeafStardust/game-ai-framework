"""Own capture and automatic play (or read-only suggestions) as one package."""
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from games.mahjong_soul.live.__main__ import main as capture_main
from games.mahjong_soul.live.runtime.session import AgentLease


def stop(process):
    """Stop only a child we created, allowing input/capture logs to flush."""
    if process is None or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        if process.poll() is None:
            process.kill()
            process.wait()


def ready(path, pid, token=None):
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        return value.get("version")==1 and (value.get("launch_token")==token if token is not None else value.get("pid")==pid)
    except (OSError, ValueError):
        return False


def supervise(command, worker, *, cwd, output, startup_timeout=120):
    capture=agent=None
    flags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0
    capture_log=output.with_suffix(".console.log")
    token=uuid.uuid4().hex
    environment=dict(os.environ,MAHJONG_CAPTURE_READY_TOKEN=token)
    output.parent.mkdir(parents=True,exist_ok=True)
    print("Capture log: "+str(capture_log),flush=True)
    try:
        with capture_log.open("w",encoding="utf-8") as stream:
            capture=subprocess.Popen(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,creationflags=flags,env=environment)
            deadline=time.monotonic()+startup_timeout
            while not ready(output.with_suffix(".ready.json"),capture.pid,token):
                if capture.poll() is not None:
                    raise RuntimeError("Capture exited before startup; inspect "+str(capture_log))
                if time.monotonic()>=deadline:
                    raise RuntimeError("Capture startup timed out; inspect "+str(capture_log))
                time.sleep(.2)
            if capture.poll() is not None:
                raise RuntimeError("Capture exited during startup")
            print("Capture ready. Open/reopen Mahjong Soul and enter a four-player AI room at 1920x1080."
                  if "agents.mahjong_soul.auto" in worker else
                  "Capture ready. Open/reopen Mahjong Soul. Suggestions only; no automatic input.",flush=True)
            agent=subprocess.Popen(worker,cwd=cwd,creationflags=flags)
            while True:
                if agent.poll() is not None:
                    return agent.returncode
                if capture.poll() is not None:
                    raise RuntimeError("Capture stopped; stopping the agent too. Inspect "+str(capture_log))
                time.sleep(.2)
    except KeyboardInterrupt:
        return 130
    finally:
        # Stop input before releasing its data source. Never kill unrelated
        # Python, game or Balatro processes.
        stop(agent)
        stop(capture)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitor",action="store_true",help="Read-only suggestions with capture; never starts mouse input")
    parser.add_argument("--process",default="Jantama_MahjongSoul.exe")
    parser.add_argument("--port",type=int,default=8080)
    parser.add_argument("--startup-timeout",type=float,default=120)
    args,extra=parser.parse_known_args(argv)
    if not math.isfinite(args.startup_timeout) or args.startup_timeout<=0:
        parser.error("Startup timeout must be finite and positive")
    if any(value=="--file" or value.startswith("--file=") for value in extra):
        parser.error("The package owns its capture file; use the standalone modules to attach another file")
    root=Path(__file__).resolve().parents[2]
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output=root/"logs/mahjong_soul"/("capture-"+stamp+".jsonl")
    module="agents.mahjong_soul.shadow" if args.monitor else "agents.mahjong_soul.auto"
    options=["--policy","playbook","--playstyle","atk"] if args.monitor else ["--execute","--resume-current"]
    worker=[sys.executable,"-u","-m",module,*options,"--file",str(output),*extra]
    lease=None
    try:
        lease=AgentLease(root/"logs/mahjong_soul/package.lock")
        return capture_main(["--process",args.process,"--port",str(args.port),"--output",str(output)],
            run=lambda command,cwd:supervise(command,worker,cwd=cwd,output=output,startup_timeout=args.startup_timeout))
    except (OSError,ValueError,RuntimeError) as error:
        print("Mahjong package stopped: "+str(error),flush=True)
        return 1
    finally:
        if lease is not None:lease.close()


if __name__=="__main__":
    raise SystemExit(main())
