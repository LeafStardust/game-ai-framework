from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveBlindSearchConfig:
    """One bounded blind-planner search configuration.

    The schedule intentionally prefers cheap shallow searches, then spends more
    horizon only when the earlier searches cannot produce an acceptable plan.
    Child beams stay narrow because recursive play branching is the dominant
    live-search cost.
    """

    horizon: int
    samples: int
    child_samples: int
    play_width: int
    discard_width: int
    child_play_width: int
    child_discard_width: int
    max_nodes: int


def _node_budget(horizon: int, cap: int) -> int:
    if horizon <= 4:
        return min(cap, 2000)
    if horizon == 5:
        return min(cap, 3000)
    return min(cap, 5000)


def _sample_count(horizon: int) -> int:
    if horizon <= 6:
        return 8
    if horizon == 7:
        return 4
    return 2


def adaptive_blind_search_schedule(
    *,
    hands_remaining: int,
    discards_remaining: int,
    max_horizon: int = 8,
    max_nodes: int = 5000,
) -> tuple[AdaptiveBlindSearchConfig, ...]:
    """Return a cheap-to-deep bounded search schedule for the current blind.

    The maximum useful horizon is bounded by the remaining real action budget:
    every play consumes one hand and every discard consumes one discard. A
    four-action search is the normal starting point when enough actions remain;
    smaller states start at their remaining action count instead.
    """

    if hands_remaining < 0:
        raise ValueError("hands_remaining cannot be negative")
    if discards_remaining < 0:
        raise ValueError("discards_remaining cannot be negative")
    if max_horizon < 1:
        raise ValueError("max_horizon must be positive")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")

    action_budget = hands_remaining + discards_remaining
    if action_budget <= 0:
        return ()

    deepest = min(max_horizon, action_budget)
    first = min(4, deepest)
    configs = []
    for horizon in range(first, deepest + 1):
        configs.append(
            AdaptiveBlindSearchConfig(
                horizon=horizon,
                samples=_sample_count(horizon),
                child_samples=1,
                play_width=3 if horizon <= 5 else 2,
                discard_width=1 if discards_remaining > 0 else 0,
                child_play_width=1,
                child_discard_width=1 if discards_remaining > 0 else 0,
                max_nodes=_node_budget(horizon, max_nodes),
            )
        )
    return tuple(configs)
