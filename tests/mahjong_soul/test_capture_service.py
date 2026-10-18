import json
from pathlib import Path
import pytest
from agents.mahjong_soul import capture_service as service
from agents.mahjong_soul import launch
from tests.mahjong_soul.test_launch import Child


def setup_service(tmp_path,monkeypatch):
    output=tmp_path/"capture.jsonl";output.touch()
    token="a"*32
    output.with_suffix(".ready.json").write_text(json.dumps({"version":1,"pid":202,"launch_token":token}))
    registry=tmp_path/"capture-service.json"
    value=service.publish(registry,output,token,"game.exe",8080)
    monkeypatch.setattr(service,"pid_alive",lambda pid:pid==202)
    return registry,output,value


def test_resident_capture_is_verified_against_real_worker_token_and_pid(tmp_path,monkeypatch):
    registry,output,value=setup_service(tmp_path,monkeypatch)
    assert service.read_service(registry)==value
    output.with_suffix(".ready.json").write_text(json.dumps({"version":1,"pid":202,"launch_token":"b"*32}))
    assert service.read_service(registry) is None


def test_dead_capture_is_not_reused(tmp_path,monkeypatch):
    registry,_,_=setup_service(tmp_path,monkeypatch)
    monkeypatch.setattr(service,"pid_alive",lambda pid:False)
    assert service.read_service(registry) is None


def test_explicit_capture_stop_requests_only_the_owned_token(tmp_path,monkeypatch):
    registry,output,value=setup_service(tmp_path,monkeypatch)
    answers=iter([value,None])
    monkeypatch.setattr(service,"read_service",lambda path:next(answers))
    assert service.stop_service(registry)==0
    assert json.loads(output.with_suffix(".stop.json").read_text())=={"launch_token":value["token"]}


def test_reused_capture_only_starts_worker_and_survives_agent_exit(tmp_path,monkeypatch):
    registry,output,value=setup_service(tmp_path,monkeypatch)
    child=Child(303);calls=[]
    def popen(command,**kwargs):calls.append(command);return child
    monkeypatch.setattr(launch.subprocess,"Popen",popen)
    monkeypatch.setattr(launch,"read_service",lambda path:value)
    monkeypatch.setattr(launch.time,"sleep",lambda seconds:setattr(child,"returncode",0))
    assert launch.supervise(None,["agent"],cwd=tmp_path,output=output,keep_capture=True,registry=registry,service=value)==0
    assert calls==[["agent"]] and not child.signals
    assert service.read_service(registry)==value


def test_new_resident_capture_survives_ctrl_c_stopping_worker(tmp_path,monkeypatch):
    capture,agent=Child(101),Child(102);children=iter([capture,agent]);options=[]
    def popen(command,**kwargs):options.append(kwargs);return next(children)
    monkeypatch.setattr(launch.subprocess,"Popen",popen)
    monkeypatch.setattr(launch,"ready",lambda *args:True)
    monkeypatch.setattr(launch,"publish",lambda *args:{"pid":202})
    monkeypatch.setattr(launch,"read_service",lambda *args:{"pid":202})
    def interrupt(seconds):raise KeyboardInterrupt
    monkeypatch.setattr(launch.time,"sleep",interrupt)
    assert launch.supervise(["capture"],["agent"],cwd=tmp_path,output=tmp_path/"capture.jsonl",keep_capture=True,registry=tmp_path/"service.json")==130
    assert capture.poll() is None and not capture.signals
    assert agent.poll() is not None
    assert options[0]["env"]["MAHJONG_CAPTURE_READY_TOKEN"]


def test_main_reuses_existing_capture_instead_of_reconfiguring_proxy(tmp_path,monkeypatch):
    value={"process":"Jantama_MahjongSoul.exe","port":8080,"output":str(tmp_path/"capture.jsonl")}
    class Lease:
        def __init__(self,*args):pass
        def close(self):pass
    monkeypatch.setattr(launch,"AgentLease",Lease)
    monkeypatch.setattr(launch,"read_service",lambda *args:value)
    def unexpected(*args,**kwargs):raise AssertionError("Must not start capture again")
    monkeypatch.setattr(launch,"capture_main",unexpected)
    def supervise(command,worker,**kwargs):
        assert command is None
        assert worker[worker.index("--file")+1]==value["output"]
        assert not kwargs.get("keep_capture",False) and kwargs["service"]==value
        return 0
    monkeypatch.setattr(launch,"supervise",supervise)
    assert launch.main([])==0


@pytest.mark.parametrize("owned",[False,True])
def test_capture_shutdown_request_requires_the_launch_token(tmp_path,monkeypatch,owned):
    import asyncio
    import sys
    from types import SimpleNamespace
    from games.mahjong_soul.live.external.capture import MahjongSoulCapture,CaptureWriter
    stopped=[]
    monkeypatch.setenv("MAHJONG_CAPTURE_READY_TOKEN","a"*32)
    monkeypatch.setitem(sys.modules,"mitmproxy",SimpleNamespace(ctx=SimpleNamespace(master=SimpleNamespace(shutdown=lambda:stopped.append(True)))))
    capture=MahjongSoulCapture();capture.writer=CaptureWriter(tmp_path/"capture.jsonl")
    request=capture.writer.path.with_suffix(".stop.json")
    request.write_text(json.dumps({"launch_token":("a" if owned else "b")*32}))
    async def run():
        await capture.running()
        await asyncio.sleep(0)
        capture.done()
    asyncio.run(run())
    assert bool(stopped)==owned
    assert request.exists()==(not owned)


def test_stop_kills_only_the_owned_windows_wrapper_tree_on_timeout(monkeypatch):
    from types import SimpleNamespace
    import subprocess
    child=Child(123);commands=[]
    monkeypatch.setattr(launch,"os",SimpleNamespace(name="nt"))
    monkeypatch.setattr(launch.signal,"CTRL_BREAK_EVENT",1,raising=False)
    def wait(timeout=None):
        if child.returncode is None:raise subprocess.TimeoutExpired("owned",5)
        return child.returncode
    child.wait=wait
    child.send_signal=lambda value:None
    def run(command,**kwargs):commands.append(command);child.returncode=1;return SimpleNamespace(returncode=0)
    monkeypatch.setattr(launch.subprocess,"run",run)
    launch.stop(child)
    assert commands==[["taskkill","/PID","123","/T","/F"]]


def test_default_package_stops_reused_legacy_capture_with_worker(tmp_path,monkeypatch):
    registry,output,value=setup_service(tmp_path,monkeypatch)
    child=Child(303);stopped=[]
    monkeypatch.setattr(launch.subprocess,"Popen",lambda *args,**kwargs:child)
    monkeypatch.setattr(launch,"read_service",lambda *args:value)
    monkeypatch.setattr(launch,"stop_service",lambda path:stopped.append(path))
    monkeypatch.setattr(launch.time,"sleep",lambda seconds:setattr(child,"returncode",0))
    assert launch.supervise(None,["agent"],cwd=tmp_path,output=output,registry=registry,service=value)==0
    assert stopped==[registry]
