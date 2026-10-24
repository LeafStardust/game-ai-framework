from copy import deepcopy
import pytest
from agents.mahjong_soul.yakuman import yakuman_targets
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from games.mahjong_soul.live.runtime.lobby import detect_lobby
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from games.mahjong_soul.live.runtime.decision import decision_request
from tests.mahjong_soul.test_sanma_east_speed import sanma
from tests.mahjong_soul.test_attack_v2 import choose
from tests.mahjong_soul.test_efficiency import tiles


def south(hand):
    r=sanma(hand)
    r["state"]["lobby"]=detect_lobby({"seat_list":[0,1,2],"game_config":{"mode":{"mode":12}}})
    return r


def test_south_routes_during_east_round_and_preserves_report():
    r=south("19m123p456p789s112z");before=deepcopy(r)
    action,a=choose(r)
    assert a["playbook"]=="Three-Player South Attack" and a["playbook_version"]=="0.4"
    assert a["lobby"]["match_length"]=="south" and r["state"]["round"]["chang"]==0
    assert action in decision_request(r)["actions"]
    assert all(t["tile"] not in {str(i)+"m" for i in range(2,9)} for t in a["improving_tiles"])
    assert r==before


def test_south_settings_independent_from_east_yonma_and_future_factories():
    registry=default_mahjong_playbooks();book=registry.get(3,"atk","south")
    east=deepcopy(registry.get(3,"atk","east").strategy)
    four=deepcopy(registry.get(4,"atk","south").strategy)
    assert book.style=="atk" and book.match_length=="south"
    assert book.strategy["defense"]["always_push"]
    assert not book.strategy["discard_value"].get("speed_first")
    assert book.strategy["calls"]["minimum_han"]==3
    assert book.strategy["riichi"]["max_threats"]==2
    book.strategy["calls"]["minimum_han"]=99
    assert registry.get(3,"atk","east").strategy==east
    assert registry.get(4,"atk","south").strategy==four
    assert default_mahjong_playbooks().get(3,"atk","south").strategy["calls"]["minimum_han"]==3


def test_two_riichi_threats_do_not_trigger_folding():
    r=south("123p456p789s11z99p2z")
    action,_=choose(r)
    r["state"]["riichi"][1:]=["accepted","accepted"]
    threatened,a=choose(r)
    assert threatened==action and a["mode"]=="attack_push"


def test_south_north_extraction_keeps_essential_north_pair():
    for hand,extract in [("123p456p789s111z24z",True),("123p456p789s44z123z",False)]:
        r=south(hand);r["state"]["operations"]["operation_list"].append({"type":11,"combination":[]})
        action,_=choose(r)
        assert (action["kind"]=="extract_north")==extract


def test_sanma_rejects_chi_offer():
    r=south("123p456p789s111z24z")
    r["state"]["operations"]={"seat":0,"operation_list":[{"type":2,"combination":["2p|3p"]}]}
    with pytest.raises(ValueError):decision_request(r)


@pytest.mark.parametrize("opening,current,wall,qualifies",[
    ("19m19p19s1234z234p",None,40,True),
    ("19m19p19s123z2345p",None,40,False),
    ("123456p234s567s1z","19m19p19s1234z234p",40,True),
    ("123456p234s567s1z","19m19p19s1234z234p",8,False),
])
def test_south_yakuman_ten_tile_and_late_feasibility_gate(opening,current,wall,qualifies):
    r=south(current or opening);r["state"].update(opening_hand=tiles(opening),left_tile_count=wall)
    b=observation_from_snapshot(r)["board"]
    targets=yakuman_targets(b,b["self"]["hand"])
    assert any(t["target_route"]=="yakuman_kokushi" for t in targets)==qualifies
    if qualifies:
        t=next(t for t in targets if t["target_route"]=="yakuman_kokushi")
        assert t["qualification"]==("current" if current else "opening")


def test_south_skips_cheap_pon_but_calls_three_han_value_route():
    r=south("55z123p456p78s22p9m");s=r["state"]
    s["turn"]=1;s["discards"][1]=[{"tile":"5z","called":False}]
    s["visible_tile_counts"]["5z"]=3
    s["operations"]={"seat":0,"operation_list":[{"type":3,"combination":["5z|5z"]}]}
    r["last_event"]={"name":"ActionDiscardTile","step":s["step"]}
    assert choose(r)[0]["kind"]=="skip"
    s["doras"]=["7z"]
    action,a=choose(r)
    assert action["kind"]=="pon" and a["projected_han"]>=3


def test_south_kokushi_narrow_wait_stays_dama():
    from tests.mahjong_soul.test_live_v07_issues import fixture
    r=fixture()["kokushi_report"]
    r["state"]["lobby"]=south("123p456p789s111z24z")["state"]["lobby"]
    action,a=choose(r)
    assert action=={"kind":"discard","tile":"6s"}
    assert a["playbook"]=="Three-Player South Attack"
