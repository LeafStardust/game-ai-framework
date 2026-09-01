from __future__ import annotations

from enum import StrEnum


class BondRelationship(StrEnum):
    NEUTRAL = "NEUTRAL"
    SYNERGY = "SYNERGY"
    CONFLICT = "CONFLICT"


RELATIONSHIPS: dict[frozenset[str], BondRelationship] = {
    frozenset(("discard", "no_discard")): BondRelationship.CONFLICT,
    frozenset(("face_cards", "no_face_cards")): BondRelationship.CONFLICT,
    frozenset(("enhancement_consumption", "enhanced_cards")): BondRelationship.CONFLICT,
    frozenset(("held_cards", "steel")): BondRelationship.SYNERGY,
    frozenset(("held_retrigger", "steel")): BondRelationship.SYNERGY,
    frozenset(("card_destruction", "deck_thinning")): BondRelationship.SYNERGY,
}


def relationship_between(left: str, right: str) -> BondRelationship:
    if left == right:
        return BondRelationship.NEUTRAL
    return RELATIONSHIPS.get(frozenset((left, right)), BondRelationship.NEUTRAL)


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
