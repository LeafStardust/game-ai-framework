"""Exact Boss effects that fire at Balatro's ``Blind:press_play`` boundary.

This module does not attempt to execute an entire PLAY_CARDS transition. It owns
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
    does not clamp at zero. The input run and RNG state are never mutated.
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


def apply_hook_press_play_discards(
    run: HeadlessRunState,
    action: BalatroAction,
) -> HeadlessRunState:
    """Apply The Hook's exact random forced-discard mutation.

    Vanilla moves the player's chosen play cards from ``G.hand`` to ``G.play``
    *before* calling ``Blind:press_play``. This narrow owner therefore excludes
    ``action.cards`` from the Hook candidate set without also pretending to own
    the ordinary hand→play transition.

    The Hook calls ``pseudorandom_element(..., pseudoseed('hook'))`` up to twice,
    removing the first selected candidate before the second draw. The eventual
    ``discard_cards_from_highlighted(nil, true)`` path moves those cards to the
    discard area but consumes no discard and does not enter DRAW_TO_HAND, so no
    replacement cards are drawn at this boundary.

    Joker/seal discard triggers are intentionally fail-closed until their own
    action-time lifecycle is exact.
    """
    played_cards = _require_current_hand_play(run, action)
    state = run.public
    if str(getattr(state, "boss_name", "") or "") != "The Hook":
        raise HeadlessTransitionError("Hook press-play discard requires The Hook")
    if state.jokers:
        raise HeadlessTransitionError(
            "Hook press-play with Joker discard triggers is not yet owned"
        )

    played_ids = {id(card) for card in played_cards}
    remaining = [card for card in state.hand if id(card) not in played_ids]
    if any(getattr(card, "seal", None) is not None for card in remaining):
        raise HeadlessTransitionError(
            "Hook press-play with sealed discard candidates is not yet owned"
        )

    next_run = run.copy()
    if boss_blind_disabled_by_owned_jokers(next_run.public):
        return next_run

    next_state = next_run.public
    # Map the original action selection into the deep-copied current hand by its
    # authoritative visible-hand positions; equality/copy semantics are not used
    # as a substitute for object identity.
    original_index_by_id = {id(card): index for index, card in enumerate(state.hand)}
    copied_played_ids = {
        id(next_state.hand[original_index_by_id[id(card)]]) for card in played_cards
    }
    candidates = [card for card in next_state.hand if id(card) not in copied_played_ids]

    creation_order = next_run.require_playing_card_order()
    creation_rank = {id(card): index for index, card in enumerate(creation_order)}
    if any(id(card) not in creation_rank for card in candidates):
        raise HeadlessTransitionError(
            "Hook candidates are missing from authoritative playing-card order"
        )

    forced: list = []
    for _ in range(min(2, len(candidates))):
        ordered_candidates = sorted(
            candidates,
            key=lambda card: creation_rank[id(card)],
        )
        selected_index = next_run.rng.pseudorandom_element_index(
            len(ordered_candidates),
            "hook",
        )
        selected = ordered_candidates[selected_index]
        forced.append(selected)
        candidates.remove(selected)

    # discard_cards_from_highlighted sorts highlighted cards by visible x before
    # moving them. Canonical hand order is the exact visible hand sort at this
    # boundary, so retain that relative order for the physical discard area.
    visible_rank = {id(card): index for index, card in enumerate(next_state.hand)}
    forced.sort(key=lambda card: visible_rank[id(card)])
    forced_ids = {id(card) for card in forced}
    next_state.hand = [card for card in next_state.hand if id(card) not in forced_ids]
    next_state.discard_pile.extend(forced)
    next_run.discard_pile.extend(forced)

    # Hook=true intentionally does not decrement discards_remaining, increment a
    # discard-use counter, change phase, or draw replacement cards.
    return next_run
