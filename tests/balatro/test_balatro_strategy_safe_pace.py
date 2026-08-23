from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS
from games.balatro.pinned_strategy_safe_pace_policy import (
    pace_strategy_equivalent_plans,
    select_strategy_safe_pace_plan,
)


def _plan(name: str, preference: float):
    return SimpleNamespace(
        name=name,
        preference=preference,
        action=SimpleNamespace(name=PLAY_CARDS),
    )


class _Policy:
    EPSILON = 1e-12
    thresholds = SimpleNamespace(pace_ratio_floor=1.0)

    @staticmethod
    def _pace_target(state):
        return 90.0

    @staticmethod
    def _pace_ratio(score, target):
        return score / target

    @staticmethod
    def _pace_play_key(plan, pace_ratio):
        # Stand-in for StrategyAwareLiveHandActionPolicy's dynamic key: higher
        # preference means the play better preserves the pinned engine.
        return (plan.preference, pace_ratio)


def test_near_equivalent_pace_play_can_be_selected_for_strategy_preservation():
    strongest = _plan("strongest", 0.0)
    preserves_engine = _plan("preserves", 10.0)
    scores = {id(strongest): 100.0, id(preserves_engine): 99.0}

    equivalent = pace_strategy_equivalent_plans(
        _Policy(), SimpleNamespace(), (strongest, preserves_engine), projected_scores=scores
    )
    selected = select_strategy_safe_pace_plan(
        _Policy(), SimpleNamespace(), equivalent, scores
    )

    assert equivalent == (strongest, preserves_engine)
    assert selected is preserves_engine


def test_materially_weaker_play_cannot_trade_survival_for_strategy_preservation():
    strongest = _plan("strongest", 0.0)
    preserves_engine = _plan("preserves", 100.0)
    scores = {id(strongest): 100.0, id(preserves_engine): 97.0}

    equivalent = pace_strategy_equivalent_plans(
        _Policy(), SimpleNamespace(), (strongest, preserves_engine), projected_scores=scores
    )
    selected = select_strategy_safe_pace_plan(
        _Policy(), SimpleNamespace(), equivalent, scores
    )

    assert equivalent == (strongest,)
    assert selected is strongest


def test_under_pace_play_never_enters_strategy_equivalence_pool():
    meets_pace = _plan("meets", 0.0)
    under_pace = _plan("under", 100.0)
    scores = {id(meets_pace): 90.0, id(under_pace): 89.9}

    equivalent = pace_strategy_equivalent_plans(
        _Policy(), SimpleNamespace(), (meets_pace, under_pace), projected_scores=scores
    )

    assert equivalent == (meets_pace,)
