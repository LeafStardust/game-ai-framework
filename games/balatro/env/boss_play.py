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


def _require_post_movement_played_pile(
    run: HeadlessRunState,
    *,
    boss_name: str,
) -> list:
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError("boss press-play effect requires SELECTING_HAND phase")
    if str(getattr(state, "boss_name", "") or "") != boss_name:
        raise HeadlessTransitionError(
            f"{boss_name} press-play effect requires {boss_name}"
        )

    cards = list(run.played_pile)
    if not cards or len(cards) > 5:
        raise HeadlessTransitionError(
            "boss press-play played pile must contain 1 to 5 cards"
        )
    if len({id(card) for card in cards}) != len(cards):
        raise HeadlessTransitionError(
            "boss press-play played pile cannot contain duplicate card objects"
        )

    hand_ids = {id(card) for card in state.hand}
    if any(id(card) in hand_ids for card in cards):
        raise HeadlessTransitionError(
            "boss press-play played cards must already have left the current hand"
        )

    playing_ids = {id(card) for card in run.require_playing_card_order()}
    if any(id(card) not in playing_ids for card in cards):
        raise HeadlessTransitionError(
            "boss press-play played cards require authoritative permanent-card identity"
        )
    return cards


def _apply_tooth_dollar_loss(
    run: HeadlessRunState,
    played_count: int,
) -> HeadlessRunState:
    state = run.public
    if str(getattr(state, "boss_name", "") or "") != "The Tooth":
        raise HeadlessTransitionError("Tooth press-play economy requires The Tooth")

    next_run = run.copy()
    if boss_blind_disabled_by_owned_jokers(next_run.public):
        return next_run

    next_run.public.money -= played_count
    return next_run


def apply_tooth_press_play_economy(
    run: HeadlessRunState,
    action: BalatroAction,
) -> HeadlessRunState:
    """Apply The Tooth's exact ``-$1 per played card`` press-play mutation.

    This entry point validates a production-shaped Play action against the
    current public hand. Vanilla permits dollars to become negative, so this
    transition deliberately does not clamp at zero. The input run and RNG state
    are never mutated.
    """
    cards = _require_current_hand_play(run, action)
    return _apply_tooth_dollar_loss(run, len(cards))


def apply_tooth_press_play_economy_from_played_pile(
    run: HeadlessRunState,
) -> HeadlessRunState:
    """Apply The Tooth at the exact post-hand→play ``Blind:press_play`` boundary."""
    cards = _require_post_movement_played_pile(run, boss_name="The Tooth")
    return _apply_tooth_dollar_loss(run, len(cards))


def _apply_hook_forced_discards(
    run: HeadlessRunState,
    *,
    candidate_hand_indices: list[int],
) -> HeadlessRunState:
    state = run.public
    if str(getattr(state, "boss_name", "") or "") != "The Hook":
        raise HeadlessTransitionError("Hook press-play discard requires The Hook")
    if state.jokers:
        raise HeadlessTransitionError(
            "Hook press-play with Joker discard triggers is not yet owned"
        )

    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or index < 0
        or index >= len(state.hand)
        for index in candidate_hand_indices
    ):
        raise HeadlessTransitionError("Hook candidate positions must reference the current hand")
    if len(set(candidate_hand_indices)) != len(candidate_hand_indices):
        raise HeadlessTransitionError("Hook candidate positions cannot contain duplicates")

    candidates = [state.hand[index] for index in candidate_hand_indices]
    if any(getattr(card, "seal", None) is not None for card in candidates):
        raise HeadlessTransitionError(
            "Hook press-play with sealed discard candidates is not yet owned"
        )

    next_run = run.copy()
    if boss_blind_disabled_by_owned_jokers(next_run.public):
        return next_run

    next_state = next_run.public
    candidates = [next_state.hand[index] for index in candidate_hand_indices]
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


def apply_hook_press_play_discards(
    run: HeadlessRunState,
    action: BalatroAction,
) -> HeadlessRunState:
    """Apply The Hook's exact random forced-discard mutation.

    Vanilla moves the player's chosen play cards from ``G.hand`` to ``G.play``
    *before* calling ``Blind:press_play``. This narrow action-shaped owner
    therefore excludes ``action.cards`` from the Hook candidate set while leaving
    ordinary hand→play movement to the complete Play lifecycle owner.
    """
    played_cards = _require_current_hand_play(run, action)
    if str(getattr(run.public, "boss_name", "") or "") != "The Hook":
        raise HeadlessTransitionError("Hook press-play discard requires The Hook")

    played_ids = {id(card) for card in played_cards}
    candidate_hand_indices = [
        index
        for index, card in enumerate(run.public.hand)
        if id(card) not in played_ids
    ]
    return _apply_hook_forced_discards(
        run,
        candidate_hand_indices=candidate_hand_indices,
    )


def apply_hook_press_play_discards_from_played_pile(
    run: HeadlessRunState,
) -> HeadlessRunState:
    """Apply The Hook at the exact post-hand→play ``Blind:press_play`` boundary.

    At this boundary the player's selected cards already live in ``played_pile``;
    every card still in the public hand is therefore an exact Hook candidate.
    The helper consumes only Hook's keyed RNG and performs no replacement draw.
    """
    _require_post_movement_played_pile(run, boss_name="The Hook")
    return _apply_hook_forced_discards(
        run,
        candidate_hand_indices=list(range(len(run.public.hand))),
    )
