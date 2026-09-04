"""Minimum exact Joker-sale ownership for Verdant Leaf.

Vanilla selling a Joker removes it from the Joker area, runs the card's
``remove_from_deck`` inverse lifecycle, credits ``sell_cost``, and disables
Verdant Leaf.  The first headless slice deliberately permits only Jokers whose
acquisition/removal is inventory-only; resource-sensitive and persistent-state
Jokers remain fail-closed until their inverse lifecycle is owned.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    _EXACT_R1_JOKER_ACQUISITION_TYPES,
    _OWNED_DECK_SCORING_TYPES,
)
from games.balatro.jokers.juggler import JugglerJoker


_STATIC_SELL_SAFE_TYPES = tuple(
    joker_type
    for joker_type in (
        *_EXACT_R1_JOKER_ACQUISITION_TYPES,
        *_OWNED_DECK_SCORING_TYPES,
    )
    if joker_type is not JugglerJoker
)


def _permanent_cards(run: HeadlessRunState) -> list[BalatroCard]:
    cards = run.require_playing_card_order()
    if not cards:
        raise HeadlessTransitionError("Verdant Leaf requires authoritative permanent cards")
    if any(not isinstance(card, BalatroCard) for card in cards):
        raise HeadlessTransitionError("Verdant Leaf permanent cards are malformed")
    return cards


def apply_verdant_leaf_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror active Verdant Leaf debuffing every non-Joker playing card."""
    state = run.public
    if state.boss_name != "Verdant Leaf":
        raise HeadlessTransitionError("Verdant Leaf debuff requires Verdant Leaf boss")
    if state.blind is None:
        raise HeadlessTransitionError("Verdant Leaf requires active blind state")
    if getattr(state.blind, "disabled", False):
        raise HeadlessTransitionError("disabled Verdant Leaf cannot apply card debuffs")
    cards = _permanent_cards(run)
    if any(card.debuffed for card in cards):
        raise HeadlessTransitionError(
            "Verdant Leaf start requires clean pre-blind card debuff state"
        )

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = True
    return next_run


def sell_static_joker_during_verdant(
    run: HeadlessRunState,
    joker_index: int,
) -> HeadlessRunState:
    """Sell one exact inventory-only Joker and disable active Verdant Leaf.

    This is intentionally not the final general ``SELL_JOKER`` action owner.
    It establishes the exact mechanical boundary required by Verdant while the
    environment contract remains ``PLANNED``.
    """
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "Verdant Joker sale currently requires SELECTING_HAND phase"
        )
    if state.boss_name != "Verdant Leaf" or state.blind is None:
        raise HeadlessTransitionError("Verdant Joker sale requires active Verdant Leaf")
    if getattr(state.blind, "disabled", False):
        raise HeadlessTransitionError("Verdant Leaf is already disabled")
    if isinstance(joker_index, bool) or not isinstance(joker_index, int):
        raise HeadlessTransitionError("joker index must be an exact integer")
    if joker_index < 0 or joker_index >= len(state.jokers):
        raise HeadlessTransitionError("joker index is out of range")

    cards = _permanent_cards(run)
    if any(not card.debuffed for card in cards):
        raise HeadlessTransitionError(
            "Verdant Joker sale requires active owned all-card debuff"
        )

    joker = state.jokers[joker_index]
    if type(joker) not in _STATIC_SELL_SAFE_TYPES:
        raise HeadlessTransitionError(
            "Joker sale inverse lifecycle is not exactly owned for this Joker"
        )
    if getattr(joker, "eternal", False):
        raise HeadlessTransitionError("Eternal Joker cannot be sold")
    if getattr(joker, "edition", None) is not None:
        raise HeadlessTransitionError("Joker editions remain fail-closed for sale")

    sell_cost = getattr(joker, "sell_cost", None)
    if isinstance(sell_cost, bool) or not isinstance(sell_cost, int) or sell_cost < 0:
        raise HeadlessTransitionError("Joker sale requires exact nonnegative sell_cost")

    next_run = run.copy()
    next_state = next_run.public
    next_state.money += sell_cost
    next_state.jokers.pop(joker_index)
    next_state.blind.disabled = True
    for card in next_run.require_playing_card_order():
        card.debuffed = False
    return next_run
