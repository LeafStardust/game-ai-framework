"""Recorded ready-hand and post-call planning regressions."""
import json
from pathlib import Path
from copy import deepcopy
from tests.mahjong_soul.test_attack_v2 import choose


def recorded(sequence):
    return json.loads((Path(__file__).parent/"fixtures/attack_ready_waits.json").read_text())[str(sequence)]


def test_scored_waits_replace_partial_yaku_wait_counts():
    report=recorded(3306);before=deepcopy(report)
    action,analysis=choose(report)
    options={o["action"]["tile"]:o for o in analysis["discard_evaluations"]}
    assert options["4p"]["effective_ukeire"]==5
    assert options["6p"]["effective_ukeire"]==4
    assert options["4p"]["route_cost"]==0
    # The actual choice must beat the old 2,600-point Riichi on 7 Pin.
    selected=options[action["tile"]]["wait_value"]
    assert selected["riichi_points"]>options["7p"]["wait_value"]["riichi_points"]
    assert report==before


def test_call_cannot_sell_remote_flush_when_post_call_policy_prefers_cheap_route():
    action,analysis=choose(recorded(407))
    assert action["kind"]=="skip"
    assert analysis["call_evaluations"][0]["rejections"]["slower_than_post_call_plan"]>0
