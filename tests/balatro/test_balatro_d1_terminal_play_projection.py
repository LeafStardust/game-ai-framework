from copy import deepcopy
from types import SimpleNamespace

import pytest

import games.balatro.live.hand_action_planner as hand_action_planner
from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import create_small_blind
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = create_small_blind(100)
    state.score = 7
    state.hands_remaining = 3
    state.discards_remaining = 2
    state.consumable_slots = 2
    state.consumables = [object()]
    scorer = BalatroCard("2", "Clubs", live_id="scorer")
    blue = BalatroCard("3", "Hearts", seal="Blue", live_id="blue")
    state.hand = [scorer, blue]
    state.deck = []
    return state


def test_env_ppo_terminal_play_projection_matches_deepcopy_without_mutating_aliases():
    state = _state()
    planner = D1LiveBlindClearPlanner(horizon=1)
    planner._round_end_play_action = BalatroAction(
        PLAY_CARDS,
        cards=[state.hand[0]],
    )
    old_branch = deepcopy(state)
    old_branch.score = 40
    old_branch.hands_remaining = 0
    expected = planner._terminal_value(old_branch, clear=False)
    original_hand = state.hand
    original_cards = tuple(state.hand)
    original_consumables = state.consumables

    actual = planner._terminal_play_outcome_value(
        state,
        score_after=40,
        hands_after=0,
        clear=False,
    )

    assert actual == expected
    assert state.score == 7
    assert state.hands_remaining == 3
    assert state.hand is original_hand
    assert tuple(state.hand) == original_cards
    assert state.consumables is original_consumables


def test_env_ppo_depth_one_estimate_uses_terminal_shell_without_deepcopy(monkeypatch):
    state = _state()
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
    outcome = SimpleNamespace(
        score=40,
        probability=1.0,
        state_after_scoring=state,
    )
    projection = SimpleNamespace(
        joker_projection_complete=True,
        state_after_scoring=state,
        outcomes=(outcome,),
    )
    planner = D1LiveBlindClearPlanner(horizon=1)
    planner.evaluator = SimpleNamespace(project_play=lambda *_args: projection)

    def unexpected_deepcopy(_value):
        raise AssertionError("canonical terminal shell must not deepcopy")

    monkeypatch.setattr(hand_action_planner, "deepcopy", unexpected_deepcopy)
    estimate = planner._estimate_action(state, action, 1)

    assert estimate.value.expected_score == 47.0
    assert estimate.value.expected_hands_remaining == 2.0
    assert state.score == 7
    assert state.hands_remaining == 3


def test_env_ppo_terminal_play_projection_keeps_state_subclasses_on_deepcopy(
    monkeypatch,
):
    class ExtendedState(BalatroState):
        pass

    state = ExtendedState()
    state.blind = create_small_blind(100)
    observed = []
    original_deepcopy = deepcopy

    def tracked_deepcopy(value):
        observed.append(value)
        return original_deepcopy(value)

    monkeypatch.setattr(hand_action_planner, "deepcopy", tracked_deepcopy)
    value = D1LiveBlindClearPlanner()._terminal_play_outcome_value(
        state,
        score_after=25,
        hands_after=0,
        clear=False,
    )

    assert observed == [state]
    assert value.expected_score == 25.0
    assert state.score == 0
    assert state.hands_remaining == 4


def test_env_ppo_terminal_play_projection_keeps_overrides_and_malformed_state_fail_closed(
    monkeypatch,
):
    class OverriddenPlanner(D1LiveBlindClearPlanner):
        def _terminal_value(self, state, *, clear):
            state.hand.append("private-mutation")
            return super()._terminal_value(state, clear=clear)

    state = _state()
    original_hand = list(state.hand)
    observed = []
    original_deepcopy = deepcopy

    def tracked_deepcopy(value):
        observed.append(value)
        return original_deepcopy(value)

    monkeypatch.setattr(hand_action_planner, "deepcopy", tracked_deepcopy)
    value = OverriddenPlanner()._terminal_play_outcome_value(
        state,
        score_after=10,
        hands_after=0,
        clear=False,
    )

    assert observed == [state]
    assert value.expected_score == 10.0
    assert state.hand == original_hand

    with pytest.raises(AttributeError):
        D1LiveBlindClearPlanner()._terminal_play_outcome_value(
            object(),
            score_after=10,
            hands_after=0,
            clear=False,
        )
