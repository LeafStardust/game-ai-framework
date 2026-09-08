"""Exact deterministic round-start resource lifecycle helpers.

Vanilla ``new_round`` computes current-round allowances from persistent
``round_resets`` plus one-shot ``round_bonus`` values, then immediately clears
those one-shot bonuses *before* ``Blind:set_blind`` and Joker ``setting_blind``
processing. Preserve that ordering so later lifecycle effects cannot observe a
bonus that vanilla has already consumed.
"""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.boss_disable import disable_supported_boss
from games.balatro.env.transition import (
    _EXACT_R1_JOKER_ACQUISITION_TYPES,
    _OWNED_DECK_SCORING_TYPES,
    HeadlessRunState,
    HeadlessTransitionError,
)
from games.balatro.joker import JokerContext
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.troubadour import TroubadourJoker


_BLIND_START_INERT_JOKER_TYPES = (
    *_EXACT_R1_JOKER_ACQUISITION_TYPES,
    *_OWNED_DECK_SCORING_TYPES,
    StuntmanJoker,
    DrunkardJoker,
    TroubadourJoker,
    MerryAndyJoker,
)


def apply_round_resource_baseline(run: HeadlessRunState) -> HeadlessRunState:
    """Apply vanilla hands/discards baseline and consume one-shot bonuses.

    Source order in ``new_round`` is exact here:

    1. compute ``discards_left`` from reset + round bonus;
    2. compute ``hands_left`` from reset + round bonus;
    3. reset per-round counters;
    4. clear ``round_bonus.next_hands`` and ``round_bonus.discards``;
    5. only later run ``Blind:set_blind`` / Joker ``setting_blind``.
    """
    state = run.public
    if not state.round_reset_hands_observed or not state.round_reset_discards_observed:
        raise HeadlessTransitionError(
            "round resource reset requires authoritative reset allowances"
        )

    next_run = run.copy()
    next_state = next_run.public

    next_state.discards_remaining = max(
        0,
        next_state.round_reset_discards + next_run.round_bonus_discards,
    )
    next_state.hands_remaining = max(
        1,
        next_state.round_reset_hands + next_run.round_bonus_hands,
    )
    next_state.discards_used = 0
    next_state.last_played_hand = None
    next_state.round_hand_play_counts = {
        hand: 0 for hand in next_state.round_hand_play_counts
    }
    next_state.score = 0

    # Vanilla clears these before Blind:set_blind and setting_blind Jokers.
    next_run.round_bonus_hands = 0
    next_run.round_bonus_discards = 0

    return next_run


def apply_supported_setting_blind_effects(run: HeadlessRunState) -> HeadlessRunState:
    """Apply the currently owned ``setting_blind`` Joker lifecycle subset.

    Burglar mutates current round resources immediately during Joker calculation.
    Chicot queues ``Blind:disable()``; vanilla executes that event only after all
    Jokers have received the setting-blind context. We therefore collect Chicot's
    disable request during the same pass, install all Joker resource outputs, and
    only then call the canonical Boss-disable owner.

    Chicot is lifecycle-modeled here but is *not* admitted to the R1 acquisition
    allowlist. Unknown identities remain fail-closed.
    """
    state = run.public
    supported_types = (
        *_BLIND_START_INERT_JOKER_TYPES,
        BurglarJoker,
        ChicotJoker,
    )
    if any(type(joker) not in supported_types for joker in state.jokers):
        raise HeadlessTransitionError(
            "blind-start Joker lifecycle contains unsupported identity"
        )

    next_run = run.copy()
    next_state = next_run.public
    is_boss = (
        next_state.blind is not None
        and getattr(next_state.blind, "type", None) is BlindType.BOSS
    )
    data = {
        "hands_gained": 0,
        "discards_remaining": next_state.discards_remaining,
        "boss_blind": is_boss,
        "boss_disable_requests": 0,
    }

    for joker in next_state.jokers:
        if type(joker) not in {BurglarJoker, ChicotJoker}:
            continue
        context = JokerContext(
            state=next_state,
            trigger="BLIND_SELECTED",
            data=data,
        )
        data = joker.apply(context).data

    hands_gained = data.get("hands_gained")
    discards_remaining = data.get("discards_remaining")
    disable_requests = data.get("boss_disable_requests")
    if isinstance(hands_gained, bool) or not isinstance(hands_gained, int):
        raise HeadlessTransitionError("blind-start hands_gained must be an exact integer")
    if (
        isinstance(discards_remaining, bool)
        or not isinstance(discards_remaining, int)
        or discards_remaining < 0
    ):
        raise HeadlessTransitionError(
            "blind-start discards_remaining must be an exact nonnegative integer"
        )
    if (
        isinstance(disable_requests, bool)
        or not isinstance(disable_requests, int)
        or disable_requests < 0
    ):
        raise HeadlessTransitionError(
            "blind-start boss_disable_requests must be an exact nonnegative integer"
        )
    if disable_requests > 1:
        raise HeadlessTransitionError(
            "multiple queued Chicot Boss disables are not yet exactly owned"
        )

    next_state.hands_remaining += hands_gained
    next_state.discards_remaining = discards_remaining

    if disable_requests == 1:
        # Chicot's event was queued from the setting_blind calculation and runs
        # before new_round's later DRAW_TO_HAND/nr{ante} shuffle event.
        next_run = disable_supported_boss(next_run, pre_deal=True)

    return next_run


def consume_round_bonuses(run: HeadlessRunState) -> HeadlessRunState:
    """Idempotently clear one-shot round bonuses."""
    next_run = run.copy()
    next_run.round_bonus_hands = 0
    next_run.round_bonus_discards = 0
    return next_run
