from copy import deepcopy
import pytest
from tests.mahjong_soul.test_attack_v2 import report,choose
from tests.mahjong_soul.test_efficiency import tiles
from games.mahjong_soul.live.runtime.lobby import detect_lobby
from games.mahjong_soul.live.runtime.decision import decision_request
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from agents.mahjong_soul.scoring import score_hand


def sanma(hand):
    r=report(hand);s=r["state"];s["player_count"]=3
    for key in ("discards","melds","norths","riichi","scores"):s[key]=s[key][:3]
    s["lobby"]=detect_lobby({"seat_list":[0,1,2],"game_config":{"mode":{"mode":11}}})
    return r


def test_sanma_east_routes_and_never_counts_removed_man_draws():
    r=sanma("19m123p456p789s112z");before=deepcopy(r)
    action,a=choose(r)
    assert a["playbook"]=="Three-Player East Speed"
    assert all(t["tile"] not in {str(i)+"m" for i in range(2,9)} for t in a["improving_tiles"])
    assert r==before


def test_sanma_has_stronger_speed_settings_without_mutating_yonma():
    registry=default_mahjong_playbooks();three=registry.get(3,"atk","east");four=registry.get(4,"atk","east")
    assert three.strategy["calls"]["max_shanten"]>four.strategy["calls"]["max_shanten"]
    assert three.strategy["riichi"]["minimum_ukeire"]<four.strategy["riichi"]["minimum_ukeire"]
    assert three.strategy["discard_value"]["riichi_speed_first"]
    assert "riichi_speed_first" not in four.strategy["discard_value"]


def test_offered_north_is_extracted_without_breaking_the_fast_hand():
    r=sanma("123p456p789s111z24z")
    r["state"]["operations"]["operation_list"].append({"type":11,"combination":[]})
    action,a=choose(r)
    assert action=={"kind":"extract_north","tile":"4z"} and a["mode"]=="north_extraction"


def test_north_pair_needed_for_tenpai_is_kept():
    r=sanma("123p456p789s44z123z")
    r["state"]["operations"]["operation_list"].append({"type":11,"combination":["4z"]})
    assert choose(r)[0]["kind"]!="extract_north"


def test_north_offer_is_rejected_in_four_player_room():
    r=report("123p456p789s111z24z")
    r["state"]["operations"]["operation_list"].append({"type":11,"combination":[]})
    with pytest.raises(ValueError,match="North-extraction"):decision_request(r)


def test_north_bonus_never_supplies_a_yaku():
    value=score_hand(tiles("123p456p789s111m5z"),"5z",player_count=3,norths=4)
    assert not value["legal"]


def test_north_bonus_and_indicator_bonus_are_scored_after_real_yaku():
    hand=tiles("123p456p789s777z5p")
    plain=score_hand(hand,"5p",player_count=3)
    bonus=score_hand(hand,"5p",player_count=3,norths=1,doras=["3z"])
    assert plain["legal"] and bonus["han"]==plain["han"]+2
    assert bonus["bonus_han"]==2


def test_sanma_dora_man_cycle_and_removed_tiles():
    hand=tiles("999m123p456p789s5z")
    plain=score_hand(hand,"5z",riichi=True,player_count=3)
    bonus=score_hand(hand,"5z",riichi=True,player_count=3,doras=["1m"])
    assert bonus["han"]==plain["han"]+3
    assert not score_hand(tiles("123m123p456p789s5z"),"5z",riichi=True,player_count=3)["legal"]


@pytest.mark.parametrize("seat",[0,1])
def test_tsumo_loss_uses_two_opponents_and_bisection_is_explicit(seat):
    args=dict(player_count=3,riichi=True,tsumo=True,seat_wind=seat)
    hand=tiles("123p456p789s777z5p")
    loss=score_hand(hand,"5p",**args);split=score_hand(hand,"5p",tsumo_loss=False,**args)
    assert loss["points"]==loss["payments"]["main"]+loss["payments"]["additional"]
    assert split["points"]>loss["points"]
    assert loss["payments"]["total"]==loss["points"]
