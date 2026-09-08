from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_deck_thinning_bond,
    evaluate_two_pair_bond,
    evaluate_vampire_bond,
)


def _joker(name):
    return SimpleNamespace(name=name)


def _card(*, enhancement=""):
    return SimpleNamespace(enhancement=enhancement)


def _state(**kwargs):
    base = dict(
        jokers=[], owned_deck=[], deck=[], hand_levels={},
        vampire_enhancements_consumed=0,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_square_joker_is_two_pair_support_not_defining_authority():
    square = evaluate_two_pair_bond(_state(jokers=[_joker("Square Joker")]))
    assert square.contribution == 3.0
    assert square.rank == BondRank.R0
    combo = evaluate_two_pair_bond(_state(jokers=[_joker("Square Joker"), _joker("Spare Trousers")]))
    assert combo.contribution == 10.0
    assert combo.rank == BondRank.R2


def test_erosion_is_major_deck_thinning_payoff():
    erosion = evaluate_deck_thinning_bond(_state(jokers=[_joker("Erosion")], owned_deck=[_card() for _ in range(52)]))
    assert erosion.contribution == 7.0
    assert erosion.rank == BondRank.R2
    thinned = evaluate_deck_thinning_bond(_state(jokers=[_joker("Erosion")], owned_deck=[_card() for _ in range(34)]))
    assert thinned.contribution == 14.0
    assert thinned.rank == BondRank.R4


def test_enhancement_consumption_axis_tracks_feedstock_before_consumer_and_matures_with_vampire():
    feed_only = evaluate_vampire_bond(_state(owned_deck=[_card(enhancement="Mult") for _ in range(10)]))
    assert feed_only.rank >= BondRank.R1
    vampire = evaluate_vampire_bond(_state(jokers=[_joker("Vampire")]))
    assert vampire.contribution == 7.0
    assert vampire.rank == BondRank.R1
    fed = evaluate_vampire_bond(_state(
        jokers=[_joker("Vampire"), _joker("Midas Mask")],
        owned_deck=[_card(enhancement="Gold") for _ in range(10)],
        vampire_enhancements_consumed=15,
    ))
    assert fed.contribution == 23.0
    assert fed.rank == BondRank.R5
