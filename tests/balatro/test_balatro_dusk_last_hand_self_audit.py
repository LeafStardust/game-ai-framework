from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="played_retrigger",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _s(left):return SimpleNamespace(jokers=[SimpleNamespace(name="Dusk")],scoring_cards=[SimpleNamespace(rank="7",seal="")],hands_left=left)
def test_dusk_live_when_final_hand_observed_before_decrement():
 assert realize_bond(_dev(),_s(1)).realization==BondRealization.ACTIVE
def test_dusk_live_when_final_hand_observed_after_decrement():
 assert realize_bond(_dev(),_s(0)).realization==BondRealization.ACTIVE
def test_dusk_not_live_with_multiple_hands_remaining():
 assert realize_bond(_dev(),_s(2)).realization==BondRealization.PARTIAL
