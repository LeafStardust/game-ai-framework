from types import SimpleNamespace

import games.balatro.reroll_joker_expectation_policy as reroll_joker_expectation_policy
from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.shop_expectation_runtime_bound_policy import (
    install_shop_expectation_runtime_bounds,
)
from games.balatro.spectral_booster_expectation_policy import SpectralBoosterExpectationEvaluator


class _CountingPackPolicy:
    def __init__(self):
        self.calls = 0

    def score_action(self, state, action):
        self.calls += 1
        return SimpleNamespace(total=2.0)


def _state():
    return SimpleNamespace(
        phase="SHOP",
        last_tarot_planet=None,
    )


def test_unopened_arcana_keeps_nested_generated_resource_probability_as_zero():
    install_shop_expectation_runtime_bounds()
    policy = _CountingPackPolicy()
    evaluator = ArcanaBoosterExpectationEvaluator(pack_policy=policy)
    state = _state()

    for name in ("The Emperor", "The High Priestess", "Judgement"):
        assert evaluator._visible_value(
            state,
            {"label": name, "ability_name": name, "ability_set": "TAROT"},
        ) == 0.0

    assert policy.calls == 0

    ordinary = evaluator._visible_value(
        state,
        {"label": "The Hermit", "ability_name": "The Hermit", "ability_set": "TAROT"},
    )
    assert ordinary == 2.0
    assert policy.calls == 1


def test_unopened_spectral_keeps_generated_resource_probability_as_zero():
    install_shop_expectation_runtime_bounds()
    policy = _CountingPackPolicy()
    evaluator = SpectralBoosterExpectationEvaluator(pack_policy=policy)
    state = _state()

    for name in ("Familiar", "Grim", "Incantation", "Wraith", "The Soul"):
        assert evaluator._visible_value(
            state,
            {"label": name, "ability_name": name, "ability_set": "SPECTRAL"},
        ) == 0.0

    assert policy.calls == 0

    ordinary = evaluator._visible_value(
        state,
        {"label": "Black Hole", "ability_name": "Black Hole", "ability_set": "SPECTRAL"},
    )
    assert ordinary == 2.0
    assert policy.calls == 1


def test_large_public_joker_expectation_runtime_budget_is_twelve_full_d2_calls():
    install_shop_expectation_runtime_bounds()
    assert reroll_joker_expectation_policy._MAX_RECORDS_PER_RARITY == 1
    assert reroll_joker_expectation_policy._MAX_D2_EVALUATIONS == 12
    assert reroll_joker_expectation_policy._MAX_EXACT_PUBLIC_RECORDS == 24
