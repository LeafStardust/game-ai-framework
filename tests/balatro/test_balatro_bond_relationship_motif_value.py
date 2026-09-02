from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motif_value import evaluate_baron_mime_steel_motif, evaluate_motif_values
from games.balatro.bonds.relationships import (
    BondRelationship,
    RELATIONSHIP_DEFINITIONS,
    relationship_between,
    value_relationships,
)
from games.balatro.bonds.strategic_value import value_bond
from games.balatro.mechanics import HELD_KING_XMULT, RETRIGGER_HELD_CARDS


def _value(bond_id: str, points: float = 12.0):
    return value_bond(
        BondDevelopment(
            bond_id=bond_id,
            unlocked=True,
            contribution=points,
            rank=BondRank.R2,
            next_rank_threshold=None,
            contributions=(),
            realization=BondRealization.ACTIVE,
        )
    )


def _component(*mechanics: str):
    return SimpleNamespace(mechanics=frozenset(mechanics))


def _card(rank="K", enhancement="steel"):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def test_unlisted_relationship_pair_is_neutral_and_not_materialized():
    assert relationship_between("pair", "cash") == BondRelationship.NEUTRAL
    results = value_relationships((_value("pair"), _value("cash")))
    assert results == ()


def test_sparse_relationship_value_uses_coefficient_times_limiting_bond_value():
    held = _value("held_cards", 16.0)
    steel = _value("steel", 10.0)
    result = value_relationships((held, steel))

    assert len(result) == 1
    interaction = result[0]
    assert interaction.relationship == BondRelationship.SYNERGY
    assert interaction.limiting_value == min(held.value, steel.value)
    assert interaction.value == interaction.coefficient * interaction.limiting_value
    assert interaction.value > 0.0


def test_conflict_relationship_has_negative_value():
    discard = _value("discard")
    no_discard = _value("no_discard")
    interaction = value_relationships((discard, no_discard))[0]
    assert interaction.relationship == BondRelationship.CONFLICT
    assert interaction.coefficient < 0.0
    assert interaction.value < 0.0


def test_relationship_table_remains_sparse():
    assert len(RELATIONSHIP_DEFINITIONS) < 12
    assert all(definition.left != definition.right for definition in RELATIONSHIP_DEFINITIONS)


def test_isolated_baron_like_component_is_not_a_motif():
    state = SimpleNamespace(
        jokers=(_component(HELD_KING_XMULT),),
        owned_deck=(),
    )
    motif = evaluate_baron_mime_steel_motif(
        state,
        (_value("held_cards"), _value("held_retrigger"), _value("kings")),
    )
    assert motif.completion == 0.0
    assert motif.value == 0.0


def test_baron_mime_steel_kings_is_the_single_canonical_exceptional_motif():
    state = SimpleNamespace(
        jokers=(
            _component(HELD_KING_XMULT),
            _component(RETRIGGER_HELD_CARDS),
        ),
        owned_deck=(_card(), _card(), _card(rank="Q")),
    )
    bond_values = (
        _value("held_cards", 18.0),
        _value("held_retrigger", 15.0),
        _value("steel", 8.0),
        _value("kings", 14.0),
    )

    motifs = evaluate_motif_values(state, bond_values)
    assert len(motifs) == 1
    motif = motifs[0]
    assert motif.motif_id == "baron_mime_steel_kings"
    assert motif.completion == 1.0
    assert motif.estimated_payoff > 0.0
    assert motif.value == motif.estimated_payoff
    assert all(requirement.satisfied for requirement in motif.requirements)


def test_partial_exact_package_has_less_motif_value_than_completed_package():
    bond_values = (
        _value("held_cards", 18.0),
        _value("held_retrigger", 15.0),
        _value("steel", 8.0),
        _value("kings", 14.0),
    )
    partial = SimpleNamespace(
        jokers=(
            _component(HELD_KING_XMULT),
            _component(RETRIGGER_HELD_CARDS),
        ),
        owned_deck=(),
    )
    complete = SimpleNamespace(
        jokers=partial.jokers,
        owned_deck=(_card(), _card()),
    )

    partial_value = evaluate_baron_mime_steel_motif(partial, bond_values)
    complete_value = evaluate_baron_mime_steel_motif(complete, bond_values)
    assert partial_value.completion == 2 / 3
    assert 0.0 < partial_value.value < complete_value.value
