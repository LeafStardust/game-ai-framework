from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="held_retrigger",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _c(seal="",enh=""):return SimpleNamespace(rank="7",suit="Hearts",seal=seal,enhancement=enh)
def test_mime_does_not_make_blue_seal_a_held_retrigger_payoff():
 s=SimpleNamespace(jokers=[SimpleNamespace(name="Mime")],hand=[_c(seal="Blue")]);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
def test_mime_still_retriggers_steel_held_effect():
 s=SimpleNamespace(jokers=[SimpleNamespace(name="Mime")],hand=[_c(enh="Steel")]);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
