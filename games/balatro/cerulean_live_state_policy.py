from __future__ import annotations

"""Expose Cerulean Bell's public forced-selection flag end to end.

Balatro stores the currently forced playing-card selection on
``card.ability.forced_selection``.  The live observer already reads the card's
ability table for permanent bonuses, but the boolean was previously dropped from
the normalized snapshot, and the state translator therefore could not hydrate
``BalatroCard.forced_selection``.  D1's Cerulean legality/branching logic depends
on that public flag.

Keep the correction narrow: add one public boolean at the observer boundary and
copy that boolean onto the existing card model.  No score or action preference is
introduced here.
"""

from games.balatro.live.runtime import live_memory_observer
from games.balatro.live.translator import DefaultBalatroStateTranslator


def install_cerulean_live_state_policy() -> None:
    if getattr(DefaultBalatroStateTranslator, "_cerulean_live_state_installed", False):
        return

    original_normalize_card = live_memory_observer._normalize_card
    original_translate_card = DefaultBalatroStateTranslator._card

    def normalize_card(decoder, address: int):
        result = original_normalize_card(decoder, address)
        card = decoder.string_fields(address)
        ability = live_memory_observer._table_fields(decoder, card.get("ability"))
        result["forced_selection"] = live_memory_observer._boolean(
            ability.get("forced_selection"),
            False,
        )
        return result

    def translate_card(self, card: dict, live_id):
        result = original_translate_card(self, card, live_id)
        result.forced_selection = bool(card.get("forced_selection", False))
        return result

    live_memory_observer._normalize_card = normalize_card
    DefaultBalatroStateTranslator._card = translate_card
    DefaultBalatroStateTranslator._cerulean_live_state_installed = True
