from types import SimpleNamespace

from games.balatro.bonds import evaluate_straight_flush_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _card(rank, suit):
    return SimpleNamespace(rank=rank, suit=suit, enhancement="")


def _dev():
    # Establish the advanced-hand Bond independently of the realization hand.
    state = SimpleNamespace(jokers=[], hand_levels={"STRAIGHT_FLUSH": 7}, owned_deck=[], deck=[])
    return evaluate_straight_flush_bond(state)


def test_four_fingers_allows_flush_and_straight_to_use_different_cards():
    # Hearts 2/3/4/9 form the four-card flush. 2/3/4/5 form the four-card
    # straight, with the 5 off-suit. Balatro's Four Fingers permits this to
    # qualify as a Straight Flush even though no single suit has the straight.
    hand = [
        _card("2", "Hearts"),
        _card("3", "Hearts"),
        _card("4", "Hearts"),
        _card("9", "Hearts"),
        _card("5", "Clubs"),
    ]
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Four Fingers")], hand=hand)
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_same_split_shape_is_not_straight_flush_without_four_fingers():
    hand = [
        _card("2", "Hearts"),
        _card("3", "Hearts"),
        _card("4", "Hearts"),
        _card("9", "Hearts"),
        _card("5", "Clubs"),
    ]
    state = SimpleNamespace(jokers=[], hand=hand)
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL
