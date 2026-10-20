from copy import deepcopy
from types import SimpleNamespace
import pytest
from games.mahjong_soul.live.runtime.result_buttons import ResultButtons,result_button
from tests.mahjong_soul.test_input import inputs,Mouse


def word(label="Continue",x=900,y=950):
    return {"text":label,"x":x,"y":y,"width":120,"height":30}


def labels(*items):
    return [word("Result",y=250),*items]


def owner(monkeypatch):
    report,_=inputs();report["state"]["status"]="round_ended";report["state"]["operations"]=None
    mouse=Mouse();logs=[]
    geometry={"width":1920,"height":1080,"left":0,"top":0}
    o=SimpleNamespace(require_ai=False,ai_games=set(),controller=SimpleNamespace(backend=mouse,snapshot=lambda:{"status":"idle"}),
                      recorder=SimpleNamespace(geometry=lambda:geometry),_current=lambda:deepcopy(report),
                      _frame=lambda *args:b"frame",sleep=lambda _:None,_record=lambda kind,**data:logs.append((kind,data)),halted=None)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",lambda _:bytes(1920*1080*3))
    return o,report,mouse,logs


def test_only_unique_lower_result_labels_are_accepted():
    assert result_button(labels(word()))==("continue",960,965)
    for words in (labels(word("Start")),labels(word(y=100)),labels(word(),word("Confirm")),labels(word("Continuation")),[word()]):
        with pytest.raises(ValueError):result_button(words)


def test_one_click_per_result_button_and_round_and_confirmation(monkeypatch):
    o,r,m,logs=owner(monkeypatch);handler=ResultButtons(lambda _:labels(word()))
    assert handler.poll(o)["reason"]=="result_button_submitted" and len(m.clicks)==1
    assert handler.poll(o) is None and len(m.clicks)==1
    handler.ocr=lambda _:labels(word("Confirm"))
    assert handler.poll(o)["button"]=="confirm" and len(m.clicks)==2
    r["state"]["status"]="tracking"
    assert handler.poll(o) is None and logs[-1][0]=="result_button_confirmed"


def test_result_controls_never_click_during_play_or_pending_input(monkeypatch):
    o,r,m,_=owner(monkeypatch);handler=ResultButtons(lambda _:labels(word()))
    r["state"]["status"]="tracking";assert handler.poll(o) is None
    r["state"]["status"]="round_ended";o.controller.snapshot=lambda:{"status":"awaiting_confirmation"}
    assert handler.poll(o) is None and not m.clicks


def test_moving_button_and_changed_board_do_not_click(monkeypatch):
    o,r,m,_=owner(monkeypatch);words=iter([labels(word()),labels(word(x=940))])
    assert ResultButtons(lambda _:next(words)).poll(o) is None and not m.clicks
    def changed(_):
        r["state"]["step"]+=1
        return labels(word())
    assert ResultButtons(changed).poll(o) is None and not m.clicks


def test_result_controls_require_verified_ai_when_enabled(monkeypatch):
    o,r,m,_=owner(monkeypatch);o.require_ai=True
    assert ResultButtons(lambda _:labels(word())).poll(o) is None and not m.clicks


def test_result_screen_recording_continues_after_network_state_stops(monkeypatch):
    from tests.mahjong_soul.test_auto import setup
    f,r,_,_,_=setup(monkeypatch)
    r["state"]["status"]="round_ended";r["state"]["operations"]=None
    f.reader=SimpleNamespace(snapshot=lambda:r);f.journal=object()
    captures=[];now=[1]
    f.clock=lambda:now[0]
    def frame(*args):
        captures.append(args);f.last_recorded_frame=now[0]
    f._frame=frame
    f._passive_frame("observe");now[0]=4;f._passive_frame("observe")
    assert len(captures)==2
