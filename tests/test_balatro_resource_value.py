from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_CONSUMABLE, BalatroAction
from games.balatro.resource_value import (
    ResourceValueBreakdown,
    RunResourceValuator,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


def _pressure_state(
    *,
    score: int,
    target: int = 100,
    hands: int = 3,
    discards: int = 2,
    ante: int = 1,
):
    return SimpleNamespace(
        score=score,
        blind=SimpleNamespace(requirement=target),
        hands_remaining=hands,
        discards_remaining=discards,
        ante=ante,
    )


def test_money_spend_cost_detects_interest_threshold_crossing():
    valuator = RunResourceValuator()

    threshold = valuator.money_spend_cost(
        money=10,
        spend=1,
        price_weight=0.35,
        interest_weight=1.25,
        reserve_target=5,
        reserve_weight=0.45,
    )
    safe = valuator.money_spend_cost(
        money=11,
        spend=1,
        price_weight=0.35,
        interest_weight=1.25,
        reserve_target=5,
        reserve_weight=0.45,
    )

    assert threshold.direct == pytest.approx(0.35)
    assert threshold.interest == pytest.approx(1.25)
    assert threshold.total == pytest.approx(1.60)
    assert safe.interest == pytest.approx(0.0)
    assert safe.total == pytest.approx(0.35)
    assert "interest_steps_lost=1" in threshold.notes


def test_money_spend_cost_only_charges_incremental_reserve_shortfall():
    valuator = RunResourceValuator()

    crossing = valuator.money_spend_cost(
        money=6,
        spend=2,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_target=5,
        reserve_weight=0.45,
    )
    above_reserve = valuator.money_spend_cost(
        money=10,
        spend=2,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_target=5,
        reserve_weight=0.45,
    )

    assert crossing.reserve == pytest.approx(0.45)
    assert crossing.total == pytest.approx(0.45)
    assert above_reserve.reserve == pytest.approx(0.0)


def test_slot_opportunity_cost_increases_as_capacity_disappears():
    valuator = RunResourceValuator()

    roomy = valuator.slot_opportunity_cost(
        occupied=2,
        capacity=5,
        last_slot_penalty=1.5,
        penultimate_slot_penalty=0.5,
        resource="joker",
    )
    penultimate = valuator.slot_opportunity_cost(
        occupied=3,
        capacity=5,
        last_slot_penalty=1.5,
        penultimate_slot_penalty=0.5,
        resource="joker",
    )
    last = valuator.slot_opportunity_cost(
        occupied=4,
        capacity=5,
        last_slot_penalty=1.5,
        penultimate_slot_penalty=0.5,
        resource="joker",
    )

    assert roomy.total == pytest.approx(0.0)
    assert penultimate.total == pytest.approx(0.5)
    assert last.total == pytest.approx(1.5)
    assert last.total > penultimate.total > roomy.total


def test_hand_and_discard_values_rise_with_survival_pressure():
    valuator = RunResourceValuator()
    pressured = _pressure_state(score=0)
    nearly_clear = _pressure_state(score=90)

    pressured_hand = valuator.hand_value(pressured)
    safe_hand = valuator.hand_value(nearly_clear)
    pressured_discard = valuator.discard_value(pressured)
    safe_discard = valuator.discard_value(nearly_clear)

    assert pressured_hand.total > safe_hand.total
    assert pressured_discard.total > safe_discard.total
    assert pressured_hand.total > pressured_discard.total
    assert "survival_pressure=1.000" in pressured_hand.notes


def test_hand_value_rises_when_hands_are_scarce():
    valuator = RunResourceValuator()

    many = valuator.hand_value(_pressure_state(score=0, hands=4))
    last = valuator.hand_value(_pressure_state(score=0, hands=1))

    assert last.total > many.total


def test_horizon_value_is_higher_earlier_in_run():
    valuator = RunResourceValuator()

    early = valuator.horizon_value(_pressure_state(score=0, ante=1))
    late = valuator.horizon_value(_pressure_state(score=0, ante=7))
    finished = valuator.horizon_value(_pressure_state(score=0, ante=8))

    assert early.total > late.total > finished.total
    assert finished.total == pytest.approx(0.0)


class _FixedEstimator:
    def estimate(self, state, action):
        return 10.0, ("fixed item utility",)


class _RecordingValuator(RunResourceValuator):
    def __init__(self):
        self.money_calls = []
        self.slot_calls = []

    def money_spend_cost(self, **kwargs):
        self.money_calls.append(kwargs)
        return ResourceValueBreakdown(
            total=6.0,
            direct=1.0,
            interest=2.0,
            reserve=3.0,
        )

    def slot_opportunity_cost(self, **kwargs):
        self.slot_calls.append(kwargs)
        return ResourceValueBreakdown(total=4.0, slot=4.0)


def test_shop_policy_consumes_shared_resource_valuation():
    valuator = _RecordingValuator()
    policy = BalatroShopPolicy(
        _FixedEstimator(),
        resource_valuator=valuator,
    )
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.consumable_slots = 2
    state.consumables = []
    target = SimpleNamespace(cost=2)

    score = policy.score_action(
        state,
        BalatroAction(BUY_CONSUMABLE, target=target),
    )

    assert score.price_penalty == pytest.approx(1.0)
    assert score.interest_penalty == pytest.approx(2.0)
    assert score.reserve_penalty == pytest.approx(3.0)
    assert score.slot_penalty == pytest.approx(4.0)
    assert score.total == pytest.approx(0.0)
    assert len(valuator.money_calls) == 1
    assert len(valuator.slot_calls) == 1
    assert valuator.money_calls[0]["money"] == 10
    assert valuator.money_calls[0]["spend"] == 2
    assert valuator.slot_calls[0]["resource"] == "consumable"
