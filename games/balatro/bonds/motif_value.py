from __future__ import annotations

"""Canonical value for exceptional super-additive Balatro packages.

Motifs are intentionally rare. Ordinary compatibility belongs in Bond
contributions or sparse pair relationships. This module carries no action
prescriptions and does not create a strategy identity.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from games.balatro.bonds.strategic_value import BondStrategicValue
from games.balatro.mechanics import HELD_KING_XMULT, RETRIGGER_HELD_CARDS, component_has_mechanic


@dataclass(frozen=True)
class MotifRequirement:
    requirement_id: str
    satisfied: bool
    evidence: str


@dataclass(frozen=True)
class MotifValue:
    motif_id: str
    requirements: tuple[MotifRequirement, ...]
    completion: float
    estimated_payoff: float
    value: float
    relevant_bonds: tuple[str, ...]


BARON_MIME_STEEL_BONDS = ("held_cards", "held_retrigger", "steel", "kings")
BARON_MIME_STEEL_PAYOFF_COEFFICIENT = 0.50


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned or ())
    return list(getattr(state, "deck", ()) or ())


def _is_steel_king(card: Any) -> bool:
    return (
        str(getattr(card, "rank", "") or "").upper() == "K"
        and str(getattr(card, "enhancement", "") or "").strip().lower() == "steel"
    )


def _positive_value(by_id: dict[str, BondStrategicValue], bond_id: str) -> float:
    item = by_id.get(bond_id)
    return max(0.0, item.value) if item is not None else 0.0


def evaluate_baron_mime_steel_motif(
    state: Any,
    bond_values: Iterable[BondStrategicValue],
) -> MotifValue:
    jokers = list(getattr(state, "jokers", ()) or ())
    steel_kings = sum(1 for card in _deck(state) if _is_steel_king(card))
    has_baron = any(component_has_mechanic(joker, HELD_KING_XMULT) for joker in jokers)
    has_mime = any(component_has_mechanic(joker, RETRIGGER_HELD_CARDS) for joker in jokers)

    requirements = (
        MotifRequirement("held_king_xmult", has_baron, "held King XMult source"),
        MotifRequirement("held_retrigger", has_mime, "held-card retrigger source"),
        MotifRequirement("steel_kings", steel_kings >= 2, f"{steel_kings} Steel Kings"),
    )
    satisfied = sum(requirement.satisfied for requirement in requirements)

    # One isolated component is ordinary synergy bait, not a motif. Once two
    # package requirements exist, completion can express the value of finishing
    # the exact super-additive package.
    completion = 0.0 if satisfied < 2 else satisfied / len(requirements)

    by_id = {item.bond_id: item for item in bond_values}
    core_values = tuple(
        value
        for value in (
            _positive_value(by_id, "held_cards"),
            _positive_value(by_id, "held_retrigger"),
            _positive_value(by_id, "kings"),
        )
        if value > 0.0
    )
    estimated_payoff = (
        min(core_values) * BARON_MIME_STEEL_PAYOFF_COEFFICIENT
        if len(core_values) >= 2
        else 0.0
    )

    return MotifValue(
        motif_id="baron_mime_steel_kings",
        requirements=requirements,
        completion=completion,
        estimated_payoff=estimated_payoff,
        value=completion * estimated_payoff,
        relevant_bonds=BARON_MIME_STEEL_BONDS,
    )


def evaluate_motif_values(
    state: Any,
    bond_values: Iterable[BondStrategicValue],
) -> tuple[MotifValue, ...]:
    values = tuple(bond_values)
    return (evaluate_baron_mime_steel_motif(state, values),)
