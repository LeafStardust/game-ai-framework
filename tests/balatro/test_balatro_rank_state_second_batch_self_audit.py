from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _d(b):return BondDevelopment(bond_id=b,unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(n):return SimpleNamespace(name=n)
def _c(r="2",s="Hearts",e=""):return SimpleNamespace(rank=r,suit=s,enhancement=e,debuffed=False)
def _r(b,j,c):return realize_bond(_d(b),SimpleNamespace(jokers=[_j(j)],scoring_cards=[c])).realization

def test_fibonacci_eight_is_outside_low_rank_bond_scope():assert _r("low_ranks","Fibonacci",_c("8"))==BondRealization.PARTIAL
def test_fibonacci_ace_is_outside_low_rank_bond_scope():assert _r("low_ranks","Fibonacci",_c("A"))==BondRealization.PARTIAL
def test_even_steven_six_is_outside_low_rank_bond_scope():assert _r("low_ranks","Even Steven",_c("6"))==BondRealization.PARTIAL
def test_even_steven_ten_is_outside_low_rank_bond_scope():assert _r("low_ranks","Even Steven",_c("10"))==BondRealization.PARTIAL
def test_walkie_talkie_ten_is_outside_low_rank_bond_scope():assert _r("low_ranks","Walkie Talkie",_c("10"))==BondRealization.PARTIAL
def test_fibonacci_five_is_live_for_low_rank_bond():assert _r("low_ranks","Fibonacci",_c("5"))==BondRealization.ACTIVE
def test_even_steven_four_is_live_for_low_rank_bond():assert _r("low_ranks","Even Steven",_c("4"))==BondRealization.ACTIVE
def test_walkie_talkie_four_is_live_for_low_rank_bond():assert _r("low_ranks","Walkie Talkie",_c("4"))==BondRealization.ACTIVE
def test_fibonacci_ace_realizes_aces_bond():assert _r("aces","Fibonacci",_c("A"))==BondRealization.ACTIVE
def test_reserved_parking_live_when_held_face_opportunity_exists():
 s=SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[]);assert realize_bond(_d("gold_cards"),s).realization==BondRealization.ACTIVE
def test_reserved_parking_remains_live_during_scoring_window():
 s=SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[_c("2")]);assert realize_bond(_d("gold_cards"),s).realization==BondRealization.ACTIVE
