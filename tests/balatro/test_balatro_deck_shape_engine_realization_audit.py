from types import SimpleNamespace

from games.balatro.bonds import evaluate_deck_growth_bond, evaluate_deck_thinning_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _state(joker):
    deck = [SimpleNamespace(rank="2", suit="Hearts", enhancement="") for _ in range(52)]
    return SimpleNamespace(jokers=[_joker(joker)], owned_deck=deck, deck=deck)


def test_trading_card_is_live_deck_thinning_engine_before_first_removal():
    state = _state("Trading Card")
    dev = evaluate_deck_thinning_bond(state)
    assert dev.contribution >= 4.0
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_sixth_sense_is_live_deck_thinning_engine_before_first_removal():
    state = _state("Sixth Sense")
    dev = evaluate_deck_thinning_bond(state)
    assert dev.contribution >= 4.0
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_certificate_is_live_deck_growth_engine_before_first_added_card():
    state = _state("Certificate")
    dev = evaluate_deck_growth_bond(state)
    assert dev.contribution >= 4.0
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_dna_is_live_deck_growth_engine_before_first_added_card():
    state = _state("DNA")
    dev = evaluate_deck_growth_bond(state)
    assert dev.contribution >= 4.0
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_hologram_payoff_waits_for_actual_growth():
    state = _state("Hologram")
    dev = evaluate_deck_growth_bond(state)
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.PARTIAL
