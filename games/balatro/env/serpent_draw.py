"""Exact The Serpent post-play/post-discard draw override.

Vanilla ``G.FUNCS.draw_from_deck_to_hand`` normally draws only into free hand
capacity.  While an enabled The Serpent is active, once at least one hand has
been played or one discard used this is replaced with ``min(#deck, 3)``.  The
override can therefore grow the hand beyond its ordinary card limit.

This module owns only that override.  Ordinary capacity-limited draw semantics
remain in :mod:`games.balatro.env.deal`.
"""

from __future__ import annotations

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.env.deal import (
    _hand_sort_key,
    _is_provably_base_order_allowing_transient_debuff,
    _public_card_sort_key,
    _vanilla_hand_primary_nominal,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _serpent_history_triggered(run: HeadlessRunState) -> bool:
    """Return exact public proof that Serpent's 3-card override is active."""
    state = run.public

    counts = state.round_hand_play_counts
    counts_exact = isinstance(counts, dict)
    if counts_exact:
        for value in counts.values():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                counts_exact = False
                break
            if value > 0:
                return True

    discards = state.discards_used
    if type(discards) is int and discards >= 0:
        if discards > 0:
            return True
        discards_exact = True
    else:
        discards_exact = False

    if not counts_exact or not discards_exact:
        raise HeadlessTransitionError(
            "Serpent requires authoritative current-round play/discard history"
        )
    return False


def draw_serpent_post_action_cards(run: HeadlessRunState) -> HeadlessRunState:
    """Draw exactly ``min(remaining deck, 3)`` cards for an active Serpent.

    Preconditions describe the stable draw-to-hand boundary after a play or
    discard has already advanced public current-round history.  The physical
    future order must already be owned privately; public ``state.deck`` is used
    only to verify composition and is re-canonicalized after movement.

    The input run and RNG are never mutated.  This effect consumes no RNG.
    """
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "Serpent post-action draw requires SELECTING_HAND phase"
        )
    if state.boss_name != "The Serpent":
        raise HeadlessTransitionError(
            "Serpent post-action draw requires The Serpent"
        )
    if boss_blind_disabled_by_owned_jokers(state):
        raise HeadlessTransitionError(
            "disabled Serpent uses ordinary draw semantics, not the Serpent override"
        )
    if not _serpent_history_triggered(run):
        raise HeadlessTransitionError(
            "Serpent 3-card override is inactive before the first play or discard"
        )

    if len(run.draw_pile) != len(state.deck):
        raise HeadlessTransitionError(
            "Serpent private draw pile and public remaining deck size disagree"
        )
    if {id(card) for card in run.draw_pile} != {id(card) for card in state.deck}:
        raise HeadlessTransitionError(
            "Serpent private draw pile and public remaining deck cards disagree"
        )

    order = run.require_playing_card_order()
    infer_base_original_suit = _is_provably_base_order_allowing_transient_debuff(order)
    if not infer_base_original_suit:
        for card in order:
            _vanilla_hand_primary_nominal(card, pristine=False)

    next_run = run.copy()
    next_state = next_run.public
    next_order = next_run.require_playing_card_order()
    creation_index = {id(card): index for index, card in enumerate(next_order)}

    draw_count = min(len(next_run.draw_pile), 3)
    for _ in range(draw_count):
        next_state.hand.append(next_run.draw_pile.pop())

    next_state.hand.sort(
        key=lambda card: _hand_sort_key(
            card,
            pristine=infer_base_original_suit,
            creation_index=creation_index,
        ),
        reverse=True,
    )
    next_state.deck = sorted(next_run.draw_pile, key=_public_card_sort_key)
    return next_run
