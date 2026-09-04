"""Source-exact hidden Joker permutation primitive for Amber Acorn.

This module deliberately owns only Amber's seeded ordering consequence. Facing
and policy masking are separate lifecycle/observation concerns and Amber is not
training-exposed until those boundaries are composed safely.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.joker_order import JokerOrderState, JokerOrderError
from games.balatro.env.rng import BalatroRNG


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
