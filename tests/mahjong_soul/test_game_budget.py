from copy import deepcopy
from types import SimpleNamespace
import pytest
from agents.mahjong_soul.game_budget import GameBudget,positive_games
from agents.mahjong_soul import launch


def report(status,connection="one",generation=1):
    return {"game_connection":connection,"game_generation":generation,"state":{"status":status}}


def test_counts_matches_once_not_rounds_disconnects_or_historical_end():
    b=GameBudget(2)
    assert not b.observe(report("match_ended","old"))
    assert not b.completed
    for state in ("tracking","round_ended","tracking","round_ended","match_ended","match_ended"):
        b.observe(report(state))
    assert len(b.completed)==1 and not b.done
    b.observe(report("waiting_for_round","two",2))
    assert not b.observe(report("match_ended","two",2))
    b.observe(report("tracking","two",2))
    assert b.observe(report("match_ended","two",2)) and len(b.completed)==2


def test_unlimited_default_and_new_generation_on_same_connection():
    b=GameBudget()
    for generation in (1,2):
        b.observe(report("tracking",generation=generation))
        assert not b.observe(report("match_ended",generation=generation))
    assert len(b.completed)==2 and not b.done


@pytest.mark.parametrize("bad",["0","-1","1.5","abc",""])
def test_invalid_counts_rejected_before_launch(bad):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError):positive_games(bad)
    with pytest.raises(SystemExit):launch.main([bad])


def test_numeric_bat_argument_reaches_auto_worker_without_confusing_forwarded_options(monkeypatch):
    seen={}
    class Lease:
        def __init__(self,path):pass
        def close(self):pass
    monkeypatch.setattr(launch,"AgentLease",Lease)
    monkeypatch.setattr(launch,"read_service",lambda _:None)
    monkeypatch.setattr(launch,"capture_main",lambda argv,run:run(["capture"],None))
    def supervise(command,worker,**kwargs):seen["worker"]=worker;return 0
    monkeypatch.setattr(launch,"supervise",supervise)
    assert launch.main(["3","--duration","10"])==0
    worker=seen["worker"]
    assert worker[worker.index("--games")+1]=="3" and worker[-2:]==["--duration","10"]
    assert launch.main(["--duration","10"])==0
    assert "--games" not in seen["worker"] and seen["worker"][-2:]==["--duration","10"]
    with pytest.raises(SystemExit):launch.main(["2","--monitor"])


def test_limit_prevents_result_restart_or_any_further_input(monkeypatch):
    from tests.mahjong_soul.test_auto import setup
    from agents.mahjong_soul.shadow import ShadowFollower
    f,r,_,_,mouse=setup(monkeypatch);f.game_budget=GameBudget(1)
    r["game_connection"]="one";r["game_generation"]=1
    f.reader=SimpleNamespace(snapshot=lambda:deepcopy(r))
    f._game_limit()
    assert f.game_budget.active
    r["state"]["status"]="match_ended"
    monkeypatch.setattr(ShadowFollower,"poll",lambda _: {"kind":"status"})
    f.result_buttons.poll=lambda _:pytest.fail("No result or Start input after game limit")
    assert f.poll()=={"kind":"finished","reason":"game_limit_reached","completed":1,"limit":1}
    assert not f.enabled and not mouse.clicks
    assert f.poll()["kind"]=="finished" and not mouse.clicks


def test_result_snapshot_that_drains_match_end_also_enforces_limit(monkeypatch):
    from tests.mahjong_soul.test_result_buttons import owner
    from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
    o,r,m,logs=owner(monkeypatch)
    def done():return {"kind":"finished","reason":"game_limit_reached","completed":1,"limit":1}
    o._game_limit=done
    handler=ResultButtons(lambda _:pytest.fail("Budget must precede OCR and clicks"))
    assert handler.poll(o)["kind"]=="finished" and not m.clicks


def test_ranked_limit_navigates_results_then_stops_on_end_screen_without_requeue(monkeypatch):
    from tests.mahjong_soul.test_auto import setup
    from tests.mahjong_soul.test_result_buttons import word,labels
    from tests.mahjong_soul.test_ranked_requeue import words
    from tests.mahjong_soul.test_ranked_access import auth
    from games.mahjong_soul.live.runtime.lobby import detect_lobby
    from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
    from agents.mahjong_soul.shadow import ShadowFollower
    f,r,_,_,mouse=setup(monkeypatch);now=[1];f.clock=lambda:now[0]
    f.game_budget=GameBudget(1);r["state"]["lobby"]=detect_lobby(auth())
    f.reader=SimpleNamespace(snapshot=lambda:deepcopy(r));f._result_snapshot=lambda:deepcopy(r)
    assert f._game_limit() is None
    r["state"].update(status="match_ended",operations=None)
    assert f._game_limit() is None and f.game_budget.done and f.enabled
    monkeypatch.setattr(ShadowFollower,"poll",lambda _:{"kind":"status","reason":"waiting_for_ready_board"})
    monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",lambda _:bytes(1920*1080*3))
    monkeypatch.setattr("games.mahjong_soul.live.runtime.ranked_requeue.decode_frame",lambda _:bytes(1920*1080*3))
    handler=ResultButtons(lambda _:labels(word("Confirm")));f.result_buttons=handler
    assert f.poll()["reason"]=="result_button_submitted" and len(mouse.clicks)==1
    assert f.enabled and not f.final_result_verified
    handler.ocr=lambda _:words();now[0]=2
    event=f.poll()
    assert event=={"kind":"finished","reason":"game_limit_reached","completed":1,"limit":1}
    assert not f.enabled and f.final_result_verified and len(mouse.clicks)==1
    assert f.poll()["kind"]=="finished" and len(mouse.clicks)==1
