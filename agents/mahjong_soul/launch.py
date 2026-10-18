"""Own capture and automatic play (or read-only suggestions) as one package."""
import argparse
from contextlib import ExitStack
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
from agents.mahjong_soul.capture_service import read_service, publish, stop_service


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
            if os.name=="nt":
                # The venv executable is a wrapper around the real Python
                # worker. Kill this owned tree, not only the wrapper PID.
                result=subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                                      stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                if result.returncode and process.poll() is None:process.kill()
            else:process.kill()
            process.wait()


def ready(path, pid, token=None):
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        return value.get("version")==1 and (value.get("launch_token")==token if token is not None else value.get("pid")==pid)
    except (OSError, ValueError):
        return False


def supervise(command, worker, *, cwd, output, startup_timeout=120,
              keep_capture=False, registry=None, service=None, process=None, port=None):
    capture=agent=None
    capture_ready=False
    flags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0
    capture_log=output.with_suffix(".console.log")
    token=uuid.uuid4().hex
    environment=dict(os.environ,MAHJONG_CAPTURE_READY_TOKEN=token)
    output.parent.mkdir(parents=True,exist_ok=True)
    print("Capture log: "+str(capture_log),flush=True)
    try:
        with ExitStack() as stack:
            if service is None:
                stream=stack.enter_context(capture_log.open("w",encoding="utf-8"))
                capture_flags=flags | (subprocess.DETACHED_PROCESS if os.name=="nt" and keep_capture else 0)
                capture=subprocess.Popen(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,creationflags=capture_flags,env=environment,
                    start_new_session=keep_capture and os.name!="nt")
                deadline=time.monotonic()+startup_timeout
                while not ready(output.with_suffix(".ready.json"),capture.pid,token):
                    if capture.poll() is not None:
                        raise RuntimeError("Capture exited before startup; inspect "+str(capture_log))
                    if time.monotonic()>=deadline:
                        raise RuntimeError("Capture startup timed out; inspect "+str(capture_log))
                    time.sleep(.2)
                if capture.poll() is not None:raise RuntimeError("Capture exited during startup")
                if keep_capture:service=publish(registry,output,token,process,port)
            else:
                print("Reusing resident capture; existing game connections are preserved.",flush=True)
            capture_ready=True
            print("Capture ready. Four-player AI room, 1920x1080, game foreground."
                  if "agents.mahjong_soul.auto" in worker else
                  "Capture ready. Suggestions only; no automatic input.",flush=True)
            agent=subprocess.Popen(worker,cwd=cwd,creationflags=flags)
            while True:
                if agent.poll() is not None:return agent.returncode
                if (capture is not None and capture.poll() is not None
                        or service is not None and read_service(registry) is None):
                    raise RuntimeError("Capture stopped; stopping the agent too. Inspect "+str(capture_log))
                time.sleep(.2)
    except KeyboardInterrupt:
        return 130
    finally:
        stop(agent)
        if not keep_capture or not capture_ready:
            stop(capture)
        elif capture is not None or service is not None:
            print("Agent stopped; capture remains running to preserve game connections. "
                  "Use MahjongSoulCaptureStop.bat to shut capture down explicitly.",flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-capture",action="store_true",help="Explicitly stop resident capture after stopping the agent")
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
    registry=root/"logs/mahjong_soul/capture-service.json"
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output=root/"logs/mahjong_soul"/("capture-"+stamp+".jsonl")
    module="agents.mahjong_soul.shadow" if args.monitor else "agents.mahjong_soul.auto"
    options=["--policy","playbook","--playstyle","atk"] if args.monitor else ["--execute","--resume-current"]
    worker=[sys.executable,"-u","-m",module,*options,"--file",str(output),*extra]
    lease=None
    try:
        lease=AgentLease(root/"logs/mahjong_soul/package.lock")
        if args.stop_capture:return stop_service(registry)
        service=read_service(registry)
        if service is not None:
            if service.get("process")!=args.process or service.get("port")!=args.port:
                raise ValueError("Resident capture uses different process/port settings; stop it explicitly before changing them")
            output=Path(service["output"])
            worker[worker.index("--file")+1]=str(output)
            return supervise(None,worker,cwd=root,output=output,keep_capture=True,registry=registry,service=service)
        return capture_main(["--process",args.process,"--port",str(args.port),"--output",str(output)],
            run=lambda command,cwd:supervise(command,worker,cwd=cwd,output=output,startup_timeout=args.startup_timeout,
                                                  keep_capture=True,registry=registry,process=args.process,port=args.port))
    except (OSError,ValueError,RuntimeError) as error:
        print("Mahjong package stopped: "+str(error),flush=True)
        return 1
    finally:
        if lease is not None:lease.close()


if __name__=="__main__":
    raise SystemExit(main())
