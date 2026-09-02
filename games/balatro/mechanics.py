from __future__ import annotations

"""Canonical public mechanical descriptors for persistent Balatro components.

Strategic systems should query these mechanics instead of branching on Joker or
component display names. Mechanically modeled classes expose ``mechanics``
directly. The name fallback exists only for public snapshot/test objects that do
not carry the concrete runtime class yet and should shrink as those objects gain
native descriptors.
"""

from typing import Any, Iterable


DISCARD_HAND_LEVELING = "discard_hand_leveling"
PROBABILISTIC_HAND_LEVELING = "probabilistic_hand_leveling"
HAND_LEVEL_COPY = "hand_level_copy"
PLANET_PACK_TARGETING = "planet_pack_targeting"
GOLD_CARD_GENERATION = "gold_card_generation"
GOLD_CARD_SCORING_ECONOMY = "gold_card_scoring_economy"
HELD_FACE_ECONOMY = "held_face_economy"
ENHANCEMENT_CONSUMPTION = "enhancement_consumption"
ENHANCEMENT_FEED_ACCESS = "enhancement_feed_access"
TAROT_GENERATION = "tarot_generation"


def _normalize_name(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = getattr(value, "name", None)
        if raw is None:
            raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


# Compatibility-only semantics for state snapshots and lightweight test objects.
# Runtime Joker classes should expose their mechanics directly.
_LEGACY_NAME_MECHANICS: dict[str, frozenset[str]] = {
    "burntjoker": frozenset({DISCARD_HAND_LEVELING}),
    "spacejoker": frozenset({PROBABILISTIC_HAND_LEVELING}),
    "blueprint": frozenset({HAND_LEVEL_COPY}),
    "blueprintjoker": frozenset({HAND_LEVEL_COPY}),
    "brainstorm": frozenset({HAND_LEVEL_COPY}),
    "brainstormjoker": frozenset({HAND_LEVEL_COPY}),
    "telescope": frozenset({PLANET_PACK_TARGETING}),
    "midasmask": frozenset({GOLD_CARD_GENERATION, ENHANCEMENT_FEED_ACCESS}),
    "midasmaskjoker": frozenset({GOLD_CARD_GENERATION, ENHANCEMENT_FEED_ACCESS}),
    "goldenticket": frozenset({GOLD_CARD_SCORING_ECONOMY}),
    "goldenticketjoker": frozenset({GOLD_CARD_SCORING_ECONOMY}),
    "reservedparking": frozenset({HELD_FACE_ECONOMY}),
    "reservedparkingjoker": frozenset({HELD_FACE_ECONOMY}),
    "vampire": frozenset({ENHANCEMENT_CONSUMPTION}),
    "vampirejoker": frozenset({ENHANCEMENT_CONSUMPTION}),
    "cartomancer": frozenset({TAROT_GENERATION}),
    "cartomancerjoker": frozenset({TAROT_GENERATION}),
}


def component_mechanics(component: Any) -> frozenset[str]:
    """Return public persistent mechanics exposed by one component."""
    declared = getattr(component, "mechanics", None)
    if declared is not None:
        if callable(declared):
            declared = declared()
        return frozenset(str(item) for item in (declared or ()))
    return _LEGACY_NAME_MECHANICS.get(_normalize_name(component), frozenset())


def component_has_mechanic(component: Any, mechanic: str) -> bool:
    return mechanic in component_mechanics(component)


def components_have_mechanic(values: Iterable[Any], mechanic: str) -> bool:
    return any(component_has_mechanic(value, mechanic) for value in values)


def components_with_mechanic(values: Iterable[Any], mechanic: str) -> tuple[Any, ...]:
    return tuple(value for value in values if component_has_mechanic(value, mechanic))
