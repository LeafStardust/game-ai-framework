import json
from copy import deepcopy
from pathlib import Path
from tests.mahjong_soul.test_attack_v2 import choose


def recorded(sequence):
    return json.loads((Path(__file__).parent/"fixtures/sanma_ready_calls.json").read_text())[str(sequence)]


def test_cheap_fast_pon_is_not_blocked_by_four_player_value_floor():
    report=recorded(577);before=deepcopy(report)
    action,analysis=choose(report)
    assert action["kind"]=="pon" and action["called_tile"]=="6z"
    assert analysis["shanten"]==0 and analysis["effective_ukeire"]==4
    assert 1000<=analysis["wait_value"]["dama_points"]<2000
    assert analysis["danger"]<=85 and report==before


def test_lower_value_floor_does_not_override_danger_limit():
    action,analysis=choose(recorded(818))
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["rejections"]["call_requires_unsafe_push"]>0


def test_recorded_safe_four_copy_riichi_is_retained():
    action,analysis=choose(recorded(837))
    assert action=={"kind":"riichi","tile":"2p"}
    assert analysis["effective_ukeire"]==4 and analysis["danger"]==0
