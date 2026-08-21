from __future__ import annotations

"""Telemetry-backed Ten-Four / Walkie Talkie relationship calibration.

Effective Red/White semantics:

* Walkie Talkie alone -> Silver.
* Even Steven alone -> Silver for Ten-Four.
* Walkie Talkie + Even Steven -> Walkie Talkie is conditionally Gold while
  Even Steven remains Silver.

The state-dependent promotion is resolved by ``conditional_joker_relationship``.
This module only normalizes the static catalogue to Silver/Silver; it deliberately
never monkey-patches ``_assess`` or ``evaluate_item`` so tree/state-aware trackers
retain their own assessment pipeline.
"""

from dataclasses import replace

from games.balatro.strategy import BalatroStrategyTracker, build_component_strategy_index


_TEN_FOUR = "ten_four"
_WALKIE = frozenset({"walkietalkie", "walkietalkiejoker"})
_EVEN = frozenset({"evensteven", "evenstevenjoker"})


def _static_ten_four(definition):
    walkie_even = set(_WALKIE | _EVEN)
    return replace(
        definition,
        gold_jokers=frozenset(set(definition.gold_jokers) - walkie_even),
        silver_jokers=frozenset(set(definition.silver_jokers) | walkie_even),
        bronze_jokers=frozenset(set(definition.bronze_jokers) - walkie_even),
    )


def install_ten_four_strategy_calibration() -> None:
    if getattr(BalatroStrategyTracker, "_ten_four_strategy_calibration_installed", False):
        return

    original_init = BalatroStrategyTracker.__init__

    def __init__(self, definitions, *args, **kwargs):
        calibrated = dict(definitions)
        if _TEN_FOUR in calibrated:
            calibrated[_TEN_FOUR] = _static_ten_four(calibrated[_TEN_FOUR])
        original_init(self, calibrated, *args, **kwargs)
        self.component_index = build_component_strategy_index(self.definitions)

    BalatroStrategyTracker.__init__ = __init__
    BalatroStrategyTracker._ten_four_strategy_calibration_installed = True
