from types import SimpleNamespace

from games.balatro.bonds import (
    evaluate_aces_bond,
    evaluate_face_cards_bond,
    evaluate_hearts_bond,
    evaluate_low_ranks_bond,
    evaluate_no_face_cards_bond,
)
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank, suit="Hearts", enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement)


def test_hidden_stone_ace_does_not_trigger_scholar():
    deck = [_card("A") for _ in range(6)]
    state = SimpleNamespace(jokers=[_joker("Scholar")], owned_deck=deck, deck=deck, scoring_cards=[_card("A", enhancement="Stone")])
    dev = evaluate_aces_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.PARTIAL


def test_hidden_stone_two_does_not_trigger_wee_joker():
    deck = [_card("2") for _ in range(20)]
    state = SimpleNamespace(jokers=[_joker("Wee Joker")], owned_deck=deck, deck=deck, scoring_cards=[_card("2", enhancement="Stone")])
    dev = evaluate_low_ranks_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.PARTIAL


def test_hidden_stone_heart_does_not_trigger_lusty_joker():
    deck = [_card("7", "Hearts") for _ in range(20)]
    state = SimpleNamespace(jokers=[_joker("Lusty Joker")], owned_deck=deck, deck=deck, scoring_cards=[_card("7", "Hearts", "Stone")])
    dev = evaluate_hearts_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.PARTIAL


def test_hidden_stone_face_is_safe_for_ride_the_bus_without_pareidolia():
    deck = [_card("7") for _ in range(52)]
    state = SimpleNamespace(jokers=[_joker("Ride the Bus")], owned_deck=deck, deck=deck, scoring_cards=[_card("K", enhancement="Stone")], ride_the_bus_streak=1)
    dev = evaluate_no_face_cards_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_pareidolia_still_makes_stone_card_a_face_card():
    deck = [_card("7") for _ in range(52)]
    state = SimpleNamespace(jokers=[_joker("Pareidolia")], owned_deck=deck, deck=deck, scoring_cards=[_card("2", enhancement="Stone")])
    dev = evaluate_face_cards_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE
