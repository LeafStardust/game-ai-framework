from __future__ import annotations

from games.balatro.live.protocol import LiveBalatroSnapshot


PlayingCardSignature = tuple[
    object,
    object,
    object | None,
    object | None,
    object | None,
]


def _area_cards(snapshot: LiveBalatroSnapshot, name: str) -> list[dict]:
    area = snapshot.payload.get(name)
    if not isinstance(area, dict):
        return []
    cards = area.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, dict)]


def standard_pack_card_signature(card: dict) -> PlayingCardSignature | None:
    value = card.get("value")
    if not isinstance(value, dict):
        return None

    rank = value.get("rank")
    suit = value.get("suit")
    if rank is None or suit is None:
        return None

    modifier = card.get("modifier")
    if not isinstance(modifier, dict):
        modifier = {}

    return (
        rank,
        suit,
        modifier.get("enhancement"),
        modifier.get("edition"),
        modifier.get("seal"),
    )


def _signature_count(
    cards: list[dict],
    signature: PlayingCardSignature,
) -> int:
    return sum(
        standard_pack_card_signature(card) == signature
        for card in cards
    )


def standard_pack_card_added(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
    *,
    expected_signature: PlayingCardSignature | None = None,
) -> bool:
    """Verify the visible semantic effect of a Standard-Pack card selection."""
    before_owned = _area_cards(before, "owned_cards")
    after_owned = _area_cards(after, "owned_cards")

    if before_owned or after_owned:
        before_cards = before_owned
        after_cards = after_owned
    else:
        # Retain the prior remaining-deck fallback for diagnostic/synthetic
        # snapshots that predate authoritative G.playing_cards observation.
        before_cards = _area_cards(before, "cards")
        after_cards = _area_cards(after, "cards")

    if len(after_cards) != len(before_cards) + 1:
        return False
    if expected_signature is None:
        return True

    return (
        _signature_count(after_cards, expected_signature)
        == _signature_count(before_cards, expected_signature) + 1
    )
