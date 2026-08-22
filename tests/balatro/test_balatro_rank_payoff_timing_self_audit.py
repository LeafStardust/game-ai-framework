from types import SimpleNamespace

from games.balatro.bonds import evaluate_kings_bond, evaluate_queens_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement="", seal="")


def _state(jokers, *, hand=(), scoring=(), deck=()):
    return SimpleNamespace(
        jokers=[_joker(name) for name in jokers],
        hand=list(hand),
        current_hand=list(hand),
        cards_in_hand=list(hand),
        scoring_cards=list(scoring),
        played_cards=list(scoring),
        current_played_cards=list(scoring),
        owned_deck=list(deck),
        deck=list(deck),
    )


def test_triboulet_king_requires_scored_king_not_held_king():
    deck = [_card("K") for _ in range(6)]
    held = _state(["Triboulet"], hand=[_card("K")], scoring=[], deck=deck)
    scored = _state(["Triboulet"], hand=[], scoring=[_card("K")], deck=deck)
    assert realize_bond(evaluate_kings_bond(held), held).realization == BondRealization.PARTIAL
    assert realize_bond(evaluate_kings_bond(scored), scored).realization == BondRealization.ACTIVE


def test_baron_king_requires_held_king_not_scored_king():
    deck = [_card("K") for _ in range(6)]
    held = _state(["Baron"], hand=[_card("K")], scoring=[], deck=deck)
    scored = _state(["Baron"], hand=[], scoring=[_card("K")], deck=deck)
    assert realize_bond(evaluate_kings_bond(held), held).realization == BondRealization.ACTIVE
    assert realize_bond(evaluate_kings_bond(scored), scored).realization == BondRealization.PARTIAL


def test_shoot_the_moon_queen_requires_held_queen():
    deck = [_card("Q") for _ in range(6)]
    held = _state(["Shoot the Moon"], hand=[_card("Q")], scoring=[], deck=deck)
    scored = _state(["Shoot the Moon"], hand=[], scoring=[_card("Q")], deck=deck)
    assert realize_bond(evaluate_queens_bond(held), held).realization == BondRealization.ACTIVE
    assert realize_bond(evaluate_queens_bond(scored), scored).realization == BondRealization.PARTIAL
