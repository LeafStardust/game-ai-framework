from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def test_madness_does_not_realize_on_boss_blind_selection():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Madness")], blind_selection_pending=True, blind_type="Boss Blind")
    assert realize_bond(_dev("joker_sacrifice"), state).realization == BondRealization.PARTIAL


def test_madness_realizes_on_small_blind_selection():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Madness")], blind_selection_pending=True, blind_type="Small Blind")
    assert realize_bond(_dev("joker_sacrifice"), state).realization == BondRealization.ACTIVE


def test_glass_joker_does_not_realize_from_non_scoring_glass_when_scoring_telemetry_present():
    glass = _card("9", "Glass")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Glass Joker")], hand=[glass], scoring_cards=[])
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.PARTIAL


def test_glass_joker_realizes_from_scoring_glass_card():
    glass = _card("9", "Glass")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Glass Joker")], hand=[glass], scoring_cards=[glass])
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.ACTIVE


def test_midas_after_vampire_cannot_create_same_hand_feed():
    face = _card("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Vampire"), SimpleNamespace(name="Midas Mask")], scoring_cards=[face], hand=[face], owned_deck=[face])
    assert realize_bond(_dev("vampire"), state).realization == BondRealization.PARTIAL


def test_midas_before_vampire_creates_same_hand_feed():
    face = _card("K")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Midas Mask"), SimpleNamespace(name="Vampire")], scoring_cards=[face], hand=[face], owned_deck=[face])
    assert realize_bond(_dev("vampire"), state).realization == BondRealization.ACTIVE
