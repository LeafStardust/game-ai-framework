from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="held_retrigger",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _c(seal="",enh=""):return SimpleNamespace(rank="7",suit="Hearts",seal=seal,enhancement=enh,debuffed=False)
def test_mime_blue_seal_not_live_before_round_end():
 s=SimpleNamespace(jokers=[SimpleNamespace(name="Mime")],hand=[_c(seal="Blue")],hands_left=2);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
def test_mime_blue_seal_live_at_round_end():
 s=SimpleNamespace(jokers=[SimpleNamespace(name="Mime")],hand=[_c(seal="Blue")],hands_left=0);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_mime_gold_card_live_at_round_end():
 s=SimpleNamespace(jokers=[SimpleNamespace(name="Mime")],hand=[_c(enh="Gold")],hands_left=0);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_mime_still_retriggers_steel_held_effect_while_scoring():
 s=SimpleNamespace(jokers=[SimpleNamespace(name="Mime")],hand=[_c(enh="Steel")],hands_left=2);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
