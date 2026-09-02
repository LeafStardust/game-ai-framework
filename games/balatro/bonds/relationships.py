from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from games.balatro.bonds.strategic_value import BondStrategicValue


class BondRelationship(StrEnum):
    NEUTRAL = "NEUTRAL"
    SYNERGY = "SYNERGY"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class RelationshipDefinition:
    left: str
    right: str
    relationship: BondRelationship
    coefficient: float

    @property
    def key(self) -> frozenset[str]:
        return frozenset((self.left, self.right))


@dataclass(frozen=True)
class RelationshipValue:
    left: str
    right: str
    relationship: BondRelationship
    coefficient: float
    left_value: float
    right_value: float
    limiting_value: float
    value: float


# Sparse by design. These express interactions not already captured by the
# individual Bond values. Coefficients are deliberately conservative until live
# tuning; unlisted pairs are neutral.
RELATIONSHIP_DEFINITIONS: tuple[RelationshipDefinition, ...] = (
    RelationshipDefinition("held_cards", "steel", BondRelationship.SYNERGY, 0.20),
    RelationshipDefinition("held_cards", "held_retrigger", BondRelationship.SYNERGY, 0.20),
    RelationshipDefinition("steel", "held_retrigger", BondRelationship.SYNERGY, 0.25),
    RelationshipDefinition("card_destruction", "deck_thinning", BondRelationship.SYNERGY, 0.20),
    RelationshipDefinition("discard", "no_discard", BondRelationship.CONFLICT, -0.25),
    RelationshipDefinition("face_cards", "no_face_cards", BondRelationship.CONFLICT, -0.25),
    RelationshipDefinition("enhancement_consumption", "enhanced_cards", BondRelationship.CONFLICT, -0.15),
)

_DEFINITIONS_BY_KEY = {definition.key: definition for definition in RELATIONSHIP_DEFINITIONS}

# Compatibility surface for existing callers that only need relationship kind.
RELATIONSHIPS: dict[frozenset[str], BondRelationship] = {
    key: definition.relationship for key, definition in _DEFINITIONS_BY_KEY.items()
}


def relationship_between(left: str, right: str) -> BondRelationship:
    if left == right:
        return BondRelationship.NEUTRAL
    definition = _DEFINITIONS_BY_KEY.get(frozenset((left, right)))
    return definition.relationship if definition is not None else BondRelationship.NEUTRAL


def relationship_definition(left: str, right: str) -> RelationshipDefinition | None:
    if left == right:
        return None
    return _DEFINITIONS_BY_KEY.get(frozenset((left, right)))


def value_relationships(values: Iterable[BondStrategicValue]) -> tuple[RelationshipValue, ...]:
    """Value only explicitly listed Bond relationships.

    RelationshipValue = coefficient * min(BondValueA, BondValueB).
    Zero-valued sides produce zero interaction value; unlisted pairs are never
    materialized, keeping the relationship layer intentionally sparse.
    """
    by_id = {item.bond_id: item for item in values}
    results: list[RelationshipValue] = []
    for definition in RELATIONSHIP_DEFINITIONS:
        left = by_id.get(definition.left)
        right = by_id.get(definition.right)
        if left is None or right is None:
            continue
        limiting = min(max(0.0, left.value), max(0.0, right.value))
        results.append(
            RelationshipValue(
                left=definition.left,
                right=definition.right,
                relationship=definition.relationship,
                coefficient=definition.coefficient,
                left_value=left.value,
                right_value=right.value,
                limiting_value=limiting,
                value=definition.coefficient * limiting,
            )
        )
    return tuple(results)


def conflicts_with_any(bond_id: str, others: set[str]) -> bool:
    return any(relationship_between(bond_id, other) == BondRelationship.CONFLICT for other in others)


def synergies_with(bond_id: str, others: set[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            other
            for other in others
            if relationship_between(bond_id, other) == BondRelationship.SYNERGY
        )
    )
