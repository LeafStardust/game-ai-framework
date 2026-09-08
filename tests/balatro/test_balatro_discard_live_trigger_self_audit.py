from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="discard",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _c(rank="2",suit="Hearts",stone=False):return SimpleNamespace(rank=rank,suit=suit,enhancement="Stone" if stone else "",is_stone=stone)
def _state(name,cards,**kw):return SimpleNamespace(jokers=[SimpleNamespace(name=name)],discarded_cards=cards,discards_left=2,**kw)
def test_hit_the_road_requires_discarded_jack():
    assert realize_bond(_dev(),_state("Hit the Road",[_c("9")])).realization==BondRealization.PARTIAL
def test_hit_the_road_live_on_discarded_jack():
    assert realize_bond(_dev(),_state("Hit the Road",[_c("J")])).realization==BondRealization.ACTIVE
def test_faceless_requires_three_face_cards():
    assert realize_bond(_dev(),_state("Faceless Joker",[_c("J"),_c("Q")])).realization==BondRealization.PARTIAL
def test_faceless_live_on_three_face_cards():
    assert realize_bond(_dev(),_state("Faceless Joker",[_c("J"),_c("Q"),_c("K")])).realization==BondRealization.ACTIVE
def test_mail_in_rebate_requires_current_target_rank():
    assert realize_bond(_dev(),_state("Mail-In Rebate",[_c("8")],mail_in_rebate_rank="7")).realization==BondRealization.PARTIAL
def test_mail_in_rebate_live_on_target_rank():
    assert realize_bond(_dev(),_state("Mail-In Rebate",[_c("7")],mail_in_rebate_rank="7")).realization==BondRealization.ACTIVE
def test_castle_requires_current_target_suit():
    assert realize_bond(_dev(),_state("Castle",[_c("4","Hearts")],castle_suit="Spades")).realization==BondRealization.PARTIAL
def test_castle_live_on_target_suit():
    assert realize_bond(_dev(),_state("Castle",[_c("4","Spades")],castle_suit="Spades")).realization==BondRealization.ACTIVE
def test_stone_hidden_jack_does_not_feed_hit_the_road():
    assert realize_bond(_dev(),_state("Hit the Road",[_c("J",stone=True)])).realization==BondRealization.PARTIAL
