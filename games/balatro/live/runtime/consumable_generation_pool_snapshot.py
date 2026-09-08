"""Attach authoritative Tarot/Planet generation eligibility to live snapshots."""

from __future__ import annotations

from typing import Any

from .consumable_generation_pool_observer import observe_consumable_generation_pools
from .luajit_memory import LuaValue
from .luajit_non_gc64_memory import LuaJITNonGC64Decoder


def augment_consumable_generation_pool_payload(
    decoder: LuaJITNonGC64Decoder,
    root: dict[str, LuaValue],
    payload: dict[str, Any],
) -> None:
    """Attach one all-or-nothing canonical observation to ``payload`` in place."""
    pools = observe_consumable_generation_pools(decoder, root)
    if pools is None:
        payload["consumable_generation_pool_observed"] = False
        payload.pop("consumable_generation_pools", None)
        return

    payload["consumable_generation_pool_observed"] = True
    payload["consumable_generation_pools"] = {
        card_type: [dict(record) for record in records]
        for card_type, records in pools.items()
    }
