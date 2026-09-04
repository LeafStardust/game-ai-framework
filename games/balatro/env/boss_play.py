"""Exact Boss effects that fire at Balatro's ``Blind:press_play`` boundary.

This module does not attempt to execute an entire PLAY_CARDS transition.  It owns
only source-audited Boss mutations that occur once a canonical play has already
been selected, so later R4 tactical execution can compose the same exact owner.
"""

from __future__ import annotations

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _require_current_hand_play(run: HeadlessRunState, action: BalatroAction) -> list:
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError("boss press-play effect requires SELECTING_HAND phase")
    if not isinstance(action, BalatroAction) or action.name != PLAY_CARDS:
        raise HeadlessTransitionError("boss press-play effect requires PLAY_CARDS")

    cards = list(action.cards or [])
    if not cards:
        raise HeadlessTransitionError("PLAY_CARDS requires at least one played card")
    if len(cards) > 5:
        raise HeadlessTransitionError("PLAY_CARDS cannot contain more than five cards")
    if len({id(card) for card in cards}) != len(cards):
        raise HeadlessTransitionError("PLAY_CARDS cannot contain duplicate card objects")

    hand_ids = {id(card) for card in state.hand}
    if any(id(card) not in hand_ids for card in cards):
        raise HeadlessTransitionError(
            "PLAY_CARDS must reference authoritative current-hand card objects"
        )
    return cards


def apply_tooth_press_play_economy(
    run: HeadlessRunState,
    action: BalatroAction,
) -> HeadlessRunState:
    """Apply The Tooth's exact ``-$1 per played card`` press-play mutation.

    Vanilla permits dollars to become negative, so this transition deliberately
    does not clamp at zero.  The input run and RNG state are never mutated.
    """
    cards = _require_current_hand_play(run, action)
    state = run.public
    if str(getattr(state, "boss_name", "") or "") != "The Tooth":
        raise HeadlessTransitionError("Tooth press-play economy requires The Tooth")

    next_run = run.copy()
    if boss_blind_disabled_by_owned_jokers(next_run.public):
        return next_run

    next_run.public.money -= len(cards)
    return next_run
