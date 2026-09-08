from __future__ import annotations

import inspect

import games.balatro  # noqa: F401 - install production policy stack
import games.balatro.live_decision_quality_policy as quality_policy
from games.balatro.planets import PLANET_CARDS
from games.balatro.state import BalatroState


def _planet(name: str):
    return next(card for card in PLANET_CARDS.values() if card.name == name)


def test_h12_planet_relevance_has_no_strategy_controller_dependency():
    source = inspect.getsource(quality_policy)

    assert "evaluate_bond_composition" not in source
    assert "strategy_plan" not in source.lower()
    assert "pinned_strategy_id" not in source
    assert "strategy_candidates" not in source


def test_h12_exotic_planet_cannot_bootstrap_from_level_without_play_history():
    state = BalatroState()
    state.hand_levels = {"STRAIGHT_FLUSH": 5}
    state.hand_play_counts = {"PAIR": 12, "TWO_PAIR": 5}

    relevant, notes = quality_policy._strict_planet_hand_relevant(
        state,
        _planet("Neptune"),
    )

    assert not relevant
    assert any("zero play history" in note for note in notes)
    assert all("strategy plan" not in note.lower() for note in notes)
    assert all("pinned strategy" not in note.lower() for note in notes)


def test_h12_sustained_public_exotic_hand_use_can_make_planet_relevant():
    state = BalatroState()
    state.hand_levels = {"STRAIGHT_FLUSH": 2}
    state.hand_play_counts = {"STRAIGHT_FLUSH": 3, "PAIR": 7}

    relevant, notes = quality_policy._strict_planet_hand_relevant(
        state,
        _planet("Neptune"),
    )

    assert relevant
    assert any("sustained use" in note for note in notes)
