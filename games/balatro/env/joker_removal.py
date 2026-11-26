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
from games.balatro.jokers.madness import MadnessJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.jokers.supernova import SupernovaJoker
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
        MadnessJoker,
        DNAJoker,
        FacelessJoker,
        MidasMaskJoker,
        RocketJoker,
        RunnerJoker,
        SupernovaJoker,
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


def _require_destructible_joker(run: HeadlessRunState, joker_index: int):
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if type(joker_index) is not int or not 0 <= joker_index < len(run.public.jokers):
        raise HeadlessTransitionError("destroyed Joker index must reference an owned Joker")
    joker = run.public.jokers[joker_index]
    if getattr(joker, "eternal", False) is not False:
        raise HeadlessTransitionError("Eternal Joker destruction is unavailable")
    if getattr(joker, "edition", None) is not None:
        raise HeadlessTransitionError("Joker editions remain fail-closed for destruction")
    run.require_joker_order_state()
    return joker


def destroy_inventory_only_joker_exact(
    run: HeadlessRunState, joker_index: int
) -> HeadlessRunState:
    """Resolve an already selected destruction with an exact inventory inverse."""
    joker = _require_destructible_joker(run, joker_index)
    if type(joker) not in INVENTORY_ONLY_JOKER_REMOVAL_TYPES:
        raise HeadlessTransitionError("Joker destruction inverse lifecycle is not exactly owned")
    return remove_validated_owned_joker(run, joker_index)


def destroy_joker_at_round_start_exact(
    run: HeadlessRunState, joker_index: int
) -> HeadlessRunState:
    """Resolve destruction and retain the opening draw's earlier capacity read."""
    joker = _require_destructible_joker(run, joker_index)
    state = run.public
    if type(joker) is JugglerJoker:
        if type(state.hand_size) is not int or state.hand_size < 2:
            raise HeadlessTransitionError("Juggler destruction requires exact opening capacity")
        result = remove_validated_owned_joker(run, joker_index)
        if result.opening_draw_capacity is None:
            # CardArea:change_size queues its delta behind the opening draw.
            result.opening_draw_capacity = state.hand_size
        return result
    if type(joker) is DrunkardJoker:
        if (
            state.round_reset_discards_observed is not True
            or type(state.round_reset_discards) is not int
            or state.round_reset_discards < 1
            or type(state.discards_remaining) is not int
            or state.discards_remaining < 0
        ):
            raise HeadlessTransitionError("Drunkard destruction requires exact discard allowances")
        result = remove_validated_owned_joker(run, joker_index)
        # The baseline already includes Drunkard. The queued ease clamps at zero.
        result.public.discards_remaining = max(0, state.discards_remaining - 1)
        return result
    if type(joker) not in INVENTORY_ONLY_JOKER_REMOVAL_TYPES:
        raise HeadlessTransitionError("Joker destruction inverse lifecycle is not exactly owned")
    return remove_validated_owned_joker(run, joker_index)
