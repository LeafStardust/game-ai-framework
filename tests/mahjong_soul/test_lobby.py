from copy import deepcopy
import pytest
from games.mahjong_soul.live.runtime.lobby import detect_lobby,unknown_lobby
from games.mahjong_soul.playbook.model import MahjongPlaybook,MahjongPlaybookRegistry,default_mahjong_playbooks,UnsupportedLobby
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from tests.mahjong_soul.test_attack_v2 import report


def auth(count=4,mode=2,detail=None):
    return {"seat_list":list(range(count)),"game_config":{"category":1,"mode":{"mode":mode,"ai":True,"detail_rule":detail or {"shiduan":1,"dora_count":3}},"meta":{"room_id":42}}}


@pytest.mark.parametrize("count,mode,length",[(4,1,"east"),(4,2,"south"),(3,11,"east"),(3,12,"south")])
def test_detects_format_from_auth_not_current_wind(count,mode,length):
    lobby=detect_lobby(auth(count,mode))
    assert lobby["identified"] and lobby["player_count"]==count and lobby["match_length"]==length


def observation(lobby):
    r=report("123m456p789s11z99p2z");r["state"]["lobby"]=lobby
    return observation_from_snapshot(r)


def test_south_atk_routes_only_to_registered_format():
    registry=default_mahjong_playbooks()
    assert registry.for_observation(observation(detect_lobby(auth())),"atk").name=="Four-Player South Attack"
    for data in (auth(4,99),{}):
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


@pytest.mark.parametrize("count,mode",[(3,11),(3,12),(4,1),(4,2)])
def test_show_hands_is_supported_for_ai_practice(count,mode):
    data=auth(count,mode,{"open_hand":True})
    lobby=detect_lobby(data)
    assert lobby["unsupported_rules"]==[]
    o=observation(lobby);o["board"]["player_count"]=count
    assert default_mahjong_playbooks().for_observation(o,"atk").player_count==count


@pytest.mark.parametrize("ai",[False,None])
def test_show_hands_requires_authenticated_ai_room(ai):
    data=auth(detail={"open_hand":True});data["game_config"]["mode"]["ai"]=ai
    assert detect_lobby(data)["unsupported_rules"]==["open_hand"]


def test_show_hands_does_not_allow_other_special_rules():
    assert detect_lobby(auth(detail={"open_hand":True,"guyi_mode":1}))["unsupported_rules"]==["guyi_mode"]


def test_opponent_revealed_hands_and_draws_do_not_change_policy_information():
    from games.mahjong_soul.live.runtime.state import GameState
    from tests.mahjong_soul.test_efficiency import tiles
    hidden=GameState(0,3);shown=GameState(0,3)
    opening={"tiles":tiles("123p456p789s1123z"),"scores":[35000]*3,"ju":1,"doras":["9s"]}
    for state,reveal in [(hidden,False),(shown,True)]:
        data=deepcopy(opening)
        data["opens"]=[{"seat":1,"tiles":tiles("111p222p333s4455z"),"count":[]} ] if reveal else []
        state.apply({"name":"ActionNewRound","step":1,"data":data})
        state.apply({"name":"ActionDealTile","step":2,"data":{"seat":1,"tile":"6z" if reveal else "","left_tile_count":53}})
    assert shown.snapshot()==hidden.snapshot()
    assert "6z" not in shown.visible_tiles()[0]
