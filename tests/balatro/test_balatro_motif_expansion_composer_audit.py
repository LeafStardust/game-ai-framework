from types import SimpleNamespace

from games.balatro.bonds.composer import compose_build
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization
from games.balatro.bonds.motifs import MotifState,evaluate_motifs


def dev(bond_id,rank=BondRank.R3,realization=BondRealization.ACTIVE,target=None):
    return BondDevelopment(bond_id,True,10.0,rank,None,(),target=target,realization=realization)


def card(rank="",suit="Hearts",enhancement=""):
    return SimpleNamespace(rank=rank,suit=suit,enhancement=enhancement)


def test_photo_chad_requires_both_jokers_and_face_infrastructure():
    state=SimpleNamespace(jokers=["Photograph","Hanging Chad"],owned_deck=[card("K") for _ in range(8)])
    motifs={m.motif_id:m for m in evaluate_motifs(state,[dev("face_cards"),dev("played_retrigger")])}
    assert motifs["photograph_hanging_chad"].state==MotifState.ACTIVE


def test_vampire_midas_is_distinct_motif():
    state=SimpleNamespace(jokers=["Vampire","Midas Mask"],owned_deck=[card("K",enhancement="gold") for _ in range(3)])
    motifs={m.motif_id:m for m in evaluate_motifs(state,[dev("vampire")])}
    assert motifs["vampire_midas"].state==MotifState.ACTIVE


def test_composer_exposes_motif_distance():
    state=SimpleNamespace(jokers=["Photograph"],owned_deck=[card("K") for _ in range(8)])
    comp=compose_build(state,[dev("face_cards",BondRank.R4),dev("played_retrigger",BondRank.R2)])
    distances=dict(comp.motif_distance)
    assert distances["photograph_hanging_chad"]==1


def test_composer_deduplicates_relationship_accounting():
    state=SimpleNamespace(jokers=[],owned_deck=[])
    comp=compose_build(state,[dev("held_cards"),dev("held_retrigger"),dev("steel")])
    assert len(comp.synergies)==len(set(comp.synergies))
