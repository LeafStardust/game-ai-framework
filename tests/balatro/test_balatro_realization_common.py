from types import SimpleNamespace

from games.balatro.bonds import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization_common import realize_common_family


def card(rank="", suit="", seal="", enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, seal=seal, enhancement=enhancement)


def dev(bond_id, rank=BondRank.R3):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=15.0, rank=rank, next_rank_threshold=None, contributions=())


def state(**kwargs):
    base = dict(jokers=[], hand=[], owned_deck=[])
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_hand_bond_requires_currently_available_shape():
    pair = realize_common_family(dev("pair"), state(hand=[card("A"), card("A"), card("7")]))
    miss = realize_common_family(dev("pair"), state(hand=[card("A"), card("K"), card("7")]))
    assert pair.realization == BondRealization.ACTIVE
    assert miss.realization == BondRealization.PARTIAL


def test_straight_and_flush_use_actual_current_hand_shape():
    straight = realize_common_family(dev("straight"), state(hand=[card("2","hearts"),card("3","clubs"),card("4","spades"),card("5","diamonds"),card("6","hearts")]))
    flush = realize_common_family(dev("flush"), state(hand=[card("2","hearts"),card("4","hearts"),card("7","hearts"),card("9","hearts"),card("K","hearts")]))
    assert straight.realization == BondRealization.ACTIVE
    assert flush.realization == BondRealization.ACTIVE


def test_mature_hand_bond_requires_high_rank_and_repeatability_evidence():
    out = realize_common_family(dev("two_pair", BondRank.R4), state(hand=[card("A"),card("A"),card("K"),card("K")], hand_consistency_high=True))
    assert out.realization == BondRealization.MATURE


def test_played_retrigger_respects_joker_specific_targets():
    hack = realize_common_family(dev("played_retrigger"), state(jokers=["Hack"], selected_cards=[card("2"),card("3")]))
    miss = realize_common_family(dev("played_retrigger"), state(jokers=["Hack"], selected_cards=[card("K"),card("Q")]))
    assert hack.realization == BondRealization.ACTIVE
    assert miss.realization == BondRealization.PARTIAL


def test_red_seal_can_realize_played_retrigger_without_joker():
    out = realize_common_family(dev("played_retrigger"), state(selected_cards=[card("A", seal="red")]))
    assert out.realization == BondRealization.ACTIVE


def test_deck_thinning_needs_actual_reduction():
    full = realize_common_family(dev("deck_thinning"), state(jokers=["Erosion"], owned_deck=[card() for _ in range(52)]))
    thin = realize_common_family(dev("deck_thinning"), state(jokers=["Erosion"], owned_deck=[card() for _ in range(40)]))
    assert full.realization == BondRealization.PARTIAL
    assert thin.realization == BondRealization.ACTIVE


def test_deck_growth_needs_actual_growth():
    base = realize_common_family(dev("deck_growth"), state(jokers=["Hologram"], owned_deck=[card() for _ in range(52)]))
    grown = realize_common_family(dev("deck_growth"), state(jokers=["Hologram"], owned_deck=[card() for _ in range(60)]))
    assert base.realization == BondRealization.PARTIAL
    assert grown.realization == BondRealization.ACTIVE


def test_realization_never_changes_rank_or_contribution():
    original = dev("four_kind", BondRank.R4)
    out = realize_common_family(original, state(hand=[card("9"),card("9"),card("9"),card("9")]))
    assert out.rank == original.rank
    assert out.contribution == original.contribution
