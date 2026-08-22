from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="lucky",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _lucky():return SimpleNamespace(rank="7",suit="Hearts",enhancement="Lucky",debuffed=False)
def test_scoring_lucky_card_realizes_intrinsic_lucky_bond():
 assert realize_bond(_dev(),SimpleNamespace(scoring_cards=[_lucky()],jokers=[])).realization==BondRealization.ACTIVE
def test_lucky_cat_with_scoring_lucky_card_realizes():
 assert realize_bond(_dev(),SimpleNamespace(scoring_cards=[_lucky()],jokers=[SimpleNamespace(name="Lucky Cat")])).realization==BondRealization.ACTIVE
def test_oops_all_sixes_with_scoring_lucky_card_realizes():
 assert realize_bond(_dev(),SimpleNamespace(scoring_cards=[_lucky()],jokers=[SimpleNamespace(name="Oops! All 6s")])).realization==BondRealization.ACTIVE
