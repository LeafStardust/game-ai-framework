from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev(bond):return BondDevelopment(bond_id=bond,unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(name):return SimpleNamespace(name=name)
def test_drivers_license_requires_sixteen_enhanced_cards():
 deck=[SimpleNamespace(enhancement="Bonus") for _ in range(15)];assert realize_bond(_dev("enhanced_cards"),SimpleNamespace(jokers=[_j("Driver's License")],deck=deck)).realization==BondRealization.PARTIAL
def test_drivers_license_live_at_sixteen_enhanced_cards():
 deck=[SimpleNamespace(enhancement="Bonus") for _ in range(16)];assert realize_bond(_dev("enhanced_cards"),SimpleNamespace(jokers=[_j("Driver's License")],deck=deck)).realization==BondRealization.MATURE
def test_swashbuckler_requires_positive_other_joker_sell_value():
 assert realize_bond(_dev("sell_value"),SimpleNamespace(jokers=[_j("Swashbuckler")],joker_sell_value_total=0)).realization==BondRealization.PARTIAL
def test_throwback_is_live_when_owned():
 assert realize_bond(_dev("blind_skip"),SimpleNamespace(jokers=[_j("Throwback")],blinds_skipped=0)).realization==BondRealization.ACTIVE
