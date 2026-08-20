from __future__ import annotations

"""Ante-scaled strategy pressure for the Balatro run lifecycle.

The run lifecycle is intentionally asymmetric:

* Antes 1-2: Foundation. Survive, build economy/capacity, keep routes flexible.
* Antes 3-5: Formation. Increase pressure toward the routes actually assembling.
* Ante 6+: Commitment. Use full strategy pressure and existing late hysteresis.

The authoritative phase multiplier is installed at ``BalatroStrategyTracker`` so
Joker purchases, consumables, hand fit, rerolls and every other strategy consumer
see the same pressure exactly once. Generic Joker scoring/context value remains
untouched. Foundation also keeps scoring probes broad so a provisional route does
not become a poker-hand commitment prematurely.
"""

from dataclasses import replace

from games.balatro.strategy import BalatroStrategyTracker
from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator


_PHASE_WEIGHTS = {
    1: 0.25,
    2: 0.25,
    3: 0.50,
    4: 0.70,
    5: 0.90,
}


def strategy_phase_weight(ante: int) -> float:
    """Return the strategy-pressure multiplier for the current Ante."""
    resolved = max(1, int(ante or 1))
    return float(_PHASE_WEIGHTS.get(resolved, 1.0))


def strategy_phase_name(ante: int) -> str:
    resolved = max(1, int(ante or 1))
    if resolved <= 2:
        return "FOUNDATION"
    if resolved <= 5:
        return "FORMATION"
    return "COMMITMENT"


def install_strategy_phase_weight_policy() -> None:
    if getattr(BalatroStrategyTracker, "_phase_weight_policy_installed", False):
        return

    original_active_probe_hands = StrategyAwareJokerBuildValueEvaluator._active_probe_hands
    original_evaluate = StrategyAwareJokerBuildValueEvaluator.evaluate

    def strategy_pressure(self, state) -> float:
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        config = self._config(state)
        return max(
            0.0,
            strategy_phase_weight(ante)
            * self._number(config, "strategy_pressure_multiplier", 1.0),
        )

    def _active_probe_hands(self, state):
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante <= 2:
            return ()
        return original_active_probe_hands(self, state)

    def evaluate(self, state, joker):
        # ``original_evaluate`` already obtains its strategy adjustment from the
        # tracker, whose strategy_pressure is now the phase schedule above. Do not
        # multiply that adjustment a second time.
        result = original_evaluate(self, state, joker)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        phase = strategy_phase_name(ante)
        weight = strategy_phase_weight(ante)
        return replace(
            result,
            rationale=(
                *result.rationale,
                f"strategy phase={phase} ante={ante} authoritative pressure={weight:.2f}",
                "Ante phase pressure is applied once by BalatroStrategyTracker.strategy_pressure",
            ),
        )

    BalatroStrategyTracker.strategy_pressure = strategy_pressure
    StrategyAwareJokerBuildValueEvaluator._active_probe_hands = _active_probe_hands
    StrategyAwareJokerBuildValueEvaluator.evaluate = evaluate
    BalatroStrategyTracker._phase_weight_policy_installed = True
    StrategyAwareJokerBuildValueEvaluator._phase_weight_policy_installed = True
