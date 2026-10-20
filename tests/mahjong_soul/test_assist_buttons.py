import base64,json,zlib
from pathlib import Path
from games.mahjong_soul.live.runtime.assist_buttons import AssistButtons
from tests.mahjong_soul.test_result_buttons import owner


def panel():
    data=json.loads((Path(__file__).parent/"fixtures/assist_panel.json").read_text())
    x,y,w,h=data["crop"];crop=zlib.decompress(base64.b64decode(data["rgb_zlib"]));rgb=bytearray(1920*1080*3)
    for row in range(h):rgb[((y+row)*1920+x)*3:((y+row)*1920+x+w)*3]=crop[row*w*3:(row+1)*w*3]
    return rgb


def test_real_panel_states_and_unknown_panel(monkeypatch):
    rgb=panel();monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons()
    assert handler.read(b"frame")=={"arrange":True,"auto_win":False,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    rgb[:]=bytes(len(rgb))
    assert handler.read(b"frame") is None


def test_toggle_is_confirmed_without_second_click(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired)["reason"]=="assist_submitted" and len(m.clicks)==1
    now[0]=2
    assert handler.poll(o,desired)["reason"]=="awaiting_assist_confirmation" and len(m.clicks)==1
    for y in range(539,546):
        for x in range(57,64):rgb[(y*1920+x)*3:(y*1920+x)*3+3]=bytes(handler.profile["on"])
    now[0]=3
    assert handler.poll(o,desired) is None and len(m.clicks)==1
    assert logs[-1][0]=="assist_confirmed"


def test_toggle_rechecks_board_and_never_retries_unknown_delivery(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    o.sleep=lambda _:r["state"].update(step=r["state"]["step"]+1)
    assert handler.poll(o,desired) is None and not m.clicks
    o.sleep=lambda _:None;now[0]=2
    assert handler.poll(o,desired)["reason"]=="assist_submitted"
    now[0]=6
    assert handler.poll(o,desired)["kind"]=="blocked" and len(m.clicks)==1 and o.halted
