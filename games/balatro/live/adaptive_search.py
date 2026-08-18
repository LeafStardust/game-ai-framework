from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import DISCARD_CARDS


LIVE_ADAPTIVE_MAX_HORIZON = 4


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
    horizon: int | None = None
    intensified: bool = False


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

    The maximum useful horizon is bounded by the remaining real action budget and
    by ``LIVE_ADAPTIVE_MAX_HORIZON``. The latter is a live-runtime safety guard:
    recursive public-draw projections can spend substantial wall-clock time inside
    one planner node, so the planner's per-node deadline check is not by itself a
    hard latency bound. Keeping ordinary live D1 search at horizon four prevents
    early-ante 4-hand/4-discard states from expanding to horizon eight and stalling
    the autonomous supervisor for minutes.

    Search starts at horizon two whenever possible so the first pass is genuinely
    cheap enough to complete on an ordinary opening hand. Deeper horizons are
    attempted only after a shallower result exists or the shallower search itself
    exhausts its bounded budget.

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

    deepest = min(max_horizon, action_budget, LIVE_ADAPTIVE_MAX_HORIZON)
    first = 1 if deepest == 1 else 2
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
                samples=max(8, _sample_count(deepest)),
                child_samples=1,
                play_width=3,
                discard_width=2 if discards_remaining > 0 else 0,
                child_play_width=2,
                child_discard_width=1 if discards_remaining > 0 else 0,
                max_nodes=max_nodes,
            )
        )

    return tuple(configs)


def stable_discard_consensus(
    recommendations: tuple[AdaptiveRecommendationSummary, ...],
    *,
    minimum_agreement: int = 3,
    tolerance: float = 1e-9,
) -> bool:
    """Return whether the deepest searches agree on one setup discard.

    The deepest ``minimum_agreement`` completed searches must recommend the exact
    same non-empty discard. Ordinary deepening projections must also be
    non-regressing in both clear probability and expected score. A regression is
    tolerated only when the current result is an explicitly intensified repeat
    of the same horizon and is strictly worse on both objectives; this isolates
    sampled duplicate-horizon noise without weakening the normal deepening rule.
    Scored plays remain governed by the normal clear-probability threshold.
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
    if any(
        item.action != DISCARD_CARDS or item.indices != first.indices
        for item in tail[1:]
    ):
        return False

    for previous, current in zip(tail, tail[1:]):
        probability_regressed = (
            current.clear_probability + tolerance < previous.clear_probability
        )
        score_regressed = current.expected_score + tolerance < previous.expected_score
        if not (probability_regressed or score_regressed):
            continue

        duplicate_horizon_noise = (
            probability_regressed
            and score_regressed
            and current.intensified
            and previous.horizon is not None
            and current.horizon == previous.horizon
        )
        if not duplicate_horizon_noise:
            return False

    return True
