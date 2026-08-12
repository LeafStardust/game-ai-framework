from types import SimpleNamespace

from games.balatro.actions import (
    BUY_JOKER,
    END_SHOP,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollThresholds,
)
from games.balatro.state import BalatroState


class FlatEstimator:
    def __init__(self, value: float):
        self.value = value

    def estimate(self, state, action):
        return self.value, ("flat visible-shop value",)


class EmptyProfile:
    effects = ()

    def supports(self, feature):
        return False


class MissingRequirementProfile:
    effects = (
        SimpleNamespace(requires=frozenset({"HELD_EFFECT", "SCORE_XMULT"})),
    )

    def supports(self, feature):
        return False


class StaticProfiler:
    def __init__(self, profile):
        self._profile = profile

    def profile(self, state):
        return self._profile


def _state(*, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    return state


def _thresholds(**overrides):
    values = {
        "exploration_prior": 2.5,
        "unmet_requirement_bonus": 0.75,
        "max_unmet_requirement_bonus": 3.0,
        "minimum_margin": 0.25,
    }
    values.update(overrides)
    return ShopRerollThresholds(**values)


def test_reroll_fails_closed_when_current_cost_is_not_observed():
    state = _state()
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert result.decision == "HOLD"
    assert result.executable_action is None
    assert result.reroll_score == float("-inf")
    assert any("fails closed" in note for note in result.rationale)


def test_reroll_holds_when_current_cost_is_unaffordable():
    state = _state(money=3)
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert result.decision == "HOLD"
    assert result.executable_action is None
    assert any("only $3" in note for note in result.rationale)


def test_weak_visible_shop_can_reroll_when_observed_cost_is_cheap():
    state = _state(money=20)
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        thresholds=_thresholds(exploration_prior=3.0),
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert result.decision == "REROLL"
    assert result.executable_action is not None
    assert result.executable_action.name == REFRESH_SHOP
    assert result.reroll_score > result.current_best_score


def test_strong_visible_purchase_suppresses_reroll():
    state = _state(money=20)
    candidate = SimpleNamespace(cost=0, label="Known Strong Offer")
    shop_policy = BalatroShopPolicy(
        FlatEstimator(10.0),
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
    )
    policy = BuildAwareShopRerollPolicy(
        shop_policy=shop_policy,
        build_profiler=StaticProfiler(EmptyProfile()),
        thresholds=_thresholds(exploration_prior=5.0),
    )

    result = policy.recommend(
        state,
        [
            BalatroAction(BUY_JOKER, target=candidate),
            BalatroAction(END_SHOP),
        ],
        reroll_cost=0,
    )

    assert result.decision == "HOLD"
    assert result.current_best_score == 10.0
    assert result.executable_action is None


def test_reroll_uses_same_interest_and_reserve_economics_as_shop_policy():
    state = _state(money=10)
    shop_policy = BalatroShopPolicy(
        price_weight=0.0,
        interest_weight=2.0,
        reserve_target=5,
        reserve_weight=2.0,
    )
    policy = BuildAwareShopRerollPolicy(
        shop_policy=shop_policy,
        build_profiler=StaticProfiler(EmptyProfile()),
        thresholds=_thresholds(
            exploration_prior=2.0,
            minimum_margin=0.0,
        ),
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=6,
    )

    assert result.decision == "HOLD"
    assert result.reroll_score < result.current_best_score
    assert any("interest penalty=4.000" in note for note in result.rationale)
    assert any("reserve penalty=2.000" in note for note in result.rationale)


def test_unmet_build_requirements_raise_exploration_value_without_predicting_items():
    state = _state(money=20)
    base = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        thresholds=_thresholds(),
    ).recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )
    needy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(MissingRequirementProfile()),
        thresholds=_thresholds(),
    ).recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert needy.unmet_requirements == ("HELD_EFFECT", "SCORE_XMULT")
    assert needy.exploration_value == base.exploration_value + 1.5
    assert any(
        "does not predict unseen shop contents" in note
        for note in needy.rationale
    )


def test_unsupported_random_visible_action_is_not_given_fake_shop_quality():
    state = _state(money=20)
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        thresholds=_thresholds(exploration_prior=3.0),
    )

    result = policy.recommend(
        state,
        [
            BalatroAction("BUY_BOOSTER", target=SimpleNamespace(price=4)),
            BalatroAction(END_SHOP),
        ],
        reroll_cost=1,
    )

    assert result.decision == "REROLL"
    assert result.current_best_score == policy.shop_policy.hold_bias
