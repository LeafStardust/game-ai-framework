"""Balatro live integration primitives and production runtime wiring."""

import sys as _sys

from .consumable_timing import (
    HOLD,
    USE,
    ConsumableTimingRecommendation,
    LiveConsumableTimingPolicy,
)
from .protocol import LiveBalatroSnapshot
from .shop import (
    BalatroShopActionGenerator,
    LiveShopItem,
    LiveShopItemFactory,
)
from .shop_sync import (
    BufferedShopTransaction,
    UnsupportedBufferedShopAction,
)
from .translator import DefaultBalatroStateTranslator
from . import runtime as _runtime

# Transitional import compatibility for callers created before the runtime
# namespace cleanup. The former external-control implementation itself is gone;
# this alias resolves only modules that now physically live in live.runtime.
_sys.modules[__name__ + ".external"] = _runtime

__all__ = [
    "BalatroShopActionGenerator",
    "BufferedShopTransaction",
    "ConsumableTimingRecommendation",
    "DefaultBalatroStateTranslator",
    "HOLD",
    "LiveBalatroSnapshot",
    "LiveConsumableTimingPolicy",
    "LiveShopItem",
    "LiveShopItemFactory",
    "USE",
    "UnsupportedBufferedShopAction",
]
