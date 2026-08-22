from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name): return SimpleNamespace(name=name)
def _card(rank, suit): return SimpleNamespace(rank=rank, suit=suit, enhancement="", is_stone=False)
def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=10.0, rank=BondRank.R2, next_rank_threshold=15.0, contributions=(), realization=BondRealization.PARTIAL)


def test_four_fingers_realizes_four_card_straight():
    state=SimpleNamespace(jokers=[_joker("Four Fingers")],hand=[_card("5","Hearts"),_card("6","Clubs"),_card("7","Spades"),_card("8","Diamonds")])
    assert realize_bond(_dev("straight"),state).realization==BondRealization.ACTIVE


def test_shortcut_realizes_gapped_straight():
    state=SimpleNamespace(jokers=[_joker("Shortcut")],hand=[_card("2","Hearts"),_card("4","Clubs"),_card("6","Spades"),_card("8","Diamonds"),_card("10","Hearts")])
    assert realize_bond(_dev("straight"),state).realization==BondRealization.ACTIVE


def test_smeared_realizes_mixed_red_flush():
    state=SimpleNamespace(jokers=[_joker("Smeared Joker")],hand=[_card("2","Hearts"),_card("5","Diamonds"),_card("7","Hearts"),_card("9","Diamonds"),_card("K","Hearts")])
    assert realize_bond(_dev("flush"),state).realization==BondRealization.ACTIVE


def test_four_fingers_realizes_four_card_flush():
    state=SimpleNamespace(jokers=[_joker("Four Fingers")],hand=[_card("2","Clubs"),_card("5","Clubs"),_card("7","Clubs"),_card("K","Clubs")])
    assert realize_bond(_dev("flush"),state).realization==BondRealization.ACTIVE
