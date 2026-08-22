from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _dev():return BondDevelopment(bond_id="hand_repetition",unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(name):return SimpleNamespace(name=name)
def test_supernova_ownership_without_current_play_is_not_live():
 s=SimpleNamespace(jokers=[_j("Supernova")],current_hand_type="Pair",hand_play_counts={"PAIR":4},scoring_cards=[]);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
def test_supernova_is_live_on_current_play():
 s=SimpleNamespace(jokers=[_j("Supernova")],current_hand_type="Pair",hand_play_counts={"PAIR":4},scoring_cards=[SimpleNamespace(rank="2")]);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
def test_card_sharp_first_play_of_hand_type_is_not_repetition():
 s=SimpleNamespace(jokers=[_j("Card Sharp")],current_hand_type="Pair",hand_play_counts={"PAIR":1},scoring_cards=[SimpleNamespace(rank="2")]);assert realize_bond(_dev(),s).realization==BondRealization.PARTIAL
def test_card_sharp_second_play_of_hand_type_is_live():
 s=SimpleNamespace(jokers=[_j("Card Sharp")],current_hand_type="Pair",hand_play_counts={"PAIR":2},scoring_cards=[SimpleNamespace(rank="2")]);assert realize_bond(_dev(),s).realization==BondRealization.ACTIVE
