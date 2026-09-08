from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="planet",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def test_space_joker_ownership_alone_is_not_live():
    assert realize_bond(_dev(),SimpleNamespace(jokers=[SimpleNamespace(name="Space Joker")],scoring_cards=[])).realization==BondRealization.PARTIAL
def test_space_joker_is_live_when_hand_is_being_played():
    assert realize_bond(_dev(),SimpleNamespace(jokers=[SimpleNamespace(name="Space Joker")],scoring_cards=[SimpleNamespace(rank="2")])).realization==BondRealization.ACTIVE
def test_blue_seal_is_not_live_before_round_end():
    c=SimpleNamespace(seal="Blue");assert realize_bond(_dev(),SimpleNamespace(jokers=[],hand=[c],hands_left=2)).realization==BondRealization.PARTIAL
def test_blue_seal_is_live_at_round_end():
    c=SimpleNamespace(seal="Blue");assert realize_bond(_dev(),SimpleNamespace(jokers=[],hand=[c],hands_left=0,round_end_pending=True)).realization==BondRealization.ACTIVE
def test_constellation_requires_planet_history():
    s=SimpleNamespace(jokers=[SimpleNamespace(name="Constellation")],planets_used=0);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
