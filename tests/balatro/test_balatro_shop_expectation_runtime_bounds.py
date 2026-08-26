from types import SimpleNamespace

import games.balatro.reroll_joker_expectation_policy as reroll_joker_expectation_policy
import games.balatro.shop_expectation_runtime_bound_policy as runtime_bounds
from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.held_consumable_option_policy import HeldConsumableOptionEvaluator
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


def test_unopened_arcana_omits_every_base_stochastic_or_deferred_tarot():
    install_shop_expectation_runtime_bounds()
    policy = _CountingPackPolicy()
    evaluator = ArcanaBoosterExpectationEvaluator(pack_policy=policy)
    state = _state()

    assert runtime_bounds._D8_OMITTED_TAROTS
    for name in sorted(runtime_bounds._D8_OMITTED_TAROTS):
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


def test_unopened_spectral_omits_every_base_stochastic_or_deferred_outcome():
    install_shop_expectation_runtime_bounds()
    policy = _CountingPackPolicy()
    evaluator = SpectralBoosterExpectationEvaluator(pack_policy=policy)
    state = _state()

    assert runtime_bounds._D8_OMITTED_SPECTRALS
    for name in sorted(runtime_bounds._D8_OMITTED_SPECTRALS):
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


def test_held_shop_option_omits_second_layer_stochastic_expectation():
    install_shop_expectation_runtime_bounds()
    evaluator = HeldConsumableOptionEvaluator()
    name = sorted(runtime_bounds._D8_OMITTED_SPECTRALS)[0]
    candidate = SimpleNamespace(category="SPECTRAL", name=name)

    result = evaluator.evaluate(_state(), candidate)

    assert result.complete is True
    assert result.expected_gain == 0.0
    assert result.exact is False
    assert any("second-layer" in note for note in result.rationale)


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


def test_shop_future_hand_models_share_small_deterministic_branch_budget():
    install_shop_expectation_runtime_bounds()

    assert HeldConsumableOptionEvaluator.EXACT_COMBINATION_LIMIT == 16
    assert HeldConsumableOptionEvaluator.SAMPLE_COUNT == 8
    assert HandSizeOpportunityEvaluator.EXACT_COMBINATION_LIMIT == 16
    assert HandSizeOpportunityEvaluator.SAMPLE_COUNT == 8


def test_large_public_joker_expectation_runtime_budget_is_twelve_full_d2_calls():
    install_shop_expectation_runtime_bounds()
    assert reroll_joker_expectation_policy._MAX_RECORDS_PER_RARITY == 1
    assert reroll_joker_expectation_policy._MAX_D2_EVALUATIONS == 12
    assert reroll_joker_expectation_policy._MAX_EXACT_PUBLIC_RECORDS == 24
