from __future__ import annotations

from copy import deepcopy
from typing import Any

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import LiveMemoryBalatroObserver


_ID_AREAS = (
    "hand",
    "cards",
    "jokers",
    "consumables",
    "shop_jokers",
    "shop_boosters",
    "shop_vouchers",
)


class ProductionBalatroObserver:
    """Agent-facing authoritative observer.

    The raw live-memory decoder preserves Lua numeric representation. Balatro IDs
    that are mathematically integral are normalized to Python ints here so stable
    identity matching does not depend on ``5`` versus ``5.0`` formatting.
    """

    def __init__(self, observer: LiveMemoryBalatroObserver | None = None) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()

    def observe(self) -> LiveBalatroSnapshot:
        snapshot = self.observer.observe()
        payload = deepcopy(snapshot.payload)
        for area_name in _ID_AREAS:
            area = payload.get(area_name)
            if not isinstance(area, dict):
                continue
            cards = area.get("cards")
            if not isinstance(cards, list):
                continue
            for card in cards:
                if not isinstance(card, dict):
                    continue
                card["live_id"] = _stable_identity(card.get("live_id"))

        return LiveBalatroSnapshot(
            sequence=snapshot.sequence,
            phase=snapshot.phase,
            state_complete=snapshot.state_complete,
            payload=payload,
        )

    def is_connected(self) -> bool:
        return self.observer.is_connected()

    def close(self) -> None:
        self.observer.close()

    def __enter__(self) -> "ProductionBalatroObserver":
        self.observer.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def _stable_identity(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
