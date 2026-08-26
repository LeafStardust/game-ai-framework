from types import SimpleNamespace

import games.balatro.reroll_joker_expectation_policy as reroll_joker_expectation_policy
from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
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


def test_unopened_spectral_omits_all_deferred_d9_outcomes():
    install_shop_expectation_runtime_bounds()
    policy = _CountingPackPolicy()
    evaluator = SpectralBoosterExpectationEvaluator(pack_policy=policy)
    state = _state()

    omitted = set(BalatroPackPolicy.DEFERRED_SPECTRALS) | {"The Soul"}
    for name in sorted(omitted):
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


def test_same_state_arcana_expectation_is_memoized_for_duplicate_shop_packs():
    install_shop_expectation_runtime_bounds()
    policy = _CountingPackPolicy()
    evaluator = ArcanaBoosterExpectationEvaluator(pack_policy=policy)
    state = SimpleNamespace(
        phase="SHOP",
        last_tarot_planet=None,
        consumable_generation_pool_observed=True,
        consumable_generation_pools={
            "TAROT": (
                {
                    "label": "The Hermit",
                    "ability_name": "The Hermit",
                    "ability_set": "TAROT",
                },
            )
        },
        soul_generation_available=False,
        omen_globe_active=False,
    )

    first = evaluator.evaluate(state)
    calls_after_first = policy.calls
    second = evaluator.evaluate(state)

    assert second is first
    assert policy.calls == calls_after_first


def test_large_public_joker_expectation_runtime_budget_is_twelve_full_d2_calls():
    install_shop_expectation_runtime_bounds()
    assert reroll_joker_expectation_policy._MAX_RECORDS_PER_RARITY == 1
    assert reroll_joker_expectation_policy._MAX_D2_EVALUATIONS == 12
    assert reroll_joker_expectation_policy._MAX_EXACT_PUBLIC_RECORDS == 24
