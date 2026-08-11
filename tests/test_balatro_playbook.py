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
    assert playbook.key == ("RED", "WHITE")
    assert playbook.strategy["planner"]["min_clear_probability"] == 0.75


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
