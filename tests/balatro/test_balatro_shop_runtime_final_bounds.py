from types import SimpleNamespace

import games.balatro.shop_expectation_runtime_bound_policy as runtime_bounds
from games.balatro.actions import END_SHOP, BalatroAction
from games.balatro.shop_expectation_runtime_bound_policy import install_shop_expectation_runtime_bounds
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.spectral_booster_expectation_policy import SpectralBoosterExpectationEvaluator
from games.balatro.state import BalatroState


class _CountingPackPolicy:
    def __init__(self):
        self.calls = 0

    def score_action(self, state, action):
        self.calls += 1
        return SimpleNamespace(total=2.0)


class _FailIfCalledProfiler:
    def profile(self, state):
        raise AssertionError("parent-driven runtime reroll must not re-run BuildProfiler")


class _CountingProfiler:
    def __init__(self):
        self.calls = 0

    def profile(self, state):
        self.calls += 1
        return SimpleNamespace(effects=(), supports=lambda requirement: False)


def _reroll_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 25
    state.ante = 1
    state.joker_slots = 5
    state.consumable_slots = 2
    state.joker_generation_pool_observed = True
    return state


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


def test_parent_driven_runtime_reroll_skips_diagnostic_build_profiler_pass():
    install_shop_expectation_runtime_bounds()
    policy = BuildAwareShopRerollPolicy(build_profiler=_FailIfCalledProfiler())
    state = _reroll_state()

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
        visible_score_floor=policy.shop_policy.hold_bias + 2.0,
    )

    assert result.unmet_requirements == ()
    assert result.current_best_score == policy.shop_policy.hold_bias + 2.0


def test_standalone_runtime_reroll_preserves_build_profiler_diagnostics():
    install_shop_expectation_runtime_bounds()
    profiler = _CountingProfiler()
    policy = BuildAwareShopRerollPolicy(build_profiler=profiler)
    state = _reroll_state()

    policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert profiler.calls == 1
