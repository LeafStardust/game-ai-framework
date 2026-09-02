from types import SimpleNamespace

from games.balatro.bonds import evaluate_cash_bond, evaluate_vampire_bond
from games.balatro.bonds.gold_cards import evaluate_gold_cards_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond
from games.balatro.bonds.realization_engine import realize_vampire


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


def test_pareidolia_does_not_make_debuffed_cards_live_for_reserved_parking():
    card = _card("7")
    card.debuffed = True
    state = SimpleNamespace(
        jokers=[_joker("Reserved Parking"), _joker("Pareidolia")],
        hand=[card],
        current_hand=[card],
        cards_in_hand=[card],
        owned_deck=[card],
        deck=[card],
        money=50,
    )
    dev = evaluate_cash_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.PARTIAL


def test_pareidolia_makes_midas_generator_live_inside_gold_cards():
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
    dev = evaluate_gold_cards_bond(state)
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


def test_base_vampire_realizer_respects_midas_order_during_scoring():
    card = _card("7")
    wrong_order = SimpleNamespace(
        jokers=[_joker("Vampire"), _joker("Midas Mask"), _joker("Pareidolia")],
        scoring_cards=[card],
        hand=[card],
        owned_deck=[card],
        deck=[card],
        vampire_enhancements_consumed=0,
    )
    dev = evaluate_vampire_bond(wrong_order)
    assert realize_vampire(dev, wrong_order).realization == BondRealization.PARTIAL

    correct_order = SimpleNamespace(
        jokers=[_joker("Midas Mask"), _joker("Vampire"), _joker("Pareidolia")],
        scoring_cards=[card],
        hand=[card],
        owned_deck=[card],
        deck=[card],
        vampire_enhancements_consumed=0,
    )
    dev = evaluate_vampire_bond(correct_order)
    assert realize_vampire(dev, correct_order).realization == BondRealization.ACTIVE


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
