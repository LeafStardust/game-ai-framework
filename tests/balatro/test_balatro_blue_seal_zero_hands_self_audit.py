from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="planet",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _card():return SimpleNamespace(seal="Blue")
def test_blue_seal_live_when_hands_left_is_zero_without_extra_flag():
 s=SimpleNamespace(jokers=[],hand=[_card()],hands_left=0);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_blue_seal_not_live_with_one_hand_remaining():
 s=SimpleNamespace(jokers=[],hand=[_card()],hands_left=1);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
