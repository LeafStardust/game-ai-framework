from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="discard",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _card(rank="2",suit="Hearts",stone=False):return SimpleNamespace(rank=rank,suit=suit,enhancement="Stone" if stone else "",is_stone=stone)
def test_discard_joker_ownership_alone_is_not_live():
    s=SimpleNamespace(jokers=[SimpleNamespace(name="Hit the Road")],discards_left=2,discarded_cards=[]);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
def test_hit_the_road_requires_discarded_jack():
    s=SimpleNamespace(jokers=[SimpleNamespace(name="Hit the Road")],discarded_cards=[_card("J")]);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_faceless_joker_requires_three_faces_in_same_discard():
    j=[SimpleNamespace(name="Faceless Joker")];s=SimpleNamespace(jokers=j,discarded_cards=[_card("J"),_card("Q")]);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
    s=SimpleNamespace(jokers=j,discarded_cards=[_card("J"),_card("Q"),_card("K")]);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_mail_in_rebate_requires_current_target_rank():
    j=[SimpleNamespace(name="Mail-In Rebate")];s=SimpleNamespace(jokers=j,discarded_cards=[_card("9")],mail_in_rebate_rank="8");assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
    s=SimpleNamespace(jokers=j,discarded_cards=[_card("8")],mail_in_rebate_rank="8");assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_castle_requires_current_target_suit():
    j=[SimpleNamespace(name="Castle")];s=SimpleNamespace(jokers=j,discarded_cards=[_card("2","Hearts")],castle_suit="Spades");assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
    s=SimpleNamespace(jokers=j,discarded_cards=[_card("2","Spades")],castle_suit="Spades");assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
