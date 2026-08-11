from __future__ import annotations

import hashlib
import json
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

    Integral Lua numeric IDs are canonicalized to Python ints. The production
    sequence advances only when logical agent-facing state changes; volatile UI
    geometry remains available for execution targeting but cannot masquerade as
    an authoritative game-state checkpoint.
    """

    def __init__(self, observer: LiveMemoryBalatroObserver | None = None) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self._sequence = 0
        self._last_logical_fingerprint: str | None = None

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

        fingerprint_payload = _without_ui_geometry(payload)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "phase": snapshot.phase,
                    "state_complete": snapshot.state_complete,
                    "payload": fingerprint_payload,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if fingerprint != self._last_logical_fingerprint:
            self._sequence += 1
            self._last_logical_fingerprint = fingerprint

        return LiveBalatroSnapshot(
            sequence=self._sequence,
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


def _without_ui_geometry(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_ui_geometry(item)
            for key, item in value.items()
            if key != "ui"
        }
    if isinstance(value, list):
        return [_without_ui_geometry(item) for item in value]
    return value
