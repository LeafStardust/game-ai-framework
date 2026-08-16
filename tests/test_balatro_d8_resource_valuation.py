from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.live.shop import LiveShopItem
from games.balatro.resource_value import ResourceValueBreakdown
from games.balatro.shop_booster_policy import (
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


class RecordingResourceValuator:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def money_spend_cost(self, **kwargs) -> ResourceValueBreakdown:
        self.calls.append(dict(kwargs))
        return ResourceValueBreakdown(
            total=6.0,
            direct=1.0,
            interest=2.0,
            reserve=3.0,
        )


def _state(*, money: int) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    return state


def _booster(*, label: str, price: int, center: str) -> LiveShopItem:
    return LiveShopItem(
        kind="BOOSTER",
        label=label,
        price=price,
        area_index=0,
        center=center,
    )


def test_d8_uses_parent_shared_resource_valuator_with_d8_owned_coefficients():
    valuator = RecordingResourceValuator()
    shop_policy = BalatroShopPolicy(resource_valuator=valuator)
    thresholds = BoosterAcquisitionThresholds(
        price_weight=0.7,
        interest_weight=1.9,
        reserve_target=9,
        reserve_weight=0.8,
    )
    policy = BuildAwareShopBoosterPolicy(
        shop_policy=shop_policy,
        thresholds=thresholds,
    )
    state = _state(money=20)
    action = BalatroAction(
        BUY_BOOSTER,
        target=_booster(
            label="Celestial Pack",
            price=5,
            center="p_celestial_normal_4",
        ),
    )

    result = policy.recommend(state, action)

    assert valuator.calls == [
        {
            "money": 20,
            "spend": 5,
            "price_weight": 0.7,
            "interest_weight": 1.9,
            "reserve_target": 9,
            "reserve_weight": 0.8,
            "vouchers": [],
        }
    ]
    assert result.price_penalty == 1.0
    assert result.interest_penalty == 2.0
    assert result.reserve_penalty == 3.0
    assert result.advantage_over_save == result.option_utility - 6.0


def test_d8_default_resource_breakdown_preserves_previous_economics():
    state = _state(money=10)
    action = BalatroAction(
        BUY_BOOSTER,
        target=_booster(
            label="Standard Pack",
            price=10,
            center="p_standard_normal_1",
        ),
    )

    result = BuildAwareShopBoosterPolicy().recommend(state, action)

    assert result.price_penalty == 3.5
    assert result.interest_penalty == 2.5
    assert result.reserve_penalty == 2.25
