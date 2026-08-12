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
    assert playbook.version == "0.6"
    assert playbook.key == ("RED", "WHITE")

    planner = playbook.strategy["planner"]
    assert planner["max_horizon"] == 8
    assert planner["max_search_nodes"] == 5000
    assert "min_clear_probability" not in planner
    assert "min_pace_ratio" not in planner

    decision_thresholds = playbook.strategy["decision_thresholds"]
    hand_action = decision_thresholds["hand_action"]
    assert hand_action["clear_path_probability_floor"] == 0.75
    assert hand_action["pace_ratio_floor"] == 1.0
    assert hand_action["setup_discard_consensus_agreement"] == 3
    assert hand_action["low_discard_reserve"] == 1
    assert hand_action["low_discard_fallback_penalty"] == 10.0
    assert hand_action["low_hand_reserve"] == 1
    assert hand_action["low_hand_discard_fallback_bonus"] == 10.0

    joker_acquisition = decision_thresholds["joker_acquisition"]
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
