from types import SimpleNamespace

from games.balatro.bonds import (
    evaluate_flush_five_bond,
    evaluate_flush_house_bond,
    evaluate_straight_flush_bond,
)
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _card(rank, suit, enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement)


def _state(hand):
    return SimpleNamespace(jokers=[], hand=list(hand), current_hand=list(hand), cards_in_hand=list(hand))


def _established_state(hand, hand_type):
    # Level 7 contributes 5 structural points under the audited hand-level band,
    # which clears the R1=4 floor for all three advanced Bonds. Realization
    # tests must start from an established Bond rather than asking a realizer to
    # promote R0/DORMANT structure.
    return SimpleNamespace(
        jokers=[],
        hand_levels={hand_type: 7},
        owned_deck=list(hand),
        deck=list(hand),
    )


def test_wild_card_can_complete_straight_flush():
    hand = [
        _card("5", "Hearts"),
        _card("6", "Hearts"),
        _card("7", "Hearts"),
        _card("8", "Hearts"),
        _card("9", "Clubs", "Wild"),
    ]
    state = _state(hand)
    dev = evaluate_straight_flush_bond(_established_state(hand, "STRAIGHT_FLUSH"))
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_wild_cards_can_complete_flush_house():
    hand = [
        _card("K", "Hearts"),
        _card("K", "Hearts"),
        _card("K", "Clubs", "Wild"),
        _card("Q", "Hearts"),
        _card("Q", "Spades", "Wild"),
    ]
    state = _state(hand)
    dev = evaluate_flush_house_bond(_established_state(hand, "FLUSH_HOUSE"))
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_wild_cards_can_complete_flush_five():
    hand = [
        _card("K", "Hearts"),
        _card("K", "Hearts"),
        _card("K", "Hearts"),
        _card("K", "Clubs", "Wild"),
        _card("K", "Spades", "Wild"),
    ]
    state = _state(hand)
    dev = evaluate_flush_five_bond(_established_state(hand, "FLUSH_FIVE"))
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE
