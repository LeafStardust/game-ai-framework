from types import SimpleNamespace

import pytest

import games.balatro.playbook.red_white.shop_policy as playbook_shop_policy_module
from games.balatro.actions import BUY_BOOSTER, BUY_VOUCHER, END_SHOP, BalatroAction
from games.balatro.playbook import (
    BalatroPlaybook,
    BalatroPlaybookRegistry,
    default_balatro_playbooks,
)
from games.balatro.playbook_shop_policy import (
    PlaybookBuildAwareShopArbiter,
    PlaybookShopUtilityScale,
    PlaybookVoucherAwareBalatroShopPolicy,
    ResourceValuationThresholds,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


def _state(*, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def _registry_with_d14(**thresholds) -> BalatroPlaybookRegistry:
    registry = BalatroPlaybookRegistry()
    registry.register(
        BalatroPlaybook(
            deck="RED",
            stake="WHITE",
            name="d14-test",
            strategy={
                "decision_thresholds": {
                    "resource_valuation": thresholds,
                }
            },
        )
    )
    return registry


def test_red_white_exposes_d14_resource_scale_and_d12_is_threshold_free():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    assert ResourceValuationThresholds.from_mapping(
        playbook.thresholds_for("D14")
    ) == ResourceValuationThresholds()
    assert playbook.thresholds_for("D12") == {}


def test_d14_rejects_unknown_resource_threshold_names():
    with pytest.raises(ValueError, match="unknown D14 resource-valuation"):
        ResourceValuationThresholds.from_mapping({"mystery_weight": 1.0})


def test_playbook_d14_changes_parent_resource_cost_without_changing_child_value(
    monkeypatch,
):
    registry = _registry_with_d14(
        price_weight=2.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
    )
    monkeypatch.setattr(
        playbook_shop_policy_module,
        "default_balatro_playbooks",
        lambda: registry,
    )
    state = _state()
    scale = PlaybookShopUtilityScale(BalatroShopPolicy())
    child_option_value = 5.0
    recommendation = SimpleNamespace(
        action=BalatroAction(
            BUY_BOOSTER,
            target=SimpleNamespace(price=2),
        ),
        option_utility=child_option_value,
    )

    normalized = scale.booster_gain(state, recommendation)

    assert recommendation.option_utility == child_option_value
    assert normalized.resource_cost == 4.0
    assert normalized.gain == 1.0


def test_explicit_d14_override_beats_state_playbook(monkeypatch):
    registry = _registry_with_d14(
        price_weight=9.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
    )
    monkeypatch.setattr(
        playbook_shop_policy_module,
        "default_balatro_playbooks",
        lambda: registry,
    )
    state = _state()
    override = ResourceValuationThresholds(
        price_weight=1.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
    )
    scale = PlaybookShopUtilityScale(
        BalatroShopPolicy(),
        thresholds=override,
    )
    recommendation = SimpleNamespace(
        action=BalatroAction(BUY_BOOSTER, target=SimpleNamespace(price=2)),
        option_utility=5.0,
    )

    normalized = scale.booster_gain(state, recommendation)

    assert normalized.resource_cost == 2.0
    assert normalized.gain == 3.0


class _AdmittedVoucherPolicy:
    def decide(self, state, candidate):
        action = BalatroAction(BUY_VOUCHER, target=candidate)
        return SimpleNamespace(
            action="BUY",
            executable_action=action,
            persistent_value=10.0,
            price=4,
            rationale=("fixture D3 admission",),
        )


def test_admitted_d3_voucher_is_remapped_onto_d14_resource_scale():
    state = _state()
    thresholds = ResourceValuationThresholds(
        price_weight=1.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
    )
    policy = PlaybookVoucherAwareBalatroShopPolicy(
        voucher_policy=_AdmittedVoucherPolicy(),
        resource_thresholds=thresholds,
    )
    voucher = BalatroAction(
        BUY_VOUCHER,
        target=SimpleNamespace(label="Fixture Voucher", price=4),
    )

    ranked = policy.rank_actions(state, [voucher])

    assert len(ranked) == 1
    assert ranked[0].action is voucher
    assert ranked[0].item_utility == 10.0
    assert ranked[0].price_penalty == 4.0
    assert ranked[0].interest_penalty == 0.0
    assert ranked[0].reserve_penalty == 0.0
    assert ranked[0].total == pytest.approx(policy.hold_bias + 6.0)
    assert any("D14 remaps admitted D3 Voucher" in note for note in ranked[0].notes)


def test_parent_arbiter_applies_d14_to_shared_shop_policy_before_d11(monkeypatch):
    registry = _registry_with_d14(
        price_weight=2.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
    )
    monkeypatch.setattr(
        playbook_shop_policy_module,
        "default_balatro_playbooks",
        lambda: registry,
    )
    state = _state()
    shop_policy = PlaybookVoucherAwareBalatroShopPolicy()
    arbiter = PlaybookBuildAwareShopArbiter(shop_policy=shop_policy)

    decision = arbiter.decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.source == "END_SHOP"
    assert shop_policy.price_weight == 2.0
    assert shop_policy.interest_weight == 0.0
    assert arbiter.utility_scale.thresholds_for_state(state).price_weight == 2.0
