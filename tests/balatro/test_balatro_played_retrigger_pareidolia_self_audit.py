from types import SimpleNamespace

from games.balatro.bonds import evaluate_played_retrigger_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank):
    return SimpleNamespace(rank=rank, suit="Hearts", seal="", enhancement="")


def test_pareidolia_makes_non_face_cards_valid_sock_and_buskin_targets():
    state = SimpleNamespace(
        jokers=[_joker("Sock and Buskin"), _joker("Pareidolia")],
        scoring_cards=[_card("7")],
        selected_cards=[_card("7")],
        cards_to_play=[_card("7")],
        owned_deck=[],
        deck=[],
        hands_left=2,
    )
    dev = evaluate_played_retrigger_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_sock_and_buskin_without_pareidolia_does_not_retrigger_non_face_card():
    state = SimpleNamespace(
        jokers=[_joker("Sock and Buskin")],
        scoring_cards=[_card("7")],
        selected_cards=[_card("7")],
        cards_to_play=[_card("7")],
        owned_deck=[],
        deck=[],
        hands_left=2,
    )
    dev = evaluate_played_retrigger_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.PARTIAL
