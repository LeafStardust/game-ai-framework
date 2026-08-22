from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import mean
from typing import Any, Iterable


@dataclass(frozen=True)
class ScoreProjection:
    blind_requirement: float
    current_score: float
    remaining_requirement: float
    conservative_hand_score: float
    expected_hand_score: float
    ceiling_hand_score: float
    hands_remaining: int
    conservative_total: float
    expected_total: float
    ceiling_total: float
    conservative_margin: float
    expected_margin: float
    ceiling_margin: float
    expected_clear_ratio: float
    hands_to_clear_expected: int | None
    clear_probability: float | None = None

    @property
    def expected_clear(self) -> bool:
        return self.expected_margin >= 0.0

    @property
    def conservative_clear(self) -> bool:
        return self.conservative_margin >= 0.0


def _number(state: Any, names: tuple[str, ...], default: float = 0.0) -> float:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return float(default)


def _integer(state: Any, names: tuple[str, ...], default: int = 0) -> int:
    return max(0, int(_number(state, names, float(default))))


def _blind_requirement(state: Any) -> float:
    flat = _number(
        state,
        ("blind_requirement", "blind_score_requirement", "blind_target", "target_score"),
        -1.0,
    )
    if flat >= 0.0:
        return flat
    blind = getattr(state, "blind", None)
    try:
        return max(0.0, float(getattr(blind, "requirement", 0) or 0))
    except (TypeError, ValueError):
        return 0.0


def _candidate_scores(state: Any, explicit: Iterable[float] | None) -> list[float]:
    if explicit is not None:
        return [max(0.0, float(v)) for v in explicit]
    for name in ("candidate_hand_scores", "projected_hand_scores", "hand_score_estimates"):
        values = getattr(state, name, None)
        if values is not None:
            return [max(0.0, float(v)) for v in values]
    single = _number(state, ("expected_hand_score", "projected_hand_score", "best_hand_score"), 0.0)
    return [single] if single > 0 else []


def _quantile_triplet(scores: list[float]) -> tuple[float, float, float]:
    if not scores:
        return 0.0, 0.0, 0.0
    ordered = sorted(scores)
    n = len(ordered)
    conservative = ordered[max(0, int((n - 1) * 0.20))]
    expected = mean(ordered)
    ceiling = ordered[-1]
    return conservative, expected, ceiling


def project_score(
    state: Any,
    *,
    candidate_hand_scores: Iterable[float] | None = None,
    clear_probability: float | None = None,
) -> ScoreProjection:
    """Project blind-clear capacity from actual/runtime scoring estimates.

    This module deliberately does not convert Bond rank, realization, motifs or
    composer coherence into chips. Candidate scores must come from Balatro score
    mechanics/search/runtime estimates. The projection only aggregates them
    against the current blind requirement.
    """
    blind = _blind_requirement(state)
    current = _number(state, ("current_score", "round_score", "chips_scored", "score"), 0.0)
    hands = _integer(state, ("hands_remaining", "hands_left"), 1)
    remaining = max(0.0, blind - current)

    scores = _candidate_scores(state, candidate_hand_scores)
    conservative, expected, ceiling = _quantile_triplet(scores)

    conservative_total = current + conservative * hands
    expected_total = current + expected * hands
    ceiling_total = current + ceiling * hands

    expected_clear_ratio = (expected_total / blind) if blind > 0 else 1.0
    hands_to_clear = None
    if remaining <= 0:
        hands_to_clear = 0
    elif expected > 0:
        hands_to_clear = ceil(remaining / expected)

    probability = clear_probability
    if probability is None:
        raw = getattr(state, "clear_probability", None)
        if raw is not None:
            try:
                probability = max(0.0, min(1.0, float(raw)))
            except (TypeError, ValueError):
                probability = None

    return ScoreProjection(
        blind_requirement=blind,
        current_score=current,
        remaining_requirement=remaining,
        conservative_hand_score=conservative,
        expected_hand_score=expected,
        ceiling_hand_score=ceiling,
        hands_remaining=hands,
        conservative_total=conservative_total,
        expected_total=expected_total,
        ceiling_total=ceiling_total,
        conservative_margin=conservative_total - blind,
        expected_margin=expected_total - blind,
        ceiling_margin=ceiling_total - blind,
        expected_clear_ratio=expected_clear_ratio,
        hands_to_clear_expected=hands_to_clear,
        clear_probability=probability,
    )
