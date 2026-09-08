from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _stone(rank, suit="Spades"):
    return SimpleNamespace(rank=rank, suit=suit, enhancement="Stone", is_stone=True, seal="")


def test_baron_does_not_realize_from_stone_with_hidden_king_rank():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Baron")], hand=[_stone("K")])
    assert realize_bond(_dev("kings"), state).realization == BondRealization.PARTIAL


def test_shoot_the_moon_does_not_realize_from_stone_with_hidden_queen_rank():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Shoot the Moon")], hand=[_stone("Q")])
    assert realize_bond(_dev("queens"), state).realization == BondRealization.PARTIAL


def test_triboulet_does_not_realize_from_scoring_stone_hidden_rank():
    stone = _stone("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Triboulet")], hand=[], scoring_cards=[stone])
    assert realize_bond(_dev("kings"), state).realization == BondRealization.PARTIAL


def test_blackboard_realizes_with_empty_hand():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Blackboard")], hand=[])
    assert realize_bond(_dev("held_cards"), state).realization == BondRealization.ACTIVE
