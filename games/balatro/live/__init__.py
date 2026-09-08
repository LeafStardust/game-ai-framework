"""Balatro live integration primitives and production runtime wiring.

The live package exposes a convenient public surface, but importing a specific
submodule such as ``games.balatro.live.final_joker_outcomes`` must not eagerly load
unrelated build-health/strategy modules.  Eager package imports create a cycle while
Bond composition is still initializing:

``bonds.composer -> build.literal_score_expectation -> live.final_joker_outcomes
-> live.__init__ -> live.bond_health -> bonds.build_health -> bonds.composer``.

Keep the public package API while resolving exports lazily on first access.
"""

from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    "LiveBondHealthSnapshot": (".bond_health", "LiveBondHealthSnapshot"),
    "evaluate_live_build_health": (".bond_health", "evaluate_live_build_health"),
    "score_projection_from_blind_plan": (".bond_health", "score_projection_from_blind_plan"),
    "score_projection_from_live_play": (".bond_health", "score_projection_from_live_play"),
    "LiveStrategyHealth": (".strategy_health", "LiveStrategyHealth"),
    "StrategyHealthMode": (".strategy_health", "StrategyHealthMode"),
    "evaluate_live_strategy_health": (".strategy_health", "evaluate_live_strategy_health"),
    "HOLD": (".consumable_timing", "HOLD"),
    "USE": (".consumable_timing", "USE"),
    "ConsumableTimingRecommendation": (".consumable_timing", "ConsumableTimingRecommendation"),
    "LiveConsumableTimingPolicy": (".consumable_timing", "LiveConsumableTimingPolicy"),
    "LiveBalatroSnapshot": (".protocol", "LiveBalatroSnapshot"),
    "BalatroShopActionGenerator": (".shop", "BalatroShopActionGenerator"),
    "LiveShopItem": (".shop", "LiveShopItem"),
    "LiveShopItemFactory": (".shop", "LiveShopItemFactory"),
    "BufferedShopTransaction": (".shop_sync", "BufferedShopTransaction"),
    "UnsupportedBufferedShopAction": (".shop_sync", "UnsupportedBufferedShopAction"),
    "DefaultBalatroStateTranslator": (".translator", "DefaultBalatroStateTranslator"),
}


__all__ = list(_EXPORTS)


def __getattr__(name: str):
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__():
    return sorted((*globals().keys(), *_EXPORTS.keys()))
