import base64
from copy import deepcopy
import json
from pathlib import Path
import zlib
import pytest
from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
from games.mahjong_soul.live.runtime.room_restart import room_start,unchanged_room
from tests.mahjong_soul.test_result_buttons import owner


def fixture():
    data=json.loads((Path(__file__).parent/"fixtures/custom_room_start.json").read_text())
    rgb=bytearray(1920*1080*3)
    for patch in data["patches"]:
        x,y,w,h=patch["bounds"];raw=zlib.decompress(base64.b64decode(patch["rgb_zlib"]))
        for j in range(h):rgb[((y+j)*1920+x)*3:((y+j)*1920+x+w)*3]=raw[j*w*3:(j+1)*w*3]
    return data["words"],rgb


def setup(monkeypatch):
    o,r,m,logs=owner(monkeypatch);words,rgb=fixture()
    r["state"]["status"]="match_ended"
    r["state"]["lobby"]={"identified":True,"ai":True,"player_count":3,"room_id":72808,"match_length":"south"}
    o.ai_games.add((r.get("game_connection"),r.get("game_generation",0)))
    monkeypatch.setattr("games.mahjong_soul.live.runtime.room_restart.decode_frame",lambda _:rgb)
    return o,r,m,logs,words,rgb


def test_recorded_room_start_once_then_confirm_on_new_game(monkeypatch):
    o,r,m,logs,words,rgb=setup(monkeypatch);handler=ResultButtons(lambda _:words)
    assert room_start(words,r["state"]["lobby"])==(1142,999)
    assert handler.poll(o)["reason"]=="room_start_submitted"
    assert handler.poll(o) is None and len(m.clicks)==1
    assert (round(m.clicks[0][0]*1919),round(m.clicks[0][1]*1079))==(1142,999)
    r["state"]["status"]="tracking"
    assert handler.poll(o) is None
    assert logs[-1][0]=="result_button_confirmed" and logs[-1][1]["button"]=="start"


@pytest.mark.parametrize("field,value",[("room_id",99999),("ai",False),("player_count",4),("identified",False),("match_length","east"),("unsupported_rules",["special"])])
def test_changed_or_unverified_room_does_not_restart(monkeypatch,field,value):
    o,r,m,logs,words,rgb=setup(monkeypatch);r["state"]["lobby"][field]=value
    assert ResultButtons(lambda _:words).poll(o) is None and not m.clicks


def test_requires_completed_match_verified_ai_and_current_roster(monkeypatch):
    o,r,m,logs,words,rgb=setup(monkeypatch)
    r["state"]["status"]="round_ended"
    assert ResultButtons(lambda _:words).poll(o) is None
    r["state"]["status"]="match_ended";o.ai_games.clear()
    assert ResultButtons(lambda _:words).poll(o) is None
    o.ai_games.add((r.get("game_connection"),r.get("game_generation",0)))
    words=[w for w in words if w["text"]!="Al"]
    assert ResultButtons(lambda _:words).poll(o) is None and not m.clicks


def test_changed_roster_pixels_disabled_button_or_board_do_not_click(monkeypatch):
    o,r,m,logs,words,rgb=setup(monkeypatch)
    changed=bytearray(rgb)
    for y in range(850,880):changed[(y*1920+550)*3:(y*1920+700)*3]=bytes(150*3)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.room_restart.decode_frame",lambda p:rgb if p==b"frame" else changed)
    frames=iter([b"frame",b"changed"]);o._frame=lambda *args:next(frames)
    assert ResultButtons(lambda _:words).poll(o) is None and not m.clicks
    o._frame=lambda *args:b"changed"
    monkeypatch.setattr("games.mahjong_soul.live.runtime.room_restart.decode_frame",lambda _:bytes(1920*1080*3))
    assert ResultButtons(lambda _:words).poll(o) is None and not m.clicks
    monkeypatch.setattr("games.mahjong_soul.live.runtime.room_restart.decode_frame",lambda _:rgb)
    def move(_):r["state"]["step"]+=1
    o.sleep=move
    assert ResultButtons(lambda _:words).poll(o) is None and not m.clicks


def test_start_input_failure_is_not_replayed(monkeypatch):
    o,r,m,logs,words,rgb=setup(monkeypatch);handler=ResultButtons(lambda _:words)
    def fail(*args):raise OSError("failed delivery")
    o.controller.backend.click=fail
    with pytest.raises(OSError):handler.poll(o)
    assert o.halted and handler.poll(o) is None
