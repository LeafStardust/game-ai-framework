from types import SimpleNamespace

from games.balatro.bonds import (
    BondRealization,
    evaluate_held_cards_bond,
    evaluate_held_retrigger_bond,
    evaluate_kings_bond,
    evaluate_queens_bond,
    evaluate_steel_bond,
)
from games.balatro.bonds.realization_held import (
    realize_held_cards,
    realize_held_retrigger,
    realize_kings,
    realize_queens,
    realize_steel,
)


def joker(name):
    return SimpleNamespace(name=name)


def card(rank="2", suit="hearts", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal=seal)


def state(*, jokers=(), hand=(), deck=()):
    return SimpleNamespace(jokers=list(jokers), hand=list(hand), current_hand=list(hand), owned_deck=list(deck), deck=list(deck), hand_size=8)


def test_baron_high_rank_can_be_only_partial_without_held_kings():
    deck = [card(rank="K") for _ in range(18)]
    s = state(jokers=[joker("Baron")], hand=[card(rank="2")], deck=deck)
    dev = evaluate_held_cards_bond(s)
    out = realize_held_cards(dev, s)
    assert out.realization == BondRealization.PARTIAL


def test_baron_and_steel_realize_held_cards_differently_from_blackboard():
    s = state(jokers=[joker("Baron")], hand=[card(rank="K"), card(enhancement="steel")], deck=[card(enhancement="steel") for _ in range(6)])
    out = realize_held_cards(evaluate_held_cards_bond(s), s)
    assert out.realization in {BondRealization.ACTIVE, BondRealization.MATURE}

    b = state(jokers=[joker("Blackboard")], hand=[card(suit="spades"), card(suit="clubs")])
    bout = realize_held_cards(evaluate_held_cards_bond(b), b)
    assert bout.realization == BondRealization.ACTIVE

    bad = state(jokers=[joker("Blackboard")], hand=[card(suit="spades"), card(suit="hearts")])
    badout = realize_held_cards(evaluate_held_cards_bond(bad), bad)
    assert badout.realization == BondRealization.PARTIAL


def test_mime_requires_actual_retriggerable_held_effect():
    empty = state(jokers=[joker("Mime")], hand=[card(rank="2")])
    out = realize_held_retrigger(evaluate_held_retrigger_bond(empty), empty)
    assert out.realization == BondRealization.PARTIAL

    active = state(jokers=[joker("Mime")], hand=[card(enhancement="steel")])
    out2 = realize_held_retrigger(evaluate_held_retrigger_bond(active), active)
    assert out2.realization == BondRealization.ACTIVE


def test_steel_requires_steel_currently_held():
    s = state(hand=[card(rank="2")], deck=[card(enhancement="steel") for _ in range(10)])
    out = realize_steel(evaluate_steel_bond(s), s)
    assert out.realization == BondRealization.PARTIAL
    s2 = state(hand=[card(enhancement="steel")], deck=[card(enhancement="steel") for _ in range(10)])
    out2 = realize_steel(evaluate_steel_bond(s2), s2)
    assert out2.realization == BondRealization.ACTIVE


def test_kings_and_queens_require_matching_current_hand_and_payoff():
    ks = state(jokers=[joker("Baron")], hand=[card(rank="K")], deck=[card(rank="K") for _ in range(18)])
    assert realize_kings(evaluate_kings_bond(ks), ks).realization == BondRealization.ACTIVE

    qs = state(jokers=[joker("Shoot the Moon")], hand=[card(rank="Q")], deck=[card(rank="Q") for _ in range(18)])
    assert realize_queens(evaluate_queens_bond(qs), qs).realization == BondRealization.ACTIVE

    qbad = state(jokers=[joker("Shoot the Moon")], hand=[card(rank="2")], deck=[card(rank="Q") for _ in range(18)])
    assert realize_queens(evaluate_queens_bond(qbad), qbad).realization == BondRealization.PARTIAL
