import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from agents.mahjong_soul import launch
from games.mahjong_soul.live.external.capture import CaptureWriter, MahjongSoulCapture


def test_capture_ready_marker_is_published_only_on_running_and_removed(tmp_path):
    capture=MahjongSoulCapture()
    capture.writer=CaptureWriter(tmp_path/"capture.jsonl")
    marker=capture.writer.path.with_suffix(".ready.json")
    assert not marker.exists()
    async def run():
        await capture.running()
        assert launch.ready(marker,launch.os.getpid())
        assert not launch.ready(marker,launch.os.getpid()+1)
        capture.done()
    asyncio.run(run())
    assert not marker.exists()


class Child:
    def __init__(self,pid):self.pid=pid;self.returncode=None;self.signals=[]
    def poll(self):return self.returncode
    def send_signal(self,value):self.signals.append(value);self.returncode=0
    def wait(self,timeout=None):return self.returncode
    def kill(self):self.returncode=-9


@pytest.mark.parametrize("exit_source",["worker","capture","interrupt"])
def test_supervisor_stops_only_its_children_when_either_exits(monkeypatch,tmp_path,exit_source):
    capture,agent=Child(101),Child(102)
    children=iter([capture,agent]);commands=[];sleeps=[]
    def popen(command,**kwargs):commands.append(command);return next(children)
    monkeypatch.setattr(launch.subprocess,"Popen",popen)
    monkeypatch.setattr(launch,"ready",lambda path,pid,token:pid==101)
    def sleep(_):
        sleeps.append(1)
        if exit_source=="interrupt":raise KeyboardInterrupt
        (agent if exit_source=="worker" else capture).returncode=7
    monkeypatch.setattr(launch.time,"sleep",sleep)
    options=dict(cwd=tmp_path,output=tmp_path/"capture.jsonl")
    if exit_source=="capture":
        with pytest.raises(RuntimeError,match="Capture stopped"):
            launch.supervise(["capture"],["agent"],**options)
    else:
        assert launch.supervise(["capture"],["agent"],**options)==(130 if exit_source=="interrupt" else 7)
    assert commands==[["capture"],["agent"]]
    assert capture.poll() is not None and agent.poll() is not None


def test_capture_start_failure_never_launches_agent(monkeypatch,tmp_path):
    capture=Child(101);capture.returncode=1;commands=[]
    def popen(command,**kwargs):commands.append(command);return capture
    monkeypatch.setattr(launch.subprocess,"Popen",popen)
    monkeypatch.setattr(launch,"ready",lambda *args:False)
    with pytest.raises(RuntimeError,match="before startup"):
        launch.supervise(["capture"],["agent"],cwd=tmp_path,output=tmp_path/"capture.jsonl")
    assert commands==[["capture"]]


@pytest.mark.parametrize("monitor",[False,True])
def test_package_binds_capture_and_worker_to_same_file(monkeypatch,monitor):
    seen={}
    class Lease:
        def __init__(self,path):pass
        def close(self):seen["closed"]=True
    monkeypatch.setattr(launch,"AgentLease",Lease)
    def capture_main(argv,run):
        seen["capture_args"]=argv
        return run(["capture"],Path.cwd())
    def supervise(command,worker,**kwargs):seen.update(worker=worker,**kwargs);return 0
    monkeypatch.setattr(launch,"capture_main",capture_main)
    monkeypatch.setattr(launch,"supervise",supervise)
    assert launch.main((["--monitor"] if monitor else [])+["--duration","10"])==0
    worker=seen["worker"]
    assert str(seen["output"])==worker[worker.index("--file")+1]
    assert str(seen["output"])==seen["capture_args"][-1]
    assert ("--execute" in worker)==(not monitor)
    assert ("agents.mahjong_soul.shadow" in worker)==monitor
    assert worker[-2:]==["--duration","10"]
    assert seen["closed"]


def test_package_rejects_capture_file_override():
    with pytest.raises(SystemExit):launch.main(["--file=old-capture.jsonl"])


def test_ready_token_accepts_windows_python_child_pid_without_accepting_other_runs(tmp_path):
    marker=tmp_path/"capture.ready.json"
    marker.write_text(json.dumps({"version":1,"pid":202,"launch_token":"owned-run"}),encoding="utf-8")
    assert launch.ready(marker,101,"owned-run")
    assert not launch.ready(marker,101,"different-run")
    assert not launch.ready(marker,101)
