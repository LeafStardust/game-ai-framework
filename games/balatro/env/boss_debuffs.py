"""Exact transient card debuffs for the first audited static-suit Boss family.

Vanilla ``Blind:set_blind`` walks every permanent playing card after Boss-specific
resource mutations and before Joker ``setting_blind`` effects.  For The Goad,
Window, Head and Club it debuffs cards matching one suit via ``card:is_suit``.

This first headless slice intentionally supports only the untouched base 52-card
rank/suit composition with no suit-changing enhancement or other persistent card
mutation.  On that boundary ``card:is_suit(..., true)`` is exactly equivalent to
current base suit equality.  Modified decks remain fail-closed until Wild/suit
conversion semantics are explicitly owned.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


_STATIC_SUIT_BOSS_TO_SUIT = {
    "The Goad": "Spades",
    "The Window": "Diamonds",
    "The Head": "Hearts",
    "The Club": "Clubs",
}

_RANKS = frozenset({"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"})
_SUITS = frozenset({"Spades", "Hearts", "Diamonds", "Clubs"})
_BASE_IDENTITIES = frozenset((rank, suit) for rank in _RANKS for suit in _SUITS)


def _require_exact_base_permanent_cards(run: HeadlessRunState) -> list[BalatroCard]:
    state = run.public
    cards = run.require_playing_card_order()
    if len(cards) != 52:
        raise HeadlessTransitionError(
            "static suit Boss debuff requires exact base 52-card composition"
        )
    identities = [(card.rank, card.suit) for card in cards]
    if len(set(identities)) != 52 or set(identities) != _BASE_IDENTITIES:
        raise HeadlessTransitionError(
            "static suit Boss debuff requires exact base 52-card composition"
        )
    if any(
        card.live_id is not None
        or card.enhancement is not None
        or card.edition is not None
        or card.seal is not None
        or card.permanent_bonus != 0
        or card.forced_selection
        or card.original_suit_nominal is not None
        for card in cards
    ):
        raise HeadlessTransitionError(
            "static suit Boss debuff does not yet own modified playing cards"
        )
    if any(card.debuffed for card in cards):
        raise HeadlessTransitionError(
            "static suit Boss debuff requires clean pre-blind card debuff state"
        )

    # Before the initial deal the public deck must still be the complete physical
    # playing-card collection.  Require object identity so we never mutate a
    # detached semantic copy while the shuffle consumes another card set.
    if len(state.deck) != 52 or {id(card) for card in state.deck} != {id(card) for card in cards}:
        raise HeadlessTransitionError(
            "static suit Boss debuff requires complete authoritative pre-deal deck"
        )
    return cards


def apply_static_suit_boss_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Apply exact pre-deal suit debuffs for Goad/Window/Head/Club."""
    suit = _STATIC_SUIT_BOSS_TO_SUIT.get(run.public.boss_name)
    if suit is None:
        raise HeadlessTransitionError("boss has no audited static suit debuff")
    _require_exact_base_permanent_cards(run)

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = card.suit == suit
    return next_run


def clear_static_suit_boss_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror disable/defeat clearing of this Boss-owned transient debuff.

    Start requires a completely clean debuff state, so every active debuff on the
    exact base-card boundary is owned by this Boss and may be cleared safely.
    The retained playing-card order spans hand/draw/discard zones after dealing.
    """
    suit = _STATIC_SUIT_BOSS_TO_SUIT.get(run.public.boss_name)
    if suit is None:
        raise HeadlessTransitionError("boss has no audited static suit debuff cleanup")

    cards = run.require_playing_card_order()
    matching = [card for card in cards if card.suit == suit]
    if len(cards) != 52 or len(matching) != 13:
        raise HeadlessTransitionError(
            "static suit Boss cleanup requires exact base permanent-card set"
        )
    if any(not card.debuffed for card in matching):
        raise HeadlessTransitionError(
            "static suit Boss cleanup requires active owned suit debuffs"
        )
    if any(card.debuffed for card in cards if card.suit != suit):
        raise HeadlessTransitionError(
            "static suit Boss cleanup encountered unowned card debuff"
        )

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = False
    return next_run
