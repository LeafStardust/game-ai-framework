import pytest
from agents.mahjong_soul.north_choice import north_choice
from games.mahjong_soul.live.runtime.decision import decision_request
from tests.mahjong_soul.test_sanma_south_attack import south


@pytest.mark.parametrize("hand,extract,reason",[
    ("123p456p789s111z24z",True,"bank_kita_without_shape_loss"),
    ("123p456p789s44z123z",False,"retain_useful_north"),
    ("123p456p789s444z12z",False,"retain_useful_north"),
    ("19m19p19s1234z234p",False,"qualified_north_yakuman"),
])
def test_north_shape_and_qualified_yakuman(hand,extract,reason):
    result=north_choice(decision_request(south(hand)))
    assert result["extract"] is extract
    assert result["reason"]==reason


def test_equal_shanten_pair_must_not_lose_live_improvements(monkeypatch):
    # Isolate the tie-break: Kita's bonus cannot excuse shrinking a useful pair's ukeire.
    monkeypatch.setattr("agents.mahjong_soul.north_choice.yakuman_targets",lambda *a:[])
    monkeypatch.setattr("agents.mahjong_soul.north_choice.rank_discards",lambda *a:[
        {"action":{"tile":"1p"},"shanten":2,"ukeire":24},
        {"action":{"tile":"4z"},"shanten":2,"ukeire":16}])
    req=decision_request(south("123p456p789s44z123z"))
    assert not north_choice(req)["extract"]
    monkeypatch.setattr("agents.mahjong_soul.north_choice.rank_discards",lambda *a:[
        {"action":{"tile":"1p"},"shanten":2,"ukeire":24},
        {"action":{"tile":"4z"},"shanten":2,"ukeire":24}])
    assert north_choice(req)["extract"]
