"""Exact deterministic round-start resource lifecycle helpers.

Vanilla ``new_round`` computes current-round allowances from persistent
``round_resets`` plus one-shot ``round_bonus`` values, then runs blind/Joker
setup, and only afterward clears those one-shot bonuses.  Keep those operations
separate so later ``setting_blind`` ownership can preserve source order.
"""

from __future__ import annotations

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


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


def consume_round_bonuses(run: HeadlessRunState) -> HeadlessRunState:
    """Clear vanilla one-shot round bonuses after blind/Joker setup."""
    next_run = run.copy()
    next_run.round_bonus_hands = 0
    next_run.round_bonus_discards = 0
    return next_run
