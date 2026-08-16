from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.resource_value import RunResourceValuator
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


def _shop_policy() -> BalatroShopPolicy:
    return BalatroShopPolicy(
        price_weight=1.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
    )


def test_signed_money_transaction_preserves_deterministic_sale_credit_value():
    valuator = RunResourceValuator()

    result = valuator.money_transaction_cost(
        money=4,
        net_spend=-6,
        price_weight=0.35,
        interest_weight=1.25,
        reserve_target=5,
        reserve_weight=0.45,
    )

    assert result.direct == pytest.approx(-2.1)
    assert result.interest == pytest.approx(-2.5)
    assert result.reserve == pytest.approx(0.0)
    assert result.total == pytest.approx(-4.6)
    assert "money=$4->$10" in result.notes


def test_d14_maps_d2_d4_and_d8_onto_one_parent_money_scale():
    scale = ShopUtilityScale(_shop_policy())
    state = SimpleNamespace(
        money=10,
        jokers=[],
        joker_slots=5,
        consumables=[],
        consumable_slots=3,
    )

    joker_selected = SimpleNamespace(
        build_gain=5.0,
        total_advantage=999.0,
        economics=SimpleNamespace(net_spend=3, edition_delta=0.0),
    )
    joker = SimpleNamespace(
        source="JOKER_BUY",
        decision=SimpleNamespace(selected=joker_selected),
    )

    consumable_selected = SimpleNamespace(
        mode="BUY",
        build_gain=5.0,
        immediate_gain=0.0,
        total_advantage=-999.0,
        economics=SimpleNamespace(price=3),
    )
    consumable = SimpleNamespace(
        decision=SimpleNamespace(
            selected=consumable_selected,
            thresholds=SimpleNamespace(immediate_money_weight=0.20),
        ),
    )

    booster = SimpleNamespace(
        action=BalatroAction(
            BUY_BOOSTER,
            target=SimpleNamespace(price=3),
        ),
        option_utility=5.0,
        total=123.0,
    )

    assert scale.joker_gain(state, joker).gain == pytest.approx(2.0)
    assert scale.consumable_gain(state, consumable).gain == pytest.approx(2.0)
    assert scale.booster_gain(state, booster).gain == pytest.approx(2.0)


def test_d14_joker_replacement_uses_signed_net_spend_without_slot_charge():
    scale = ShopUtilityScale(
        BalatroShopPolicy(
            price_weight=1.0,
            interest_weight=0.0,
            reserve_weight=0.0,
            last_joker_slot_penalty=100.0,
            penultimate_joker_slot_penalty=100.0,
        )
    )
    state = SimpleNamespace(
        money=5,
        jokers=[object()] * 5,
        joker_slots=5,
    )
    selected = SimpleNamespace(
        build_gain=1.0,
        economics=SimpleNamespace(net_spend=-2, edition_delta=0.0),
    )
    executable = SimpleNamespace(
        source="JOKER_REPLACE_SELL",
        decision=SimpleNamespace(selected=selected),
    )

    result = scale.joker_gain(state, executable)

    assert result.resource_cost == pytest.approx(-2.0)
    assert result.gain == pytest.approx(3.0)


def test_baseline_normalization_remains_explicit_for_absolute_child_scores():
    normalized = ShopUtilityScale.baseline_gain(0.50, 0.35)

    assert normalized.gain == pytest.approx(0.15)
    assert "child no-action baseline=0.350" in normalized.notes
