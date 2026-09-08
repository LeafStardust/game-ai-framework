from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization_advanced import (
    realize_full_house, realize_straight_flush, realize_five_kind,
    realize_flush_house, realize_flush_five,
)


def dev(bond_id, rank=BondRank.R3):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=15.0, rank=rank,
                           next_rank_threshold=20.0, contributions=(), realization=BondRealization.PARTIAL)

def card(rank, suit): return SimpleNamespace(rank=rank, suit=suit, enhancement="")

def test_full_house_realizes_from_actual_shape():
    state = SimpleNamespace(hand=[card("A","Hearts"),card("A","Spades"),card("A","Clubs"),card("K","Hearts"),card("K","Clubs")])
    assert realize_full_house(dev("full_house"), state).realization == BondRealization.ACTIVE

def test_straight_flush_realizes_from_actual_shape():
    state = SimpleNamespace(hand=[card("2","Hearts"),card("3","Hearts"),card("4","Hearts"),card("5","Hearts"),card("6","Hearts")])
    assert realize_straight_flush(dev("straight_flush"), state).realization == BondRealization.ACTIVE

def test_five_kind_realizes_from_actual_shape():
    state = SimpleNamespace(hand=[card("7",s) for s in ("Hearts","Spades","Clubs","Diamonds","Hearts")])
    assert realize_five_kind(dev("five_kind"), state).realization == BondRealization.ACTIVE

def test_flush_house_requires_both_shape_and_suit():
    state = SimpleNamespace(hand=[card("Q","Hearts"),card("Q","Hearts"),card("Q","Hearts"),card("9","Hearts"),card("9","Hearts")])
    assert realize_flush_house(dev("flush_house"), state).realization == BondRealization.ACTIVE

def test_flush_five_requires_same_rank_same_suit():
    state = SimpleNamespace(hand=[card("4","Clubs") for _ in range(5)])
    assert realize_flush_five(dev("flush_five"), state).realization == BondRealization.ACTIVE
