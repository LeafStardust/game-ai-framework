import json
from itertools import count
from types import SimpleNamespace

import pytest

import games.balatro.env.ppo_tactical_performance as tactical_performance
from games.balatro.env.ppo_contract import PPOContractError
from games.balatro.env.ppo_tactical_performance import (
    PPO_TACTICAL_COST_SCHEMA,
    PPO_TACTICAL_COST_WORKLOAD,
    PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA,
    PPO_TACTICAL_EPISODE_COST_SCHEMA,
    measure_ppo_tactical_cost,
    trace_episode_seven_candidate_subowners,
    trace_initial_policy_ppo_episode_tactical_costs,
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


class _FakeScoreOutcomes:
    def __init__(self):
        self.scorer = SimpleNamespace(score=lambda *args, **kwargs: 1.0)

    def project_transition(self, *args, **kwargs):
        return SimpleNamespace(expected=1.0, minimum=0.0)

    def project(self, *args, **kwargs):
        result = self.project_transition(*args, **kwargs)
        self.scorer.score(*args, **kwargs)
        return result


class _FakeEvaluator:
    def __init__(self):
        self._outer_d1_cache_state = None
        self._outer_d1_evaluation_cache = {}
        self.score_outcomes = _FakeScoreOutcomes()
        self.action_generator = SimpleNamespace(
            generate_play_actions=lambda state: (_FakeAction(state.hand),)
        )

    @staticmethod
    def _action_key(action):
        return action.name, tuple(id(card) for card in action.cards)

    def _context(self, state):
        self._estimate_play(state, _FakeAction(state.hand))
        return state

    def _discard_value(self, state, action, context):
        self._has_guaranteed_clearing_play(state)
        return self._retained_structure_value(action.cards)

    def _estimate_play(self, state, action):
        hand = self._hand_for_cards(state, action.cards)
        return self.score_outcomes.project(hand, state, action.cards).expected

    def _has_guaranteed_clearing_play(self, state):
        for action in self.action_generator.generate_play_actions(state):
            hand = self._hand_for_cards(state, action.cards)
            if self.score_outcomes.project(hand, state, action.cards).minimum > 0:
                return True
        return False

    def _retained_structure_value(self, cards):
        return float(len(cards))

    def _hand_for_cards(self, state, cards):
        return "HIGH_CARD"

    def evaluate(self, state, action):
        if self._outer_d1_cache_state is not state:
            self._outer_d1_cache_state = state
            self._outer_d1_evaluation_cache = {}
        key = self._action_key(action)
        cached = self._outer_d1_evaluation_cache.get(key)
        if cached is not None:
            return cached
        value = self._discard_value(state, action, self._context(state))
        self._outer_d1_evaluation_cache[key] = value
        return value


class _FakePlanner:
    def __init__(self):
        self.evaluator = _FakeEvaluator()

    def _child_play_candidates(self, state, play_limit=1):
        return (state.hand[0],)

    def _discard_priority(self, state, action):
        return (self.evaluator.evaluate(state, action), len(action.cards))

    def _diverse_discard_beam(self, state, discards, limit=1):
        ranked = sorted(
            discards,
            key=lambda action: self._discard_priority(state, action),
            reverse=True,
        )
        self._discard_priority(state, ranked[0])
        return ranked[:limit]

    def _candidate_actions(self, state, **kwargs):
        self._diverse_discard_beam(state, (_FakeAction([state.hand[0]]),))
        return self._child_play_candidates(state)


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


def test_env_ppo_initial_policy_episode_trace_targets_only_requested_first_wave(
    monkeypatch,
):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    engine = _FakeEngine()
    environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=engine)
    )
    requested_streams = []
    collector_calls = []

    def environment_factory(stream_index):
        requested_streams.append(stream_index)
        return environment

    class FakeLearner:
        def __init__(self, training_run):
            self.training_run = training_run
            self.model = SimpleNamespace(infer=lambda observation, mask: None)

    def collector(target, training_run, *, episode_index, policy):
        collector_calls.append(
            (target, training_run.game_seed(episode_index), episode_index, policy)
        )
        engine.decide(state)
        engine.decide(state)
        return SimpleNamespace(episode_index=episode_index, decisions=(1, 2, 3))

    monkeypatch.setattr(
        tactical_performance,
        "make_ppo_training_environment",
        environment_factory,
    )
    monkeypatch.setattr(tactical_performance, "PPOLearner", FakeLearner)
    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collector,
    )
    ticks = iter(float(value) for value in range(18))

    report = trace_initial_policy_ppo_episode_tactical_costs(
        episode_index=7,
        clock=lambda: next(ticks),
    )

    assert requested_streams == [7]
    assert len(collector_calls) == 1
    assert collector_calls[0][:3] == (environment, "3DEFB26A", 7)
    assert callable(collector_calls[0][3])
    assert report.schema == PPO_TACTICAL_EPISODE_COST_SCHEMA
    assert report.root_seed == "RED-WHITE-PPO-V1"
    assert report.episode_index == 7
    assert report.stream_index == 7
    assert report.game_seed == "3DEFB26A"
    assert report.environment_transitions == 3
    assert report.total_elapsed_seconds == 17.0
    assert report.tactical_elapsed_seconds == 14.0
    assert len(report.decisions) == 2
    assert [record.action for record in report.decisions] == [
        "PLAY_CARDS",
        "PLAY_CARDS",
    ]
    payload = json.loads(report.to_json())
    assert payload["episode_index"] == 7
    assert len(payload["decisions"]) == 2


def test_env_ppo_candidate_subowner_stops_at_verified_target(monkeypatch):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    digest = tactical_performance._public_input_sha256(state)
    monkeypatch.setattr(
        tactical_performance,
        "_EPISODE_7_EXPECTED_PREFIX",
        ((digest, "PLAY_CARDS", (0,), ()),),
    )
    engine = _FakeEngine()
    environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=engine)
    )
    requested_streams = []

    def environment_factory(stream_index):
        requested_streams.append(stream_index)
        return environment

    class FakeLearner:
        def __init__(self, training_run):
            self.model = SimpleNamespace(infer=lambda observation, mask: None)

    def collector(target, training_run, *, episode_index, policy):
        engine.decide(state)
        raise AssertionError("target decision must stop collection")

    monkeypatch.setattr(
        tactical_performance,
        "make_ppo_training_environment",
        environment_factory,
    )
    monkeypatch.setattr(tactical_performance, "PPOLearner", FakeLearner)
    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collector,
    )
    ticks = count()

    report = trace_episode_seven_candidate_subowners(
        clock=lambda: float(next(ticks)),
    )

    assert requested_streams == [7]
    assert report.schema == PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA
    assert report.schema == "balatro-red-white-ppo-tactical-candidate-subowner-v6"
    assert report.game_seed == "3DEFB26A"
    assert report.verified_prefix_decisions == 1
    assert report.target_decision_index == 0
    assert report.public_input_sha256 == digest
    assert report.action == "PLAY_CARDS"
    assert report.selected_hand_indices == (0,)
    assert report.search_attempts == ()
    assert report.candidate_generation_elapsed_seconds > 0.0
    assert report.helper_costs[0].name == "_child_play_candidates"
    assert report.helper_costs[0].calls == 1
    helper_costs = {cost.name: cost for cost in report.helper_costs}
    assert helper_costs["_diverse_discard_beam"].calls == 1
    assert helper_costs["_discard_priority"].calls == 2
    assert helper_costs["_evaluator_evaluate"].calls == 2
    assert helper_costs["_evaluator_context"].calls == 1
    assert helper_costs["_evaluator_discard_value"].calls == 1
    assert helper_costs["_evaluator_estimate_play"].calls == 1
    assert helper_costs["_evaluator_guaranteed_clear"].calls == 1
    assert helper_costs["_evaluator_retained_structure"].calls == 1
    assert helper_costs["_evaluator_hand_for_cards"].calls == 2
    assert helper_costs["_score_outcomes_project"].calls == 2
    assert helper_costs["_score_outcomes_project_transition"].calls == 2
    assert helper_costs["_score_outcomes_scorer_score"].calls == 2
    assert helper_costs["_generate_play_actions"].calls == 1
    assert report.evaluation_cache_hits == 1
    assert report.evaluation_cache_misses == 1
    assert helper_costs["_diverse_discard_beam"].exclusive_elapsed_seconds > 0.0
    assert helper_costs["_discard_priority"].exclusive_elapsed_seconds > 0.0
    assert sum(
        cost.exclusive_elapsed_seconds for cost in report.helper_costs
    ) <= report.candidate_generation_elapsed_seconds
    assert json.loads(report.to_json())["target_decision_index"] == 0


@pytest.mark.parametrize("root_seed", ["", "OTHER"])
def test_env_ppo_candidate_subowner_rejects_noncanonical_root_seed(root_seed):
    with pytest.raises(PPOContractError, match="root seed RED-WHITE-PPO-V1"):
        trace_episode_seven_candidate_subowners(root_seed=root_seed)


def test_env_ppo_candidate_subowner_rejects_prefix_drift(monkeypatch):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    engine = _FakeEngine()
    environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=engine)
    )
    monkeypatch.setattr(
        tactical_performance,
        "make_ppo_training_environment",
        lambda stream_index: environment,
    )
    monkeypatch.setattr(
        tactical_performance,
        "PPOLearner",
        lambda training_run: SimpleNamespace(
            model=SimpleNamespace(infer=lambda observation, mask: None)
        ),
    )
    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        lambda target, training_run, *, episode_index, policy: engine.decide(state),
    )

    with pytest.raises(PPOContractError, match="digest drifted at decision 0"):
        trace_episode_seven_candidate_subowners()


@pytest.mark.parametrize("episode_index", [-1, 8, True, 1.0, None])
def test_env_ppo_initial_policy_episode_trace_rejects_non_first_wave_index(
    episode_index,
):
    with pytest.raises(PPOContractError, match="first-wave episode index"):
        trace_initial_policy_ppo_episode_tactical_costs(episode_index=episode_index)
