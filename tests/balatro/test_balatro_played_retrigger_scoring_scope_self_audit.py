from types import SimpleNamespace

from games.balatro.bonds import evaluate_played_retrigger_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="7", seal=""):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement="", seal=seal)


def test_hanging_chad_does_not_realize_from_non_scoring_selected_card():
    state = SimpleNamespace(
        jokers=[_joker("Hanging Chad")],
        owned_deck=[_card() for _ in range(52)],
        deck=[_card() for _ in range(52)],
        selected_cards=[_card()],
        scoring_cards=[],
    )
    dev = evaluate_played_retrigger_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.PARTIAL


def test_hanging_chad_realizes_when_scoring_card_exists():
    state = SimpleNamespace(
        jokers=[_joker("Hanging Chad")],
        owned_deck=[_card() for _ in range(52)],
        deck=[_card() for _ in range(52)],
        selected_cards=[_card()],
        scoring_cards=[_card()],
    )
    dev = evaluate_played_retrigger_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_red_seal_non_scoring_selected_card_does_not_realize_retrigger():
    deck = [_card(seal="Red") for _ in range(4)] + [_card() for _ in range(48)]
    state = SimpleNamespace(
        jokers=[],
        owned_deck=deck,
        deck=deck,
        selected_cards=[_card(seal="Red")],
        scoring_cards=[],
    )
    dev = evaluate_played_retrigger_bond(state)
    assert dev.rank.value >= 1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.PARTIAL


def test_red_seal_scoring_card_realizes_retrigger():
    deck = [_card(seal="Red") for _ in range(4)] + [_card() for _ in range(48)]
    state = SimpleNamespace(
        jokers=[],
        owned_deck=deck,
        deck=deck,
        selected_cards=[_card(seal="Red")],
        scoring_cards=[_card(seal="Red")],
    )
    dev = evaluate_played_retrigger_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE
