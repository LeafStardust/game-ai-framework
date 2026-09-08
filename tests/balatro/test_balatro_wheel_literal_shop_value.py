from types import SimpleNamespace

import games.balatro.shop_consumable_policy as shop_consumable_policy
from games.balatro.shop_consumable_policy import BUY_AND_USE, ConsumableAcquisitionPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import WheelOfFortune


class _ZeroBuildEvaluator:
    def evaluate(self, candidate, state):
        del candidate, state
        return SimpleNamespace(total_gain=0.0, rationale=())


class _LiteralWheelExpectation:
    def evaluate(self, state):
        del state
        return SimpleNamespace(
            available=True,
            complete=True,
            expected_build_gain=0.2,
            rationale=("fixture literal Wheel expectation=0.200",),
        )


def test_shop_wheel_uses_literal_analytic_expectation_without_floor(monkeypatch):
    monkeypatch.setattr(
        shop_consumable_policy,
        "WheelOfFortuneExpectationEvaluator",
        lambda: _LiteralWheelExpectation(),
    )

    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.jokers = [object()]
    state.consumables = []
    state.consumable_slots = 2

    wheel = WheelOfFortune()
    wheel.price = 0
    policy = ConsumableAcquisitionPolicy(evaluator=_ZeroBuildEvaluator())

    decision = policy.decide(state, wheel)

    assert decision.action == BUY_AND_USE
    assert decision.selected is not None
    assert decision.selected.build_gain == 0.2
    assert decision.selected.total_advantage == 0.2
    assert all("option floor" not in note for note in decision.selected.rationale)
