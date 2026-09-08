from types import SimpleNamespace

from games.balatro.bonds.build_value import compose_build_value
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.motif_value import MotifRequirement, MotifValue
from games.balatro.bonds.relationships import BondRelationship, RelationshipValue
from games.balatro.bonds.strategic_value import value_bond


def _bond(bond_id: str, points: float):
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


def test_build_value_is_exact_sum_of_canonical_subtotals():
    bonds = (_bond("held_cards", 12.0), _bond("steel", 8.0))
    relationship = RelationshipValue(
        left="held_cards",
        right="steel",
        relationship=BondRelationship.SYNERGY,
        coefficient=0.2,
        left_value=bonds[0].value,
        right_value=bonds[1].value,
        limiting_value=min(bonds[0].value, bonds[1].value),
        value=0.2 * min(bonds[0].value, bonds[1].value),
    )
    motif = MotifValue(
        motif_id="baron_mime_steel_kings",
        requirements=(MotifRequirement("example", True, "example"),),
        completion=1.0,
        estimated_payoff=3.0,
        value=3.0,
        relevant_bonds=("held_cards", "steel"),
    )

    result = compose_build_value(bonds, (relationship,), (motif,))

    assert result.bond_total == sum(item.value for item in bonds)
    assert result.relationship_total == relationship.value
    assert result.motif_total == motif.value
    assert result.total == result.bond_total + result.relationship_total + result.motif_total


def test_build_value_preserves_explainable_diagnostics():
    bonds = (_bond("pair", 9.0), _bond("cash", 7.0))
    result = compose_build_value(bonds, (), ())

    assert result.bond_values is bonds
    assert result.relationship_values == ()
    assert result.motif_values == ()
    assert result.by_bond_id["pair"] is bonds[0]
    assert result.by_bond_id["cash"] is bonds[1]


def test_build_value_does_not_need_action_or_strategy_identity_inputs():
    bonds = (_bond("pair", 6.0),)
    result = compose_build_value(bonds, (), ())

    assert result.total == bonds[0].value
    assert not hasattr(result, "strategy")
    assert not hasattr(result, "action")
    assert not hasattr(result, "prescriptions")
