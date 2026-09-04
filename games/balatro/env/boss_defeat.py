"""Exact normal ``Blind:defeat`` cleanup for the first audited Boss families.

This owner is deliberately distinct from :mod:`boss_disable`: Chicot invokes
``Blind:disable`` during an active round, while normal defeat occurs after the
Blind has been cleared.  Vanilla defeat resets the active blind across permanent
playing cards, clears transient Boss card state, flips hidden Jokers, and restores
The Manacle's persistent hand-size reduction without drawing a replacement.

Only families whose teardown is already represented exactly are admitted here.
Unsupported Bosses fail closed rather than borrowing disable semantics.
"""

from __future__ import annotations

from games.balatro.env.boss_debuffs import (
    clear_pillar_history_debuff,
    clear_plant_face_debuff,
    clear_static_suit_boss_debuff,
)
from games.balatro.env.boss_draw import clear_cerulean_bell_forced_selection
from games.balatro.env.boss_resources import defeat_resource_boss
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_RESOURCE_BOSSES = frozenset({"The Water", "The Needle", "The Manacle"})
_STATIC_SUIT_BOSSES = frozenset({"The Goad", "The Window", "The Head", "The Club"})
_SIMPLE_DEFEAT_BOSSES = frozenset({
    "The Wall",
    "Violet Vessel",
    "The Psychic",
    "The Flint",
    "The Tooth",
    "The Hook",
    "The Ox",
    "The Arm",
    "The Serpent",
    "The Eye",
    "The Mouth",
})


def _clear_public_blind_transients(run: HeadlessRunState) -> HeadlessRunState:
    """Clear public state owned only by the defeated active Blind object."""
    next_run = run.copy()
    state = next_run.public
    state.boss_blind_state_observed = False
    state.boss_blind_hands.clear()
    state.boss_blind_only_hand = None
    return next_run


def defeat_supported_boss(run: HeadlessRunState) -> HeadlessRunState:
    """Apply exact normal-defeat cleanup for one supported Boss Blind.

    The caller must already be at the round-evaluation boundary after meeting the
    Boss requirement.  This function does not award dollars, advance the Ante, or
    generate the shop; those are separate source-ordered lifecycle owners.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "ROUND_EVAL":
        raise HeadlessTransitionError("Boss defeat cleanup requires ROUND_EVAL phase")
    if state.blind is None or not state.boss_name:
        raise HeadlessTransitionError("Boss defeat cleanup requires authoritative Boss state")

    name = state.boss_name
    disabled = bool(getattr(state.blind, "disabled", False))

    # A Chicot-disabled Boss has already run the exact disable inverse while the
    # round was active. Normal defeat must not apply those inverses a second time.
    if disabled:
        if name in (
            _RESOURCE_BOSSES
            | _STATIC_SUIT_BOSSES
            | _SIMPLE_DEFEAT_BOSSES
            | {"The Plant", "The Pillar", "Cerulean Bell"}
        ):
            return _clear_public_blind_transients(run)
        raise HeadlessTransitionError(
            f"normal Boss defeat is not exactly owned for disabled {name!r}"
        )

    if name in _RESOURCE_BOSSES:
        cleaned = defeat_resource_boss(run)
    elif name in _STATIC_SUIT_BOSSES:
        cleaned = clear_static_suit_boss_debuff(run)
    elif name == "The Plant":
        cleaned = clear_plant_face_debuff(run)
    elif name == "The Pillar":
        cleaned = clear_pillar_history_debuff(run)
    elif name == "Cerulean Bell":
        cleaned = clear_cerulean_bell_forced_selection(run)
    elif name in _SIMPLE_DEFEAT_BOSSES:
        cleaned = run.copy()
    else:
        raise HeadlessTransitionError(
            f"normal Boss defeat is not exactly owned for {name!r}"
        )

    return _clear_public_blind_transients(cleaned)
