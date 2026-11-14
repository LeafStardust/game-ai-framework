from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.env.ppo_boss_safe_pace_counterfactual import (
    PPOBossSafePaceCounterfactualError,
    _counterfactual_plan,
)


def _plan(name, *, exact, score):
    return SimpleNamespace(
        action=SimpleNamespace(name=name),
        exact=exact,
        value=SimpleNamespace(expected_score=score),
    )


def test_safe_pace_counterfactual_selects_highest_exact_play_at_decision_zero():
    lower = _plan(PLAY_CARDS, exact=True, score=100)
    higher = _plan(PLAY_CARDS, exact=True, score=200)
    discard = _plan(DISCARD_CARDS, exact=True, score=300)
    inexact = _plan(PLAY_CARDS, exact=False, score=400)
    production = SimpleNamespace(
        completed_search_plans=(lower, higher, discard, inexact)
    )
    assert _counterfactual_plan(0, production) is higher
    assert _counterfactual_plan(1, production) is None


def test_safe_pace_counterfactual_fails_closed_without_exact_play():
    production = SimpleNamespace(
        completed_search_plans=(_plan(DISCARD_CARDS, exact=True, score=100),)
    )
    with pytest.raises(PPOBossSafePaceCounterfactualError, match="exact Play"):
        _counterfactual_plan(0, production)
