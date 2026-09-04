"""Canonical exact Boss-disable ownership for Chicot and other disable effects.

Vanilla ``Blind:disable`` is one lifecycle boundary with Boss-specific inverse
mutations. Keep those inverses centralized so setting-blind effects cannot pick
and choose ad-hoc cleanup that diverges from live Balatro.

This dispatcher deliberately supports only Bosses whose disable semantics are
already exact at the caller's current state. In particular, pre-deal Manacle
remains unavailable: vanilla restores hand size and immediately draws one card
*before* the later ``nr{ante}`` round-start shuffle, while headless does not yet
own arbitrary prior-round physical deck order at that boundary.
"""

from __future__ import annotations

from games.balatro.env.amber_acorn import disable_amber_acorn
from games.balatro.env.boss_debuffs import (
    clear_pillar_history_debuff,
    clear_plant_face_debuff,
    clear_static_suit_boss_debuff,
)
from games.balatro.env.boss_resources import disable_resource_boss
from games.balatro.env.crimson_heart import disable_crimson_heart
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_STATIC_SUIT_BOSSES = frozenset({"The Goad", "The Window", "The Head", "The Club"})
_REQUIREMENT_DISABLE_DIVISORS = {
    "The Wall": 2,
    "Violet Vessel": 3,
}
_SUPPORTED_SIMPLE_DISABLE_BOSSES = frozenset({
    "The Eye",
    "The Mouth",
    "The Psychic",
    "The Flint",
    "The Tooth",
    "The Hook",
    "The Ox",
    "The Arm",
    "The Serpent",
})


def _mark_disabled(run: HeadlessRunState) -> HeadlessRunState:
    next_run = run.copy()
    if next_run.public.blind is None:
        raise HeadlessTransitionError("Boss disable requires authoritative blind state")
    next_run.public.blind.disabled = True
    return next_run


def _disable_requirement_boss(run: HeadlessRunState, divisor: int) -> HeadlessRunState:
    """Mirror Wall/Violet ``self.chips = self.chips / divisor`` exactly.

    The headless public model keeps the active target in both ``blind_score`` and
    ``Blind.requirement``. Keep those two representations synchronized. Current
    environment state intentionally requires exact integer blind targets, so a
    non-divisible target fails closed instead of widening the schema to floats.
    """
    state = run.public
    requirement = getattr(state.blind, "requirement", None)
    if (
        isinstance(requirement, bool)
        or not isinstance(requirement, int)
        or requirement < 0
        or isinstance(state.blind_score, bool)
        or not isinstance(state.blind_score, int)
        or state.blind_score < 0
    ):
        raise HeadlessTransitionError(
            "requirement Boss disable requires exact nonnegative integer targets"
        )
    if requirement != state.blind_score:
        raise HeadlessTransitionError(
            "requirement Boss disable requires synchronized active target state"
        )
    if requirement % divisor != 0:
        raise HeadlessTransitionError(
            "requirement Boss disable target is not exactly divisible"
        )

    next_run = run.copy()
    next_state = next_run.public
    restored = requirement // divisor
    next_state.blind.requirement = restored
    next_state.blind_score = restored
    next_state.blind.disabled = True
    return next_run


def disable_supported_boss(
    run: HeadlessRunState,
    *,
    pre_deal: bool = False,
) -> HeadlessRunState:
    """Apply one source-exact ``Blind:disable`` for the currently owned Boss set.

    ``pre_deal=True`` is the Chicot setting-blind timing: the disable event runs
    before the later ``DRAW_TO_HAND``/``nr{ante}`` shuffle event. Any Boss whose
    disable needs physical pre-shuffle card order must fail closed there.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.blind is None:
        raise HeadlessTransitionError("Boss disable requires authoritative blind state")
    if not state.boss_name:
        raise HeadlessTransitionError("Boss disable requires authoritative boss name")
    if bool(getattr(state.blind, "disabled", False)):
        raise HeadlessTransitionError("Boss blind is already disabled")

    name = state.boss_name

    if name in _REQUIREMENT_DISABLE_DIVISORS:
        return _disable_requirement_boss(run, _REQUIREMENT_DISABLE_DIVISORS[name])

    if name in {"The Water", "The Needle"}:
        restored = disable_resource_boss(run)
        return _mark_disabled(restored)

    if name == "The Manacle":
        if pre_deal:
            raise HeadlessTransitionError(
                "pre-deal Manacle disable requires unowned pre-shuffle physical deck order"
            )
        restored = disable_resource_boss(run)
        return _mark_disabled(restored)

    if name in _STATIC_SUIT_BOSSES:
        cleared = clear_static_suit_boss_debuff(run)
        return _mark_disabled(cleared)

    if name == "The Plant":
        cleared = clear_plant_face_debuff(run)
        return _mark_disabled(cleared)

    if name == "The Pillar":
        cleared = clear_pillar_history_debuff(run)
        return _mark_disabled(cleared)

    if name == "Amber Acorn":
        return disable_amber_acorn(run)

    if name == "Crimson Heart":
        return disable_crimson_heart(run)

    if name in _SUPPORTED_SIMPLE_DISABLE_BOSSES:
        return _mark_disabled(run)

    # Cerulean Bell, facing Bosses, Verdant Leaf, and any as-yet-unclassified
    # Boss stay unavailable until their exact disable consequences are
    # centralized and tested.
    raise HeadlessTransitionError(
        f"Boss disable is not exactly owned for {name!r} at this boundary"
    )
