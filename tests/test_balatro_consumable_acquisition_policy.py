import pytest

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BUY_CONSUMABLE
from games.balatro.jokers.mime import MimeJoker
from games.balatro.shop_consumable_policy import (
    BUY,
    BUY_AND_USE,
    HOLD,
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.state import BalatroState
from games.balatro.tarots import Chariot, Hermit, HighPriestess, Magician


def _state(*, money: int = 20, slots: int = 2) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.consumable_slots = slots
    return state


def _no_economy_thresholds(**overrides) -> ConsumableAcquisitionThresholds:
    values = {
        "minimum_purchase_advantage": 0.0,
        "minimum_buy_and_use_advantage": 0.0,
        "price_weight": 0.0,
        "interest_weight": 0.0,
        "reserve_weight": 0.0,
        "last_consumable_slot_penalty": 0.0,
    }
    values.update(overrides)
    return ConsumableAcquisitionThresholds(**values)


def test_d4_threshold_mapping_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown D4 consumable threshold"):
        ConsumableAcquisitionThresholds.from_mapping({"shared_shop_threshold": 1})


def test_d4_buys_targeted_transform_when_b4_build_path_is_positive():
    state = _state()
    state.jokers = [MimeJoker()]
    candidate = Chariot()
    candidate.price = 0

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.executable_action is not None
    assert decision.selected.executable_action.name == BUY_CONSUMABLE
    assert decision.selected.build_gain > 0.0
    assert any("MimeJoker" in note for note in decision.selected.rationale)
    assert all(option.mode != BUY_AND_USE for option in decision.options)


def test_d4_holds_weak_transform_when_purchase_economics_dominate():
    state = _state(money=20)
    candidate = Magician()
    candidate.price = 5

    decision = ConsumableAcquisitionPolicy().decide(state, candidate)

    assert decision.action == HOLD
    assert decision.selected is None
    assert decision.options
    assert decision.options[0].mode == BUY
    assert decision.options[0].total_advantage < 0.35


def test_d4_hermit_buy_and_use_uses_post_purchase_peak_money():
    state = _state(money=13)
    candidate = Hermit()
    candidate.price = 3

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY_AND_USE
    assert decision.selected is not None
    assert decision.selected.executable_action is not None
    assert decision.selected.executable_action.name == BUY_AND_USE_CONSUMABLE
    assert decision.selected.economics.money_after == 10
    assert decision.selected.immediate_gain == 10.0
    assert any("post-purchase threshold" in note for note in decision.selected.rationale)


def test_d4_hermit_below_peak_prefers_buy_and_hold_when_slot_is_free():
    state = _state(money=9)
    candidate = Hermit()
    candidate.price = 3

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert all(option.mode != BUY_AND_USE for option in decision.options)


def test_d4_full_slots_can_buy_and_use_positive_hermit_below_peak():
    state = _state(money=9, slots=1)
    state.consumables = [HighPriestess()]
    candidate = Hermit()
    candidate.price = 3

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY_AND_USE
    assert decision.selected is not None
    assert decision.selected.immediate_gain == 6.0
    assert all(option.mode != BUY for option in decision.options)
    assert any("slots are full" in note for note in decision.selected.rationale)


def test_d4_full_slots_hold_targeted_consumable_without_safe_immediate_mode():
    state = _state(money=20, slots=1)
    state.consumables = [HighPriestess()]
    candidate = Chariot()
    candidate.price = 0

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == HOLD
    assert decision.selected is None
    assert decision.options == ()
