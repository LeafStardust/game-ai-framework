import json
from pathlib import Path
from tests.mahjong_soul.test_attack_v2 import choose
from agents.mahjong_soul.scoring import score_hand


def recorded(sequence):
    return json.loads((Path(__file__).parent/"fixtures/sanma_yakuless_pon.json").read_text())[str(sequence)]


def test_disputed_pon_makes_no_yaku_ready_hand():
    report=recorded(344)
    assert choose(report)[0]["kind"]=="skip"
    hand=list(report["state"]["hand"])
    for tile in ("3p","3p","4p"):hand.remove(tile)
    value=score_hand(hand,"8p",melds=[{"type":1,"tiles":["3p"]*3}],player_count=3)
    assert not value["legal"]


def test_recorded_riichi_keeps_more_winning_copies_than_nine_pin():
    action,analysis=choose(recorded(1061))
    options={o["action"]["tile"]:o for o in analysis["discard_evaluations"]}
    assert action=={"kind":"riichi","tile":"5p"}
    assert options["5p"]["effective_ukeire"]==5 and options["9p"]["effective_ukeire"]==3
