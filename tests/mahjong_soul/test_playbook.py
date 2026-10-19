from copy import deepcopy
import pytest
from games.mahjong_soul.playbook.model import MahjongPlaybookRegistry,default_mahjong_playbooks
from games.mahjong_soul.playbook.features import dora_kind,value_honors,discard_features,safe_against
from agents.mahjong_soul.playbook_policy import PlaybookPolicy
from agents.mahjong_soul.evaluate import decide
from games.mahjong_soul.live.runtime.decision import decision_request
from tests.mahjong_soul.test_efficiency import request
from tests.mahjong_soul.test_win_input import offer as win_offer


def test_playbooks_select_by_player_count_and_thresholds_are_isolated():
    registry = default_mahjong_playbooks()
    for count in (3,4):
        book = registry.get(count)
        assert book.player_count == count and book.version == "0.1"
        settings = book.thresholds_for("d2"); settings["fold_from_shanten"] = 99
        assert book.thresholds_for("D2")["fold_from_shanten"] == 2
    with pytest.raises(ValueError): registry.register(registry.get(4))
    with pytest.raises(LookupError): registry.get(2)
    with pytest.raises(ValueError): registry.get(4).thresholds_for("D99")


@pytest.mark.parametrize("indicator,players,dora", [("9m",4,"1m"),("4z",4,"1z"),
 ("5z",4,"6z"),("6z",4,"7z"),("7z",4,"5z"),("0p",4,"6p"),
 ("1m",3,"9m"),("9m",3,"1m")])
def test_dora_indicator_cycles(indicator,players,dora):
    assert dora_kind(indicator,players) == dora


def test_value_winds_use_dealer_relative_seat_and_double_wind():
    q,_ = request("12m",4); board = q["observation"]["board"]
    board["round"] = {"chang":0,"ju":0}
    assert value_honors(board)["1z"] == 2
    board["self_seat"] = 2; board["round"] = {"chang":1,"ju":1}
    assert value_honors(board)["2z"] == 2


def test_genbutsu_normalizes_red_fives_and_is_opponent_specific():
    threats = [{"seat":1,"discards":[{"tile":"0p","called":True}]},
               {"seat":2,"discards":[{"tile":"1m","called":False}]}]
    assert safe_against("5p",threats) == [1]
    assert safe_against("0p",threats) == [1]
    assert safe_against("2m",threats) == []


def test_dora_value_breaks_efficiency_tie_without_changing_legal_actions():
    q,report = request("12m",4,drawn="2m")
    report["state"]["round"] = {"chang":0,"ju":0}
    report["state"]["doras"] = ["1m"]
    policy = PlaybookPolicy(); result = decide(policy,report,lambda:report)
    assert result["action"] == {"kind":"discard","tile":"1m"}  # Keep dora 2m.
    assert policy.last_analysis["value_loss"] == 0
    assert policy.last_analysis["playbook"] == "Four-Player Balanced"


def test_completed_yakuhai_and_pair_breaking_are_value_evidence():
    q,_ = request("55z",4); board = q["observation"]["board"]
    assert discard_features(board,"5z")["yakuhai_pair_loss"] == 1
    board["self"]["hand"] = ["5z"]*3
    feature = discard_features(board,"5z")
    assert feature["yakuhai_triplet_loss"] == 1 and not feature["yakuhai_triplets"]


def controlled_options(monkeypatch, report, *, distance=3):
    import agents.mahjong_soul.playbook_policy as module
    # Deliberately choose different distances to exercise the fold/efficiency boundary.
    options = [{"action":{"kind":"discard","tile":"1m"},"shanten":distance,"ukeire":20,"improving_tiles":[]},
               {"action":{"kind":"discard","tile":"2m"},"shanten":distance+1,"ukeire":1,"improving_tiles":[]}]
    monkeypatch.setattr(module,"rank_discards",lambda request:deepcopy(options))
    report["state"]["riichi"][1] = "accepted"
    report["state"]["discards"][1] = [{"tile":"2m","called":False}]
    report["state"]["round"] = {"chang":0,"ju":0}


def test_far_hand_folds_to_known_safe_tile_but_near_hand_retains_efficiency(tmp_path,monkeypatch):
    q,report = request("12m",4)
    controlled_options(monkeypatch,report)
    policy = PlaybookPolicy()
    assert decide(policy,report,lambda:report)["action"]["tile"] == "2m"
    assert policy.last_analysis["mode"] == "fold"
    assert policy.last_analysis["safe_against_riichi_seats"] == [1]
    controlled_options(monkeypatch,report,distance=1)
    assert decide(policy,report,lambda:report)["action"]["tile"] == "1m"
    assert policy.last_analysis["mode"] == "efficiency"


def test_all_riichi_opponents_are_considered_and_no_evidence_means_no_claimed_safety(monkeypatch):
    q,report = request("12m",4)
    controlled_options(monkeypatch,report)
    report["state"]["riichi"][2] = "accepted"
    report["state"]["discards"][2] = [{"tile":"2m","called":False}]
    policy=PlaybookPolicy(); decide(policy,report,lambda:report)
    assert policy.last_analysis["safe_against_riichi_seats"] == [1,2]
    report["state"]["discards"][1] = []
    report["state"]["discards"][2] = []
    assert decide(policy,report,lambda:report)["action"]["tile"] == "1m"
    assert policy.last_analysis["mode"] == "efficiency"


def test_playbook_riichi_threat_rule_and_win_priority():
    q,report = request("123m123p123s11z22z7z")
    report["state"]["round"] = {"chang":0,"ju":0}
    report["state"]["operations"]["operation_list"].append({"type":7,"combination":["7z"]})
    policy=PlaybookPolicy()
    assert decide(policy,report,lambda:report)["action"]["kind"] == "riichi"
    report["state"]["riichi"][1] = "declared"
    assert decide(policy,report,lambda:report)["action"]["kind"] == "discard"
    win,_=win_offer()
    assert decide(policy,win,lambda:win)["action"]["kind"] == "tsumo"


def test_custom_playbook_thresholds_change_shared_policy_without_replacing_rules(monkeypatch):
    from dataclasses import replace
    q,report = request("12m",4)
    controlled_options(monkeypatch,report)
    book = default_mahjong_playbooks().get(4)
    strategy = deepcopy(book.strategy); strategy["defense"]["fold_from_shanten"] = 4
    registry = MahjongPlaybookRegistry(); registry.register(replace(book,name="manual-test-custom",strategy=strategy))
    policy = PlaybookPolicy(registry)
    assert decide(policy,report,lambda:report)["action"]["tile"] == "1m"
    assert policy.last_analysis["playbook"] == "manual-test-custom"
    assert default_mahjong_playbooks().get(4).thresholds_for("D2")["fold_from_shanten"] == 2
