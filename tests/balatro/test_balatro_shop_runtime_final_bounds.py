from types import SimpleNamespace

import games.balatro.shop_expectation_runtime_bound_policy as runtime_bounds
from games.balatro.shop_expectation_runtime_bound_policy import install_shop_expectation_runtime_bounds
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.spectral_booster_expectation_policy import SpectralBoosterExpectationEvaluator


class _CountingPackPolicy:
    def __init__(self):
        self.calls = 0

    def score_action(self, state, action):
        self.calls += 1
        return SimpleNamespace(total=2.0)


class _FailIfCalledProfiler:
    def profile(self, state):
        raise AssertionError("runtime reroll must not re-run BuildProfiler")


def test_runtime_spectral_expectation_uses_one_record_without_renormalizing():
    install_shop_expectation_runtime_bounds()
    pack_policy = _CountingPackPolicy()
    evaluator = SpectralBoosterExpectationEvaluator(pack_policy=pack_policy)
    records = tuple(
        {
            "label": f"Public Spectral {index}",
            "ability_name": f"Public Spectral {index}",
            "ability_set": "SPECTRAL",
        }
        for index in range(5)
    )
    state = SimpleNamespace(
        phase="SHOP",
        last_tarot_planet=None,
        consumable_generation_pool_observed=True,
        consumable_generation_pools={"SPECTRAL": records},
        black_hole_generation_available=False,
        soul_generation_available=False,
    )

    option_ev, positive, rationale = evaluator.evaluate(state)

    assert pack_policy.calls == runtime_bounds._SHOP_SPECTRAL_RECORD_BUDGET == 1
    assert option_ev == 2.0 / 5.0
    assert positive == 1.0 / 5.0
    assert any("1/5" in note for note in rationale)
    assert any("probability mass contributes zero" in note for note in rationale)


def test_runtime_reroll_skips_diagnostic_build_profiler_pass():
    install_shop_expectation_runtime_bounds()
    policy = BuildAwareShopRerollPolicy(build_profiler=_FailIfCalledProfiler())
    state = SimpleNamespace(phase="SHOP")

    assert policy._unmet_requirements(state) == ()
