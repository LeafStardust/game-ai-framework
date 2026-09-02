from types import SimpleNamespace

from games.balatro.bonds.mechanical_patterns import (
    evaluate_deck_growth_bond,
    evaluate_flush_bond,
    evaluate_full_house_bond,
    evaluate_pair_bond,
    evaluate_played_retrigger_bond,
    evaluate_straight_bond,
)
from games.balatro.mechanics import (
    ADD_SEALED_CARD,
    CONTAINS_PAIR_MULT,
    CONTAINS_PAIR_XMULT,
    CONTAINS_THREE_XMULT,
    DUPLICATE_SELECTED_CARD,
    FLUSH_XMULT,
    FOUR_CARD_STRAIGHT_FLUSH,
    RETRIGGER_FIRST_SCORED,
    RETRIGGER_PLAYED_FACE,
    SCALE_ON_CARD_ADDED,
    STRAIGHT_GAP_RELAXATION,
    STRAIGHT_XMULT,
    SUIT_MERGE_RED_BLACK,
)


def component(*mechanics):
    return SimpleNamespace(name="arbitrary-component-name", mechanics=frozenset(mechanics))


def card(*, suit="Hearts", rank="7", enhancement="", seal=""):
    return SimpleNamespace(suit=suit, rank=rank, enhancement=enhancement, seal=seal)


def state(*, jokers=(), deck=(), hand_levels=None):
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=list(deck),
        deck=list(deck),
        deck_name="Red Deck",
        hand_levels=dict(hand_levels or {}),
    )


def test_pair_and_full_house_share_pair_mechanic_without_display_names():
    s = state(
        jokers=(component(CONTAINS_PAIR_XMULT), component(CONTAINS_PAIR_MULT), component(CONTAINS_THREE_XMULT)),
        hand_levels={"PAIR": 4, "FULL_HOUSE": 4},
    )
    pair = evaluate_pair_bond(s)
    full_house = evaluate_full_house_bond(s)
    assert pair.contribution == 13.0
    assert full_house.contribution == 7.0


def test_straight_uses_enabler_and_payoff_mechanics_without_display_names():
    s = state(
        jokers=(component(STRAIGHT_XMULT), component(STRAIGHT_GAP_RELAXATION), component(FOUR_CARD_STRAIGHT_FLUSH)),
        hand_levels={"STRAIGHT": 7},
    )
    dev = evaluate_straight_bond(s)
    assert dev.contribution == 19.0


def test_flush_uses_suit_merge_mechanic_for_density_without_display_names():
    deck = tuple(card(suit="Hearts") for _ in range(10)) + tuple(card(suit="Diamonds") for _ in range(10))
    s = state(jokers=(component(FLUSH_XMULT), component(SUIT_MERGE_RED_BLACK)), deck=deck)
    dev = evaluate_flush_bond(s)
    assert dev.contribution == 14.0


def test_played_retrigger_uses_generic_trigger_mechanics_without_display_names():
    s = state(
        jokers=(component(RETRIGGER_PLAYED_FACE), component(RETRIGGER_FIRST_SCORED)),
        deck=tuple(card(seal="Red") for _ in range(4)),
    )
    dev = evaluate_played_retrigger_bond(s)
    assert dev.contribution == 17.0


def test_deck_growth_uses_generation_mechanics_without_display_names():
    deck = tuple(card() for _ in range(60))
    s = state(
        jokers=(
            component(ADD_SEALED_CARD),
            component(DUPLICATE_SELECTED_CARD),
            component(SCALE_ON_CARD_ADDED),
        ),
        deck=deck,
    )
    dev = evaluate_deck_growth_bond(s)
    assert dev.contribution == 18.0
