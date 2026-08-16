from types import SimpleNamespace

import pytest

from games.balatro.playbook import (
    BalatroPlaybook,
    BalatroPlaybookNotFound,
    BalatroPlaybookRegistry,
    default_balatro_playbooks,
)


def test_default_registry_selects_red_white_from_live_state():
    state = SimpleNamespace(deck_name="RED", stake_name="WHITE")

    playbook = default_balatro_playbooks().for_state(state)

    assert playbook.name == "red-white"
    assert playbook.version == "1.0"
    assert playbook.key == ("RED", "WHITE")

    planner = playbook.strategy["planner"]
    assert planner["max_horizon"] == 5
    assert planner["max_search_nodes"] == 5000
    assert planner["search_schedule_mode"] == "probe-deepest"
    assert "min_clear_probability" not in planner
    assert "min_pace_ratio" not in planner

    hand_action = playbook.thresholds_for("D1")
    assert hand_action["clear_path_probability_floor"] == 0.75
    assert hand_action["pace_ratio_floor"] == 1.0
    assert hand_action["setup_discard_consensus_agreement"] == 3
    assert hand_action["low_discard_reserve"] == 1
    assert hand_action["low_discard_fallback_penalty"] == 10.0
    assert hand_action["low_hand_reserve"] == 1
    assert hand_action["low_hand_discard_fallback_bonus"] == 10.0

    joker_acquisition = playbook.thresholds_for("d2")
    assert joker_acquisition["minimum_purchase_build_gain"] == 0.0
    assert joker_acquisition["minimum_purchase_advantage"] == 0.35
    assert joker_acquisition["minimum_replacement_build_delta"] == 0.0
    assert joker_acquisition["minimum_replacement_advantage"] == 0.75
    assert joker_acquisition["price_weight"] == 0.35
    assert joker_acquisition["interest_weight"] == 1.25
    assert joker_acquisition["reserve_target"] == 5
    assert joker_acquisition["reserve_weight"] == 0.45
    assert joker_acquisition["last_joker_slot_penalty"] == 1.5
    assert joker_acquisition["penultimate_joker_slot_penalty"] == 0.5

    voucher_acquisition = playbook.thresholds_for("D3")
    assert voucher_acquisition["minimum_persistent_value"] == 1.0
    assert voucher_acquisition["minimum_money_after"] == 0

    pack_target = playbook.thresholds_for("D10")
    assert pack_target["minimum_total_gain"] is None
    assert pack_target["minimum_contextual_delta"] == 0.0

    blind_skip = playbook.thresholds_for("D13")
    assert blind_skip["minimum_skip_advantage"] == 2.0
    assert blind_skip["fallback_tag_value"] == 4.0
    assert blind_skip["base_shop_opportunity_value"] == 1.5
    assert blind_skip["build_development_shop_weight"] == 2.0
    assert blind_skip["pre_boss_shop_weight"] == 2.5
    assert blind_skip["interest_cap"] == 5


def test_playbook_threshold_blocks_are_independent_by_decision_layer():
    playbook = BalatroPlaybook(
        "RED",
        "WHITE",
        "custom",
        strategy={
            "decision_thresholds": {
                "consumable_acquisition": {"minimum_advantage": 0.4},
                "consumable_use": {"minimum_advantage": 0.7},
            }
        },
    )

    acquisition = playbook.thresholds_for("D4")
    use = playbook.thresholds_for("D5")

    assert acquisition == {"minimum_advantage": 0.4}
    assert use == {"minimum_advantage": 0.7}
    assert playbook.thresholds_for("D6") == {}

    acquisition["minimum_advantage"] = 99.0
    assert playbook.thresholds_for("D4") == {"minimum_advantage": 0.4}


def test_playbook_rejects_unknown_decision_layer_threshold_lookup():
    playbook = BalatroPlaybook("RED", "WHITE", "custom")

    with pytest.raises(ValueError, match="unknown Balatro decision layer"):
        playbook.thresholds_for("D15")


def test_registry_requires_exact_deck_stake_cartridge():
    registry = default_balatro_playbooks()

    with pytest.raises(BalatroPlaybookNotFound, match="RED / RED"):
        registry.get("RED", "RED")


def test_registry_rejects_duplicate_cartridge():
    registry = BalatroPlaybookRegistry()
    first = BalatroPlaybook("RED", "WHITE", "first")
    registry.register(first)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(BalatroPlaybook("red", "white", "second"))