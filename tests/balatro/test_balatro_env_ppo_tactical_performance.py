import json

import pytest

from games.balatro.env.ppo_tactical_performance import (
    PPO_TACTICAL_COST_SCHEMA,
    PPO_TACTICAL_COST_WORKLOAD,
    measure_ppo_tactical_cost,
    _instrument_episode_engine,
)


class _FakeAction:
    name = "PLAY_CARDS"

    def __init__(self, cards):
        self.cards = cards


class _FakeDecision:
    def __init__(self, cards):
        self.action = _FakeAction(cards)
        self.search_attempts = ()


class _FakePlanner:
    def _candidate_actions(self, state, **kwargs):
        return ()


class _FakePolicy:
    def decide(self, state, plans, **kwargs):
        return None


class _FakeEngine:
    def __init__(self):
        self.planner = _FakePlanner()
        self.policy = _FakePolicy()

    def _adaptive_planner(self, config):
        return _FakePlanner()

    def rank_plans(self, state, **kwargs):
        return ()

    def decide(self, state):
        self.planner._candidate_actions(state)
        self.rank_plans(state)
        self.policy.decide(state, ())
        return _FakeDecision([state.hand[0]])


def test_env_ppo_tactical_cost_pins_first_production_decision_and_search_trace():
    report = measure_ppo_tactical_cost()

    assert report.schema == PPO_TACTICAL_COST_SCHEMA
    assert report.workload == PPO_TACTICAL_COST_WORKLOAD
    assert report.root_seed == "RED-WHITE-PPO-V1"
    assert report.game_seed == "7258FFDA"
    assert report.action == "DISCARD_CARDS"
    assert report.selected_hand_indices == (3, 4, 5, 6, 7)
    assert report.search_attempts == (
        (2, 18, 2000, False),
        (3, 79, 2000, False),
        (3, 38, 1000, False),
    )
    assert report.total_elapsed_seconds > 0.0
    assert report.candidate_generation_elapsed_seconds > 0.0
    assert report.search_evaluation_elapsed_seconds > 0.0
    assert report.policy_arbitration_elapsed_seconds > 0.0
    assert report.other_elapsed_seconds >= 0.0
    assert json.loads(report.to_json())["selected_hand_indices"] == [3, 4, 5, 6, 7]


@pytest.mark.parametrize("root_seed", ["", 1, None])
def test_env_ppo_tactical_cost_rejects_invalid_root_seed(root_seed):
    with pytest.raises(ValueError, match="root_seed"):
        measure_ppo_tactical_cost(root_seed=root_seed)


def test_env_ppo_tactical_cost_rejects_noncallable_clock():
    with pytest.raises(TypeError, match="clock"):
        measure_ppo_tactical_cost(clock=None)


def test_env_ppo_episode_instrumentation_records_ordered_decision_cost():
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    engine = _FakeEngine()
    records = []
    ticks = iter(float(value) for value in range(20))
    _instrument_episode_engine(engine, lambda: next(ticks), records)

    decision = engine.decide(state)

    assert decision.action.cards == state.hand
    assert len(records) == 1
    assert records[0].action == "PLAY_CARDS"
    assert records[0].selected_hand_indices == (0,)
    assert len(records[0].public_input_sha256) == 64
    assert records[0].search_attempts == ()
