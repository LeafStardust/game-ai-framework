"""Exact transient playing-card debuffs for audited Boss families.

Vanilla ``Blind:set_blind`` walks every permanent playing card after Boss-specific
resource mutations and before Joker ``setting_blind`` effects.

Current exact base-deck families:

* Goad / Window / Head / Club: suit debuffs;
* The Plant: ``card:is_face(true)`` debuff, including Pareidolia making every
  playing card a face card.

These helpers intentionally support only the untouched base 52-card rank/suit
composition with no suit/rank-changing enhancement or other persistent card
mutation. Modified decks remain fail-closed until those predicates are exact.
"""

from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.pareidolia import PareidoliaJoker


_STATIC_SUIT_BOSS_TO_SUIT = {
    "The Goad": "Spades",
    "The Window": "Diamonds",
    "The Head": "Hearts",
    "The Club": "Clubs",
}
_FACE_RANKS = frozenset({"J", "Q", "K"})
_RANKS = frozenset({"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"})
_SUITS = frozenset({"Spades", "Hearts", "Diamonds", "Clubs"})
_BASE_IDENTITIES = frozenset((rank, suit) for rank in _RANKS for suit in _SUITS)


def _require_exact_base_permanent_cards(
    run: HeadlessRunState,
    *,
    label: str,
) -> list[BalatroCard]:
    state = run.public
    cards = run.require_playing_card_order()
    if len(cards) != 52:
        raise HeadlessTransitionError(
            f"{label} requires exact base 52-card composition"
        )
    identities = [(card.rank, card.suit) for card in cards]
    if len(set(identities)) != 52 or set(identities) != _BASE_IDENTITIES:
        raise HeadlessTransitionError(
            f"{label} requires exact base 52-card composition"
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
            f"{label} does not yet own modified playing cards"
        )
    if any(card.debuffed for card in cards):
        raise HeadlessTransitionError(
            f"{label} requires clean pre-blind card debuff state"
        )

    # Before the initial deal the public deck must still be the complete physical
    # playing-card collection. Require object identity so we never mutate a
    # detached semantic copy while the shuffle consumes another card set.
    if len(state.deck) != 52 or {id(card) for card in state.deck} != {id(card) for card in cards}:
        raise HeadlessTransitionError(
            f"{label} requires complete authoritative pre-deal deck"
        )
    return cards


def _pareidolia_active(run: HeadlessRunState) -> bool:
    """Mirror ``next(find_joker('Pareidolia'))`` for the owned Joker inventory.

    Vanilla's call does not request the ``non_debuff`` filter, so identity alone
    is enough here; a debuffed Pareidolia would still make ``Card:is_face(true)``
    return true.
    """
    return any(type(joker) is PareidoliaJoker for joker in run.public.jokers)


def apply_static_suit_boss_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Apply exact pre-deal suit debuffs for Goad/Window/Head/Club."""
    suit = _STATIC_SUIT_BOSS_TO_SUIT.get(run.public.boss_name)
    if suit is None:
        raise HeadlessTransitionError("boss has no audited static suit debuff")
    _require_exact_base_permanent_cards(run, label="static suit Boss debuff")

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = card.suit == suit
    return next_run


def clear_static_suit_boss_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror disable/defeat clearing of this Boss-owned transient debuff."""
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


def apply_plant_face_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Apply The Plant's exact ``card:is_face(true)`` debuff on the base deck."""
    if run.public.boss_name != "The Plant":
        raise HeadlessTransitionError("Plant debuff requires The Plant boss")
    _require_exact_base_permanent_cards(run, label="Plant face-card debuff")

    all_face = _pareidolia_active(run)
    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = all_face or card.rank in _FACE_RANKS
    return next_run


def clear_plant_face_debuff(run: HeadlessRunState) -> HeadlessRunState:
    """Mirror Plant disable/defeat clearing on the exact owned base-card set."""
    if run.public.boss_name != "The Plant":
        raise HeadlessTransitionError("Plant cleanup requires The Plant boss")

    cards = run.require_playing_card_order()
    if len(cards) != 52:
        raise HeadlessTransitionError(
            "Plant cleanup requires exact base permanent-card set"
        )
    all_face = _pareidolia_active(run)
    expected = [card for card in cards if all_face or card.rank in _FACE_RANKS]
    if len(expected) not in {12, 52}:
        raise HeadlessTransitionError("Plant cleanup cannot prove owned face debuffs")
    if any(not card.debuffed for card in expected):
        raise HeadlessTransitionError(
            "Plant cleanup requires active owned face-card debuffs"
        )
    if any(card.debuffed for card in cards if card not in expected):
        raise HeadlessTransitionError(
            "Plant cleanup encountered unowned card debuff"
        )

    next_run = run.copy()
    for card in next_run.require_playing_card_order():
        card.debuffed = False
    return next_run
