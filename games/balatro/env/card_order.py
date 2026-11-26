"""Exact private playing-card creation order for deterministic shuffles.

Balatro's ``pseudoshuffle`` sorts card areas by each card's monotonic ``sort_id``
before consuming RNG.  The public model intentionally does not expose that
engine-private identifier.  For playing cards we can still recover the exact
relative order in two narrowly audited cases:

* live/public snapshots where every owned playing card has a unique exact
  integer ``playing_card`` id (stored as :attr:`BalatroCard.live_id`), because
  both ``sort_id`` and ``playing_card`` increase with playing-card creation; and
* an untouched 52-card base composition containing exactly one card of every
  vanilla rank/suit pair, whose initial creation order is the source game's
  lexicographically sorted control-code order.

Structural inference otherwise fails closed. In particular, mixed/missing live ids or a deck
with duplicated/missing rank-suit identities cannot safely reconstruct creation
order after card creation/destruction/rank conversion mechanics.
"""

from __future__ import annotations

from collections.abc import Sequence

from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState


_VANILLA_SUIT_CODE = {
    "Clubs": "C",
    "Diamonds": "D",
    "Hearts": "H",
    "Spades": "S",
}

_VANILLA_RANK_CODE = {
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "10": "T",
    "J": "J",
    "Q": "Q",
    "K": "K",
    "A": "A",
}

_VANILLA_BASE_CREATION_ORDER = tuple(
    (rank, suit)
    for suit in sorted(_VANILLA_SUIT_CODE, key=_VANILLA_SUIT_CODE.get)
    for rank in sorted(_VANILLA_RANK_CODE, key=_VANILLA_RANK_CODE.get)
)
_VANILLA_BASE_IDENTITIES = frozenset(_VANILLA_BASE_CREATION_ORDER)

BASE_DECK_CARD_COUNT = len(_VANILLA_BASE_CREATION_ORDER)
MAX_DNA_DECK_CARDS = BASE_DECK_CARD_COUNT + 30


def has_bounded_base_copy_order(
    cards: Sequence[BalatroCard], removed_base_six_suits: tuple[str, ...] = (),
) -> bool:
    """Validate retained base survivors followed by distinct copy objects."""
    if type(removed_base_six_suits) is not tuple:
        return False
    expected = _VANILLA_BASE_CREATION_ORDER
    if removed_base_six_suits:
        if (
            any(type(suit) is not str or suit not in _VANILLA_SUIT_CODE
                for suit in removed_base_six_suits)
            or tuple(sorted(set(removed_base_six_suits))) != removed_base_six_suits
        ):
            return False
        removed = {("6", suit) for suit in removed_base_six_suits}
        expected = tuple(identity for identity in expected if identity not in removed)

    base_count = len(expected)
    if not base_count <= len(cards) <= MAX_DNA_DECK_CARDS - len(removed_base_six_suits):
        return False
    if len({id(card) for card in cards}) != len(cards):
        return False

    base = cards[:base_count]
    actual = tuple((card.rank, card.suit) for card in base)
    if all(card.live_id is None for card in base):
        # A surviving DNA copy cannot replace an absent original in the prefix.
        if actual != expected:
            return False
    elif set(actual) != set(expected):
        # A live snapshot can prove a different creation order via its card IDs.
        return False
    return all((card.rank, card.suit) in _VANILLA_BASE_IDENTITIES for card in cards[base_count:])


def vanilla_playing_card_sort_key(card: BalatroCard) -> str:
    """Return the source game's initial playing-card control-code sort key."""
    try:
        return _VANILLA_SUIT_CODE[card.suit] + _VANILLA_RANK_CODE[card.rank]
    except KeyError as exc:
        raise ValueError(
            f"card has no vanilla playing-card control code: {card.rank!r} {card.suit!r}"
        ) from exc


def derive_playing_card_order(state: BalatroState) -> list[BalatroCard] | None:
    """Recover exact relative ``sort_id`` order when the public state proves it.

    The returned list contains the *same card objects* as the authoritative
    source collection; callers may retain it as simulator-private creation order.
    ``None`` means the order cannot be reconstructed exactly and shuffle-dependent
    transitions must remain unavailable.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    cards = state.owned_deck if state.owned_deck is not None else state.deck
    if not isinstance(cards, list) or any(not isinstance(card, BalatroCard) for card in cards):
        return None

    live_ids = [card.live_id for card in cards]
    if live_ids and all(type(value) is int for value in live_ids):
        if len(set(live_ids)) != len(live_ids):
            return None
        return sorted(cards, key=lambda card: card.live_id)

    # A partially observed identity stream cannot be combined with structural
    # inference: once any card carries a live creation id, all cards must do so.
    if any(value is not None for value in live_ids):
        return None

    # Structural reconstruction is safe only for the original one-of-each base
    # rank/suit composition.  Any creation/destruction/rank conversion produces
    # duplicate or missing identities and therefore fails this exact-set test.
    identities = [(card.rank, card.suit) for card in cards]
    if len(identities) != 52 or set(identities) != _VANILLA_BASE_IDENTITIES:
        return None
    if len(set(identities)) != len(identities):
        return None

    return sorted(cards, key=vanilla_playing_card_sort_key)


def playing_card_order_matches(
    order: Sequence[BalatroCard],
    state: BalatroState,
) -> bool:
    """Return whether ``order`` is exactly the authoritative owned-card objects."""
    if not isinstance(order, Sequence) or isinstance(order, (str, bytes)):
        return False
    if any(not isinstance(card, BalatroCard) for card in order):
        return False

    cards = state.owned_deck if state.owned_deck is not None else state.deck
    if not isinstance(cards, list) or len(order) != len(cards):
        return False

    return {id(card) for card in order} == {id(card) for card in cards}
