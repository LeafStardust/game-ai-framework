from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND
from games.balatro.safe_pace_optimization_policy import _scoring_readiness
from games.balatro.strategy_blind_skip_policy import StrategyAwareBlindSkipPolicy


def install_safe_pace_blind_skip_patch() -> None:
    if getattr(StrategyAwareBlindSkipPolicy, "_safe_pace_survival_gate_installed", False):
        return

    original_decide = StrategyAwareBlindSkipPolicy.decide

    def decide(self, snapshot, state, *, thresholds=None):
        decision = original_decide(self, snapshot, state, thresholds=thresholds)
        if decision.action_name != SKIP_BLIND:
            return decision

        readiness = _scoring_readiness(state)
        required = 0.40 if str(decision.blind_type).upper() == "SMALL" else 0.55
        if readiness >= required:
            return decision

        return replace(
            decision,
            action_name=SELECT_BLIND,
            margin=min(float(decision.margin), -float(decision.threshold)),
            build_readiness=readiness,
            strategy_tag_support=(
                f"{decision.strategy_tag_support}; survival-gated-scoring-readiness"
            ),
        )

    StrategyAwareBlindSkipPolicy.decide = decide
    StrategyAwareBlindSkipPolicy._safe_pace_survival_gate_installed = True
