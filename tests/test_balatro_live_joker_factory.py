from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.jokers.the_idol import TheIdolJoker
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


def test_live_joker_factory_maps_base_joker_to_plus_four_mult_model():
    joker = LiveJokerFactory().create(
        {
            "center": "j_joker",
            "label": "Joker",
        }
    )

    assert isinstance(joker, FlatMultJoker)
    assert joker.mult == 4


def test_live_joker_factory_requires_public_castle_suit_and_hydrates_chips():
    factory = LiveJokerFactory()

    assert factory.create({"center": "j_castle", "label": "Castle"}) is None

    joker = factory.create(
        {
            "center": "j_castle",
            "label": "Castle",
            "public_state": {
                "suit": "Hearts",
                "chips": 18,
                "chip_mod": 3,
            },
        }
    )

    assert isinstance(joker, CastleJoker)
    assert joker.suit == "Hearts"
    assert joker.chips == 18


def test_live_joker_factory_requires_and_normalizes_public_idol_target():
    factory = LiveJokerFactory()

    assert factory.create({"center": "j_idol", "label": "The Idol"}) is None

    joker = factory.create(
        {
            "center": "j_idol",
            "label": "The Idol",
            "public_state": {
                "rank": "Ace",
                "suit": "Spades",
            },
        }
    )

    assert isinstance(joker, TheIdolJoker)
    assert joker.rank == "A"
    assert joker.suit == "Spades"


def test_live_joker_factory_constructs_supernova_without_fixed_hand_parameter():
    joker = LiveJokerFactory().create(
        {
            "center": "j_supernova",
            "label": "Supernova",
        }
    )

    assert isinstance(joker, SupernovaJoker)


def test_live_joker_factory_rejects_unknown_jokers():
    assert LiveJokerFactory().create(
        {
            "center": "j_not_a_real_joker",
            "label": "Not a Real Joker",
        }
    ) is None
