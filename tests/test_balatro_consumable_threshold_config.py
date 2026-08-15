from types import SimpleNamespace

import pytest

from games.balatro.live.consumable_timing import (
    ConsumableTargetThresholds,
    ConsumableUseThresholds,
    LiveConsumableTimingPolicy,
)
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_consumable_policy import ConsumableAcquisitionThresholds


def _state():
    return SimpleNamespace(
        deck_name="RED",
        stake_name="WHITE",
        blind=SimpleNamespace(requirement=100),
        score=0,
        hands_remaining=2,
        consumables=[],
        consumable_slots=2,
    )


def test_red_white_exposes_independent_d4_d5_d6_threshold_blocks():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    d4 = ConsumableAcquisitionThresholds.from_mapping(playbook.thresholds_for("D4"))
    d5 = ConsumableUseThresholds.from_mapping(playbook.thresholds_for("D5"))
    d6 = ConsumableTargetThresholds.from_mapping(playbook.thresholds_for("D6"))

    assert d4.minimum_purchase_advantage == 0.35
    assert d4.minimum_buy_and_use_advantage == 0.35
    assert d5.minimum_clear_probability_gain == 0.0
    assert d5.minimum_immediate_gain == 0.0
    assert d6.minimum_total_gain is None
    assert d6.minimum_contextual_delta is None


def test_d5_thresholds_are_resolved_from_current_playbook():
    thresholds = LiveConsumableTimingPolicy()._use_thresholds_for_state(_state())

    assert thresholds == ConsumableUseThresholds()


def test_d5_clear_probability_threshold_can_hold_a_marginal_gain():
    state = _state()
    before = SimpleNamespace(clear_probability=0.10, expected_hand_score=60.0)
    after = SimpleNamespace(clear_probability=0.20, expected_hand_score=60.0)
    target = SimpleNamespace(contextual_delta=0.0)

    permissive = LiveConsumableTimingPolicy(
        use_thresholds=ConsumableUseThresholds(
            minimum_clear_probability_gain=0.0,
        )
    )
    conservative = LiveConsumableTimingPolicy(
        use_thresholds=ConsumableUseThresholds(
            minimum_clear_probability_gain=0.20,
        )
    )

    assert (
        permissive._use_reason(
            state,
            target=target,
            before=before,
            after=after,
            required_per_hand=50.0,
        )
        == "consumable increases current best-play clear probability"
    )
    assert (
        conservative._use_reason(
            state,
            target=target,
            before=before,
            after=after,
            required_per_hand=50.0,
        )
        is None
    )


def test_d6_target_thresholds_gate_total_and_contextual_gain_independently():
    thresholds = ConsumableTargetThresholds(
        minimum_total_gain=2.0,
        minimum_contextual_delta=1.0,
    )

    assert thresholds.accepts(SimpleNamespace(total_gain=2.5, contextual_delta=1.5))
    assert not thresholds.accepts(
        SimpleNamespace(total_gain=1.5, contextual_delta=1.5)
    )
    assert not thresholds.accepts(
        SimpleNamespace(total_gain=2.5, contextual_delta=0.5)
    )


def test_consumable_threshold_mapping_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown D5 consumable-use threshold"):
        ConsumableUseThresholds.from_mapping({"shop_reserve": 4})

    with pytest.raises(ValueError, match="unknown D6 consumable-target threshold"):
        ConsumableTargetThresholds.from_mapping({"shop_reserve": 4})