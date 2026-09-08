from types import SimpleNamespace
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.realization import realize_bond

def _d(b):return BondDevelopment(bond_id=b,unlocked=True,contribution=22.0,rank=BondRank.R4,next_rank_threshold=30.0,contributions=(),realization=BondRealization.PARTIAL)
def _j(n):return SimpleNamespace(name=n)
def _c(r="2",debuffed=False):return SimpleNamespace(rank=r,suit="Hearts",enhancement="",debuffed=debuffed)
def test_dna_debuffed_single_card_is_not_live():
 s=SimpleNamespace(jokers=[_j("DNA")],cards_to_play=[_c(debuffed=True)],first_hand_available=True);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.PARTIAL
def test_dna_live_single_card_is_live():
 s=SimpleNamespace(jokers=[_j("DNA")],cards_to_play=[_c()],first_hand_available=True);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.ACTIVE
def test_dna_not_live_after_first_hand():
 s=SimpleNamespace(jokers=[_j("DNA")],cards_to_play=[_c()],first_hand_available=False);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.PARTIAL
def test_dna_not_live_with_two_cards():
 s=SimpleNamespace(jokers=[_j("DNA")],cards_to_play=[_c(),_c("3")],first_hand_available=True);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.PARTIAL
def test_certificate_live_at_blind_selection():
 s=SimpleNamespace(jokers=[_j("Certificate")],blind_selection_pending=True);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.ACTIVE
def test_certificate_not_live_mid_round():
 s=SimpleNamespace(jokers=[_j("Certificate")],blind_selection_pending=False);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.PARTIAL
def test_marble_live_at_blind_selection():
 s=SimpleNamespace(jokers=[_j("Marble Joker")],blind_selection_pending=True);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.ACTIVE
def test_marble_not_live_mid_round():
 s=SimpleNamespace(jokers=[_j("Marble Joker")],blind_selection_pending=False);assert realize_bond(_d("deck_growth"),s).realization==BondRealization.PARTIAL
def test_sixth_sense_debuffed_six_is_not_live_for_thinning():
 s=SimpleNamespace(jokers=[_j("Sixth Sense")],cards_to_play=[_c("6",True)],first_hand_available=True);assert realize_bond(_d("deck_thinning"),s).realization==BondRealization.PARTIAL
def test_sixth_sense_live_six_is_live_for_thinning():
 s=SimpleNamespace(jokers=[_j("Sixth Sense")],cards_to_play=[_c("6")],first_hand_available=True);assert realize_bond(_d("deck_thinning"),s).realization==BondRealization.ACTIVE
