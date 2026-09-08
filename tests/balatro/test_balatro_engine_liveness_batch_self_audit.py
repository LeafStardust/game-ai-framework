from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _j(name):
    return SimpleNamespace(name=name)


def _c(rank="7", debuffed=False):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement="", debuffed=debuffed)


def test_bull_requires_scoring_window():
    assert realize_bond(_dev("cash"), SimpleNamespace(jokers=[_j("Bull")], money=50, scoring_cards=[])).realization == BondRealization.PARTIAL


def test_bull_live_while_scoring_with_money():
    state = SimpleNamespace(jokers=[_j("Bull")], money=50, scoring_cards=[_c()])
    assert realize_bond(_dev("cash"), state).realization == BondRealization.ACTIVE


def test_golden_joker_requires_round_end_window():
    assert realize_bond(_dev("cash"), SimpleNamespace(jokers=[_j("Golden Joker")], hands_left=2)).realization == BondRealization.PARTIAL


def test_golden_joker_live_at_round_end():
    assert realize_bond(_dev("cash"), SimpleNamespace(jokers=[_j("Golden Joker")], hands_left=0)).realization == BondRealization.ACTIVE


def test_cloud_nine_requires_round_end_even_with_nine_in_deck():
    state = SimpleNamespace(jokers=[_j("Cloud 9")], deck=[_c("9")], hands_left=2)
    assert realize_bond(_dev("cash"), state).realization == BondRealization.PARTIAL


def test_cloud_nine_live_at_round_end_with_nine_in_deck():
    state = SimpleNamespace(jokers=[_j("Cloud 9")], deck=[_c("9")], hands_left=0)
    assert realize_bond(_dev("cash"), state).realization == BondRealization.ACTIVE


def test_satellite_unknown_planet_history_is_not_assumed_live():
    state = SimpleNamespace(jokers=[_j("Satellite")], hands_left=0)
    assert realize_bond(_dev("cash"), state).realization == BondRealization.PARTIAL


def test_satellite_live_at_round_end_with_planet_history():
    state = SimpleNamespace(jokers=[_j("Satellite")], hands_left=0, unique_planets_used=3)
    assert realize_bond(_dev("cash"), state).realization == BondRealization.ACTIVE


def test_reserved_parking_requires_scoring_window():
    state = SimpleNamespace(jokers=[_j("Reserved Parking")], hand=[_c("K")], scoring_cards=[])
    assert realize_bond(_dev("cash"), state).realization == BondRealization.PARTIAL


def test_reserved_parking_live_while_scoring_with_held_face():
    state = SimpleNamespace(jokers=[_j("Reserved Parking")], hand=[_c("K")], scoring_cards=[_c("2")])
    assert realize_bond(_dev("cash"), state).realization == BondRealization.ACTIVE


def test_green_joker_requires_played_hand():
    state = SimpleNamespace(jokers=[_j("Green Joker")], discards_used_this_round=0, scoring_cards=[])
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.PARTIAL


def test_green_joker_live_on_played_hand():
    state = SimpleNamespace(jokers=[_j("Green Joker")], discards_used_this_round=0, scoring_cards=[_c()])
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.ACTIVE


def test_burglar_requires_blind_selection_window():
    state = SimpleNamespace(jokers=[_j("Burglar")], blind_selection_pending=False)
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.PARTIAL


def test_burglar_live_at_blind_selection():
    state = SimpleNamespace(jokers=[_j("Burglar")], blind_selection_pending=True)
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.ACTIVE


def test_delayed_gratification_requires_round_end_and_zero_discards():
    state = SimpleNamespace(jokers=[_j("Delayed Gratification")], hands_left=2, discards_used_this_round=0)
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.PARTIAL


def test_delayed_gratification_live_at_round_end_after_no_discards():
    state = SimpleNamespace(jokers=[_j("Delayed Gratification")], hands_left=0, discards_used_this_round=0)
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.ACTIVE


def test_banner_requires_scoring_and_remaining_discard():
    state = SimpleNamespace(jokers=[_j("Banner")], scoring_cards=[_c()], discards_left=0)
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.PARTIAL


def test_banner_live_while_scoring_with_remaining_discard():
    state = SimpleNamespace(jokers=[_j("Banner")], scoring_cards=[_c()], discards_left=2)
    assert realize_bond(_dev("no_discard"), state).realization == BondRealization.ACTIVE
