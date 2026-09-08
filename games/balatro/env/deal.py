"""Exact R2 round-start shuffle/deal primitives.

This module deliberately does **not** expose ``SELECT_BLIND``. It owns the
source-order slice beginning once lifecycle setup has entered ``DRAW_TO_HAND``
with every permanent playing card back in the deck.

The generalized boundary remains deliberately strict. Modified decks are
supported only when the simulator can prove that the current complete deck and
its authoritative permanent owned deck are the same card objects, retained
creation order is exact, and every card carries Balatro's original-suit nominal
needed by ``Card:get_nominal()``. A structurally untouched base 52-card deck may
also carry transient blind debuff flags: those do not alter rank/suit history, so
its original suit remains provably equal to its current suit. Anything less
fails closed before RNG advances.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
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

_ORIGINAL_SUIT_NOMINAL = frozenset({0.001, 0.002, 0.003, 0.004})

_VANILLA_BASE_IDENTITIES = frozenset(
    (rank, suit)
    for rank in _RANK_NOMINAL
    for suit in _SUIT_NOMINAL
)


def _is_provably_base_order_allowing_transient_debuff(
    cards: list[BalatroCard],
) -> bool:
    """Return whether only transient ``debuffed`` state may differ from base.

    Debuff is applied by ``Blind:set_blind`` after card creation and never changes
    the card's base rank/suit or original-suit nominal.  This narrow structural
    proof therefore lets static debuff Bosses reach the exact shuffle/deal path
    without pretending other mutations (enhancements, conversions, editions,
    seals, permanent bonuses, forced selection, or live-created cards) are base.
    """
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
        and card.permanent_bonus == 0
        and not card.forced_selection
        and card.original_suit_nominal is None
        for card in cards
    )


def _is_provably_pristine_base_order(cards: list[BalatroCard]) -> bool:
    return _is_provably_base_order_allowing_transient_debuff(cards) and all(
        not card.debuffed for card in cards
    )


def _card_original_suit_nominal(card: BalatroCard, *, pristine: bool) -> float:
    if pristine:
        try:
            return _SUIT_NOMINAL[card.suit] / 10.0
        except KeyError as exc:
            raise HeadlessTransitionError("card has no exact vanilla original suit") from exc

    value = card.original_suit_nominal
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or float(value) not in _ORIGINAL_SUIT_NOMINAL
    ):
        raise HeadlessTransitionError(
            "modified round-start deal requires exact original-suit nominal"
        )
    return float(value)


def _vanilla_hand_primary_nominal(card: BalatroCard, *, pristine: bool) -> float:
    """Mirror the non-unique portion of vanilla ``Card:get_nominal()``."""
    try:
        rank = _RANK_NOMINAL[card.rank]
        face = _FACE_NOMINAL.get(card.rank, 0.0)
        suit = _SUIT_NOMINAL[card.suit]
    except KeyError as exc:
        raise HeadlessTransitionError("card has no exact vanilla nominal") from exc

    original_suit = _card_original_suit_nominal(card, pristine=pristine)
    mult = -1000.0 if card.is_stone else 1.0
    return rank + suit * mult + original_suit * 0.0001 * mult + face


def _public_card_sort_key(card: BalatroCard) -> tuple[str, ...]:
    """Mirror the observer's non-future-order public deck canonicalizer."""
    return (
        str(card.suit or ""),
        str(card.rank or ""),
        str(card.enhancement or ""),
        str(card.edition or ""),
        str(card.seal or ""),
        str(card.permanent_bonus or ""),
        str(card.live_id or ""),
    )


def _hand_sort_key(
    card: BalatroCard,
    *,
    pristine: bool,
    creation_index: dict[int, int],
) -> tuple[float, int]:
    return (
        _vanilla_hand_primary_nominal(card, pristine=pristine),
        -creation_index[id(card)],
    )


def _require_empty_round_start_zones(run: HeadlessRunState) -> None:
    state = run.public
    if state.phase != "DRAW_TO_HAND":
        raise HeadlessTransitionError("round-start deal requires DRAW_TO_HAND phase")
    if state.hand or state.discard_pile:
        raise HeadlessTransitionError(
            "round-start deal requires empty public hand/discard zones"
        )
    if run.draw_pile or run.discard_pile or run.played_pile:
        raise HeadlessTransitionError(
            "round-start deal requires empty private card zones"
        )


def _modified_complete_owned_order(run: HeadlessRunState) -> list[BalatroCard]:
    state = run.public
    if state.owned_deck is None:
        raise HeadlessTransitionError(
            "modified round-start deal requires authoritative owned deck"
        )
    order = run.require_playing_card_order()
    if len(state.deck) != len(order):
        raise HeadlessTransitionError(
            "current deck is not a complete permanent-card collection"
        )

    # This is intentionally stronger than semantic equality. Headless transitions
    # must retain one canonical card object per owned playing card so mutations,
    # creation order, and future zone movement cannot silently diverge.
    if {id(card) for card in state.deck} != {id(card) for card in order}:
        raise HeadlessTransitionError(
            "current deck must reference the authoritative owned cards exactly"
        )

    for card in order:
        _vanilla_hand_primary_nominal(card, pristine=False)
    return order


def deal_supported_round_start(run: HeadlessRunState) -> HeadlessRunState:
    """Shuffle and deal an exact supported round-start card collection.

    Vanilla draws ``min(#deck, hand capacity)`` cards, so short exact decks are
    allowed. The input state and RNG remain unchanged on every rejected path.
    """
    _require_empty_round_start_zones(run)

    order = run.require_playing_card_order()
    infer_base_original_suit = _is_provably_base_order_allowing_transient_debuff(order)
    if not infer_base_original_suit:
        order = _modified_complete_owned_order(run)

    next_run = run.copy()
    next_state = next_run.public
    next_order = next_run.require_playing_card_order()

    if infer_base_original_suit and next_state.owned_deck is None:
        next_state.owned_deck = list(next_order)

    draw_pile = list(next_order)
    next_run.rng.shuffle_in_place(draw_pile, f"nr{next_state.ante}")

    # Vanilla draw_from_deck_to_hand uses min(#G.deck.cards, hand space).
    deal_count = min(len(draw_pile), next_state.hand_size)
    dealt = [draw_pile.pop() for _ in range(deal_count)]

    creation_index = {id(card): index for index, card in enumerate(next_order)}
    next_run.draw_pile = draw_pile
    next_state.hand = sorted(
        dealt,
        key=lambda card: _hand_sort_key(
            card,
            pristine=infer_base_original_suit,
            creation_index=creation_index,
        ),
        reverse=True,
    )
    # Never expose hidden physical draw order through canonical public state.
    next_state.deck = sorted(draw_pile, key=_public_card_sort_key)
    next_state.phase = "SELECTING_HAND"
    return next_run


def draw_one_supported_card_to_hand(run: HeadlessRunState) -> HeadlessRunState:
    """Draw one exact card from the owned physical draw pile into the hand.

    This owns the deterministic draw used by effects such as disabling The
    Manacle after its initial deal.  It deliberately requires an already-owned
    physical draw pile; a pre-shuffle ``G.deck`` state is not reconstructed from
    the public canonical deck ordering.
    """
    state = run.public
    if state.phase != "SELECTING_HAND":
        raise HeadlessTransitionError(
            "single-card headless draw requires SELECTING_HAND phase"
        )
    if len(state.hand) >= state.hand_size:
        raise HeadlessTransitionError(
            "single-card headless draw requires free hand capacity"
        )
    if len(run.draw_pile) != len(state.deck):
        raise HeadlessTransitionError(
            "private draw pile and public remaining deck size disagree"
        )
    if {id(card) for card in run.draw_pile} != {id(card) for card in state.deck}:
        raise HeadlessTransitionError(
            "private draw pile and public remaining deck cards disagree"
        )
    if not run.draw_pile:
        return run.copy()

    order = run.require_playing_card_order()
    infer_base_original_suit = _is_provably_base_order_allowing_transient_debuff(order)
    if not infer_base_original_suit:
        for card in order:
            _vanilla_hand_primary_nominal(card, pristine=False)

    next_run = run.copy()
    next_state = next_run.public
    next_order = next_run.require_playing_card_order()
    creation_index = {id(card): index for index, card in enumerate(next_order)}

    card = next_run.draw_pile.pop()
    next_state.hand.append(card)
    next_state.hand.sort(
        key=lambda value: _hand_sort_key(
            value,
            pristine=infer_base_original_suit,
            creation_index=creation_index,
        ),
        reverse=True,
    )
    next_state.deck = sorted(next_run.draw_pile, key=_public_card_sort_key)
    return next_run


def deal_pristine_round_start(run: HeadlessRunState) -> HeadlessRunState:
    """Backward-compatible exact pristine-base wrapper."""
    _require_empty_round_start_zones(run)
    order = run.require_playing_card_order()
    if not _is_provably_pristine_base_order(order):
        raise HeadlessTransitionError(
            "exact pristine base-card hand sort is unavailable for this deck"
        )
    return deal_supported_round_start(run)
