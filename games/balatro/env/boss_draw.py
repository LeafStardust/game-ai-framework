"""Exact Boss effects that fire after cards are drawn into the hand.

This module is deliberately separate from blind-start setup. Vanilla Cerulean
Bell performs its forced-card selection in ``Blind:drawn_to_hand`` after the hand
exists. The effect is therefore composed after exact shuffle/deal, not folded
into ``Blind:set_blind`` or the Joker ``setting_blind`` pass.
"""

from __future__ import annotations

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_CERULEAN_BELL_KEY = "cerulean_bell"


def apply_cerulean_bell_drawn_to_hand(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror Cerulean Bell's exact ``Blind:drawn_to_hand`` forced selection.

    Vanilla ``pseudorandom_element(G.hand.cards, pseudoseed('cerulean_bell'))``
    sorts candidate entries by each card's ``sort_id`` before making one
    ``math.random(#hand)`` draw. For permanent playing cards, the simulator's
    retained creation order is the exact relative ``sort_id`` order.

    This owner intentionally assumes an active, non-disabled Cerulean Bell. The
    currently supported blind-start path rejects Chicot and other unowned Boss
    disable lifecycles before reaching this boundary.
    """
    state = run.public
    if state.boss_name != "Cerulean Bell":
        raise HeadlessTransitionError(
            "Cerulean Bell drawn-to-hand effect requires Cerulean Bell"
        )
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "Cerulean Bell drawn-to-hand effect requires SELECTING_HAND phase"
        )
    if not state.hand:
        raise HeadlessTransitionError(
            "Cerulean Bell drawn-to-hand effect requires a non-empty hand"
        )

    forced = [card for card in state.hand if card.forced_selection]
    if len(forced) > 1:
        raise HeadlessTransitionError(
            "Cerulean Bell hand contains multiple forced selections"
        )
    if len(forced) == 1:
        # Vanilla scans the hand and consumes no RNG when a forced card is
        # already present.
        return run.copy()

    creation_order = run.require_playing_card_order()
    order_by_identity = {id(card): index for index, card in enumerate(creation_order)}
    if len(order_by_identity) != len(creation_order):
        raise HeadlessTransitionError(
            "Cerulean Bell requires unique authoritative playing-card identities"
        )

    try:
        sorted_hand_indices = sorted(
            range(len(state.hand)),
            key=lambda index: order_by_identity[id(state.hand[index])],
        )
    except KeyError as exc:
        raise HeadlessTransitionError(
            "Cerulean Bell hand contains card outside authoritative playing-card order"
        ) from exc

    next_run = run.copy()
    # The RNG draw chooses a position in the sort_id-sorted candidate list; the
    # returned card still occupies its original G.hand.cards array index.
    sorted_position = next_run.rng.pseudorandom_element_index(
        len(sorted_hand_indices),
        _CERULEAN_BELL_KEY,
    )
    chosen_hand_index = sorted_hand_indices[sorted_position]
    next_run.public.hand[chosen_hand_index].forced_selection = True
    return next_run
