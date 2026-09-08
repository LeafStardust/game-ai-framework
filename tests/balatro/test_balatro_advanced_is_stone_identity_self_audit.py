from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _card(rank, suit="Spades", *, stone=False):
    return SimpleNamespace(rank=rank, suit=suit, enhancement="", is_stone=stone)


def test_is_stone_flag_hidden_rank_does_not_complete_five_kind():
    hand = [_card("K") for _ in range(4)] + [_card("K", stone=True)]
    assert realize_bond(_dev("five_kind"), SimpleNamespace(hand=hand, jokers=[])).realization == BondRealization.PARTIAL


def test_is_stone_flag_hidden_rank_does_not_complete_full_house():
    hand = [_card("K"), _card("K"), _card("K"), _card("Q"), _card("Q", stone=True)]
    assert realize_bond(_dev("full_house"), SimpleNamespace(hand=hand, jokers=[])).realization == BondRealization.PARTIAL


def test_is_stone_flag_hidden_suit_does_not_complete_straight_flush():
    hand = [_card("2"), _card("3"), _card("4"), _card("5"), _card("6", stone=True)]
    assert realize_bond(_dev("straight_flush"), SimpleNamespace(hand=hand, jokers=[])).realization == BondRealization.PARTIAL
