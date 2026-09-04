"""Source-exact hidden Joker ordering for Amber Acorn.

Amber is still not training-exposed. This module owns the exact seeded Joker
permutation, its narrow headless start mutation, and the Amber-specific reveal
behavior on blind disable. Policy masking is owned separately by
``public_observation_state``.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.joker_order import JokerOrderError, JokerOrderState
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_AMBER_KEY = "aajk"
_AMBER_SHUFFLES = 3


@dataclass(frozen=True)
class AmberShuffleResult:
    order: JokerOrderState
    rng: BalatroRNG


def apply_amber_acorn_shuffle(
    order: JokerOrderState,
    rng: BalatroRNG,
    owned_jokers,
) -> AmberShuffleResult:
    """Return Amber's exact post-event Joker order and RNG state.

    Vanilla flips any owned Jokers, then—only when more than one Joker exists—
    calls ``G.jokers:shuffle('aajk')`` three times. ``pseudoshuffle`` sorts by
    ``sort_id`` before *each* call, so every pass starts from creation order while
    advancing the same keyed pseudoseed node. The final physical permutation is
    therefore the third shuffle of creation order, not three chained shuffles.

    Inputs are never mutated.
    """
    if not isinstance(order, JokerOrderState):
        raise TypeError("order must be JokerOrderState")
    if not isinstance(rng, BalatroRNG):
        raise TypeError("rng must be BalatroRNG")

    owned = list(owned_jokers)
    order.validate_against(owned)

    next_order = JokerOrderState(
        creation_order=list(order.creation_order),
        physical_order=list(order.physical_order),
    )
    next_rng = BalatroRNG.from_snapshot(rng.snapshot())

    if len(owned) <= 1:
        return AmberShuffleResult(order=next_order, rng=next_rng)

    final_order = list(next_order.creation_order)
    for _ in range(_AMBER_SHUFFLES):
        candidate = list(next_order.creation_order)
        next_rng.shuffle_in_place(candidate, _AMBER_KEY)
        final_order = candidate

    try:
        next_order.set_physical_order(final_order, owned)
    except JokerOrderError:
        raise

    return AmberShuffleResult(order=next_order, rng=next_rng)


def apply_amber_acorn_order_effect(run: HeadlessRunState) -> HeadlessRunState:
    """Apply Amber's exact hidden physical Joker permutation to one run snapshot.

    This is the ``Blind:set_blind`` ordering effect only. The caller is
    responsible for invoking it in source order between baseline blind setup and
    the Joker ``setting_blind`` pass. Exact creation order may come either from
    unique live engine ids or from simulator-retained acquisition order.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.boss_name != "Amber Acorn":
        raise HeadlessTransitionError("Amber order effect requires Amber Acorn")
    if state.blind is None or bool(getattr(state.blind, "disabled", False)):
        raise HeadlessTransitionError("Amber order effect requires active blind state")

    next_run = run.copy()
    next_state = next_run.public
    order = next_run.require_joker_order_state()

    result = apply_amber_acorn_shuffle(order, next_run.rng, next_state.jokers)
    next_state.jokers = list(result.order.physical_order)
    next_run.joker_order_state = result.order
    next_run.rng_state = result.rng
    return next_run


def disable_amber_acorn(run: HeadlessRunState) -> HeadlessRunState:
    """Apply Amber's source-exact blind-disable reveal behavior.

    Vanilla ``Blind:disable`` flips any back-facing Jokers to the front but does
    not undo Amber's shuffled physical order. The headless model represents the
    active face-down condition through the active Amber Boss/phase boundary, so
    disabling the blind only needs to retain the physical order and mark the
    authoritative blind disabled. Policy observation then exposes that retained
    order again.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.boss_name != "Amber Acorn":
        raise HeadlessTransitionError("Amber disable requires Amber Acorn")
    if state.blind is None:
        raise HeadlessTransitionError("Amber disable requires authoritative blind state")
    if bool(getattr(state.blind, "disabled", False)):
        raise HeadlessTransitionError("Amber blind is already disabled")

    next_run = run.copy()
    next_run.require_joker_order_state()
    next_run.public.blind.disabled = True
    return next_run
