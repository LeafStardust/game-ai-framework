from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(bond_id="cash", unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _stone(rank):
    return SimpleNamespace(rank=rank, enhancement="Stone", is_stone=True)


def test_reserved_parking_does_not_see_stone_hidden_face_without_pareidolia():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Reserved Parking")], hand=[_stone("K")], money=0)
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_pareidolia_allows_reserved_parking_to_treat_stone_as_face():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Pareidolia"), SimpleNamespace(name="Reserved Parking")], hand=[_stone("K")], money=0)
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_cloud_nine_does_not_count_stone_hidden_nine():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Cloud 9")], owned_deck=[_stone("9")], money=0)
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL
