from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.live.joker_factory import LiveJokerFactory


def test_live_joker_factory_resolves_save_center_and_preserves_metadata():
    joker = LiveJokerFactory().create(
        {
            "center": "j_acrobat",
            "label": "Acrobat",
            "live_id": 640,
            "cost": 6,
        }
    )

    assert isinstance(joker, AcrobatJoker)
    assert joker.live_id == 640
    assert joker.center == "j_acrobat"
    assert joker.label == "Acrobat"
    assert joker.cost == 6


def test_live_joker_factory_uses_label_alias_for_numeric_names():
    joker = LiveJokerFactory().create(
        {
            "center": "j_8_ball",
            "label": "8 Ball",
        }
    )

    assert isinstance(joker, EightBallJoker)


def test_live_joker_factory_rejects_unknown_jokers():
    assert LiveJokerFactory().create(
        {
            "center": "j_not_a_real_joker",
            "label": "Not a Real Joker",
        }
    ) is None
