from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev(b): return BondDevelopment(bond_id=b,unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(n): return SimpleNamespace(name=n)
def _c(rank="7"): return SimpleNamespace(rank=rank,suit="Hearts",enhancement="",debuffed=False)

def test_bull_is_live_at_zero_dollars_while_scoring():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("Bull")],money=0,scoring_cards=[_c()])).realization==BondRealization.ACTIVE

def test_bootstraps_not_live_below_five_dollars():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("Bootstraps")],money=4,scoring_cards=[_c()])).realization==BondRealization.PARTIAL

def test_bootstraps_live_at_five_dollars():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("Bootstraps")],money=5,scoring_cards=[_c()])).realization==BondRealization.ACTIVE

def test_to_the_moon_not_live_below_interest_threshold():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("To the Moon")],money=4,hands_left=0)).realization==BondRealization.PARTIAL

def test_to_the_moon_live_at_interest_threshold():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("To the Moon")],money=5,hands_left=0)).realization==BondRealization.ACTIVE

def test_rocket_not_live_during_scoring():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("Rocket")],scoring_cards=[_c()],hands_left=2)).realization==BondRealization.PARTIAL

def test_rocket_live_at_round_end():
 assert realize_bond(_dev("cash"),SimpleNamespace(jokers=[_j("Rocket")],hands_left=0)).realization==BondRealization.ACTIVE

def test_green_joker_still_live_after_discard_when_scoring():
 assert realize_bond(_dev("no_discard"),SimpleNamespace(jokers=[_j("Green Joker")],discards_used_this_round=1,scoring_cards=[_c()])).realization==BondRealization.ACTIVE

def test_ramen_live_after_discard_when_still_owned_and_scoring():
 assert realize_bond(_dev("no_discard"),SimpleNamespace(jokers=[_j("Ramen")],discards_used_this_round=1,scoring_cards=[_c()])).realization==BondRealization.ACTIVE

def test_delayed_gratification_dead_at_round_end_after_discard():
 assert realize_bond(_dev("no_discard"),SimpleNamespace(jokers=[_j("Delayed Gratification")],discards_used_this_round=1,hands_left=0)).realization==BondRealization.PARTIAL

def test_banner_not_live_without_remaining_discards():
 assert realize_bond(_dev("no_discard"),SimpleNamespace(jokers=[_j("Banner")],discards_left=0,scoring_cards=[_c()])).realization==BondRealization.PARTIAL

def test_burglar_does_not_need_zero_discard_history_at_blind_selection():
 assert realize_bond(_dev("no_discard"),SimpleNamespace(jokers=[_j("Burglar")],blind_selection_pending=True,discards_used_this_round=3)).realization==BondRealization.ACTIVE
