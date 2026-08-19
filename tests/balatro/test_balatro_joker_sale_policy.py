from types import SimpleNamespace

import pytest

from games.balatro.card import BalatroCard
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import HOLD
from games.balatro.joker_sale_policy import (
    SELL,
    JokerSalePolicy,
    JokerSaleThresholds,
)
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 8
        return context


def _state(*, money: int = 20, slots: int = 2) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = slots
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("K", "Clubs"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("9", "Hearts"),
    ]
    return state


def _thresholds(**overrides) -> JokerSaleThresholds:
    values = {
        "minimum_sale_advantage": 0.0,
        "maximum_build_loss": 0.0,
        "minimum_sell_credit": 0,
        "sell_credit_weight": 1.0,
        "interest_gain_weight": 0.0,
        "reserve_recovery_weight": 0.0,
        "full_slot_release_value": 0.0,
    }
    values.update(overrides)
    return JokerSaleThresholds(**values)


def test_d2_sale_threshold_mapping_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown D2 Joker sale threshold"):
        JokerSaleThresholds.from_mapping({"shared_shop_threshold": 1})


def test_d2_standalone_sale_sells_zero_value_joker_for_observed_credit():
    state = _state(money=5, slots=2)
    joker = InertJoker()
    joker.sell_cost = 4
    state.jokers = [joker]

    decision = JokerSalePolicy(_thresholds()).decide(state)

    assert decision.action == SELL
    assert decision.selected is not None
    assert decision.selected.joker_index == 0
    assert decision.selected.joker == "InertJoker"
    assert decision.selected.build_loss == 0.0
    assert decision.selected.sell_credit == 4
    assert decision.selected.money_after == 9
    assert decision.selected.total_advantage == pytest.approx(4.0)


def test_d2_standalone_sale_holds_positive_build_value_even_for_large_credit():
    state = _state(money=0, slots=1)
    joker = PlusMultJoker()
    joker.sell_cost = 50
    state.jokers = [joker]

    decision = JokerSalePolicy(_thresholds()).decide(state)

    assert decision.action == HOLD
    assert decision.options
    assert decision.options[0].build_loss > 0.0
    assert decision.options[0].eligible is False
    assert any(
        "build loss exceeds maximum" in reason
        for reason in decision.options[0].rationale
    )


def test_d2_standalone_sale_never_recommends_eternal_joker():
    state = _state(money=0, slots=1)
    joker = InertJoker()
    joker.sell_cost = 50
    joker.eternal = True
    state.jokers = [joker]

    decision = JokerSalePolicy(_thresholds()).decide(state)

    assert decision.action == HOLD
    assert decision.options[0].eligible is False
    assert decision.options[0].blocked_reason is not None
    assert "Eternal" in decision.options[0].blocked_reason


def test_d2_standalone_sale_fails_closed_when_sell_value_is_unobserved():
    state = _state(money=0, slots=1)
    state.jokers = [InertJoker()]

    decision = JokerSalePolicy(_thresholds()).decide(state)

    assert decision.action == HOLD
    assert decision.options[0].sell_credit is None
    assert decision.options[0].eligible is False
    assert decision.options[0].blocked_reason == "public sell value is unavailable"


def test_d2_standalone_sale_ranks_all_owned_jokers_before_selecting():
    state = _state(money=0, slots=2)
    low_credit = InertJoker()
    low_credit.sell_cost = 1
    high_credit = InertJoker()
    high_credit.sell_cost = 6
    state.jokers = [low_credit, high_credit]

    decision = JokerSalePolicy(_thresholds()).decide(state)

    assert len(decision.options) == 2
    assert decision.action == SELL
    assert decision.selected is not None
    assert decision.selected.joker_index == 1
    assert decision.selected.sell_credit == 6


def test_d2_standalone_sale_default_policy_requires_real_advantage():
    state = _state(money=20, slots=2)
    joker = InertJoker()
    joker.sell_cost = 1
    state.jokers = [joker]

    decision = JokerSalePolicy().decide(state)

    assert decision.action == HOLD
    assert decision.options[0].total_advantage == pytest.approx(0.35)
    assert decision.thresholds.minimum_sale_advantage == pytest.approx(0.75)


def test_d2_standalone_sale_values_full_slot_release_without_guessing_future_shop():
    state = _state(money=20, slots=1)
    joker = InertJoker()
    joker.sell_cost = 1
    state.jokers = [joker]

    decision = JokerSalePolicy().decide(state)

    assert decision.action == SELL
    assert decision.selected is not None
    assert decision.selected.slot_release_value == pytest.approx(1.0)
    assert decision.selected.total_advantage == pytest.approx(1.35)


def test_negative_joker_is_protected_from_ordinary_standalone_sale():
    state = _state(money=0, slots=1)
    joker = InertJoker()
    joker.edition = "Negative"
    joker.sell_cost = 50
    state.jokers = [joker]

    decision = JokerSalePolicy(_thresholds()).decide(state)

    assert decision.action == HOLD
    assert decision.options[0].eligible is False
    assert decision.options[0].negative_retention_protected is True
    assert decision.options[0].negative_retention_exception is None
    assert "Negative Joker is protected" in decision.options[0].blocked_reason
    assert "Negative retention result=PROTECTED_FROM_SALE" in decision.options[0].rationale


def test_materially_harmful_negative_joker_uses_explicit_sale_exception():
    class _HarmEvaluator:
        def evaluate(self, state, joker):
            del state, joker
            return SimpleNamespace(total_gain=-10.0)

    state = _state(money=0, slots=1)
    joker = InertJoker()
    joker.edition = "Negative"
    joker.sell_cost = 1
    state.jokers = [joker]

    decision = JokerSalePolicy(
        _thresholds(minimum_negative_harm=0.75),
        evaluator=_HarmEvaluator(),
    ).decide(state)

    assert decision.action == SELL
    assert decision.selected is not None
    assert decision.selected.negative_retention_protected is False
    assert "MEASURED_WHOLE_BUILD_HARM" in (
        decision.selected.negative_retention_exception or ""
    )
