from collections import Counter
from copy import deepcopy
import re
import pytest

from agents.mahjong_soul.efficiency import counts34, shanten, rank_discards, EfficiencyPolicy
from agents.mahjong_soul.evaluate import decide
from games.mahjong_soul.live.runtime.decision import decision_request
from tests.mahjong_soul.test_input import inputs
from tests.mahjong_soul.test_win_input import offer as win_offer
from tests.mahjong_soul.test_calls import offer as pon_offer


def tiles(text):
    return [rank+suit for ranks,suit in re.findall(r"([0-9]+)([mpsz])",text) for rank in ranks]


def request(hand, fixed=0, *, drawn=None, visible=None, kan=False, players=4):
    report, _ = inputs(); state = report["state"]
    state["hand"] = tiles(hand); state["drawn_tile"] = drawn
    melds = [{"type":3 if kan and i == 0 else 1,
              "tiles":[str(i+3)+"p"]*(4 if kan and i == 0 else 3)} for i in range(fixed)]
    state["melds"][0] = melds
    all_tiles = state["hand"]+[t for m in melds for t in m["tiles"]]
    state["visible_tile_counts"] = dict(Counter("5"+t[1:] if t[0] == "0" else t for t in all_tiles))
    if visible: state["visible_tile_counts"].update(visible)
    state["player_count"] = players
    return decision_request(report), report


@pytest.mark.parametrize("hand,fixed,expected", [
    ("123m123p123s111z22z",0,-1), ("123m123p123s111z2z",0,0),
    ("1122m3344p5566s7z",0,0), ("19m19p19s1234567z",0,0),
    ("119m19p19s1234567z",0,-1), ("123m456p7z",2,0),
    ("123m456p77z",2,-1), ("5p",4,0), ("55p",4,-1)])
def test_known_regular_special_and_open_hand_distances(hand, fixed, expected):
    assert shanten(counts34(tiles(hand)),fixed) == expected


def test_discards_isolated_tile_to_keep_tenpai_instead_of_baseline_draw():
    value, report = request("123m123p123s11z22z7z",drawn="2z")
    original = deepcopy(value)
    ranked = rank_discards(value)
    assert ranked[0]["action"] == {"kind":"discard","tile":"7z"}
    assert ranked[0]["shanten"] == 0 and ranked[0]["ukeire"] == 4
    assert ranked[0]["improving_tiles"] == [{"tile":"1z","unseen":2},{"tile":"2z","unseen":2}]
    assert decide(EfficiencyPolicy(),report,lambda:report)["action"] == ranked[0]["action"]
    assert value == original


def test_visible_exhaustion_breaks_equal_shanten_tie():
    value, _ = request("12m",4,visible={"1m":4})
    ranked = rank_discards(value)
    assert [r["shanten"] for r in ranked] == [0,0]
    assert ranked[0]["action"]["tile"] == "1m"
    assert [r["ukeire"] for r in ranked] == [3,0]


def test_discarded_tile_stays_visible_and_red_five_is_preserved_on_tie():
    value, _ = request("05s",4,drawn="0s")
    ranked = rank_discards(value)
    assert ranked[0]["action"]["tile"] == "5s"
    assert all(r["ukeire"] == 2 for r in ranked)
    assert counts34(["0s","5s"])[22] == 2


def test_fixed_closed_kan_counts_as_one_meld_without_counting_four_tiles_as_concealed():
    value, _ = request("123m123s456p11z",1,kan=True)
    assert rank_discards(value)
    value["observation"]["board"]["players"][0]["melds"][0]["tiles"].pop()
    with pytest.raises(ValueError): rank_discards(value)


def test_only_offered_discards_are_ranked_and_wins_still_take_priority():
    value, report = request("123m123p123s11z22z7z")
    report["state"]["operations"]["operation_list"][0]["combination"] = ["7z"]
    assert all(r["action"]["tile"] != "7z" for r in rank_discards(decision_request(report)))
    win, _ = win_offer()
    assert decide(EfficiencyPolicy(),win,lambda:win)["action"]["kind"] == "tsumo"
    call, _ = pon_offer()
    assert decide(EfficiencyPolicy(),call,lambda:call)["action"]["kind"] == "skip"


def test_three_player_pool_excludes_removed_man_tiles():
    value, _ = request("12s11z9m",3,players=3)
    assert all(t["tile"] not in [str(i)+"m" for i in range(2,9)]
               for r in rank_discards(value) for t in r["improving_tiles"])


@pytest.mark.parametrize("bad", ["visibility","overfour","hand_count","missing_hand","missing_melds"])
def test_inconsistent_inputs_fail_instead_of_guessing(bad):
    value, _ = request("12m",4); board = value["observation"]["board"]
    if bad == "visibility": board["visibility_complete"] = False
    if bad == "overfour": board["visible_tile_counts"]["1m"] = 5
    if bad == "hand_count": board["self"]["hand"].append("1s")
    if bad == "missing_hand": board["visible_tile_counts"]["1m"] = 0
    if bad == "missing_melds": board["visible_tile_counts"]["3p"] = 0
    with pytest.raises(ValueError): rank_discards(value)


def test_riichi_uses_best_of_offered_tenpai_discards_and_validates():
    value, report = request("123m123p123s11z22z7z",drawn="2z")
    report["state"]["operations"]["operation_list"].append({"type":7,"combination":["7z"]})
    policy = EfficiencyPolicy()
    result = decide(policy,report,lambda:report)
    assert result["action"] == {"kind":"riichi","tile":"7z"}
    assert policy.last_analysis["shanten"] == 0
    assert policy.last_analysis["ukeire"] == 4


def test_riichi_does_not_select_unoffered_discard_and_win_takes_priority():
    value, report = request("12m",4,visible={"1m":4})
    # Artificial server restriction makes the lower-ukeire option the only Riichi choice.
    report["state"]["operations"]["operation_list"].append({"type":7,"combination":["2m"]})
    assert decide(EfficiencyPolicy(),report,lambda:report)["action"] == {"kind":"riichi","tile":"2m"}
    report["state"]["drawn_tile"] = "2m"
    report["state"]["operations"]["operation_list"].append({"type":8})
    assert decide(EfficiencyPolicy(),report,lambda:report)["action"]["kind"] == "tsumo"


def test_inconsistent_non_tenpai_riichi_is_rejected():
    value, report = request("123m123p123s11z22z7z")
    report["state"]["operations"]["operation_list"].append({"type":7,"combination":["1m"]})
    with pytest.raises(ValueError,match="tenpai"):
        decide(EfficiencyPolicy(),report,lambda:report)
