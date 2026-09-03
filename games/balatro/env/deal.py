"""Exact R2 shuffle/deal primitive for the currently provable base-deck case.

This module deliberately does **not** expose ``SELECT_BLIND``.  It owns only the
source-order slice beginning once the lifecycle has already entered
``DRAW_TO_HAND`` with every permanent playing card back in the deck.

The first implementation is intentionally narrow: it requires the untouched
one-of-each 52-card base composition with no live ids.  That boundary is enough
to prove Balatro's keyed ``nr{ante}`` shuffle, tail draw direction, hidden draw
pile ownership, public remaining-deck canonicalization, and vanilla hand sort
without pretending we can reconstruct converted-card ``suit_nominal_original``
from the current public card schema.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.card_order import vanilla_playing_card_sort_key
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_RANK_NOMINAL = {
    "2": 2.0,
    "3": 3.0,
    "4": 4.0,
    "5": 5.0,
    "6": 6.0,
    "7": 7.0,
    "8": 8.0,
    "9": 9.0,
    "10": 10.0,
    "J": 10.0,
    "Q": 10.0,
    "K": 10.0,
    "A": 11.0,
}

_FACE_NOMINAL = {
    "J": 0.1,
    "Q": 0.2,
    "K": 0.3,
    "A": 0.4,
}

_SUIT_NOMINAL = {
    "Diamonds": 0.01,
    "Clubs": 0.02,
    "Hearts": 0.03,
    "Spades": 0.04,
}

_VANILLA_BASE_IDENTITIES = frozenset(
    (rank, suit)
    for rank in _RANK_NOMINAL
    for suit in _SUIT_NOMINAL
)


def _is_provably_pristine_base_order(cards: list[BalatroCard]) -> bool:
    if len(cards) != 52:
        return False
    if any(card.live_id is not None for card in cards):
        return False
    identities = [(card.rank, card.suit) for card in cards]
    if len(set(identities)) != 52 or set(identities) != _VANILLA_BASE_IDENTITIES:
        return False
    return all(
        card.enhancement is None
        and card.edition is None
        and card.seal is None
        and not card.debuffed
        and card.permanent_bonus == 0
        and not card.forced_selection
        for card in cards
    )


def _vanilla_pristine_hand_sort_key(card: BalatroCard) -> float:
    """Return vanilla ``Card:get_nominal()`` without the irrelevant unique tie.

    In this primitive every rank/suit identity is unique, so ``unique_val`` can
    never be the deciding term.  ``suit_nominal_original`` equals current suit
    nominal for an untouched base card and is included exactly.
    """
    try:
        rank = _RANK_NOMINAL[card.rank]
        face = _FACE_NOMINAL.get(card.rank, 0.0)
        suit = _SUIT_NOMINAL[card.suit]
    except KeyError as exc:
        raise HeadlessTransitionError("card has no exact vanilla nominal") from exc
    original_suit = suit / 10.0
    return rank + suit + original_suit * 0.0001 + face


def _public_card_sort_key(card: BalatroCard) -> tuple[str, ...]:
    """Mirror the live observer's public, non-future-order deck canonicalizer."""
    return (
        str(card.suit or ""),
        str(card.rank or ""),
        str(card.enhancement or ""),
        str(card.edition or ""),
        str(card.seal or ""),
        str(card.permanent_bonus or ""),
        str(card.live_id or ""),
    )


def deal_pristine_round_start(run: HeadlessRunState) -> HeadlessRunState:
    """Shuffle and deal one exact pristine base-deck round start.

    Preconditions intentionally describe the stable point immediately after
    blind/lifecycle setup has entered ``DRAW_TO_HAND`` and before any card has
    moved.  The input snapshot is never mutated.
    """
    state = run.public
    if state.phase != "DRAW_TO_HAND":
        raise HeadlessTransitionError(
            "pristine round-start deal requires DRAW_TO_HAND phase"
        )
    if state.hand or state.discard_pile:
        raise HeadlessTransitionError(
            "pristine round-start deal requires empty public hand/discard zones"
        )
    if run.draw_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError(
            "pristine round-start deal requires empty private card zones"
        )

    order = run.require_playing_card_order()
    if not _is_provably_pristine_base_order(order):
        raise HeadlessTransitionError(
            "exact pristine base-card hand sort is unavailable for this deck"
        )

    next_run = run.copy()
    next_state = next_run.public
    next_order = next_run.require_playing_card_order()

    # Headless ownership now has an explicit public permanent composition before
    # ``deck`` becomes the public *remaining* composition after the deal.
    if next_state.owned_deck is None:
        next_state.owned_deck = list(next_order)

    draw_pile = list(next_order)
    next_run.rng.shuffle_in_place(draw_pile, f"nr{next_state.ante}")

    deal_count = min(len(draw_pile), next_state.hand_size)
    dealt = [draw_pile.pop() for _ in range(deal_count)]

    next_run.draw_pile = draw_pile
    next_state.hand = sorted(
        dealt,
        key=_vanilla_pristine_hand_sort_key,
        reverse=True,
    )
    # Never expose the hidden physical draw order through canonical public state.
    next_state.deck = sorted(draw_pile, key=_public_card_sort_key)
    next_state.phase = "SELECTING_HAND"

    return next_run
