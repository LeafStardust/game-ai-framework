from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.dagger import DaggerJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.green_joker import GreenJoker
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


def test_live_joker_factory_hydrates_numeric_and_dynamic_string_state():
    factory = LiveJokerFactory()

    green = factory.create(
        {
            "center": "j_green_joker",
            "label": "Green Joker",
            "public_state": {"mult": 19},
        }
    )
    ancient = factory.create(
        {
            "center": "j_ancient",
            "label": "Ancient Joker",
            "public_state": {"suit": "S"},
        }
    )
    egg = factory.create(
        {
            "center": "j_egg",
            "label": "Egg",
            "public_state": {"sell_value": 15},
        }
    )

    assert isinstance(green, GreenJoker)
    assert green.mult == 19
    assert isinstance(ancient, AncientJoker)
    assert ancient.suit == "Spades"
    assert isinstance(egg, EggJoker)
    assert egg.sell_value == 15


def test_live_joker_factory_resolves_ceremonial_dagger_alias():
    joker = LiveJokerFactory().create(
        {
            "center": "j_ceremonial",
            "label": "Ceremonial Dagger",
            "public_state": {"mult": 24},
        }
    )

    assert isinstance(joker, DaggerJoker)
    assert joker.mult == 24


def test_live_joker_factory_rejects_unknown_jokers():
    assert LiveJokerFactory().create(
        {
            "center": "j_not_a_real_joker",
            "label": "Not a Real Joker",
        }
    ) is None
