from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _d():return BondDevelopment(bond_id="gold_economy",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(n):return SimpleNamespace(name=n)
def _c(rank="7",enh="",debuffed=False):return SimpleNamespace(rank=rank,suit="Hearts",enhancement=enh,debuffed=debuffed)
def test_held_gold_not_live_mid_round():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold")],hands_left=2)).realization==BondRealization.PARTIAL
def test_held_gold_live_at_round_end():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold")],hands_left=0)).realization==BondRealization.ACTIVE
def test_debuffed_held_gold_not_live_at_round_end():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold",debuffed=True)],hands_left=0)).realization==BondRealization.PARTIAL
def test_golden_ticket_requires_scoring_window():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Golden Ticket")],scoring_cards=[],hand=[],hands_left=2)).realization==BondRealization.PARTIAL
def test_golden_ticket_live_on_scored_gold():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Golden Ticket")],scoring_cards=[_c(enh="Gold")],hands_left=2)).realization==BondRealization.ACTIVE
def test_midas_requires_scoring_window():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Midas Mask")],scoring_cards=[],hand=[_c("K")])).realization==BondRealization.PARTIAL
def test_midas_live_on_scored_face():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Midas Mask")],scoring_cards=[_c("K")])).realization==BondRealization.ACTIVE
def test_reserved_parking_requires_hand_play_window():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[])).realization==BondRealization.PARTIAL
def test_reserved_parking_live_after_hand_play_with_held_face():
 assert realize_bond(_d(),SimpleNamespace(jokers=[_j("Reserved Parking")],hand=[_c("K")],scoring_cards=[_c("2")])).realization==BondRealization.ACTIVE
def test_three_held_gold_cards_mature_only_at_round_end():
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold"),_c(enh="Gold"),_c(enh="Gold")],hands_left=2)).realization==BondRealization.PARTIAL
 assert realize_bond(_d(),SimpleNamespace(jokers=[],hand=[_c(enh="Gold"),_c(enh="Gold"),_c(enh="Gold")],hands_left=0)).realization==BondRealization.MATURE
