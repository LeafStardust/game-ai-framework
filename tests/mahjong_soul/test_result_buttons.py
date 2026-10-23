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
    o,r,m,logs=owner(monkeypatch)
    frames=iter([b"first",b"moved"]);o._frame=lambda *args:next(frames)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",
                        lambda frame:bytes([0 if frame==b"first" else 255])*(1920*1080*3))
    assert ResultButtons(lambda _:labels(word())).poll(o) is None and not m.clicks
    assert logs[-1][1]["reason"]=="label_pixels_changed"
    o,r,m,logs=owner(monkeypatch)
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


def test_idle_result_state_uses_source_checked_snapshot_not_gameplay_freshness(monkeypatch):
    o,r,m,_=owner(monkeypatch)
    def stale():raise ValueError("Gameplay capture is stale")
    o._current=stale;o._result_snapshot=lambda:deepcopy(r)
    assert ResultButtons(lambda _:labels(word())).poll(o)["reason"]=="result_button_submitted"
    assert len(m.clicks)==1


def test_real_score_and_final_result_confirm_screens(monkeypatch):
    import base64,json,zlib
    from pathlib import Path
    data=json.loads((Path(__file__).parent/"fixtures/result_confirm.json").read_text(encoding="utf-8"))
    images={};x,y,w,h=data["crop"]
    for i,frame in enumerate(data["frames"]):
        rgb=bytearray(1920*1080*3);crop=zlib.decompress(base64.b64decode(frame["rgb_zlib"]))
        for row in range(h):rgb[((y+row)*1920+x)*3:((y+row)*1920+x+w)*3]=crop[row*w*3:(row+1)*w*3]
        images[str(i).encode()]=rgb
    for first,second,expected in ((0,1,(1779,1002)),(2,3,(1760,958))):
        o,_,mouse,_=owner(monkeypatch);report=data["frames"][first]["report"]
        o._result_snapshot=lambda:report
        frames=iter([str(first).encode(),str(second).encode()]);o._frame=lambda *args:next(frames)
        monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",lambda key:images[key])
        handler=ResultButtons(lambda key:data["frames"][int(key)]["words"])
        assert handler.poll(o)["button"]=="confirm"
        assert len(mouse.clicks)==1
        click=mouse.clicks[0]
        assert (round(click[0]*1919),round(click[1]*1079))==expected


def test_ocr_score_context_must_match_at_least_two_captured_scores():
    words=[word("52000",y=300),word("44000",y=500),word("Confirm")]
    assert result_button(words,[52000,9000,44000])[0]=="confirm"
    with pytest.raises(ValueError):result_button(words,[35000,35000,35000])


def test_result_click_uses_one_ocr_and_rechecks_state_after_fresh_frame(monkeypatch):
    o,r,m,logs=owner(monkeypatch);calls=[]
    def ocr(frame):
        calls.append(frame)
        return labels(word())
    assert ResultButtons(ocr).poll(o)["reason"]=="result_button_submitted"
    assert len(calls)==1
    o,r,m,logs=owner(monkeypatch)
    def frame(*args):
        if args[-1]=="before_result_input":r["state"]["step"]+=1
        return b"frame"
    o._frame=frame
    assert ResultButtons(ocr).poll(o) is None and not m.clicks
    assert logs[-1][1]["reason"]=="state_changed_before_click"


def test_win_and_score_confirm_at_same_position_are_separate_stages(monkeypatch):
    o,r,m,_=owner(monkeypatch);words=[labels(word("Confirm"))]
    handler=ResultButtons(lambda _:words[0]);o.clock=lambda:1
    words[0]=[word("Han",y=250),word("Confirm")]
    assert handler.poll(o)["button"]=="confirm"
    words[0]=[word("Counter",y=250),word("0Repeat",y=200),word("Confirm")]
    assert handler.poll(o)["button"]=="confirm"
    assert len(m.clicks)==2


def test_same_result_has_one_bounded_verified_retry(monkeypatch):
    o,r,m,logs=owner(monkeypatch);now=[1];o.clock=lambda:now[0]
    handler=ResultButtons(lambda _:labels(word()))
    assert handler.poll(o)["button"]=="continue"
    assert handler.poll(o) is None
    now[0]=3
    assert handler.poll(o)["button"]=="continue"
    now[0]=6
    assert handler.poll(o) is None and len(m.clicks)==2


def test_reviewed_templates_require_context_and_avoid_ocr(monkeypatch):
    import base64,json,zlib
    from pathlib import Path
    handler=ResultButtons(lambda _:pytest.fail("Reviewed layout should avoid OCR"))
    rows=json.loads((Path(__file__).parent/"fixtures/result_fast.json").read_text())
    for row in rows:
        rgb=bytearray(1920*1080*3)
        for patch in row["patches"]:
            x,y,w,h=patch["bounds"];raw=zlib.decompress(base64.b64decode(patch["rgb_zlib"]))
            for j in range(h):rgb[((y+j)*1920+x)*3:((y+j)*1920+x+w)*3]=raw[j*w*3:(j+1)*w*3]
        monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",lambda _:rgb)
        x,y=row["pixel"]
        assert handler.visual_button(b"frame")==("confirm",x,y,row["stage"])
        o,r,m,_=owner(monkeypatch)
        # owner configures a decoder for other tests; restore this fixture.
        monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",lambda _:rgb)
        assert handler.poll(o)["button"]=="confirm" and len(m.clicks)==1
        rgb[:]=bytes(len(rgb))
        assert handler.visual_button(b"frame") is None


def test_all_six_recorded_ocr_fallbacks_now_use_fast_path(monkeypatch):
    import base64,json,zlib
    from pathlib import Path
    rows=json.loads((Path(__file__).parent/"fixtures/result_context_variants.json").read_text())
    for row in rows:
        rgb=bytearray(1920*1080*3)
        for patch in row["patches"]:
            x,y,w,h=patch["bounds"];raw=zlib.decompress(base64.b64decode(patch["rgb_zlib"]))
            for j in range(h):rgb[((y+j)*1920+x)*3:((y+j)*1920+x+w)*3]=raw[j*w*3:(j+1)*w*3]
        monkeypatch.setattr("games.mahjong_soul.live.runtime.result_buttons.decode_frame",lambda _:rgb)
        handler=ResultButtons(lambda _:pytest.fail("Recorded result should not require OCR"))
        result=handler.visual_button(b"frame")
        if row["stage"] is None:
            assert result is None
        else:
            assert result[0]=="confirm" and result[3]==row["stage"]


def test_context_glyphs_allow_changed_background_but_require_same_letters():
    from games.mahjong_soul.live.runtime.result_buttons import heading_matches
    reference=bytearray(bytes([20,50,75])*216);actual=bytearray(bytes([35,70,95])*216)
    for i in range(25):
        reference[i*3:i*3+3]=bytes([230,180,120])
        actual[i*3:i*3+3]=bytes([230,180,120])
    assert heading_matches(bytes(actual),bytes(reference))
    actual[:]=bytes([35,70,95])*216
    assert not heading_matches(bytes(actual),bytes(reference))


def test_draw_context_is_distinct_from_han_and_hand_words():
    assert ResultButtons.ocr_stage([word("Exhaustive"),word("Draw"),word("Ready Hand")])=="exhaustive_draw"
    assert ResultButtons.ocr_stage([word("Ready Hand")])!="win_detail"


def test_async_ocr_pending_does_not_block_poll_or_run_input(monkeypatch):
    from concurrent.futures import Future
    o,r,m,_=owner(monkeypatch)
    handler=ResultButtons(lambda _:pytest.fail("Only the worker may call OCR"))
    tasks=[]
    class Worker:
        def submit(self,fn,png):
            future=Future();tasks.append((future,png));return future
    handler.worker=Worker()
    assert handler.poll(o) is None and len(tasks)==1 and not m.clicks
    assert handler.poll(o) is None and len(tasks)==1 and not m.clicks
    tasks[0][0].set_result(labels(word()))
    assert handler.poll(o)["button"]=="continue" and len(m.clicks)==1


def test_async_ocr_old_board_result_is_discarded(monkeypatch):
    from concurrent.futures import Future
    o,r,m,_=owner(monkeypatch);handler=ResultButtons(lambda _:[]);tasks=[]
    class Worker:
        def submit(self,fn,png):
            future=Future();tasks.append(future);return future
    handler.worker=Worker()
    assert handler.poll(o) is None
    r["state"]["step"]+=1;tasks[0].set_result(labels(word()))
    assert handler.poll(o) is None and len(tasks)==2 and not m.clicks
