from __future__ import annotations

"""Exact public-state projection for deterministic Planet use.

This module owns no Planet timing or purchase policy. It only applies the real
Planet ``can_use`` / ``use`` implementation to copied public state and exposes the
canonical resulting StrategyDelta to the existing decision owners.
"""

import copy

from games.balatro.bonds.strategy_delta import StrategyDelta, strategy_delta_from_states
from games.balatro.consumable import ConsumableContext


def _identity_index(items, candidate: object) -> int | None:
    for index, item in enumerate(items):
        if item is candidate:
            return index
    return None


def project_planet_use(state, planet: object, *, held: bool) -> object | None:
    """Return copied public state after exact deterministic Planet use.

    ``held=True`` additionally consumes the exact held Planet from the projected
    inventory. Shop acquisition uses ``held=False`` because the candidate is not
    part of current state and is modeled as purchased then immediately consumed.
    """
    if str(getattr(planet, "category", "")).upper() != "PLANET":
        return None

    projected = copy.deepcopy(state)
    if held:
        index = _identity_index(getattr(state, "consumables", ()), planet)
        if index is None or not (0 <= index < len(projected.consumables)):
            return None
        projected_planet = projected.consumables[index]
    else:
        index = None
        projected_planet = copy.deepcopy(planet)

    context = ConsumableContext(state=projected)
    try:
        if not projected_planet.can_use(context):
            return None
        projected_planet.use(context)
    except (AttributeError, TypeError, ValueError):
        return None

    if held and index is not None:
        projected.consumables.pop(index)
    return projected


def planet_strategy_delta(state, planet: object, *, held: bool) -> StrategyDelta | None:
    """Evaluate canonical StrategyDelta after exact deterministic Planet use."""
    projected = project_planet_use(state, planet, held=held)
    if projected is None:
        return None
    return strategy_delta_from_states(state, projected)
