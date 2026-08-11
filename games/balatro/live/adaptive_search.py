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

    The normal schedule deliberately caps deep searches at 5000 nodes. When the
    caller explicitly supplies a larger ``max_nodes`` value, the schedule spends
    that extra budget only after the cheap schedule fails: it repeats the deepest
    useful horizon with wider root beams, then (if still needed) a wider child
    play beam. This makes ``--max-search-nodes`` a real opt-in intensification
    control without making ordinary live replans expensive.
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

    # Intensification is explicitly opt-in. The default 5000-node setting must
    # never add extra passes merely because a shallow remaining horizon normally
    # uses a smaller 2000/3000-node budget.
    if max_nodes > 5000:
        configs.append(
            AdaptiveBlindSearchConfig(
                horizon=deepest,
                samples=max(8, _sample_count(deepest)),
                child_samples=1,
                play_width=3,
                discard_width=2 if discards_remaining > 0 else 0,
                child_play_width=1,
                child_discard_width=1 if discards_remaining > 0 else 0,
                max_nodes=max_nodes,
            )
        )
        configs.append(
            AdaptiveBlindSearchConfig(
                horizon=deepest,
                samples=4,
                child_samples=1,
                play_width=3,
                discard_width=2 if discards_remaining > 0 else 0,
                child_play_width=2,
                child_discard_width=1 if discards_remaining > 0 else 0,
                max_nodes=max_nodes,
            )
        )

    return tuple(configs)


def _trim_strictly_dominated_tail(
    recommendations: tuple[AdaptiveRecommendationSummary, ...],
    *,
    minimum_remaining: int,
    tolerance: float,
) -> tuple[AdaptiveRecommendationSummary, ...]:
    """Drop trailing estimates that are strictly worse on both objectives.

    This helper is used only after discard-action agreement has already been
    established. It therefore affects the quality-trend check, not which action
    counts as evidence for consensus.
    """

    items = list(recommendations)
    while len(items) > minimum_remaining:
        previous = items[-2]
        current = items[-1]
        probability_worse = (
            current.clear_probability + tolerance < previous.clear_probability
        )
        score_worse = current.expected_score + tolerance < previous.expected_score
        if not (probability_worse and score_worse):
            break
        items.pop()
    return tuple(items)


def stable_discard_consensus(
    recommendations: tuple[AdaptiveRecommendationSummary, ...],
    *,
    minimum_agreement: int = 3,
    tolerance: float = 1e-9,
) -> bool:
    """Return whether the deepest searches agree on one setup discard.

    The deepest ``minimum_agreement`` completed searches must first recommend
    the exact same non-empty discard. That action agreement is never replaced by
    a shallower search. Only after the action vote is established may a trailing
    estimate be ignored for the monotonic quality check when it is strictly
    worse in both clear probability and expected score. Scored plays remain
    governed by the normal clear-probability execution threshold.
    """

    if minimum_agreement < 2:
        raise ValueError("minimum_agreement must be at least 2")
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")
    if len(recommendations) < minimum_agreement:
        return False

    action_tail = recommendations[-minimum_agreement:]
    first = action_tail[0]
    if first.action != DISCARD_CARDS:
        return False
    if not first.indices:
        return False
    if any(
        item.action != DISCARD_CARDS or item.indices != first.indices
        for item in action_tail[1:]
    ):
        return False

    quality_tail = _trim_strictly_dominated_tail(
        action_tail,
        minimum_remaining=2,
        tolerance=tolerance,
    )
    for previous, current in zip(quality_tail, quality_tail[1:]):
        if current.clear_probability + tolerance < previous.clear_probability:
            return False
        if current.expected_score + tolerance < previous.expected_score:
            return False
    return True
