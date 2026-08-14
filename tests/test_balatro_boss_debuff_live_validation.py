from games.balatro.live.external.boss_debuff_live_validation import (
    analyze_boss_debuff_snapshot,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(*, boss=True, debuffed=True):
    return LiveBalatroSnapshot(
        sequence=7,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "money": 8,
            "ante_num": 2,
            "round_num": 6,
            "round": {
                "chips": 0,
                "hands_left": 4,
                "discards_left": 3,
            },
            "score": 0,
            "blind": {
                "type": "BOSS" if boss else "BIG",
                "status": "CURRENT",
                "name": "The Head" if boss else "Big Blind",
                "score": 600,
            },
            "hand": {
                "count": 2,
                "limit": 8,
                "cards": [
                    {
                        "value": {"rank": "10", "suit": "D"},
                        "modifier": {
                            "enhancement": "BONUS",
                            "edition": "FOIL",
                        },
                        "live_id": 41,
                        "debuff": debuffed,
                    },
                    {
                        "value": {"rank": "A", "suit": "S"},
                        "modifier": {},
                        "live_id": 42,
                        "debuff": False,
                    },
                ],
            },
            "cards": {"count": 0, "limit": 52, "cards": []},
            "jokers": {"count": 0, "limit": 5, "cards": []},
            "consumables": {"count": 0, "limit": 2, "cards": []},
        },
    )


def test_live_boss_debuff_validator_observes_d1_suppression():
    result = analyze_boss_debuff_snapshot(_snapshot())

    assert result.applicable is True
    assert result.passed is True
    assert result.boss_name == "The Head"
    assert len(result.probes) == 1

    probe = result.probes[0]
    assert probe.index == 0
    assert probe.live_id == 41
    assert probe.label == "10 / Diamonds / Bonus / Foil"
    assert probe.hand_name == "HIGH_CARD"
    assert probe.structure_preserved is True
    assert probe.actual_minimum == 5
    assert probe.actual_expected == 5.0
    assert probe.actual_maximum == 5
    assert probe.counterfactual_minimum == 95
    assert probe.counterfactual_expected == 95.0
    assert probe.counterfactual_maximum == 95
    assert probe.expected_suppressed == 90.0


def test_live_boss_debuff_validator_waits_for_relevant_checkpoint():
    no_debuff = analyze_boss_debuff_snapshot(_snapshot(debuffed=False))
    assert no_debuff.applicable is False
    assert "no currently debuffed" in no_debuff.reason

    non_boss = analyze_boss_debuff_snapshot(_snapshot(boss=False))
    assert non_boss.applicable is False
    assert "not an active Boss Blind" in non_boss.reason
