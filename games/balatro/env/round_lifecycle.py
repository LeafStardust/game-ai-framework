"""Exact deterministic round-start resource lifecycle helpers.

Vanilla ``new_round`` computes current-round allowances from persistent
``round_resets`` plus one-shot ``round_bonus`` values, then runs blind/Joker
setup, and only afterward clears those one-shot bonuses.  Keep those operations
separate so later ``setting_blind`` ownership can preserve source order.
"""

from __future__ import annotations

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.joker import JokerContext
from games.balatro.jokers.burglar import BurglarJoker


def apply_round_resource_baseline(run: HeadlessRunState) -> HeadlessRunState:
    """Apply vanilla hands/discards baseline without consuming round bonuses."""
    state = run.public
    if not state.round_reset_hands_observed or not state.round_reset_discards_observed:
        raise HeadlessTransitionError(
            "round resource reset requires authoritative reset allowances"
        )

    next_run = run.copy()
    next_state = next_run.public

    # Vanilla state_events.lua:
    #   discards_left = max(0, round_resets.discards + round_bonus.discards)
    #   hands_left = max(1, round_resets.hands + round_bonus.next_hands)
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

    return next_run


def apply_supported_setting_blind_effects(run: HeadlessRunState) -> HeadlessRunState:
    """Apply the currently owned ``setting_blind`` Joker lifecycle subset.

    The generic Joker interface is not a universal event bus: some modeled
    Jokers intentionally have trigger-agnostic ``apply`` methods because their
    owning scoring/rule pipeline decides when to call them.  Blind-start code
    must therefore dispatch only identities explicitly audited for this event.

    R2 currently owns Burglar only.  Any other Joker identity fails closed until
    it is classified as blind-start inert or its own ``setting_blind`` effect is
    modeled at this lifecycle boundary.
    """
    state = run.public
    if any(type(joker) is not BurglarJoker for joker in state.jokers):
        raise HeadlessTransitionError(
            "blind-start Joker lifecycle contains unsupported identity"
        )

    next_run = run.copy()
    next_state = next_run.public
    data = {
        "hands_gained": 0,
        "discards_remaining": next_state.discards_remaining,
    }

    for joker in next_state.jokers:
        context = JokerContext(
            state=next_state,
            trigger="BLIND_SELECTED",
            data=data,
        )
        data = joker.apply(context).data

    hands_gained = data.get("hands_gained")
    discards_remaining = data.get("discards_remaining")
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

    next_state.hands_remaining += hands_gained
    next_state.discards_remaining = discards_remaining
    return next_run


def consume_round_bonuses(run: HeadlessRunState) -> HeadlessRunState:
    """Clear vanilla one-shot round bonuses after blind/Joker setup."""
    next_run = run.copy()
    next_run.round_bonus_hands = 0
    next_run.round_bonus_discards = 0
    return next_run
