from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _d():return BondDevelopment(bond_id="gold_cards",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(n):return SimpleNamespace(name=n)
def _c(rank="7",enh="",debuffed=False):return SimpleNamespace(rank=rank,suit="Hearts",enhancement=enh,debuffed=debuffed)
def test_held_gold_is_live_mid_round_as_available_end_of_round_payoff():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold")],hands_left=2)).realization==BondRealization.ACTIVE
def test_held_gold_stays_live_at_round_end():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold")],hands_left=0)).realization==BondRealization.ACTIVE
def test_debuffed_held_gold_not_live():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold",debuffed=True)],hands_left=0)).realization==BondRealization.PARTIAL
def test_golden_ticket_requires_scoring_gold():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Golden Ticket")],scoring_cards=[],hand=[],hands_left=2)).realization==BondRealization.PARTIAL
def test_golden_ticket_live_on_scored_gold():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Golden Ticket")],scoring_cards=[_c(enh="Gold")],hands_left=2)).realization==BondRealization.ACTIVE
def test_midas_requires_scoring_face():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Midas Mask")],scoring_cards=[],hand=[_c("K")])).realization==BondRealization.PARTIAL
def test_midas_live_on_scored_face():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Midas Mask")],scoring_cards=[_c("K")])).realization==BondRealization.ACTIVE
def test_reserved_parking_live_when_held_face_opportunity_exists():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[])).realization==BondRealization.ACTIVE
def test_reserved_parking_remains_live_during_scoring_with_held_face():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[_c("2")])).realization==BondRealization.ACTIVE
def test_three_held_gold_cards_are_mature_available_payoff():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold"),_c(enh="Gold"),_c(enh="Gold")],hands_left=2)).realization==BondRealization.MATURE
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold"),_c(enh="Gold"),_c(enh="Gold")],hands_left=0)).realization==BondRealization.MATURE
