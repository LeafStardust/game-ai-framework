"""Exact normal ``Blind:defeat`` cleanup for the first audited Boss families.

This owner is deliberately distinct from :mod:`boss_disable`: Chicot invokes
``Blind:disable`` during an active round, while normal defeat occurs after the
Blind has been cleared.  Vanilla defeat eventually installs a blank blind with
``set_blind(nil, nil, true)``, re-evaluating permanent cards/Jokers while keeping
Boss-specific teardown source-ordered.

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
from games.balatro.env.crimson_heart import clear_crimson_heart_joker_debuffs
from games.balatro.env.joker_sale import clear_verdant_leaf_defeat_debuff
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
_AMBER_ACORN = "Amber Acorn"
_VERDANT_LEAF = "Verdant Leaf"
_CRIMSON_HEART = "Crimson Heart"


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
    # Disabled Crimson remains fail-closed because the later blank-blind install
    # also resets Blind.disabled/prepped state, which is not yet globally owned.
    if disabled:
        if name in (
            _RESOURCE_BOSSES
            | _STATIC_SUIT_BOSSES
            | _SIMPLE_DEFEAT_BOSSES
            | {
                "The Plant",
                "The Pillar",
                "Cerulean Bell",
                _AMBER_ACORN,
                _VERDANT_LEAF,
            }
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
    elif name == _VERDANT_LEAF:
        cleaned = clear_verdant_leaf_defeat_debuff(run)
    elif name == _CRIMSON_HEART:
        # Blank-blind installation runs debuff_card over Jokers after replacing
        # Crimson's name/debuff config, so the selected Joker is cleared. The
        # same set_blind call initializes prepped=true; retain that source-native
        # private bit while the broader blank-blind state reset remains R2.9 work.
        cleaned = clear_crimson_heart_joker_debuffs(run)
        setattr(cleaned.public.blind, "prepped", True)
    elif name == _AMBER_ACORN:
        # Vanilla Blind:defeat flips the visually hidden Jokers face-up but does
        # not restore the pre-Boss order and consumes no RNG. Face orientation is
        # not part of the public Joker model; retaining exact physical order is
        # therefore the complete modeled state consequence here.
        cleaned = run.copy()
    elif name in _SIMPLE_DEFEAT_BOSSES:
        cleaned = run.copy()
    else:
        raise HeadlessTransitionError(
            f"normal Boss defeat is not exactly owned for {name!r}"
        )

    return _clear_public_blind_transients(cleaned)
