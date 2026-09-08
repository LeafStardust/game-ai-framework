from __future__ import annotations

"""Compatibility surface for native D1 semantic search and arbitration behavior.

Candidate bounding, root discard preservation, Bond relation guarding, planner
estimate ordering, and strategy discard ordering now live in their canonical
owners. This module intentionally performs no production class mutation.
"""

from games.balatro.actions import DISCARD_CARDS


_EPSILON = 1e-12


def _nonclearing_discard_quality_key(plan) -> tuple[float, float, float, float, float, int]:
    """Compatibility helper matching native non-clearing discard quality ordering."""
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
    """Compatibility helper for zero-modeled-progress discard detection."""
    if getattr(plan.action, "name", None) != DISCARD_CARDS:
        return False
    value = plan.value
    return (
        float(value.clear_probability) <= _EPSILON
        and float(value.expected_progress) <= _EPSILON
        and float(value.expected_score) <= _EPSILON
    )


def _zero_signal_discard_tiebreak(plan, *, strategy_fit: float = 0.0) -> tuple[float, int]:
    """Compatibility helper for strategy-first meaningful-redraw ordering."""
    return (
        float(strategy_fit),
        len(getattr(plan.action, "cards", ()) or ()),
    )


def install_semantic_search_guard_policy() -> None:
    """Compatibility no-op; semantic search behavior is native to D1 owners."""
    return None


__all__ = (
    "_nonclearing_discard_quality_key",
    "_zero_signal_discard",
    "_zero_signal_discard_tiebreak",
    "install_semantic_search_guard_policy",
)
