from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Iterable

from games.balatro.bonds.build_health import BuildHealth, evaluate_build_health
from games.balatro.bonds.composer import Composition
from games.balatro.bonds.model import BondDevelopment
from games.balatro.bonds.score_projection import ScoreProjection


@dataclass(frozen=True)
class LiveBondHealthSnapshot:
    projection: ScoreProjection
    health: BuildHealth
    source: str


def _blind_requirement(state: Any) -> float:
    blind = getattr(state, "blind", None)
    return max(0.0, float(getattr(blind, "requirement", 0) or 0))


def _current_score(state: Any) -> float:
    return max(0.0, float(getattr(state, "score", 0) or 0))


def _hands_remaining(state: Any) -> int:
    return max(0, int(getattr(state, "hands_remaining", 0) or 0))


def _from_triplet(
    state: Any,
    *,
    conservative_hand_score: float,
    expected_hand_score: float,
    ceiling_hand_score: float,
    clear_probability: float | None,
) -> ScoreProjection:
    blind = _blind_requirement(state)
    current = _current_score(state)
    hands = _hands_remaining(state)
    conservative = max(0.0, float(conservative_hand_score))
    expected = max(0.0, float(expected_hand_score))
    ceiling = max(0.0, float(ceiling_hand_score))
    remaining = max(0.0, blind - current)

    conservative_total = current + conservative * hands
    expected_total = current + expected * hands
    ceiling_total = current + ceiling * hands
    hands_to_clear = 0 if remaining <= 0 else (ceil(remaining / expected) if expected > 0 else None)

    probability = None if clear_probability is None else max(0.0, min(1.0, float(clear_probability)))
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
        expected_clear_ratio=(expected_total / blind) if blind > 0 else 1.0,
        hands_to_clear_expected=hands_to_clear,
        clear_probability=probability,
    )


def score_projection_from_live_play(state: Any, live_projection: Any) -> ScoreProjection:
    """Convert LivePlayProjection without averaging away its real min/mean/max."""
    return _from_triplet(
        state,
        conservative_hand_score=float(live_projection.hand_score),
        expected_hand_score=float(live_projection.expected_hand_score),
        ceiling_hand_score=float(live_projection.maximum_hand_score),
        clear_probability=float(live_projection.clear_probability),
    )


def score_projection_from_blind_plan(state: Any, plan: Any) -> ScoreProjection:
    """Convert expectimax plan value into a health projection.

    ``LiveBlindPlanValue.expected_score`` is an expected terminal round score, not
    a per-hand score. The search-level clear probability is authoritative. Because
    the planner currently exposes no terminal min/max score, the adapter uses the
    expected terminal score for expectation while leaving the conservative floor at
    current score. This prevents search expectation from masquerading as a guarantee.
    """
    blind = _blind_requirement(state)
    current = _current_score(state)
    hands = _hands_remaining(state)
    expected_terminal = max(current, float(plan.value.expected_score))
    expected_remaining = max(0.0, expected_terminal - current)
    expected_per_hand = expected_remaining / max(1, hands)
    return _from_triplet(
        state,
        conservative_hand_score=0.0,
        expected_hand_score=expected_per_hand,
        ceiling_hand_score=max(expected_per_hand, max(0.0, blind - current)),
        clear_probability=float(plan.value.clear_probability),
    )


def evaluate_live_build_health(
    state: Any,
    *,
    developments: Iterable[BondDevelopment],
    composition: Composition,
    live_projection: Any | None = None,
    blind_plan: Any | None = None,
) -> LiveBondHealthSnapshot:
    if blind_plan is not None:
        projection = score_projection_from_blind_plan(state, blind_plan)
        source = "blind_plan"
    elif live_projection is not None:
        projection = score_projection_from_live_play(state, live_projection)
        source = "live_play"
    else:
        raise ValueError("live_projection or blind_plan is required")

    health = evaluate_build_health(
        state,
        developments=tuple(developments),
        composition=composition,
        projection=projection,
    )
    return LiveBondHealthSnapshot(projection=projection, health=health, source=source)
