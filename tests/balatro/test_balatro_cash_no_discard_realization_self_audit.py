from types import SimpleNamespace

from games.balatro.bonds import evaluate_cash_bond, evaluate_no_discard_bond
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2"):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement="")


def _state(*, jokers=(), hand=(), deck=(), money=0, discarded=0, **extra):
    return SimpleNamespace(
        jokers=list(jokers),
        hand=list(hand), current_hand=list(hand), cards_in_hand=list(hand),
        owned_deck=list(deck), deck=list(deck),
        money=money,
        discards_used_this_round=discarded,
        **extra,
    )


def _r4(dev):
    return BondDevelopment(
        bond_id=dev.bond_id,
        unlocked=True,
        contribution=max(dev.contribution, 22.0),
        rank=BondRank.R4,
        next_rank_threshold=None,
        contributions=dev.contributions,
        target=dev.target,
        realization=BondRealization.PARTIAL,
    )


def test_unrelated_second_joker_does_not_make_no_discard_mature():
    state = _state(jokers=[_joker("Green Joker"), _joker("Joker")])
    dev = _r4(evaluate_no_discard_bond(state))
    assert realize_bond(dev, state).realization == BondRealization.ACTIVE


def test_two_actual_no_discard_sources_can_make_mature():
    state = _state(jokers=[_joker("Green Joker"), _joker("Ramen")])
    dev = _r4(evaluate_no_discard_bond(state))
    assert realize_bond(dev, state).realization == BondRealization.MATURE


def test_reserved_parking_needs_held_face_card_to_realize_cash():
    no_face = _state(jokers=[_joker("Reserved Parking"), _joker("Golden Joker")], hand=[_card("7")])
    dev = evaluate_cash_bond(no_face)
    # Golden Joker establishes and realizes the Bond; Reserved Parking itself
    # should not count as a second live source without a held face card.
    out = realize_bond(_r4(dev), no_face)
    assert out.realization == BondRealization.ACTIVE

    with_face = _state(jokers=[_joker("Reserved Parking"), _joker("Golden Joker")], hand=[_card("K")])
    out2 = realize_bond(_r4(evaluate_cash_bond(with_face)), with_face)
    assert out2.realization == BondRealization.MATURE


def test_cloud_nine_needs_a_nine_in_deck_to_be_live():
    no_nines = _state(jokers=[_joker("Cloud 9"), _joker("Golden Joker")], deck=[_card("8") for _ in range(10)])
    assert realize_bond(_r4(evaluate_cash_bond(no_nines)), no_nines).realization == BondRealization.ACTIVE

    with_nine = _state(jokers=[_joker("Cloud 9"), _joker("Golden Joker")], deck=[_card("9"), _card("8")])
    assert realize_bond(_r4(evaluate_cash_bond(with_nine)), with_nine).realization == BondRealization.MATURE


def test_to_the_moon_needs_interest_eligible_bankroll():
    poor = _state(jokers=[_joker("To the Moon"), _joker("Golden Joker")], money=0)
    assert realize_bond(_r4(evaluate_cash_bond(poor)), poor).realization == BondRealization.ACTIVE

    funded = _state(jokers=[_joker("To the Moon"), _joker("Golden Joker")], money=5)
    assert realize_bond(_r4(evaluate_cash_bond(funded)), funded).realization == BondRealization.MATURE
