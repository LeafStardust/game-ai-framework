from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _card(rank="2"):
    return SimpleNamespace(rank=rank, enhancement="", is_stone=False)


def test_trading_card_owned_but_no_single_first_discard_is_not_live():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Trading Card")], first_discard_available=False, cards_to_discard=[_card("2")])
    assert realize_bond(_dev("deck_thinning"), state).realization == BondRealization.PARTIAL


def test_trading_card_single_first_discard_is_live():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Trading Card")], first_discard_available=True, cards_to_discard=[_card("2")])
    assert realize_bond(_dev("deck_thinning"), state).realization == BondRealization.ACTIVE


def test_sixth_sense_requires_single_six_on_first_hand():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Sixth Sense")], first_hand_available=True, cards_to_play=[_card("5")])
    assert realize_bond(_dev("deck_thinning"), state).realization == BondRealization.PARTIAL


def test_dna_owned_but_multi_card_play_is_not_live():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="DNA")], first_hand_available=True, cards_to_play=[_card("2"), _card("3")])
    assert realize_bond(_dev("deck_growth"), state).realization == BondRealization.PARTIAL


def test_dna_single_first_hand_play_is_live():
    state = SimpleNamespace(jokers=[SimpleNamespace(name="DNA")], first_hand_available=True, cards_to_play=[_card("2")])
    assert realize_bond(_dev("deck_growth"), state).realization == BondRealization.ACTIVE


def test_certificate_requires_blind_selection_window():
    inactive = SimpleNamespace(jokers=[SimpleNamespace(name="Certificate")], blind_selection_pending=False)
    active = SimpleNamespace(jokers=[SimpleNamespace(name="Certificate")], blind_selection_pending=True)
    assert realize_bond(_dev("deck_growth"), inactive).realization == BondRealization.PARTIAL
    assert realize_bond(_dev("deck_growth"), active).realization == BondRealization.ACTIVE
