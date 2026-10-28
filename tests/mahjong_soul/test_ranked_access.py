from types import SimpleNamespace
import pytest
from games.mahjong_soul.live.runtime.lobby import detect_lobby
from games.mahjong_soul.live.runtime.game_access import input_game_verified
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from tests.mahjong_soul.test_auto import setup


def auth(count=4,mode=2):
    return {"seat_list":list(range(100,100+count)),"game_config":{"category":2,
            "mode":{"mode":mode,"ai":False,"detail_rule":{"shiduan":1}},"meta":{"mode_id":42}}}


def verified(monkeypatch,data=None):
    f,r,p,e,m=setup(monkeypatch);data=auth() if data is None else data
    r["state"]["lobby"]=detect_lobby(data)
    f.require_ai=True;f.allow_ranked=True
    decoded={"method":".lq.FastTest.authGame","kind":"response","data":data,"events":[]}
    f.reader=SimpleNamespace(snapshot=lambda:r,consume=lambda row:{"liqi":decoded})
    f._consume({"connection":r["game_connection"],"direction":"server"})
    e["board_token"]=board_token(r)
    return f,r,p,e,m


@pytest.mark.parametrize("count,mode,name",[(3,11,"Three-Player East Speed"),(3,12,"Three-Player South Attack"),
                                          (4,1,"Four-Player East Speed"),(4,2,"Four-Player South Attack")])
def test_ranked_auth_uses_existing_format_playbook(monkeypatch,count,mode,name):
    f,r,p,e,m=verified(monkeypatch,auth(count,mode))
    assert input_game_verified(f,r) and not f.ai_games
    obs=observation_from_snapshot(r);obs["board"]["player_count"]=count
    assert default_mahjong_playbooks().for_observation(obs,"atk").name==name


def test_ranked_native_input_still_requires_captured_auth_and_same_generation(monkeypatch):
    f,r,p,e,m=verified(monkeypatch)
    plan,current=f._plan(e);f.controller.submit(plan,current,enabled=True,now=1)
    assert len(m.clicks)==1
    r["game_generation"]+=1
    assert not input_game_verified(f,r)


@pytest.mark.parametrize("change",["friendly","contest","unknown_mode","special_rule","no_mode_id","ai","error"])
def test_unknown_or_nonranked_auth_does_not_authorize_ranked_input(monkeypatch,change):
    data=auth();config=data["game_config"]
    if change=="friendly":config["category"]=1;config["meta"]={"room_id":42}
    if change=="contest":config["meta"]["contest_uid"]=10
    if change=="unknown_mode":config["mode"]["mode"]=99
    if change=="special_rule":config["mode"]["detail_rule"]["guyi_mode"]=1
    if change=="no_mode_id":config["meta"]={}
    if change=="ai":config["mode"]["ai"]=True
    if change=="error":data["error"]={"code":100}
    f,r,p,e,m=verified(monkeypatch,data)
    assert not input_game_verified(f,r)
    with pytest.raises(ValueError,match="authenticated"):f._plan(e)
    assert not m.clicks


def test_state_flag_without_authentication_cannot_enable_ranked(monkeypatch):
    f,r,p,e,m=setup(monkeypatch);f.require_ai=True;f.allow_ranked=True
    r["state"]["lobby"]=detect_lobby(auth())
    assert not input_game_verified(f,r)


def test_ranked_result_button_uses_same_verified_path(monkeypatch):
    from tests.mahjong_soul.test_result_buttons import owner,labels,word
    from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
    o,r,m,_=owner(monkeypatch);o.require_ai=True;o.allow_ranked=True
    r["state"]["lobby"]=detect_lobby(auth())
    o.ranked_games={(r["game_connection"],r.get("game_generation",0))}
    assert ResultButtons(lambda _:labels(word())).poll(o)["reason"]=="result_button_submitted"
    assert len(m.clicks)==1


def test_ranked_switches_use_same_verified_path(monkeypatch):
    from tests.mahjong_soul.test_result_buttons import owner
    from tests.mahjong_soul.test_assist_buttons import panel
    from games.mahjong_soul.live.runtime.assist_buttons import AssistButtons
    o,r,m,_=owner(monkeypatch);o.require_ai=True;o.allow_ranked=True;o.clock=lambda:1
    r["state"].update(status="tracking",player_count=3,lobby=detect_lobby(auth(3,12)))
    o.ranked_games={(r["game_connection"],r.get("game_generation",0))}
    rgb=panel();monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    desired={"auto_win":True,"auto_kita":True,"skip_calls":False,"auto_discard":False}
    assert AssistButtons().poll(o,desired)["reason"]=="assist_submitted"
    assert len(m.clicks)==1


def test_ranked_match_cannot_enter_custom_room_restart(monkeypatch):
    from tests.mahjong_soul.test_room_restart import setup as room_setup
    from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
    o,r,m,logs,words,rgb=room_setup(monkeypatch)
    o.require_ai=True;o.allow_ranked=True;o.ai_games.clear()
    r["state"]["lobby"]=detect_lobby(auth(3,12))
    o.ranked_games={(r["game_connection"],r.get("game_generation",0))}
    assert ResultButtons(lambda _:words).poll(o) is None and not m.clicks


def test_failed_reauthentication_revokes_ranked_access(monkeypatch):
    data=auth();f,r,p,e,m=verified(monkeypatch,data)
    assert input_game_verified(f,r)
    data["error"]={"code":100}
    f._consume({"connection":r["game_connection"],"direction":"server"})
    assert not input_game_verified(f,r)


def test_client_direction_cannot_grant_ranked_authentication(monkeypatch):
    f,r,p,e,m=setup(monkeypatch);f.require_ai=True;f.allow_ranked=True
    data=auth();r["state"]["lobby"]=detect_lobby(data)
    decoded={"method":".lq.FastTest.authGame","kind":"response","data":data,"events":[]}
    f.reader=SimpleNamespace(snapshot=lambda:r,consume=lambda row:{"liqi":decoded})
    f._consume({"connection":r["game_connection"],"direction":"client"})
    assert not input_game_verified(f,r)
