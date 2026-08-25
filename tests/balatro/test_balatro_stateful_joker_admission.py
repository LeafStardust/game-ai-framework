from __future__ import annotations

from types import SimpleNamespace

import games.balatro  # install package-level authorities
from games.balatro.state import BalatroState
from games.balatro.stateful_joker_admission_policy import (
    _has_additive_scoring_base,
    _has_madness,
    _has_retriggerable_held_target,
    _projected_stencil_multiplier,
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


def test_first_stencil_replacing_into_full_roster_is_exactly_x1():
    state = BalatroState()
    state.joker_slots = 5
    state.jokers = [SimpleNamespace(name=f"Joker {index}") for index in range(5)]
    candidate = SimpleNamespace(name="Joker Stencil")
    decision = SimpleNamespace(
        action="REPLACE",
        selected=SimpleNamespace(replace_index=1),
    )

    assert _projected_stencil_multiplier(state, candidate, decision) == 1


def test_second_stencil_in_full_roster_creates_real_x2_each():
    state = BalatroState()
    state.joker_slots = 5
    state.jokers = [
        SimpleNamespace(name="Joker Stencil"),
        *(SimpleNamespace(name=f"Joker {index}") for index in range(4)),
    ]
    candidate = SimpleNamespace(name="Joker Stencil")
    decision = SimpleNamespace(
        action="REPLACE",
        selected=SimpleNamespace(replace_index=1),
    )

    assert _projected_stencil_multiplier(state, candidate, decision) == 2


def test_negative_joker_does_not_consume_stencil_slot_projection():
    state = BalatroState()
    state.joker_slots = 6
    negative = SimpleNamespace(name="Negative support", edition="Negative")
    state.jokers = [
        negative,
        *(SimpleNamespace(name=f"Joker {index}") for index in range(4)),
    ]
    candidate = SimpleNamespace(name="Joker Stencil")
    decision = SimpleNamespace(action="BUY", selected=None)

    assert _projected_stencil_multiplier(state, candidate, decision) == 2


def test_blackboard_is_not_a_retriggerable_mime_target():
    state = BalatroState()
    state.jokers = [SimpleNamespace(name="Blackboard")]
    state.owned_deck = []

    assert not _has_retriggerable_held_target(state)


def test_steel_card_is_a_retriggerable_mime_target():
    state = BalatroState()
    state.owned_deck = [SimpleNamespace(enhancement="Steel", seal=None)]

    assert _has_retriggerable_held_target(state)


def test_empty_board_has_no_additive_base_for_obelisk():
    state = BalatroState()
    state.jokers = []

    assert not _has_additive_scoring_base(state)
