from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(bond_id="tarot", unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _stone(rank):
    return SimpleNamespace(rank=rank, enhancement="Stone", is_stone=True)


def test_superposition_does_not_see_stone_hidden_ace():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Superposition")], scoring_cards=[_stone("A")], current_hand_type="Straight")
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_eight_ball_does_not_see_stone_hidden_eight():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="8 Ball")], scoring_cards=[_stone("8")])
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL
