from __future__ import annotations

from dataclasses import dataclass

from .live_memory_observer import (
    _array_table_values,
    _number,
    _table_fields,
)


@dataclass(frozen=True)
class LivePackSelectionTerms:
    """Public current-pack selection terms read from Balatro process memory."""

    choices_remaining: int
    choice_addresses: tuple[int, ...]


def read_live_pack_selection_terms(observer) -> LivePackSelectionTerms:
    """Read remaining pack picks and visible choice identities without writing state."""

    decoder, _, root = observer._root()
    game = _table_fields(decoder, root.get("GAME"))
    choices_remaining = _number(game.get("pack_choices"))
    if choices_remaining is None:
        raise RuntimeError("live Balatro pack_choices is unavailable")

    pack_area = _table_fields(decoder, root.get("pack_cards"))
    choice_addresses = tuple(
        int(address)
        for _, address in _array_table_values(decoder, pack_area.get("cards"))
    )

    return LivePackSelectionTerms(
        choices_remaining=int(choices_remaining),
        choice_addresses=choice_addresses,
    )
