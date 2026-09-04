"""Exact private card-zone movement around Balatro round/blind boundaries.

This module owns only mechanical card movement needed to retain the physical
``G.deck.cards`` order across cash-out/shop/blind-select and consume that order
when a source mechanic draws before the next normal shuffle. It deliberately
does not own end-of-round card/Joker effects, economy, Boss defeat, or shop
entry. Higher-level transitions must compose these primitives in source order.

Pinned vanilla movement semantics:

* ``draw_from_hand_to_discard`` repeatedly draws from a hand CardArea; with no
  explicit card, ``CardArea:remove_card`` removes index 1, and destination
  ``emplace`` appends. The visible hand order is therefore appended to the
  discard tail unchanged.
* ``draw_from_discard_to_deck`` repeatedly draws from a discard CardArea; with no
  explicit card, ``remove_card`` removes the *last* discard card and deck
  ``emplace`` appends. The complete discard area is therefore appended to the
  existing deck in reverse order.
* ``draw_from_deck_to_hand(1)`` removes the physical deck tail. This matters for
  Chicot disabling The Manacle because that draw occurs before the later
  ``G.deck:shuffle("nr" .. ante)`` event.

The retained physical order is otherwise normally irrelevant because the next
``CardArea:shuffle`` re-sorts by ``sort_id`` before consuming shuffle RNG.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.deal import _public_card_sort_key
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _same_objects(left: list[BalatroCard], right: list[BalatroCard]) -> bool:
    return len(left) == len(right) and {id(card) for card in left} == {
        id(card) for card in right
    }


def _require_exact_round_end_partition(run: HeadlessRunState) -> None:
    state = run.public
    # Once the current deck is only the still-drawable subset, permanent-card
    # truth must come from owned_deck. Never fall back to the partial public deck.
    if state.owned_deck is None:
        raise HeadlessTransitionError(
            "round-end repopulation requires authoritative owned_deck"
        )
    order = run.require_playing_card_order()

    if run.played_pile:
        raise HeadlessTransitionError(
            "round-end repopulation requires all played cards already returned to discard"
        )
    if not _same_objects(run.draw_pile, state.deck):
        raise HeadlessTransitionError(
            "round-end private draw pile and public deck disagree"
        )
    if len(run.discard_pile) != len(state.discard_pile) or any(
        left is not right
        for left, right in zip(run.discard_pile, state.discard_pile, strict=True)
    ):
        raise HeadlessTransitionError(
            "round-end private/public discard order is not authoritative"
        )

    zones = [*run.draw_pile, *run.discard_pile, *state.hand]
    if len({id(card) for card in zones}) != len(zones):
        raise HeadlessTransitionError("round-end card zones contain duplicate objects")
    if not _same_objects(zones, order):
        raise HeadlessTransitionError(
            "round-end card zones do not exactly partition permanent playing cards"
        )


def repopulate_round_end_deck(run: HeadlessRunState) -> HeadlessRunState:
    """Move remaining hand/discard cards back to the physical deck exactly.

    The input phase is intentionally not rewritten here: this is a low-level
    source-order primitive that higher-level round completion will compose with
    reward/economy/shop state. RNG is untouched.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    _require_exact_round_end_partition(run)

    next_run = run.copy()
    next_state = next_run.public

    # draw_from_hand_to_discard: pop hand index 1 repeatedly, append to discard.
    # Since that preserves the current visible hand sequence, it is equivalent
    # to appending the whole current list in order.
    next_run.discard_pile.extend(next_state.hand)
    next_state.discard_pile.extend(next_state.hand)
    next_state.hand = []

    # draw_from_discard_to_deck: pop the discard tail repeatedly and append to
    # the existing deck area, reversing the complete physical discard sequence.
    while next_run.discard_pile:
        card = next_run.discard_pile.pop()
        public_card = next_state.discard_pile.pop()
        if card is not public_card:
            raise HeadlessTransitionError(
                "round-end copied discard order diverged during repopulation"
            )
        next_run.draw_pile.append(card)

    next_state.deck = sorted(next_run.draw_pile, key=_public_card_sort_key)
    return next_run


def require_full_retained_preblind_deck(run: HeadlessRunState) -> None:
    """Prove that BLIND_SELECT retains all permanent cards in physical deck order."""
    state = run.public
    if state.owned_deck is None:
        raise HeadlessTransitionError(
            "retained pre-blind deck requires authoritative owned_deck"
        )
    if state.hand or state.discard_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError(
            "retained pre-blind deck requires empty hand/discard/play zones"
        )
    if not run.draw_pile:
        raise HeadlessTransitionError("retained pre-blind physical deck is unavailable")
    if not _same_objects(run.draw_pile, state.deck):
        raise HeadlessTransitionError(
            "retained pre-blind physical/public deck composition disagrees"
        )
    order = run.require_playing_card_order()
    if not _same_objects(run.draw_pile, order):
        raise HeadlessTransitionError(
            "retained pre-blind deck is not the complete permanent deck"
        )


def draw_one_retained_preblind_card(run: HeadlessRunState) -> HeadlessRunState:
    """Draw the retained physical deck tail before the normal round-start shuffle.

    This is the exact card-movement primitive needed by vanilla Manacle
    ``Blind:disable`` at Chicot timing.  It intentionally consumes no RNG and
    never reconstructs physical order from the canonical public ``deck``.

    The caller owns hand-size restoration and later ``nr{ante}`` shuffle/deal.
    This primitive owns only one tail removal, one hand emplacement, and public
    deck canonicalization.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if run.public.phase != "BLIND_SELECT":
        raise HeadlessTransitionError(
            "retained pre-blind draw requires BLIND_SELECT phase"
        )
    if run.public.hand_size <= 0:
        raise HeadlessTransitionError(
            "retained pre-blind draw requires positive hand capacity"
        )
    require_full_retained_preblind_deck(run)

    next_run = run.copy()
    next_state = next_run.public
    card = next_run.draw_pile.pop()
    next_state.hand.append(card)
    next_state.deck = sorted(next_run.draw_pile, key=_public_card_sort_key)
    return next_run
