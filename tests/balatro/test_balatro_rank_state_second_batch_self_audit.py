from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _d(b):return BondDevelopment(bond_id=b,unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(n):return SimpleNamespace(name=n)
def _c(r="2",s="Hearts",e=""):return SimpleNamespace(rank=r,suit=s,enhancement=e,debuffed=False)
def _r(b,j,c):return realize_bond(_d(b),SimpleNamespace(jokers=[_j(j)],scoring_cards=[c])).realization

def test_fibonacci_eight_is_live():assert _r("low_ranks","Fibonacci",_c("8"))==BondRealization.ACTIVE
def test_fibonacci_ace_is_live():assert _r("low_ranks","Fibonacci",_c("A"))==BondRealization.ACTIVE
def test_even_steven_six_is_live():assert _r("low_ranks","Even Steven",_c("6"))==BondRealization.ACTIVE
def test_even_steven_eight_is_live():assert _r("low_ranks","Even Steven",_c("8"))==BondRealization.ACTIVE
def test_even_steven_ten_is_live():assert _r("low_ranks","Even Steven",_c("10"))==BondRealization.ACTIVE
def test_walkie_talkie_ten_is_live():assert _r("low_ranks","Walkie Talkie",_c("10"))==BondRealization.ACTIVE
def test_walkie_talkie_four_stays_live():assert _r("low_ranks","Walkie Talkie",_c("4"))==BondRealization.ACTIVE
def test_fibonacci_seven_is_not_live():assert _r("low_ranks","Fibonacci",_c("7"))==BondRealization.PARTIAL
def test_even_steven_nine_is_not_live():assert _r("low_ranks","Even Steven",_c("9"))==BondRealization.PARTIAL
def test_walkie_talkie_jack_is_not_live():assert _r("low_ranks","Walkie Talkie",_c("J"))==BondRealization.PARTIAL
def test_reserved_parking_not_live_without_scoring_window():
 s=SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[]);assert realize_bond(_d("gold_economy"),s).realization==BondRealization.PARTIAL
def test_reserved_parking_live_during_scoring_window():
 s=SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[_c("2")]);assert realize_bond(_d("gold_economy"),s).realization==BondRealization.ACTIVE
