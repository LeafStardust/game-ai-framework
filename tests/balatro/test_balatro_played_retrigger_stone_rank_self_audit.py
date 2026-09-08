from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(bond_id="played_retrigger", unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _stone(rank):
    return SimpleNamespace(rank=rank, suit="Spades", enhancement="Stone", is_stone=True, seal="")


def test_hack_does_not_retrigger_stone_with_hidden_low_rank():
    stone = _stone("2")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Hack")], scoring_cards=[stone])
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_sock_and_buskin_does_not_retrigger_stone_hidden_face_without_pareidolia():
    stone = _stone("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Sock and Buskin")], scoring_cards=[stone])
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_pareidolia_gives_scoring_stone_face_property_for_sock_and_buskin():
    stone = _stone("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Pareidolia"), SimpleNamespace(name="Sock and Buskin")], scoring_cards=[stone])
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
