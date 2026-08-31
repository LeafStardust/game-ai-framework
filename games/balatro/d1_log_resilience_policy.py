from __future__ import annotations

"""D1 confidence safeguards derived from live Red/White runs."""

from dataclasses import replace

from games.balatro.live.hand_action_policy import CLEAR_PATH
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
    StrategyAwareLiveHandActionPolicy._d1_log_resilience_installed = True
