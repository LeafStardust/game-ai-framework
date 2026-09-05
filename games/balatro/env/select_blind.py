"""Exact strategic SELECT_BLIND legality and execution ownership.

This module does not implement a second blind-start mechanic.  It is the narrow
strategic dispatcher over the already-audited R2 lifecycle owners.  Every
vanilla Red/White Boss is mapped explicitly; unknown or currently inexact run
state fails closed.
"""

from __future__ import annotations

from collections.abc import Callable

from games.balatro.blinds.blind import BlindType
from games.balatro.env.blind_start import (
    start_supported_amber_acorn,
    start_supported_cerulean_bell,
    start_supported_mutable_hand_rule_boss,
    start_supported_nonboss_blind,
    start_supported_pillar,
    start_supported_plant,
    start_supported_requirement_only_boss,
    start_supported_resource_boss,
    start_supported_start_inert_boss,
    start_supported_static_suit_debuff_boss,
    start_supported_verdant_leaf,
)
from games.balatro.env.boss_facing import (
    start_supported_deterministic_facing_boss,
    start_supported_fish,
    start_supported_wheel,
)
from games.balatro.env.boss_selection import BOSS_KEY_BY_NAME
from games.balatro.env.crimson_heart import start_supported_crimson_heart
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_REQUIREMENT_ONLY = frozenset({"The Wall", "Violet Vessel"})
_START_INERT = frozenset(
    {
        "The Psychic",
        "The Flint",
        "The Tooth",
        "The Hook",
        "The Ox",
        "The Arm",
        "The Serpent",
    }
)
_MUTABLE_HAND_RULE = frozenset({"The Eye", "The Mouth"})
_RESOURCE_MUTATING = frozenset({"The Water", "The Needle", "The Manacle"})
_STATIC_SUIT_DEBUFF = frozenset({"The Goad", "The Window", "The Head", "The Club"})
_DETERMINISTIC_FACING = frozenset({"The House", "The Mark"})
_SINGLE_ROUTE_NAMES = frozenset(
    {
        "The Plant",
        "The Pillar",
        "Verdant Leaf",
        "Amber Acorn",
        "Cerulean Bell",
        "The Wheel",
        "The Fish",
        "Crimson Heart",
    }
)

SUPPORTED_SELECT_BLIND_BOSS_NAMES = (
    _REQUIREMENT_ONLY
    | _START_INERT
    | _MUTABLE_HAND_RULE
    | _RESOURCE_MUTATING
    | _STATIC_SUIT_DEBUFF
    | _DETERMINISTIC_FACING
    | _SINGLE_ROUTE_NAMES
)

# Boss-pool drift must become an import/test failure rather than silently creating
# an unroutable training state.
if SUPPORTED_SELECT_BLIND_BOSS_NAMES != frozenset(BOSS_KEY_BY_NAME):
    missing = frozenset(BOSS_KEY_BY_NAME) - SUPPORTED_SELECT_BLIND_BOSS_NAMES
    extra = SUPPORTED_SELECT_BLIND_BOSS_NAMES - frozenset(BOSS_KEY_BY_NAME)
    raise RuntimeError(
        f"SELECT_BLIND Boss routing is out of sync; missing={sorted(missing)!r} "
        f"extra={sorted(extra)!r}"
    )


def _boss_start_owner(name: str) -> Callable[[HeadlessRunState], HeadlessRunState]:
    if name in _REQUIREMENT_ONLY:
        return start_supported_requirement_only_boss
    if name in _START_INERT:
        return start_supported_start_inert_boss
    if name in _MUTABLE_HAND_RULE:
        return start_supported_mutable_hand_rule_boss
    if name in _RESOURCE_MUTATING:
        return start_supported_resource_boss
    if name in _STATIC_SUIT_DEBUFF:
        return start_supported_static_suit_debuff_boss
    if name in _DETERMINISTIC_FACING:
        return start_supported_deterministic_facing_boss
    if name == "The Plant":
        return start_supported_plant
    if name == "The Pillar":
        return start_supported_pillar
    if name == "Verdant Leaf":
        return start_supported_verdant_leaf
    if name == "Amber Acorn":
        return start_supported_amber_acorn
    if name == "Cerulean Bell":
        return start_supported_cerulean_bell
    if name == "The Wheel":
        return start_supported_wheel
    if name == "The Fish":
        return start_supported_fish
    if name == "Crimson Heart":
        return start_supported_crimson_heart
    raise HeadlessTransitionError(f"unsupported SELECT_BLIND Boss: {name!r}")


def select_blind_exact(run: HeadlessRunState) -> HeadlessRunState:
    """Execute one exact strategic SELECT_BLIND transition on an isolated state."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    blind_type = getattr(state.blind, "type", None)
    if blind_type in {BlindType.SMALL, BlindType.BIG}:
        if state.boss_name is not None:
            raise HeadlessTransitionError(
                "non-Boss SELECT_BLIND cannot carry authoritative boss state"
            )
        return start_supported_nonboss_blind(run)

    if blind_type is BlindType.BOSS:
        name = state.boss_name
        if not isinstance(name, str) or not name:
            raise HeadlessTransitionError(
                "Boss SELECT_BLIND requires authoritative boss name"
            )
        return _boss_start_owner(name)(run)

    raise HeadlessTransitionError(
        "SELECT_BLIND requires an exact Small, Big, or Boss Blind"
    )


def can_select_blind_exact(run: HeadlessRunState) -> bool:
    """Return exact strategic legality without mutating run or RNG state.

    Legality intentionally dry-runs the canonical transition rather than
    duplicating its many lifecycle preconditions.  Every underlying owner copies
    the input before mutation, so a successful or rejected probe leaves the
    authoritative run and its RNG untouched.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    try:
        select_blind_exact(run)
    except HeadlessTransitionError:
        return False
    return True
