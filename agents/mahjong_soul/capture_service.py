"""Worktree-local capture ownership; reattach workers without replacing sockets."""
import ctypes
import json
import os
from pathlib import Path
import time


def pid_alive(pid):
    if type(pid) is not int or pid<=0:return False
    if os.name=="nt":
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            code=ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except OSError:return False


def read_service(registry):
    registry=Path(registry)
    try:
        value=json.loads(registry.read_text(encoding="utf-8"))
        output=Path(value["output"]).resolve()
        if (value.get("version")!=1 or not output.is_relative_to(registry.parent.resolve())
                or not isinstance(value.get("token"),str) or len(value["token"])!=32):return None
        marker=json.loads(output.with_suffix(".ready.json").read_text(encoding="utf-8"))
        if (marker.get("launch_token")!=value["token"] or marker.get("pid")!=value.get("pid")
                or not pid_alive(value["pid"])):return None
        return value
    except (OSError,ValueError,KeyError,TypeError):return None


def publish(registry,output,token,process,port):
    marker=json.loads(output.with_suffix(".ready.json").read_text(encoding="utf-8"))
    if marker.get("launch_token")!=token or type(marker.get("pid")) is not int:
        raise RuntimeError("Capture readiness ownership changed")
    value={"version":1,"output":str(output.resolve()),"token":token,"pid":marker["pid"],
           "process":process,"port":port}
    registry=Path(registry);temporary=registry.with_suffix(".tmp")
    temporary.write_text(json.dumps(value),encoding="utf-8");temporary.replace(registry)
    return value


def stop_service(registry,timeout=10):
    service=read_service(registry)
    if service is None:
        print("No resident Mahjong capture is running.",flush=True);return 0
    output=Path(service["output"])
    output.with_suffix(".stop.json").write_text(json.dumps({"launch_token":service["token"]}),encoding="utf-8")
    deadline=time.monotonic()+timeout
    while read_service(registry) is not None:
        if time.monotonic()>=deadline:raise RuntimeError("Capture did not acknowledge shutdown; it was not force-killed")
        time.sleep(.1)
    Path(registry).unlink(missing_ok=True)
    print("Resident Mahjong capture stopped. Existing captured connections may reconnect.",flush=True)
    return 0
