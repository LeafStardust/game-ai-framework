from __future__ import annotations

from games.balatro.live.protocol import LiveBalatroSnapshot


def standard_pack_card_added(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
) -> bool:
    """Verify the visible semantic effect of a Standard-Pack card selection."""
    before_cards = before.payload.get("cards")
    after_cards = after.payload.get("cards")
    if not isinstance(before_cards, dict) or not isinstance(after_cards, dict):
        return False
    before_values = before_cards.get("cards")
    after_values = after_cards.get("cards")
    if not isinstance(before_values, list) or not isinstance(after_values, list):
        return False
    return len(after_values) == len(before_values) + 1
