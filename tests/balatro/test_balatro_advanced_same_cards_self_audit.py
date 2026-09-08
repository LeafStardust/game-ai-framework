from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev(b):return BondDevelopment(bond_id=b,unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _c(r,s):return SimpleNamespace(rank=r,suit=s,enhancement="")
def test_flush_house_does_not_combine_offsuit_full_house_with_unrelated_flush():
 hand=[_c("K","Hearts"),_c("K","Hearts"),_c("K","Spades"),_c("Q","Clubs"),_c("Q","Diamonds"),_c("2","Hearts"),_c("3","Hearts"),_c("4","Hearts")]
 assert realize_bond(_dev("flush_house"),SimpleNamespace(hand=hand,jokers=[])).realization==BondRealization.PARTIAL
def test_flush_house_realizes_when_rank_groups_share_the_flush_suit():
 hand=[_c("K","Hearts"),_c("K","Hearts"),_c("K","Hearts"),_c("Q","Hearts"),_c("Q","Hearts")]
 assert realize_bond(_dev("flush_house"),SimpleNamespace(hand=hand,jokers=[])).realization==BondRealization.MATURE
def test_flush_five_requires_five_same_rank_cards_in_same_effective_suit():
 hand=[_c("K","Hearts"),_c("K","Hearts"),_c("K","Spades"),_c("K","Spades"),_c("K","Clubs"),_c("2","Hearts"),_c("3","Hearts"),_c("4","Hearts")]
 assert realize_bond(_dev("flush_five"),SimpleNamespace(hand=hand,jokers=[])).realization==BondRealization.PARTIAL
