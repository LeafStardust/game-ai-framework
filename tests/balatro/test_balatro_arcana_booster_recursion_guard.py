from __future__ import annotations

from types import SimpleNamespace

from games.balatro.arcana_booster_expectation_policy import (
    ArcanaBoosterExpectationEvaluator,
)


class _ExplodingPackPolicy:
    def score_action(self, *args, **kwargs):
        del args, kwargs
        raise AssertionError("Emperor must not enter D9 scoring from D8 Arcana expectation")


def test_arcana_unopened_expectation_treats_emperor_as_zero_without_d9_recursion():
    evaluator = ArcanaBoosterExpectationEvaluator(pack_policy=_ExplodingPackPolicy())
    state = SimpleNamespace()

    assert evaluator._visible_value(
        state,
        {
            "center": "c_emperor",
            "label": "The Emperor",
            "ability_name": "The Emperor",
            "ability_set": "TAROT",
        },
    ) == 0.0


def test_arcana_unopened_expectation_guards_emperor_by_center_key_too():
    evaluator = ArcanaBoosterExpectationEvaluator(pack_policy=_ExplodingPackPolicy())
    state = SimpleNamespace()

    assert evaluator._visible_value(
        state,
        {
            "center": "c_emperor",
            "label": "Emperor",
            "ability_name": "Emperor",
            "ability_set": "TAROT",
        },
    ) == 0.0
