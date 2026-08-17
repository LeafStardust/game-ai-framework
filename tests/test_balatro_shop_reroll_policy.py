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
    FutureShopOfferPrior,
    ShopRerollPoolPrior,
    ShopRerollThresholds,
    VANILLA_SHOP_REROLL_PRIOR,
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


def _single_offer_prior(
    *,
    gross_utility: float = 10.0,
    expected_price: int = 0,
    resource: str = "JOKER",
) -> ShopRerollPoolPrior:
    return ShopRerollPoolPrior(
        card_slots=2,
        offers=(
            FutureShopOfferPrior(
                family="TEST",
                weight=1.0,
                gross_utility=gross_utility,
                expected_price=expected_price,
                resource=resource,
            ),
        ),
    )


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
    assert result.future_shop_ev == float("-inf")
    assert result.reroll_score == float("-inf")
    assert any("fails closed" in note for note in result.rationale)


def test_reroll_fails_closed_when_public_pool_prior_is_unavailable():
    state = _state()
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        pool_prior=None,
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert result.decision == "HOLD"
    assert result.executable_action is None
    assert result.future_shop_ev == float("-inf")
    assert any("pool prior is unavailable" in note for note in result.rationale)
    assert any("no heuristic exploration fallback" in note for note in result.rationale)


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


def test_weak_open_capacity_build_has_positive_reroll_ev_when_cost_is_cheap():
    state = _state(money=21)
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        pool_prior=VANILLA_SHOP_REROLL_PRIOR,
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert result.decision == "REROLL"
    assert result.executable_action is not None
    assert result.executable_action.name == REFRESH_SHOP
    assert result.future_shop_ev > 0.0
    assert result.reroll_score > result.current_best_score
    assert any("JOKER:20" in note for note in result.rationale)


def test_expensive_reroll_is_negative_for_saturated_build():
    state = _state(money=20)
    state.jokers = [object() for _ in range(state.joker_slots)]
    state.consumables = [object() for _ in range(state.consumable_slots)]
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        pool_prior=VANILLA_SHOP_REROLL_PRIOR,
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert result.decision == "HOLD"
    assert result.future_shop_ev > policy.shop_policy.hold_bias
    assert result.reroll_score < 0.0
    assert result.executable_action is None


def test_cash_rich_full_roster_rerolls_for_replacement_options_then_stops():
    state = _state(money=121)
    state.jokers = [object() for _ in range(state.joker_slots)]
    state.consumables = [object() for _ in range(state.consumable_slots)]
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
        pool_prior=VANILLA_SHOP_REROLL_PRIOR,
    )

    affordable_search = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    expensive_search = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=6,
    )

    assert affordable_search.decision == "REROLL"
    assert affordable_search.executable_action is not None
    assert affordable_search.executable_action.name == REFRESH_SHOP
    assert expensive_search.decision == "HOLD"
    assert any(
        "replacement-option penalty=1.500" in note
        for note in affordable_search.rationale
    )


def test_reroll_score_is_monotonic_with_reroll_cost():
    state = _state(money=20)
    shop_policy = BalatroShopPolicy(
        price_weight=1.0,
        interest_weight=0.0,
        reserve_weight=0.0,
    )
    policy = BuildAwareShopRerollPolicy(
        shop_policy=shop_policy,
        build_profiler=StaticProfiler(EmptyProfile()),
        thresholds=ShopRerollThresholds(minimum_margin=0.0),
        pool_prior=_single_offer_prior(gross_utility=10.0, expected_price=0),
    )

    scores = [
        policy.recommend(
            state,
            [BalatroAction(END_SHOP)],
            reroll_cost=cost,
        ).reroll_score
        for cost in (1, 2, 3, 4)
    ]

    assert scores == sorted(scores, reverse=True)
    assert all(
        earlier > later
        for earlier, later in zip(scores, scores[1:])
    )


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
        pool_prior=_single_offer_prior(gross_utility=5.0, expected_price=0),
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
        thresholds=ShopRerollThresholds(minimum_margin=0.0),
        pool_prior=_single_offer_prior(gross_utility=2.0, expected_price=0),
    )

    result = policy.recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=6,
    )

    assert result.decision == "HOLD"
    assert result.reroll_score < result.current_best_score
    assert any("reroll interest penalty=4.000" in note for note in result.rationale)
    assert any("reroll reserve penalty=2.000" in note for note in result.rationale)


def test_unmet_build_requirements_are_reported_without_free_form_ev_bonus():
    state = _state(money=21)
    base = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
    ).recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )
    needy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(MissingRequirementProfile()),
    ).recommend(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=1,
    )

    assert needy.unmet_requirements == ("HELD_EFFECT", "SCORE_XMULT")
    assert needy.future_shop_ev == base.future_shop_ev
    assert needy.reroll_score == base.reroll_score


def test_unsupported_random_visible_action_is_not_given_fake_shop_quality():
    state = _state(money=21)
    policy = BuildAwareShopRerollPolicy(
        build_profiler=StaticProfiler(EmptyProfile()),
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
