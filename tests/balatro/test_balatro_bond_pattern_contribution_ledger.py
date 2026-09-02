from types import SimpleNamespace

from games.balatro.bonds.mechanical_patterns import (
    evaluate_pair_bond,
    evaluate_two_pair_bond,
)
from games.balatro.mechanics import (
    CONTAINS_PAIR_MULT,
    CONTAINS_PAIR_XMULT,
    TWO_PAIR_SCALING,
)


def _component(*mechanics):
    return SimpleNamespace(name="arbitrary-component", mechanics=frozenset(mechanics))


def _state(*jokers):
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=[],
        deck=[],
        hand_levels={"PAIR": 1, "TWO_PAIR": 1},
        deck_name="Red Deck",
    )


def test_pair_deduplicates_overlapping_mechanics_from_one_component():
    source = _component(CONTAINS_PAIR_XMULT, CONTAINS_PAIR_MULT)
    development = evaluate_pair_bond(_state(source))

    assert development.contribution == 6.0
    assert len(development.contributions) == 1
    contribution = development.contributions[0]
    assert contribution.source_id == "jokers:slot:0"
    assert "mechanic:contains_pair_xmult" in contribution.conditions
    assert "mechanic:contains_pair_mult" in contribution.conditions


def test_same_component_may_support_pair_and_two_pair_independently():
    source = _component(CONTAINS_PAIR_MULT, TWO_PAIR_SCALING)
    state = _state(source)

    pair = evaluate_pair_bond(state)
    two_pair = evaluate_two_pair_bond(state)

    assert pair.contribution == 4.0
    assert two_pair.contribution == 7.0
    assert pair.contributions[0].source_id == "jokers:slot:0"
    assert two_pair.contributions[0].source_id == "jokers:slot:0"
