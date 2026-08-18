from types import SimpleNamespace

from games.balatro.actions import END_SHOP, BalatroAction
from games.balatro.shop_reroll_policy import (
    FutureShopOfferPrior,
    ShopRerollPoolPrior,
)
from games.balatro.strategy_booster_policy import StrategyAwareShopRerollPolicy
from games.balatro.state import BalatroState


class _Tracker:
    def __init__(self, dominant_strategy_id):
        self.dominant_strategy_id = dominant_strategy_id

    def observe(self, state):
        del state
        return SimpleNamespace(dominant_strategy_id=self.dominant_strategy_id)


class _Profile:
    effects = ()

    def supports(self, feature):
        del feature
        return False


class _Profiler:
    def profile(self, state):
        del state
        return _Profile()


def _state(*, money=44, ante=8):
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.ante = ante
    return state


def _high_value_prior():
    return ShopRerollPoolPrior(
        card_slots=2,
        offers=(
            FutureShopOfferPrior(
                family="TEST",
                weight=1.0,
                gross_utility=100.0,
                expected_price=0,
                resource="JOKER",
            ),
        ),
    )


def test_gold_card_route_preserves_larger_late_ante_reserve():
    policy = StrategyAwareShopRerollPolicy(
        strategy_tracker=_Tracker("gold_cards"),
        build_profiler=_Profiler(),
        pool_prior=_high_value_prior(),
    )

    result = policy.recommend(
        _state(),
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert result.decision == "HOLD"
    assert any("stop-loss reserve $40" in note for note in result.rationale)


def test_non_gold_route_uses_general_late_ante_reserve():
    policy = StrategyAwareShopRerollPolicy(
        strategy_tracker=_Tracker("pair"),
        build_profiler=_Profiler(),
        pool_prior=_high_value_prior(),
    )

    result = policy.recommend(
        _state(),
        [BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert result.decision == "REROLL"
