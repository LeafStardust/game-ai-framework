from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=22.0, rank=BondRank.R4, next_rank_threshold=30.0, contributions=(), realization=BondRealization.PARTIAL)


def _j(name, **kw):
    return SimpleNamespace(name=name, **kw)


def _c(rank="7", suit="Hearts", enhancement="", seal="", debuffed=False, **kw):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal=seal, debuffed=debuffed, **kw)


def test_pareidolia_itself_realizes_face_card_specialization_on_live_scoring_card():
    s = SimpleNamespace(jokers=[_j("Pareidolia")], scoring_cards=[_c("2")])
    assert realize_bond(_dev("face_cards"), s).realization == BondRealization.ACTIVE


def test_ride_the_bus_with_pareidolia_ignores_only_debuffed_scoring_cards():
    s = SimpleNamespace(jokers=[_j("Ride the Bus"), _j("Pareidolia")], scoring_cards=[_c("2", debuffed=True)])
    assert realize_bond(_dev("no_face_cards"), s).realization == BondRealization.ACTIVE


def test_ride_the_bus_with_pareidolia_is_blocked_by_any_live_scoring_card():
    s = SimpleNamespace(jokers=[_j("Ride the Bus"), _j("Pareidolia")], scoring_cards=[_c("2")])
    assert realize_bond(_dev("no_face_cards"), s).realization == BondRealization.PARTIAL


def test_raised_fist_debuffed_lowest_card_is_still_selected_and_yields_no_payoff():
    s = SimpleNamespace(jokers=[_j("Raised Fist")], hand=[_c("2", debuffed=True), _c("5")])
    assert realize_bond(_dev("held_cards"), s).realization == BondRealization.PARTIAL


def test_raised_fist_rightmost_tied_lowest_debuffed_card_blocks_live_left_tie():
    s = SimpleNamespace(jokers=[_j("Raised Fist")], hand=[_c("3"), _c("3", debuffed=True), _c("7")])
    assert realize_bond(_dev("held_cards"), s).realization == BondRealization.PARTIAL


def test_blackboard_accepts_debuffed_base_spade():
    s = SimpleNamespace(jokers=[_j("Blackboard")], hand=[_c("7", suit="Spades", debuffed=True)])
    assert realize_bond(_dev("held_cards"), s).realization == BondRealization.ACTIVE


def test_blackboard_debuffed_wild_reverts_to_base_red_suit_and_blocks():
    s = SimpleNamespace(jokers=[_j("Blackboard")], hand=[_c("7", suit="Hearts", enhancement="Wild", debuffed=True)])
    assert realize_bond(_dev("held_cards"), s).realization == BondRealization.PARTIAL


def test_ceremonial_dagger_is_not_live_mid_round_even_with_destroyable_right_neighbor():
    s = SimpleNamespace(jokers=[_j("Ceremonial Dagger"), _j("Joker")], blind_selection_pending=False)
    assert realize_bond(_dev("joker_sacrifice"), s).realization == BondRealization.PARTIAL


def test_ceremonial_dagger_is_live_at_blind_selection_with_destroyable_right_neighbor():
    s = SimpleNamespace(jokers=[_j("Ceremonial Dagger"), _j("Joker")], blind_selection_pending=True)
    assert realize_bond(_dev("joker_sacrifice"), s).realization == BondRealization.ACTIVE


def test_canio_does_not_realize_from_generic_nonface_destruction_counter():
    s = SimpleNamespace(jokers=[_j("Canio")], cards_destroyed=3)
    assert realize_bond(_dev("card_destruction"), s).realization == BondRealization.PARTIAL


def test_canio_realizes_from_explicit_face_card_destruction():
    s = SimpleNamespace(jokers=[_j("Canio")], face_cards_destroyed=1)
    assert realize_bond(_dev("card_destruction"), s).realization == BondRealization.ACTIVE


def test_canio_destroyed_card_event_checks_face_identity():
    s = SimpleNamespace(jokers=[_j("Canio")], destroyed_cards=[_c("K")])
    assert realize_bond(_dev("card_destruction"), s).realization == BondRealization.ACTIVE


def test_canio_destroyed_nonface_event_is_not_live():
    s = SimpleNamespace(jokers=[_j("Canio")], destroyed_cards=[_c("2")])
    assert realize_bond(_dev("card_destruction"), s).realization == BondRealization.PARTIAL


def test_canio_pareidolia_makes_destroyed_live_number_card_a_face():
    s = SimpleNamespace(jokers=[_j("Canio"), _j("Pareidolia")], destroyed_cards=[_c("2")])
    assert realize_bond(_dev("card_destruction"), s).realization == BondRealization.ACTIVE


def test_four_fingers_straight_flush_cannot_combine_disjoint_subsets_across_eight_cards():
    hand = [
        _c("2", "Hearts"), _c("3", "Diamonds"), _c("4", "Clubs"), _c("5", "Spades"),
        _c("8", "Hearts"), _c("9", "Hearts"), _c("J", "Hearts"), _c("K", "Hearts"),
    ]
    s = SimpleNamespace(jokers=[_j("Four Fingers")], hand=hand)
    assert realize_bond(_dev("straight_flush"), s).realization == BondRealization.PARTIAL


def test_four_fingers_straight_flush_allows_different_subsets_within_same_five_cards():
    hand = [_c("2", "Hearts"), _c("3", "Hearts"), _c("4", "Hearts"), _c("5", "Spades"), _c("9", "Hearts")]
    s = SimpleNamespace(jokers=[_j("Four Fingers")], hand=hand)
    assert realize_bond(_dev("straight_flush"), s).realization == BondRealization.MATURE
