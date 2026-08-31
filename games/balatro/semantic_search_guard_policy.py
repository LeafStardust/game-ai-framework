from __future__ import annotations

"""Compatibility installer for the remaining D1 semantic arbitration hooks.

Candidate bounding, root discard preservation, and semantic relation guarding now
live in their canonical owners. This module temporarily retains only the two
ordering rules that still need to be migrated natively:

- planner ordering for guaranteed plays versus non-clearing sampled discards;
- strategy ordering for zero-signal discard recovery.

No candidate generation, search-budget, or Bond graph behavior is owned here.
"""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


_EPSILON = 1e-12


def _nonclearing_discard_quality_key(plan) -> tuple[float, float, float, float, float, int]:
    """Rank discard recovery quality before exact-enumeration status."""
    value = plan.value
    return (
        float(value.clear_probability),
        float(value.expected_progress),
        float(value.expected_hands_remaining),
        float(value.expected_discards_remaining),
        float(value.expected_score),
        1 if bool(plan.exact) else 0,
    )


def _zero_signal_discard(plan) -> bool:
    """True when bounded D1 search has no modeled outcome signal for a discard."""
    if getattr(plan.action, "name", None) != DISCARD_CARDS:
        return False
    value = plan.value
    return (
        float(value.clear_probability) <= _EPSILON
        and float(value.expected_progress) <= _EPSILON
        and float(value.expected_score) <= _EPSILON
    )


def _zero_signal_discard_tiebreak(plan, *, strategy_fit: float = 0.0) -> tuple[float, int]:
    """Preserve real strategy intent, then prefer a meaningful redraw over peeling."""
    return (
        float(strategy_fit),
        len(getattr(plan.action, "cards", ()) or ()),
    )


def install_semantic_search_guard_policy() -> None:
    """Install only the remaining arbitration compatibility hooks."""
    if getattr(LiveBlindClearPlanner, "_semantic_search_guard_installed", False):
        return

    original_estimate_key = LiveBlindClearPlanner._estimate_key

    def estimate_key(cls, estimate):
        value = estimate.value
        action_name = getattr(estimate.action, "name", None)
        if (
            estimate.exact
            and float(value.clear_probability) >= 1.0 - _EPSILON
            and float(value.expected_progress) >= 1.0 - _EPSILON
            and action_name == PLAY_CARDS
        ):
            return (
                value.clear_probability,
                1,
                value.expected_progress,
                value.expected_hands_remaining,
                value.expected_discards_remaining,
                -len(getattr(estimate.action, "cards", ()) or ()),
                value.expected_score,
            )
        if (
            action_name == DISCARD_CARDS
            and float(value.clear_probability) < 1.0 - _EPSILON
        ):
            return (
                value.clear_probability,
                0,
                value.expected_progress,
                value.expected_hands_remaining,
                value.expected_discards_remaining,
                value.expected_score,
                1 if bool(estimate.exact) else 0,
                value.expected_consumables,
            )
        canonical = original_estimate_key(estimate)
        return (*canonical[:-1], 0, canonical[-1])

    original_strategy_key = StrategyAwareLiveHandActionPolicy._within_type_key

    def strategy_within_type_key(self, plan):
        if (
            getattr(plan.action, "name", None) == DISCARD_CARDS
            and float(plan.value.clear_probability) < 1.0 - _EPSILON
        ):
            quality = _nonclearing_discard_quality_key(plan)
            original = original_strategy_key(self, plan)
            if _zero_signal_discard(plan):
                strategy_fit = 0.0
                state = getattr(self, "_ranking_state", None)
                if state is not None:
                    try:
                        strategy_fit = float(self._strategy_fit(state, plan.action)[0])
                    except (AttributeError, TypeError, ValueError, RuntimeError):
                        strategy_fit = 0.0
                return (
                    *quality,
                    *_zero_signal_discard_tiebreak(plan, strategy_fit=strategy_fit),
                    original,
                )
            return (*quality, original)
        return original_strategy_key(self, plan)

    LiveBlindClearPlanner._estimate_key = classmethod(estimate_key)
    StrategyAwareLiveHandActionPolicy._within_type_key = strategy_within_type_key
    LiveBlindClearPlanner._semantic_search_guard_installed = True
