from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(bond_id="tarot", unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _card(rank):
    return SimpleNamespace(rank=rank, enhancement="")


def test_superposition_requires_ace_straight_trigger():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Superposition")], current_hand_type="PAIR", scoring_cards=[_card("A"), _card("A")], consumables=[], vouchers=[])
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_superposition_realizes_on_ace_straight():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Superposition")], current_hand_type="STRAIGHT", scoring_cards=[_card("A"), _card("2"), _card("3"), _card("4"), _card("5")], consumables=[], vouchers=[])
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_eight_ball_requires_scoring_eight():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="8 Ball")], scoring_cards=[_card("7")], consumables=[], vouchers=[])
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_eight_ball_realizes_with_scoring_eight():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="8 Ball")], scoring_cards=[_card("8")], consumables=[], vouchers=[])
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_vagabond_requires_four_dollars_or_less():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Vagabond")], money=5, scoring_cards=[_card("2")], consumables=[], vouchers=[])
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_vagabond_realizes_at_four_dollars_or_less_with_played_hand():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Vagabond")], money=4, scoring_cards=[_card("2")], consumables=[], vouchers=[])
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
