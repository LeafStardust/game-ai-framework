from __future__ import annotations

"""D1 runtime and confidence safeguards derived from live Red/White runs."""

from dataclasses import replace

from games.balatro.live.hand_action_policy import CLEAR_PATH, LiveHandActionDecisionEngine
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _boss_active(state) -> bool:
    boss_name = str(getattr(state, "boss_name", "") or "")
    blind_type = str(getattr(state, "blind_type", "") or "").upper()
    return bool(boss_name) or blind_type == "BOSS"


def install_d1_log_resilience_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_d1_log_resilience_installed", False):
        return

    original_policy_decide = StrategyAwareLiveHandActionPolicy.decide

    def policy_decide(self, state, plans, **kwargs):
        supplied = tuple(plans)
        confirmed = kwargs.get("confirmed_clear_path")
        boss_unconfirmed = _boss_active(state) and confirmed is None
        if boss_unconfirmed:
            supplied = tuple(
                replace(plan, exact=False) if bool(getattr(plan, "exact", False)) else plan
                for plan in supplied
            )

        decision = original_policy_decide(self, state, supplied, **kwargs)

        # Boss projections can be model-dependent even when the underlying search
        # marks a line exact. Preserve the confidence downgrade, but do not perform
        # a second Play-vs-Discard arbitration after the canonical policy returns.
        if boss_unconfirmed and decision.mode == CLEAR_PATH:
            decision = replace(
                decision,
                confidence=min(float(decision.confidence), 0.95),
                rationale=(
                    "boss projection exactness is treated as model-dependent until independently confirmed",
                    *decision.rationale,
                ),
            )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = policy_decide

    original_engine_decide = LiveHandActionDecisionEngine.decide

    def engine_decide(self, state):
        configured = self.max_search_seconds
        if configured is None or float(configured) <= 1.25:
            return original_engine_decide(self, state)
        reserve = min(1.0, max(0.50, float(configured) * 0.125))
        try:
            self.max_search_seconds = max(0.25, float(configured) - reserve)
            decision = original_engine_decide(self, state)
        finally:
            self.max_search_seconds = configured
        return replace(
            decision,
            rationale=(
                *decision.rationale,
                f"D1 deterministic fallback reserve={reserve:.3f}s from configured {float(configured):.3f}s budget",
            ),
        )

    LiveHandActionDecisionEngine.decide = engine_decide
    StrategyAwareLiveHandActionPolicy._d1_log_resilience_installed = True
