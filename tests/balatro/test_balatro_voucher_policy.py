from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_VOUCHER, END_SHOP, BalatroAction
from games.balatro.live.shop import LiveShopItem
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_voucher_policy import (
    BUY,
    HOLD,
    VoucherAcquisitionPolicy,
    VoucherAcquisitionThresholds,
    VoucherAwareBalatroShopPolicy,
)
from games.balatro.state import BalatroState


def _state(*, money: int = 20, ante: int = 1) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.ante = ante
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def _voucher(label: str, *, price: int = 10) -> LiveShopItem:
    return LiveShopItem(
        kind="VOUCHER",
        label=label,
        price=price,
        area_index=0,
    )


def test_voucher_thresholds_reject_unknown_configuration():
    with pytest.raises(ValueError, match="unknown D3 Voucher threshold"):
        VoucherAcquisitionThresholds.from_mapping({"generic_item_threshold": 1.0})


def test_affordable_high_impact_voucher_beats_saving_with_healthy_reserve():
    state = _state(money=20, ante=1)
    result = VoucherAcquisitionPolicy().decide(
        state,
        _voucher("Antimatter", price=10),
    )

    assert result.action == BUY
    assert result.executable_action is not None
    assert result.executable_action.name == BUY_VOUCHER
    assert result.build_compatibility > 0.0
    assert result.horizon_bonus > 0.0
    assert result.money_after == 10
    assert result.total_advantage > result.thresholds.minimum_purchase_advantage
    assert any("Joker-capacity" in note for note in result.rationale)


def test_voucher_purchase_holds_when_it_would_break_minimum_cash_reserve():
    state = _state(money=10, ante=1)
    result = VoucherAcquisitionPolicy().decide(
        state,
        _voucher("Antimatter", price=10),
    )

    assert result.action == HOLD
    assert result.executable_action is None
    assert result.money_after == 0
    assert result.total_advantage > 0.0
    assert any("minimum=$5" in note for note in result.rationale)


def test_early_persistent_voucher_gets_more_horizon_value_than_late_one():
    policy = VoucherAcquisitionPolicy(
        VoucherAcquisitionThresholds(minimum_money_after=0)
    )
    early = policy.decide(_state(money=30, ante=1), _voucher("Paint Brush", price=10))
    late = policy.decide(_state(money=30, ante=8), _voucher("Paint Brush", price=10))

    assert early.horizon_bonus > late.horizon_bonus
    assert early.persistent_value > late.persistent_value


def test_blank_is_not_bought_just_because_it_is_a_persistent_voucher():
    result = VoucherAcquisitionPolicy().decide(
        _state(money=20, ante=1),
        _voucher("Blank", price=10),
    )

    assert result.action == HOLD
    assert result.executable_action is None


@pytest.mark.parametrize("label", ("Wasteful", "Recyclomancy"))
def test_burglar_blocks_additional_discard_vouchers(label):
    state = _state(money=50, ante=4)
    state.jokers = [SimpleNamespace(name="Burglar")]

    result = VoucherAcquisitionPolicy().decide(
        state,
        _voucher(label, price=10),
    )

    assert result.action == HOLD
    assert result.executable_action is None
    assert any("Burglar voucher veto" in note for note in result.rationale)


def test_voucher_aware_shop_policy_admits_d3_buy_on_parent_shop_scale():
    state = _state(money=20, ante=1)
    voucher_action = BalatroAction(
        BUY_VOUCHER,
        target=_voucher("Antimatter", price=10),
    )
    policy = VoucherAwareBalatroShopPolicy()

    ranked = policy.rank_actions(
        state,
        [voucher_action, BalatroAction(END_SHOP)],
    )

    assert ranked[0].action is voucher_action
    assert ranked[0].total > policy.hold_bias
    assert any(note.startswith("D3 ") for note in ranked[0].notes)


def test_shop_arbiter_can_execute_d3_admitted_voucher():
    state = _state(money=20, ante=1)
    voucher_action = BalatroAction(
        BUY_VOUCHER,
        target=_voucher("Antimatter", price=10),
    )
    policy = VoucherAwareBalatroShopPolicy()
    decision = BuildAwareShopArbiter(shop_policy=policy).decide(
        state,
        [voucher_action, BalatroAction(END_SHOP)],
        reroll_cost=5,
    )

    assert decision.action is voucher_action
    assert decision.source == "DETERMINISTIC"
    assert decision.normalized_gain > 0.0
    assert any(note.startswith("D3 ") for note in decision.rationale)
