"""Shared inverse Joker lifecycle for the admitted headless boundaries."""

from games.balatro.env.joker_order import JokerOrderError
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    _EXACT_R1_JOKER_ACQUISITION_TYPES,
    _OWNED_DECK_SCORING_TYPES,
)
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.seance import SeanceJoker
from games.balatro.jokers.vampire import VampireJoker


INVENTORY_ONLY_JOKER_REMOVAL_TYPES = tuple(
    joker_type
    for joker_type in (
        *_EXACT_R1_JOKER_ACQUISITION_TYPES,
        *_OWNED_DECK_SCORING_TYPES,
        GoldenJoker,
        CastleJoker,
        Cloud9Joker,
        RocketJoker,
        SeanceJoker,
        VampireJoker,
    )
    if joker_type is not JugglerJoker
)


def remove_validated_owned_joker(
    run: HeadlessRunState, joker_index: int
) -> HeadlessRunState:
    """Apply the validated inverse and retain the exact inventory and pool order."""
    next_run = run.copy()
    state = next_run.public
    removed = state.jokers[joker_index]
    if next_run.joker_order_state is not None:
        try:
            next_run.joker_order_state.remove(removed, state.jokers)
        except JokerOrderError as exc:
            raise HeadlessTransitionError(
                "cannot retain exact Joker order after removal"
            ) from exc
    if type(removed) is JugglerJoker:
        state.hand_size -= 1
    elif type(removed) is DrunkardJoker:
        state.round_reset_discards -= 1
    state.jokers.pop(joker_index)
    if state.joker_generation_pool_observed:
        from games.balatro.env.shop_generation_state import (
            restore_removed_shop_jokers_to_generation_pool,
        )

        return restore_removed_shop_jokers_to_generation_pool(next_run, (removed,))
    return next_run


def destroy_inventory_only_joker_exact(
    run: HeadlessRunState, joker_index: int
) -> HeadlessRunState:
    """Resolve an already selected destruction with an exact inventory inverse."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(joker_index) is not int or not 0 <= joker_index < len(run.public.jokers):
        raise HeadlessTransitionError("destroyed Joker index must reference an owned Joker")
    joker = run.public.jokers[joker_index]
    if type(joker) not in INVENTORY_ONLY_JOKER_REMOVAL_TYPES:
        raise HeadlessTransitionError("Joker destruction inverse lifecycle is not exactly owned")
    if getattr(joker, "eternal", False) is not False:
        raise HeadlessTransitionError("Eternal Joker destruction is unavailable")
    if getattr(joker, "edition", None) is not None:
        raise HeadlessTransitionError("Joker editions remain fail-closed for destruction")
    run.require_joker_order_state()
    return remove_validated_owned_joker(run, joker_index)
