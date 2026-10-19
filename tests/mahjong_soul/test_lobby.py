from copy import deepcopy
import pytest
from games.mahjong_soul.live.runtime.lobby import detect_lobby,unknown_lobby
from games.mahjong_soul.playbook.model import MahjongPlaybook,MahjongPlaybookRegistry,default_mahjong_playbooks,UnsupportedLobby
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from tests.mahjong_soul.test_attack_v2 import report


def auth(count=4,mode=2,detail=None):
    return {"seat_list":list(range(count)),"game_config":{"category":1,"mode":{"mode":mode,"ai":True,"detail_rule":detail or {"shiduan":1,"dora_count":3}},"meta":{"room_id":42}}}


@pytest.mark.parametrize("count,mode,length",[(4,1,"east"),(4,2,"south"),(3,1,"east"),(3,2,"south")])
def test_detects_format_from_auth_not_current_wind(count,mode,length):
    lobby=detect_lobby(auth(count,mode))
    assert lobby["identified"] and lobby["player_count"]==count and lobby["match_length"]==length


def observation(lobby):
    r=report("123m456p789s11z99p2z");r["state"]["lobby"]=lobby
    return observation_from_snapshot(r)


def test_south_atk_routes_only_to_registered_format():
    registry=default_mahjong_playbooks()
    assert registry.for_observation(observation(detect_lobby(auth())),"atk").name=="4 Player South Wind ATK"
    for data in (auth(3,2),auth(4,99),{}):
        o=observation(detect_lobby(data))
        if data.get("seat_list"):o["board"]["player_count"]=len(data["seat_list"])
        with pytest.raises(UnsupportedLobby):registry.for_observation(o,"atk")


def test_registry_can_select_future_east_book_without_changing_policy():
    registry=MahjongPlaybookRegistry()
    registry.register(MahjongPlaybook(4,"East ATK",style="atk",match_length="east"))
    assert registry.for_observation(observation(detect_lobby(auth(4,1))),"atk").name=="East ATK"


def test_special_rules_are_not_silently_scored_as_standard():
    lobby=detect_lobby(auth(detail={"guyi_mode":1}))
    assert lobby["unsupported_rules"]==["guyi_mode"]
    with pytest.raises(UnsupportedLobby,match="guyi_mode"):
        default_mahjong_playbooks().for_observation(observation(lobby),"atk")


def test_lobby_snapshot_is_independent_and_unknown_is_blocked():
    lobby=detect_lobby(auth());o=observation(lobby)
    o["board"]["lobby"]["rule_details"].clear()
    assert lobby["rule_details"]
    with pytest.raises(UnsupportedLobby,match="unknown"):
        default_mahjong_playbooks().for_observation(observation(unknown_lobby()),"atk")


def test_reader_preserves_connection_scoped_lobby_and_copies_snapshots():
    from games.mahjong_soul.live.runtime.reader import GameReader
    from games.mahjong_soul.live.runtime.state import GameState
    reader=GameReader(None);reader.connections["one"]=(None,GameState(0));reader.latest_game_connection="one"
    reader.game_lobbies["one"]=detect_lobby(auth())
    first=reader.snapshot();first["state"]["lobby"]["rule_details"].clear()
    assert reader.snapshot()["state"]["lobby"]["rule_details"]
    reader.connections["two"]=(None,GameState(0));reader.latest_game_connection="two"
    assert not reader.snapshot()["state"]["lobby"]["identified"]
