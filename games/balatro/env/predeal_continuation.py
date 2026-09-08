"""Exact continuation after a pre-shuffle blind-start card draw.

Vanilla Chicot disabling The Manacle restores one hand-size slot and calls
``draw_from_deck_to_hand(1)`` before the later ``new_round`` event performs
``G.deck:shuffle("nr" .. ante)`` and fills the rest of the hand.

This helper owns only that second half.  It requires exactly one already-drawn
owned card, an authoritative retained 51-card remainder, and no other card-zone
state.  The pre-drawn card is never reinserted into the shuffle.
"""

from __future__ import annotations

from games.balatro.env.deal import (
    _hand_sort_key,
    _is_provably_base_order_allowing_transient_debuff,
    _public_card_sort_key,
    _vanilla_hand_primary_nominal,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def deal_after_retained_preblind_draw(run: HeadlessRunState) -> HeadlessRunState:
    """Shuffle the retained remainder and fill a hand containing one pre-draw."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    if state.phase != "DRAW_TO_HAND":
        raise HeadlessTransitionError(
            "pre-draw round-start continuation requires DRAW_TO_HAND phase"
        )
    if len(state.hand) != 1:
        raise HeadlessTransitionError(
            "pre-draw round-start continuation requires exactly one hand card"
        )
    if state.hand_size < 1 or len(state.hand) > state.hand_size:
        raise HeadlessTransitionError(
            "pre-draw round-start continuation requires valid hand capacity"
        )
    if state.discard_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError(
            "pre-draw round-start continuation requires empty discard/play zones"
        )
    if state.owned_deck is None:
        raise HeadlessTransitionError(
            "pre-draw round-start continuation requires authoritative owned_deck"
        )
    if len(run.draw_pile) != len(state.deck):
        raise HeadlessTransitionError(
            "pre-draw private/public remaining deck size disagrees"
        )
    if {id(card) for card in run.draw_pile} != {id(card) for card in state.deck}:
        raise HeadlessTransitionError(
            "pre-draw private/public remaining deck composition disagrees"
        )

    order = run.require_playing_card_order()
    owned_ids = {id(card) for card in order}
    hand_card = state.hand[0]
    if id(hand_card) not in owned_ids:
        raise HeadlessTransitionError(
            "pre-drawn hand card is not an authoritative owned card"
        )

    partition = [hand_card, *run.draw_pile]
    if len({id(card) for card in partition}) != len(partition):
        raise HeadlessTransitionError(
            "pre-draw card zones contain duplicate owned-card objects"
        )
    if len(partition) != len(order) or {id(card) for card in partition} != owned_ids:
        raise HeadlessTransitionError(
            "pre-draw hand and remaining deck do not partition owned cards"
        )

    infer_base_original_suit = _is_provably_base_order_allowing_transient_debuff(order)
    if not infer_base_original_suit:
        for card in order:
            _vanilla_hand_primary_nominal(card, pristine=False)

    # CardArea:shuffle first sorts the *remaining* deck by creation/sort_id.
    creation_index = {id(card): index for index, card in enumerate(order)}
    remainder = sorted(run.draw_pile, key=lambda card: creation_index[id(card)])

    next_run = run.copy()
    next_state = next_run.public
    next_order = next_run.require_playing_card_order()
    next_creation_index = {
        id(card): index for index, card in enumerate(next_order)
    }

    # Rebind the copied remainder by creation index because HeadlessRunState.copy
    # deep-copies canonical card objects.
    copied_by_index = {index: card for index, card in enumerate(next_order)}
    copied_hand_id_index = creation_index[id(hand_card)]
    copied_hand_card = copied_by_index[copied_hand_id_index]
    copied_remainder = [
        copied_by_index[creation_index[id(card)]] for card in remainder
    ]

    next_run.rng.shuffle_in_place(copied_remainder, f"nr{next_state.ante}")
    fill_count = min(
        len(copied_remainder),
        next_state.hand_size - 1,
    )
    dealt = [copied_remainder.pop() for _ in range(fill_count)]

    next_run.draw_pile = copied_remainder
    next_state.hand = [copied_hand_card, *dealt]
    next_state.hand.sort(
        key=lambda card: _hand_sort_key(
            card,
            pristine=infer_base_original_suit,
            creation_index=next_creation_index,
        ),
        reverse=True,
    )
    next_state.deck = sorted(copied_remainder, key=_public_card_sort_key)
    next_state.phase = "SELECTING_HAND"
    return next_run
