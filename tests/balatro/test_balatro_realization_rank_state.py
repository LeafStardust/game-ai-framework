from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization_rank_state import (
    realize_aces, realize_face_cards, realize_low_ranks, realize_jacks,
    realize_no_face_cards, realize_hearts, realize_lucky, realize_glass,
    realize_stone, realize_gold_economy,
)


def card(rank="", suit="", enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement)


def dev(bond_id, rank=BondRank.R2):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=10.0, rank=rank, next_rank_threshold=13.0, contributions=())


def state(**kwargs):
    base = dict(jokers=[], scoring_cards=[], played_cards=[], discarded_cards=[], hand=[])
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_rank_payoffs_require_matching_current_cards():
    assert realize_aces(dev("aces"), state(jokers=["Scholar"], scoring_cards=[card("A")])).realization == BondRealization.ACTIVE
    assert realize_aces(dev("aces"), state(jokers=["Scholar"], scoring_cards=[card("K")])).realization == BondRealization.PARTIAL
    assert realize_face_cards(dev("face_cards"), state(jokers=["Photograph"], scoring_cards=[card("K")])).realization == BondRealization.ACTIVE
    assert realize_low_ranks(dev("low_ranks"), state(jokers=["Hack"], scoring_cards=[card("4")])).realization == BondRealization.ACTIVE


def test_hit_the_road_uses_discarded_jacks_not_scored_jacks():
    d = dev("jacks")
    assert realize_jacks(d, state(jokers=["Hit the Road"], scoring_cards=[card("J")])).realization == BondRealization.PARTIAL
    assert realize_jacks(d, state(jokers=["Hit the Road"], discarded_cards=[card("J")])).realization == BondRealization.ACTIVE


def test_no_face_cards_requires_current_safe_play():
    d = dev("no_face_cards")
    assert realize_no_face_cards(d, state(jokers=["Ride the Bus"], scoring_cards=[card("7"), card("9")])).realization == BondRealization.ACTIVE
    assert realize_no_face_cards(d, state(jokers=["Ride the Bus"], scoring_cards=[card("Q")])).realization == BondRealization.PARTIAL


def test_suit_realization_requires_matching_suit_and_payoff():
    d = dev("hearts")
    assert realize_hearts(d, state(jokers=["Bloodstone"], scoring_cards=[card("7", "Hearts")])).realization == BondRealization.ACTIVE
    assert realize_hearts(d, state(jokers=["Bloodstone"], scoring_cards=[card("7", "Spades")])).realization == BondRealization.PARTIAL


def test_enhancement_realization_uses_actual_current_cards():
    assert realize_lucky(dev("lucky"), state(scoring_cards=[card("7", enhancement="Lucky")])).realization == BondRealization.ACTIVE
    assert realize_glass(dev("glass"), state(scoring_cards=[card("7", enhancement="Glass")])).realization == BondRealization.ACTIVE
    assert realize_stone(dev("stone"), state(scoring_cards=[card(enhancement="Stone")])).realization == BondRealization.ACTIVE
    assert realize_gold_economy(dev("gold_economy"), state(hand=[card("K", enhancement="Gold")])).realization == BondRealization.ACTIVE


def test_realization_preserves_rank_and_contribution():
    original = dev("aces", BondRank.R4)
    realized = realize_aces(original, state(jokers=["Scholar"], scoring_cards=[card("A"), card("A"), card("A")]))
    assert realized.rank == original.rank
    assert realized.contribution == original.contribution
    assert realized.realization == BondRealization.MATURE
