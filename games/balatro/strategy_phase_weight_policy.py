from __future__ import annotations

"""Ante-scaled strategy pressure for Joker build evaluation.

The run lifecycle is intentionally asymmetric:

* Antes 1-2: Foundation. Survive, build economy/capacity, keep routes flexible.
* Antes 3-5: Formation. Increase pressure toward the routes actually assembling.
* Ante 6+: Commitment. Use full strategy pressure and existing late hysteresis.

This policy scales only the strategy-derived component of whole-build Joker value.
The generic scoring/context value remains untouched, so strong universal pieces can
still carry early runs while aligned pieces become progressively more important.
"""

from dataclasses import replace

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
    if getattr(StrategyAwareJokerBuildValueEvaluator, "_phase_weight_policy_installed", False):
        return

    original_evaluate = StrategyAwareJokerBuildValueEvaluator.evaluate
    original_active_probe_hands = StrategyAwareJokerBuildValueEvaluator._active_probe_hands

    def _active_probe_hands(self, state):
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante <= 2:
            # Foundation must keep generic scoring probes broad. A provisional
            # strategy leader is evidence, not a hand-type commitment yet.
            return ()
        return original_active_probe_hands(self, state)

    def evaluate(self, state, joker):
        result = original_evaluate(self, state, joker)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        weight = strategy_phase_weight(ante)
        if weight >= 1.0 or abs(float(result.strategic_adjustment)) <= 1e-12:
            return result

        raw_adjustment = float(result.strategic_adjustment)
        weighted_adjustment = raw_adjustment * weight
        total = float(result.base_total_gain) + weighted_adjustment
        phase = strategy_phase_name(ante)
        return replace(
            result,
            strategic_adjustment=weighted_adjustment,
            total_gain=total,
            rationale=(
                *result.rationale,
                f"strategy phase={phase} ante={ante} weight={weight:.2f}",
                f"phase-weighted strategy adjustment={raw_adjustment:+.3f}->{weighted_adjustment:+.3f}",
                f"phase-weighted whole-build gain={total:.3f}",
            ),
        )

    StrategyAwareJokerBuildValueEvaluator._active_probe_hands = _active_probe_hands
    StrategyAwareJokerBuildValueEvaluator.evaluate = evaluate
    StrategyAwareJokerBuildValueEvaluator._phase_weight_policy_installed = True
