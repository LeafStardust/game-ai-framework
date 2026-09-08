from __future__ import annotations

import inspect
from types import SimpleNamespace

import games.balatro  # noqa: F401 - install production policy stack
import games.balatro.stateful_joker_admission_policy as admission
from games.balatro.state import BalatroState


def test_h13_stateful_joker_admission_has_no_strategy_controller_dependency():
    source = inspect.getsource(admission)

    assert "evaluate_bond_composition" not in source
    assert "strategy_plan" not in source.lower()
    assert "pinned_strategy_id" not in source
    assert "strategy_candidates" not in source
    assert "_creates_strategy" not in source
    assert "_planned_hand_bonds" not in source
    assert "_plan_owns_hand" not in source


def test_h13_todo_exotic_target_requires_actual_public_play_history():
    state = BalatroState()
    state.hand_play_counts = {"PAIR": 12, "TWO_PAIR": 5}
    candidate = SimpleNamespace(target_hand="STRAIGHT_FLUSH")

    assert not admission._todo_target_supported(state, candidate)

    state.hand_play_counts["STRAIGHT_FLUSH"] = 1
    assert admission._todo_target_supported(state, candidate)


def test_h13_conditional_hand_requirement_uses_sustained_public_history(monkeypatch):
    state = BalatroState()
    state.hand_play_counts = {"PAIR": 8, "STRAIGHT": 1}
    candidate = SimpleNamespace()

    monkeypatch.setattr(
        admission,
        "_candidate_hand_requirements",
        lambda value: ("STRAIGHT",),
    )
    assert not admission._hand_requirements_supported(state, candidate)

    state.hand_play_counts = {"PAIR": 6, "STRAIGHT": 2}
    assert admission._hand_requirements_supported(state, candidate)
