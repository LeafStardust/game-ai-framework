from types import SimpleNamespace

import games.balatro.bond_shop_health_policy as policy
from games.balatro.live.strategy_health import StrategyHealthMode
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale


def _health(mode):
    return SimpleNamespace(mode=mode)


def test_positive_gain_modifier_never_turns_negative_utility_positive():
    original = ShopNormalizedUtility(gain=-2.0, resource_cost=1.0, notes=("base",))
    adjusted = policy._positive_gain_with_health(
        original,
        factor=1.25,
        note="mode=SURVIVE",
    )
    assert adjusted is original
    assert adjusted.gain == -2.0


def test_positive_gain_modifier_is_bounded_and_multiplicative():
    original = ShopNormalizedUtility(gain=4.0, resource_cost=1.0, notes=("base",))
    adjusted = policy._positive_gain_with_health(
        original,
        factor=1.25,
        note="mode=SURVIVE",
    )
    assert adjusted.gain == 5.0
    assert adjusted.resource_cost == 1.0
    assert any("factor=1.250" in note for note in adjusted.notes)


def test_health_factor_contract_keeps_strong_builds_neutral():
    assert policy._JOKER_GAIN_FACTOR[StrategyHealthMode.SURVIVE] == 1.25
    assert policy._JOKER_GAIN_FACTOR[StrategyHealthMode.REPAIR] == 1.15
    assert policy._JOKER_GAIN_FACTOR[StrategyHealthMode.HOLD] == 1.0
    assert policy._JOKER_GAIN_FACTOR[StrategyHealthMode.REINFORCE] == 1.0
    assert policy._JOKER_GAIN_FACTOR[StrategyHealthMode.EXPLOIT] == 1.0

    assert policy._REROLL_MARGIN_FACTOR[StrategyHealthMode.SURVIVE] == 1.35
    assert policy._REROLL_MARGIN_FACTOR[StrategyHealthMode.REPAIR] == 1.20
    assert policy._REROLL_MARGIN_FACTOR[StrategyHealthMode.HOLD] == 1.0
    assert policy._REROLL_MARGIN_FACTOR[StrategyHealthMode.REINFORCE] == 1.0
    assert policy._REROLL_MARGIN_FACTOR[StrategyHealthMode.EXPLOIT] == 1.0


def test_installation_marks_production_authorities_once():
    policy.install_bond_shop_health_policy()
    assert getattr(policy.LiveHandActionDecisionEngine, "_bond_shop_health_capture_installed")
    assert getattr(ShopUtilityScale, "_bond_shop_health_utility_installed")
    assert getattr(policy.BuildAwareShopRerollPolicy, "_bond_shop_health_reroll_installed")


def test_joker_utility_weak_health_only_scales_positive_admitted_gain():
    scale = ShopUtilityScale(SimpleNamespace())
    state = SimpleNamespace(
        phase="SHOP",
        deck_name="RED",
        stake_name="WHITE",
        ante=3,
        round=5,
        money=100,
        jokers=(),
        joker_slots=5,
        vouchers=(),
    )
    candidate = SimpleNamespace(discovered=True, edition=None)
    selected = SimpleNamespace(
        economics=SimpleNamespace(net_spend=0, edition_delta=0.0),
        build_gain=10.0,
    )
    executable = SimpleNamespace(
        source="JOKER_REPLACE_SELL",
        candidate=candidate,
        decision=SimpleNamespace(selected=selected),
    )

    policy.clear_strategy_health()
    baseline = scale.joker_gain(state, executable)
    assert baseline.gain > 0.0

    policy._LAST_STRATEGY_HEALTH = _health(StrategyHealthMode.SURVIVE)
    policy._LAST_STRATEGY_HEALTH_PROVENANCE = policy.StrategyHealthProvenance(
        "RED",
        "WHITE",
        3,
        5,
    )
    adjusted = scale.joker_gain(state, executable)
    # Replacement churn receives half of the 25% SURVIVE boost: 1.125x.
    assert adjusted.gain == baseline.gain * 1.125

    policy.clear_strategy_health()
