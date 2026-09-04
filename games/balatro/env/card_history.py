"""Exact permanent playing-card history mutations used by The Pillar.

These helpers own only the source-audited ``ability.played_this_ante`` field.
They deliberately do not pretend to execute a complete PLAY_CARDS action or
Ante transition; later tactical/run lifecycle owners must compose them at the
same source boundaries.
"""

from __future__ import annotations

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _require_authoritative_history(run: HeadlessRunState) -> list:
    cards = run.require_playing_card_order()
    if any(not card.played_this_ante_observed for card in cards):
        raise HeadlessTransitionError(
            "played-this-ante mutation requires authoritative permanent-card history"
        )
    return cards


def initialize_pristine_played_this_ante_history(
    run: HeadlessRunState,
) -> HeadlessRunState:
    """Establish authoritative false history for a pristine fresh run.

    This is intentionally narrow. It accepts only the simulator's untouched
    52-card Red/White base composition with no live ids or existing history.
    Live/public snapshots must obtain this state from the memory observer instead.
    """
    cards = run.require_playing_card_order()
    if len(cards) != 52:
        raise HeadlessTransitionError(
            "pristine played-this-ante initialization requires 52 playing cards"
        )
    if any(card.live_id is not None for card in cards):
        raise HeadlessTransitionError(
            "pristine played-this-ante initialization cannot replace live history"
        )
    if any(card.played_this_ante_observed or card.played_this_ante for card in cards):
        raise HeadlessTransitionError(
            "pristine played-this-ante initialization requires uninitialized history"
        )

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.played_this_ante_observed = True
        card.played_this_ante = False
    return next_run


def mark_played_cards_this_ante(
    run: HeadlessRunState,
    action: BalatroAction,
) -> HeadlessRunState:
    """Mirror vanilla marking each accepted highlighted play card as played.

    ``state_events.lua`` sets ``G.hand.highlighted[i].ability.played_this_ante``
    to true during accepted PLAY_CARDS processing. This helper validates only the
    identity/history mutation boundary; it does not move cards, score the hand,
    consume a hand, or draw replacements.
    """
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "played-this-ante marking requires SELECTING_HAND phase"
        )
    if not isinstance(action, BalatroAction) or action.name != PLAY_CARDS:
        raise HeadlessTransitionError("played-this-ante marking requires PLAY_CARDS")

    selected = list(action.cards or [])
    if not selected or len(selected) > 5:
        raise HeadlessTransitionError(
            "played-this-ante marking requires one to five played cards"
        )
    if len({id(card) for card in selected}) != len(selected):
        raise HeadlessTransitionError("played-this-ante marking rejects duplicate cards")

    _require_authoritative_history(run)
    hand_index_by_id = {id(card): index for index, card in enumerate(state.hand)}
    if any(id(card) not in hand_index_by_id for card in selected):
        raise HeadlessTransitionError(
            "played-this-ante marking requires authoritative current-hand cards"
        )

    next_run = run.copy()
    next_hand = next_run.public.hand
    for card in selected:
        copied = next_hand[hand_index_by_id[id(card)]]
        copied.played_this_ante_observed = True
        copied.played_this_ante = True

    # Deep-copy memoization should preserve the same copied card objects in the
    # private creation-order collection. Verify that invariant rather than
    # silently updating only one representation.
    order_ids = {id(card) for card in next_run.require_playing_card_order()}
    if any(id(next_hand[hand_index_by_id[id(card)]]) not in order_ids for card in selected):
        raise HeadlessTransitionError(
            "played-this-ante marking lost permanent-card identity linkage"
        )
    return next_run


def clear_played_this_ante_for_new_ante(
    run: HeadlessRunState,
) -> HeadlessRunState:
    """Mirror vanilla clearing ``played_this_ante`` at Boss→next-Ante reset."""
    _require_authoritative_history(run)

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.played_this_ante_observed = True
        card.played_this_ante = False
    return next_run
