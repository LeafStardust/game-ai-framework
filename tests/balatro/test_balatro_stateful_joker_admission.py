from __future__ import annotations

from types import SimpleNamespace

import games.balatro  # install package-level authorities
from games.balatro.state import BalatroState
from games.balatro.stateful_joker_admission_policy import (
    _has_madness,
    _target_hand,
    _todo_target_supported,
)


def test_madness_is_detected_from_owned_roster():
    state = BalatroState()
    state.jokers = [SimpleNamespace(name="Madness")]
    assert _has_madness(state)


def test_todo_straight_flush_target_is_rejected_without_history_or_pinned_path():
    state = BalatroState()
    state.hand_play_counts["STRAIGHT_FLUSH"] = 0
    candidate = SimpleNamespace(
        name="To Do List",
        public_state={"target_hand": "Straight Flush"},
    )

    assert _target_hand(candidate) == "STRAIGHT_FLUSH"
    assert not _todo_target_supported(state, candidate)


def test_todo_exotic_target_becomes_supported_after_actual_play_history():
    state = BalatroState()
    state.hand_play_counts["STRAIGHT_FLUSH"] = 1
    candidate = SimpleNamespace(
        name="To Do List",
        public_state={"target_hand": "Straight Flush"},
    )

    assert _todo_target_supported(state, candidate)


def test_todo_ordinary_hand_target_is_not_overblocked():
    state = BalatroState()
    candidate = SimpleNamespace(
        name="To Do List",
        public_state={"target_hand": "Pair"},
    )

    assert _todo_target_supported(state, candidate)
