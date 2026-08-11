from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import DISCARD_CARDS


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


@dataclass(frozen=True)
class AdaptiveRecommendationSummary:
    """Planner recommendation fields needed for cross-search consensus checks."""

    action: str
    indices: tuple[int, ...]
    clear_probability: float
    expected_score: float


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


def stable_discard_consensus(
    recommendations: tuple[AdaptiveRecommendationSummary, ...],
    *,
    minimum_agreement: int = 3,
    tolerance: float = 1e-9,
) -> bool:
    """Return whether the deepest completed searches agree on one discard.

    This is deliberately stricter than merely choosing the best sampled result.
    The last ``minimum_agreement`` completed searches must recommend the exact
    same discard indexes, and both clear probability and expected score must be
    non-decreasing as search horizon deepens. It is intended as an explicit
    best-effort setup-action policy; scored plays remain governed by the normal
    clear-probability execution threshold.
    """

    if minimum_agreement < 2:
        raise ValueError("minimum_agreement must be at least 2")
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")
    if len(recommendations) < minimum_agreement:
        return False

    tail = recommendations[-minimum_agreement:]
    first = tail[0]
    if first.action != DISCARD_CARDS:
        return False
    if not first.indices:
        return False
    if any(item.action != DISCARD_CARDS or item.indices != first.indices for item in tail[1:]):
        return False

    for previous, current in zip(tail, tail[1:]):
        if current.clear_probability + tolerance < previous.clear_probability:
            return False
        if current.expected_score + tolerance < previous.expected_score:
            return False
    return True
