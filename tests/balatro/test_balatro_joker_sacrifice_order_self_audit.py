from types import SimpleNamespace

from games.balatro.bonds import evaluate_joker_sacrifice_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _state(jokers):
    return SimpleNamespace(
        jokers=list(jokers),
        blind_selection_pending=True,
        sacrificable_joker_available=False,
        jokers_destroyed=0,
    )


def test_ceremonial_dagger_realizes_with_riffraff_immediately_to_right():
    state = _state([_joker("Ceremonial Dagger"), _joker("Riff-Raff")])
    dev = evaluate_joker_sacrifice_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_ceremonial_dagger_does_not_realize_from_fodder_on_left():
    state = _state([_joker("Riff-Raff"), _joker("Ceremonial Dagger")])
    dev = evaluate_joker_sacrifice_bond(state)
    assert dev.rank.value >= 1
    assert realize_bond(dev, state).realization == BondRealization.PARTIAL
