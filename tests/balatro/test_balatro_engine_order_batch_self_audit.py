from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=22.0,
        rank=BondRank.R4,
        next_rank_threshold=30.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def test_madness_does_not_realize_on_boss_blind_selection():
    state = SimpleNamespace(
        jokers=[_joker("Madness")],
        blind_selection_pending=True,
        selected_blind_type="Boss Blind",
    )
    assert realize_bond(_dev("joker_sacrifice"), state).realization == BondRealization.PARTIAL


def test_madness_realizes_on_small_blind_selection():
    state = SimpleNamespace(
        jokers=[_joker("Madness")],
        blind_selection_pending=True,
        selected_blind_type="Small Blind",
    )
    assert realize_bond(_dev("joker_sacrifice"), state).realization == BondRealization.ACTIVE


def test_vampire_does_not_get_same_hand_feed_from_midas_to_its_right():
    face = _card("K")
    state = SimpleNamespace(
        jokers=[_joker("Vampire"), _joker("Midas Mask")],
        scoring_cards=[face],
        hand=[face],
    )
    assert realize_bond(_dev("enhancement_consumption"), state).realization == BondRealization.PARTIAL


def test_vampire_gets_same_hand_feed_from_midas_to_its_left():
    face = _card("K")
    state = SimpleNamespace(
        jokers=[_joker("Midas Mask"), _joker("Vampire")],
        scoring_cards=[face],
        hand=[face],
    )
    assert realize_bond(_dev("enhancement_consumption"), state).realization == BondRealization.ACTIVE


def test_glass_destruction_does_not_realize_from_non_scoring_glass_when_scoring_known():
    glass = _card("9", "Glass")
    state = SimpleNamespace(
        jokers=[_joker("Glass Joker")],
        hand=[glass],
        scoring_cards=[],
        selected_cards=[glass],
    )
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.PARTIAL


def test_glass_destruction_realizes_from_scoring_glass():
    glass = _card("9", "Glass")
    state = SimpleNamespace(
        jokers=[_joker("Glass Joker")],
        hand=[glass],
        scoring_cards=[glass],
        selected_cards=[glass],
    )
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.ACTIVE
