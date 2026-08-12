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
    assert playbook.version == "0.3"
    assert playbook.key == ("RED", "WHITE")
    planner = playbook.strategy["planner"]
    assert planner["min_clear_probability"] == 0.75
    assert planner["allow_pace_fallback"] is True
    assert planner["min_pace_ratio"] == 1.0

    hand_action = playbook.strategy["decision_thresholds"]["hand_action"]
    assert hand_action["play_clear_probability_floor"] == 0.75
    assert hand_action["discard_clear_probability_advantage"] == 0.05
    assert hand_action["discard_progress_advantage"] == 0.08
    assert hand_action["low_discard_reserve"] == 1
    assert hand_action["low_hand_reserve"] == 1


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
