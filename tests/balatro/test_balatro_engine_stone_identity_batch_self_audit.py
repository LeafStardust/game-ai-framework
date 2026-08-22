from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _stone(rank):
    return SimpleNamespace(rank=rank, enhancement="Stone", is_stone=True)


def test_sixth_sense_does_not_see_stone_hidden_six():
    stone = _stone("6")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Sixth Sense")], cards_to_play=[stone], first_hand_available=True)
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.PARTIAL


def test_midas_does_not_see_stone_hidden_face_without_pareidolia():
    stone = _stone("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Midas Mask"), SimpleNamespace(name="Vampire")], scoring_cards=[stone])
    assert realize_bond(_dev("vampire"), state).realization == BondRealization.ACTIVE


def test_pareidolia_allows_midas_to_treat_stone_as_face_before_vampire():
    stone = _stone("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Midas Mask"), SimpleNamespace(name="Pareidolia"), SimpleNamespace(name="Vampire")], scoring_cards=[stone])
    assert realize_bond(_dev("vampire"), state).realization == BondRealization.ACTIVE
