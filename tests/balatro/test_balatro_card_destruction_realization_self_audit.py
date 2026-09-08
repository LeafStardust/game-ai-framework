from types import SimpleNamespace

from games.balatro.bonds import evaluate_card_destruction_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=str(rank), suit="Hearts", enhancement=enhancement)


def test_trading_card_stops_realizing_after_first_discard_is_spent():
    hand = [_card("7"), _card("9")]
    fresh = SimpleNamespace(
        jokers=[_joker("Trading Card")], hand=hand, current_hand=hand, cards_in_hand=hand,
        owned_deck=hand, deck=hand, discards_used_this_round=0,
    )
    spent = SimpleNamespace(
        jokers=[_joker("Trading Card")], hand=hand, current_hand=hand, cards_in_hand=hand,
        owned_deck=hand, deck=hand, discards_used_this_round=1,
    )
    assert realize_bond(evaluate_card_destruction_bond(fresh), fresh).realization == BondRealization.ACTIVE
    assert realize_bond(evaluate_card_destruction_bond(spent), spent).realization == BondRealization.PARTIAL


def test_sixth_sense_requires_first_hand_opportunity_and_a_six():
    hand = [_card("6"), _card("9")]
    fresh = SimpleNamespace(
        jokers=[_joker("Sixth Sense")], hand=hand, current_hand=hand, cards_in_hand=hand,
        owned_deck=hand, deck=hand, hands_played_this_round=0,
    )
    spent = SimpleNamespace(
        jokers=[_joker("Sixth Sense")], hand=hand, current_hand=hand, cards_in_hand=hand,
        owned_deck=hand, deck=hand, hands_played_this_round=1,
    )
    no_six = SimpleNamespace(
        jokers=[_joker("Sixth Sense")], hand=[_card("5")], current_hand=[_card("5")], cards_in_hand=[_card("5")],
        owned_deck=[_card("5")], deck=[_card("5")], hands_played_this_round=0,
    )
    assert realize_bond(evaluate_card_destruction_bond(fresh), fresh).realization == BondRealization.ACTIVE
    assert realize_bond(evaluate_card_destruction_bond(spent), spent).realization == BondRealization.PARTIAL
    assert realize_bond(evaluate_card_destruction_bond(no_six), no_six).realization == BondRealization.PARTIAL
