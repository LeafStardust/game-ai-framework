from types import SimpleNamespace

from games.balatro.bonds import evaluate_cash_bond, evaluate_gold_economy_bond, evaluate_vampire_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="7", enhancement=""):
    return SimpleNamespace(rank=rank, suit="Clubs", enhancement=enhancement)


def test_pareidolia_makes_reserved_parking_live_on_non_face_held_cards():
    hand = [_card("7")]
    state = SimpleNamespace(
        jokers=[_joker("Reserved Parking"), _joker("Pareidolia")],
        hand=hand,
        current_hand=hand,
        cards_in_hand=hand,
        owned_deck=hand,
        deck=hand,
        money=50,
    )
    dev = evaluate_cash_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_pareidolia_makes_midas_and_parking_live_inside_gold_economy():
    card = _card("7")
    state = SimpleNamespace(
        jokers=[_joker("Midas Mask"), _joker("Reserved Parking"), _joker("Pareidolia")],
        scoring_cards=[card],
        hand=[card],
        current_hand=[card],
        cards_in_hand=[card],
        owned_deck=[card],
        deck=[card],
    )
    dev = evaluate_gold_economy_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_pareidolia_supplies_midas_face_feed_for_vampire_when_midas_is_left():
    card = _card("7")
    state = SimpleNamespace(
        jokers=[_joker("Midas Mask"), _joker("Vampire"), _joker("Pareidolia")],
        scoring_cards=[card],
        hand=[card],
        owned_deck=[card],
        deck=[card],
        vampire_enhancements_consumed=0,
    )
    dev = evaluate_vampire_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_non_face_cards_do_not_enable_these_face_engines_without_pareidolia():
    card = _card("7")
    state = SimpleNamespace(
        jokers=[_joker("Reserved Parking")],
        hand=[card],
        current_hand=[card],
        cards_in_hand=[card],
        owned_deck=[card],
        deck=[card],
        money=0,
    )
    dev = evaluate_cash_bond(state)
    assert dev.rank.value >= 0
    assert realize_bond(dev, state).realization in {BondRealization.DORMANT, BondRealization.PARTIAL}
