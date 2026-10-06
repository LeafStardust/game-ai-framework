import json
from hashlib import sha256
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
    PPO_TACTICAL_SCHEDULE_PROBE_SCHEMA,
    PPO_TACTICAL_HORIZON_TWO_PARITY_SCHEMA,
    PPO_TACTICAL_EPISODE_PAIRED_PARITY_SCHEMA,
    PPO_TACTICAL_SELECTIVE_ESCALATION_SCHEMA,
    measure_ppo_tactical_cost,
    compare_first_production_inert_transition_aliases,
    probe_episode_seven_bounded_schedules,
    probe_episode_seven_horizon_two_parity,
    probe_episode_seven_selective_escalation,
    probe_episode_zero_horizon_two_parity,
    trace_episode_seven_candidate_subowners,
    trace_episode_43_decision_11_candidate_subowners,
    trace_episode_43_decision_12_candidate_subowners,
    trace_initial_policy_ppo_episode_tactical_costs,
    write_ppo_tactical_candidate_subowner_report,
    write_ppo_tactical_episode_report,
    _ReconstructTypeSampler,
    _instrument_episode_engine,
)


def test_env_ppo_inert_generated_transition_alias_contract():
    report = compare_first_production_inert_transition_aliases()

    assert report.schema == "balatro-red-white-ppo-inert-alias-v1"
    assert report.inherited_public_state_sha256 == report.wrapped_public_state_sha256
    assert report.inherited_input_card_aliases > 0
    assert report.wrapped_input_card_aliases == 0


class _FakeAction:
    name = "PLAY_CARDS"

    def __init__(self, cards):
        self.cards = cards


class _FakeDecision:
    def __init__(self, cards):
        self.action = _FakeAction(cards)
        self.search_attempts = ()
        self.mode = "PACE_RECOVERY"
        self.confidence = 0.625
        self.setup_discard_consensus = False
        self.clear_path_candidates = 0
        self.best_play_pace_ratio = 0.75
        self.selected_pace_ratio = None
        self.selected_fallback_value = 12.5


class _FakeDiscardProjector:
    def project(self, state, cards, **kwargs):
        branch_state = self._copy_state_shell(state)
        self._clone_joker_graph(branch_state, state)
        active = self._active_jokers(branch_state, **kwargs)
        context, _discards_used = self._prepare_discard_context(
            branch_state,
            cards,
            active,
            **kwargs,
        )
        context = self._apply_active_jokers(active, context)
        self._finalize_discard_side_effects(
            branch_state,
            cards,
            context,
            discards_used=0,
            **kwargs,
        )
        return branch_state

    @staticmethod
    def _copy_state_shell(state):
        return state

    @staticmethod
    def _clone_joker_graph(branch_state, source_state):
        return ()

    @staticmethod
    def _active_jokers(state, **kwargs):
        return ("active",)

    @staticmethod
    def _prepare_discard_context(state, cards, active, **kwargs):
        return SimpleNamespace(), 0

    @staticmethod
    def _apply_active_jokers(active, context):
        return context

    @staticmethod
    def _finalize_discard_side_effects(
        state,
        cards,
        context,
        **kwargs,
    ):
        return None


class _FakeScoreOutcomes:
    def __init__(self):
        self.scorer = SimpleNamespace(score=lambda *args, **kwargs: 1.0)
        self.joker_projector = SimpleNamespace(
            score=lambda *args, **kwargs: SimpleNamespace()
        )
        self.discard_joker_projector = _FakeDiscardProjector()

    @staticmethod
    def _activation_count(state, class_name):
        return 0

    @staticmethod
    def _effective_main_abilities(state):
        return ()

    @staticmethod
    def _joker_active(joker):
        return True

    def project_transition(self, *args, **kwargs):
        self._project_hook_transition(*args, **kwargs)
        return self._project_non_hook_transition(*args, **kwargs)

    def _project_hook_transition(self, *args, **kwargs):
        state = args[1]
        cards = args[2]
        held = self._held_cards_after_play_selection(state, cards)
        branches = self._hook_forced_discard_branches(held, 1)
        for forced_cards in branches:
            branch_state = self.discard_joker_projector.project(
                state,
                forced_cards,
                consume_discard_use=False,
            )
            self._remove_cards(branch_state.hand, forced_cards)
            self._append_hook_outcomes([], SimpleNamespace(), 1.0)
        return SimpleNamespace(expected=1.0, minimum=0.0)

    def _project_non_hook_transition(self, *args, **kwargs):
        return SimpleNamespace(expected=1.0, minimum=0.0)

    def project(self, *args, **kwargs):
        result = self.project_transition(*args, **kwargs)
        self.scorer.score(*args, **kwargs)
        return result

    @classmethod
    def _held_cards_after_play_selection(cls, state, cards):
        return cls._remove_cards(state.hand, cards)

    @staticmethod
    def _hook_forced_discard_branches(held, discard_count):
        return ((held[0],),) if held else ((),)

    @staticmethod
    def _remove_cards(source, removed):
        return list(source)

    @staticmethod
    def _append_hook_outcomes(outcomes, transition, branch_probability):
        return 1


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
        self.max_horizon = 8
        self.max_search_nodes = 5000

    def _adaptive_planner(self, config):
        return _FakePlanner()

    def rank_plans(self, state, **kwargs):
        return ()

    def decide(self, state):
        self.planner._candidate_actions(state)
        self.rank_plans(state)
        self.policy.decide(state, ())
        return _FakeDecision([state.hand[0]])


def test_reconstruct_type_sampler_uses_exact_bounded_exclusive_sample():
    ticks = count()
    sampler = _ReconstructTypeSampler(
        clock=lambda: float(next(ticks)),
        limit=2,
    )
    sampled_child = sampler.wrap_child(lambda: None)
    sampled_reconstruct = None

    def reconstruct(value):
        if value == "outer":
            sampled_reconstruct("inner")
            sampled_child()
        return value

    sampled_reconstruct = sampler.wrap_reconstruct(reconstruct)

    assert sampled_reconstruct("outer") == "outer"
    assert sampled_reconstruct("after-limit") == "after-limit"
    assert sampler.sampled_calls == 2
    assert sampler.calls_by_type == {str: 2}
    assert sampler.elapsed_by_type == {str: 4.0}
    assert next(ticks) == 6


def test_env_ppo_tactical_cost_pins_first_production_decision_and_search_trace():
    report = measure_ppo_tactical_cost()

    assert report.schema == PPO_TACTICAL_COST_SCHEMA
    assert report.workload == PPO_TACTICAL_COST_WORKLOAD
    assert report.root_seed == "RED-WHITE-PPO-V1"
    assert report.game_seed == "7258FFDA"
    assert report.action == "DISCARD_CARDS"
    assert report.selected_hand_indices == (3, 4, 5, 6, 7)
    assert report.search_attempts == ((2, 18, 2000, False),)
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


def test_env_ppo_episode_instrumentation_owns_immediate_fallback_search_cost():
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    engine = _FakeEngine()

    def rank_immediate_plans(target):
        engine.planner._candidate_actions(target)
        return ()

    engine._rank_immediate_plans = rank_immediate_plans

    def decide(target):
        engine._rank_immediate_plans(target)
        engine.policy.decide(target, ())
        return _FakeDecision([target.hand[0]])

    engine.decide = decide
    records = []
    ticks = count()
    _instrument_episode_engine(engine, lambda: float(next(ticks)), records)

    engine.decide(state)

    assert len(records) == 1
    record = records[0]
    assert record.candidate_generation_elapsed_seconds > 0.0
    assert record.search_evaluation_elapsed_seconds > 0.0
    assert sum(
        (
            record.candidate_generation_elapsed_seconds,
            record.search_evaluation_elapsed_seconds,
            record.policy_arbitration_elapsed_seconds,
            record.other_elapsed_seconds,
        )
    ) == record.total_elapsed_seconds


def test_env_ppo_search_subowner_scope_excludes_candidate_and_policy_helpers(
    monkeypatch,
):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    digest = tactical_performance._public_input_sha256(state)
    engine = _FakeEngine()
    environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=engine)
    )

    def estimate_action(target, action, depth):
        return engine.planner.evaluator.evaluate(target, action)

    engine.planner._estimate_action = estimate_action

    def rank_plans(target, **kwargs):
        engine.planner._estimate_action(
            target,
            _FakeAction(target.hand),
            2,
        )
        return ()

    engine.rank_plans = rank_plans

    def collect(target, training_run, *, episode_index, policy):
        engine.decide(state)
        raise AssertionError("search subowner target must stop collection")

    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collect,
    )
    ticks = count()
    result = tactical_performance._trace_candidate_subowners(
        episode_index=637,
        target_index=0,
        expected_prefix=((digest, "PLAY_CARDS", (0,), ()),),
        clock=lambda: float(next(ticks)),
        environment=environment,
        policy=lambda observation, mask: None,
        helper_scope="search_evaluation",
    )

    assert isinstance(result, tactical_performance._PPOTacticalScopedSubownerTrace)
    costs = {item.name: item for item in result.report.helper_costs}
    assert costs["_estimate_action"].calls == 1
    assert costs["_evaluator_evaluate"].calls == 1
    assert "_candidate_actions" not in costs
    assert result.search_evaluation_elapsed_seconds > 0.0
    assert result.policy_arbitration_elapsed_seconds > 0.0
    assert result.residual_search_evaluation_elapsed_seconds >= 0.0


def test_env_ppo_search_subowner_scope_rejects_clock_drift(monkeypatch):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    digest = tactical_performance._public_input_sha256(state)
    engine = _FakeEngine()
    environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=engine)
    )

    def collect(target, training_run, *, episode_index, policy):
        engine.decide(state)

    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collect,
    )
    ticks = count()
    with pytest.raises(PPOContractError, match="clock moved backwards"):
        tactical_performance._trace_candidate_subowners(
            episode_index=637,
            target_index=0,
            expected_prefix=((digest, "PLAY_CARDS", (0,), ()),),
            clock=lambda: -float(next(ticks)),
            environment=environment,
            policy=lambda observation, mask: None,
            helper_scope="search_evaluation",
        )


def test_env_ppo_initial_policy_episode_trace_targets_only_requested_episode(
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
        episode_index=43,
        clock=lambda: next(ticks),
    )

    assert requested_streams == [3]
    assert len(collector_calls) == 1
    assert collector_calls[0][:3] == (environment, "EE424B52", 43)
    assert callable(collector_calls[0][3])
    assert report.schema == PPO_TACTICAL_EPISODE_COST_SCHEMA
    assert report.root_seed == "RED-WHITE-PPO-V1"
    assert report.episode_index == 43
    assert report.stream_index == 3
    assert report.game_seed == "EE424B52"
    assert report.environment_transitions == 3
    assert report.total_elapsed_seconds == 17.0
    assert report.tactical_elapsed_seconds == 14.0
    assert len(report.decisions) == 2
    assert [record.action for record in report.decisions] == [
        "PLAY_CARDS",
        "PLAY_CARDS",
    ]
    payload = json.loads(report.to_json())
    assert payload["episode_index"] == 43
    assert len(payload["decisions"]) == 2


def test_env_ppo_generated_consumable_capability_classification_is_exact():
    sixth_sense = type("SixthSenseJoker", (), {})()
    state = SimpleNamespace(jokers=[sixth_sense])
    model = SimpleNamespace(
        _activation_count=lambda observed, name: 2,
        _effective_main_abilities=lambda observed: ("VagabondJoker",),
        _joker_active=lambda joker: True,
    )

    assert tactical_performance._generated_consumable_capabilities(
        model, state
    ) == (True, True, True)

    model._activation_count = lambda observed, name: 0
    model._effective_main_abilities = lambda observed: ()
    model._joker_active = lambda joker: False
    assert tactical_performance._generated_consumable_capabilities(
        model, state
    ) == (False, False, False)


def test_env_ppo_schedule_probe_is_bounded_and_restores_engine(monkeypatch):
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

    def collector(target, training_run, *, episode_index, policy):
        target._backend._tactical_decision_engine.decide(state)
        raise AssertionError("schedule probe must stop at target")

    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collector,
    )
    ticks = count()

    report = probe_episode_seven_bounded_schedules(
        clock=lambda: float(next(ticks))
    )

    assert report.schema == PPO_TACTICAL_SCHEDULE_PROBE_SCHEMA
    assert report.public_input_sha256 == digest
    assert report.verified_prefix_decisions == 0
    assert [result.max_horizon for result in report.results] == [2, 3]
    assert all(result.max_nodes == 2000 for result in report.results)
    assert all(result.action == "PLAY_CARDS" for result in report.results)
    assert all(result.selected_hand_indices == (0,) for result in report.results)
    assert all(result.elapsed_seconds == 1.0 for result in report.results)
    assert engine.max_horizon == 8
    assert engine.max_search_nodes == 5000


def test_env_ppo_horizon_two_parity_uses_separate_bounded_engine(monkeypatch):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    digest = tactical_performance._public_input_sha256(state)
    monkeypatch.setattr(
        tactical_performance,
        "_EPISODE_7_EXPECTED_PREFIX",
        (
            (digest, "PLAY_CARDS", (0,), ()),
            (digest, "PLAY_CARDS", (0,), ()),
        ),
    )
    production_engine = _FakeEngine()
    probe_engine = _FakeEngine()
    environments = iter(
        (
            SimpleNamespace(
                _backend=SimpleNamespace(
                    _tactical_decision_engine=production_engine
                )
            ),
            SimpleNamespace(
                _backend=SimpleNamespace(_tactical_decision_engine=probe_engine)
            ),
        )
    )
    monkeypatch.setattr(
        tactical_performance,
        "make_ppo_training_environment",
        lambda stream_index: next(environments),
    )
    monkeypatch.setattr(
        tactical_performance,
        "PPOLearner",
        lambda training_run: SimpleNamespace(
            model=SimpleNamespace(infer=lambda observation, mask: None)
        ),
    )

    def collector(target, training_run, *, episode_index, policy):
        target._backend._tactical_decision_engine.decide(state)
        target._backend._tactical_decision_engine.decide(state)
        raise AssertionError("parity probe must stop at target")

    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collector,
    )
    ticks = count()

    report = probe_episode_seven_horizon_two_parity(
        clock=lambda: float(next(ticks))
    )

    assert report.schema == PPO_TACTICAL_HORIZON_TWO_PARITY_SCHEMA
    assert report.verified_production_decisions == 1
    assert report.all_actions_match is True
    assert len(report.records) == 2
    assert report.records[0].matches_expected is True
    assert report.records[0].elapsed_seconds == 1.0
    assert report.records[0].probe_signal.mode == "PACE_RECOVERY"
    assert report.records[0].probe_signal.confidence == 0.625
    assert report.records[0].probe_signal.best_play_pace_ratio == 0.75
    assert report.records[0].probe_signal.selected_pace_ratio is None
    assert report.records[0].probe_signal.selected_fallback_value == 12.5
    assert report.records[0].production_signal == report.records[0].probe_signal
    assert report.records[1].production_signal is None
    assert probe_engine.max_horizon == 8
    assert probe_engine.max_search_nodes == 5000
    assert production_engine.max_horizon == 8


def test_env_ppo_episode_zero_parity_keeps_production_authoritative(monkeypatch):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    production_engine = _FakeEngine()
    probe_engine = _FakeEngine()
    production_environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=production_engine)
    )
    environments = iter(
        (
            production_environment,
            SimpleNamespace(
                _backend=SimpleNamespace(_tactical_decision_engine=probe_engine)
            ),
        )
    )
    monkeypatch.setattr(
        tactical_performance,
        "make_ppo_training_environment",
        lambda stream_index: next(environments),
    )
    monkeypatch.setattr(
        tactical_performance,
        "PPOLearner",
        lambda training_run: SimpleNamespace(
            model=SimpleNamespace(infer=lambda observation, mask: None)
        ),
    )

    def collector(target, training_run, *, episode_index, policy):
        target._backend._tactical_decision_engine.decide(state)
        return SimpleNamespace(episode_index=0, decisions=(object(),))

    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collector,
    )
    ticks = count()

    report = probe_episode_zero_horizon_two_parity(
        clock=lambda: float(next(ticks))
    )

    assert report.schema == PPO_TACTICAL_EPISODE_PAIRED_PARITY_SCHEMA
    assert report.episode_index == 0
    assert report.environment_transitions == 1
    assert report.all_actions_match is True
    assert len(report.records) == 1
    assert report.records[0].probe_elapsed_seconds == 1.0
    assert report.records[0].production_elapsed_seconds == 1.0
    assert report.records[0].matches_production is True
    assert report.records[0].probe_signal.setup_discard_consensus is False
    assert report.records[0].probe_signal.clear_path_candidates == 0
    assert report.records[0].production_signal == report.records[0].probe_signal
    assert json.loads(report.to_json())["records"][0]["probe_signal"] == {
        "best_play_pace_ratio": 0.75,
        "clear_path_candidates": 0,
        "confidence": 0.625,
        "mode": "PACE_RECOVERY",
        "selected_fallback_value": 12.5,
        "selected_pace_ratio": None,
        "setup_discard_consensus": False,
    }
    assert probe_engine.max_horizon == 8
    assert probe_engine.max_search_nodes == 5000


def test_env_ppo_parity_decision_signal_rejects_nonfinite_evidence():
    decision = _FakeDecision(())
    decision.confidence = float("nan")

    with pytest.raises(RuntimeError, match="nonfinite"):
        tactical_performance._decision_signal(decision)


def test_env_ppo_selective_escalation_recovers_frozen_target(monkeypatch):
    from games.balatro.actions import DISCARD_CARDS, BalatroAction
    from games.balatro.card import BalatroCard
    from games.balatro.live.hand_action_policy import (
        PACE_RECOVERY,
        LiveHandActionDecisionEngine,
    )
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard(rank, "Spades") for rank in ("A", "K", "Q", "J", "10")]
    digest = tactical_performance._public_input_sha256(state)
    monkeypatch.setattr(
        tactical_performance,
        "_EPISODE_7_EXPECTED_PREFIX",
        ((digest, "DISCARD_CARDS", (0, 1, 2, 3, 4), ()),),
    )
    monkeypatch.setattr(
        tactical_performance,
        "_SELECTIVE_ESCALATION_TARGET_DIGEST",
        digest,
    )

    class SelectiveEngine:
        def __init__(self, card_count):
            self.card_count = card_count
            self.max_horizon = 8
            self.max_search_nodes = 5000

        def decide(self, observed):
            return SimpleNamespace(
                action=BalatroAction(
                    DISCARD_CARDS,
                    cards=list(observed.hand[: self.card_count]),
                ),
                search_attempts=(),
                mode=PACE_RECOVERY,
                confidence=0.6,
                setup_discard_consensus=False,
                clear_path_candidates=0,
                best_play_pace_ratio=0.4,
                selected_pace_ratio=None,
                selected_fallback_value=100.0,
            )

        _selective_deepening_candidate = staticmethod(
            LiveHandActionDecisionEngine._selective_deepening_candidate
        )

    production_engine = SelectiveEngine(5)
    shallow_engine = SelectiveEngine(2)
    escalation_engine = SelectiveEngine(5)
    environments = iter(
        SimpleNamespace(
            _backend=SimpleNamespace(_tactical_decision_engine=engine)
        )
        for engine in (production_engine, shallow_engine, escalation_engine)
    )
    monkeypatch.setattr(
        tactical_performance,
        "make_ppo_training_environment",
        lambda stream_index: next(environments),
    )
    monkeypatch.setattr(
        tactical_performance,
        "PPOLearner",
        lambda training_run: SimpleNamespace(
            model=SimpleNamespace(infer=lambda observation, mask: None)
        ),
    )

    def collector(target, training_run, *, episode_index, policy):
        target._backend._tactical_decision_engine.decide(state)
        raise AssertionError("selective probe must stop at target")

    monkeypatch.setattr(
        tactical_performance,
        "collect_complete_ppo_episode",
        collector,
    )

    report = probe_episode_seven_selective_escalation()

    assert report.schema == PPO_TACTICAL_SELECTIVE_ESCALATION_SCHEMA
    assert report.verified_production_decisions == 1
    assert report.trigger_count == 1
    assert report.all_escalations_match is True
    assert report.records[0].shallow_hand_indices == (0, 1)
    assert report.records[0].escalated_hand_indices == (0, 1, 2, 3, 4)
    assert report.records[0].matches_production is True
    assert shallow_engine.max_horizon == 8
    assert escalation_engine.max_horizon == 8


@pytest.mark.parametrize(
    ("episode_index", "prefix_name", "trace", "expected_stream", "game_seed"),
    (
        (
            7,
            "_EPISODE_7_EXPECTED_PREFIX",
            trace_episode_seven_candidate_subowners,
            7,
            "3DEFB26A",
        ),
        (
            43,
            "_EPISODE_43_DECISION_11_EXPECTED_PREFIX",
            trace_episode_43_decision_11_candidate_subowners,
            3,
            "EE424B52",
        ),
        (
            43,
            "_EPISODE_43_DECISION_12_EXPECTED_PREFIX",
            trace_episode_43_decision_12_candidate_subowners,
            3,
            "EE424B52",
        ),
    ),
)
def test_env_ppo_candidate_subowner_stops_at_verified_target(
    monkeypatch,
    episode_index,
    prefix_name,
    trace,
    expected_stream,
    game_seed,
):
    from games.balatro.card import BalatroCard
    from games.balatro.state import BalatroState

    state = BalatroState()
    state.hand = [BalatroCard("A", "Spades")]
    digest = tactical_performance._public_input_sha256(state)
    monkeypatch.setattr(
        tactical_performance,
        prefix_name,
        ((digest, "PLAY_CARDS", (0,), ()),),
    )
    engine = _FakeEngine()
    environment = SimpleNamespace(
        _backend=SimpleNamespace(_tactical_decision_engine=engine)
    )
    requested_streams = []
    generated_transition_class = (
        tactical_performance.LiveGeneratedConsumableScoreOutcomeModel
    )
    visible_transition_class = (
        tactical_performance.LiveVisibleCardScoreOutcomeModel
    )

    def visible_transition(self, *args, **kwargs):
        return SimpleNamespace(expected=1.0, minimum=0.0)

    def tactical_copy(self):
        card = self.hand[0]
        if tactical_performance.balatro_state._has_exact_scalar_card_state(
            card,
            frozenset(BalatroCard.__dataclass_fields__),
        ):
            tactical_performance.balatro_state._copy_exact_scalar_card(card)
        return tactical_performance.balatro_state.deepcopy(self)

    def state_deepcopy(value, memo=None):
        tactical_performance.copy_module._deepcopy_dispatch[dict]({}, {})
        tactical_performance.copy_module._deepcopy_dispatch[list]([], {})
        tactical_performance.copy_module._reconstruct(
            value,
            {},
            SimpleNamespace,
            (),
        )
        return value

    def generated_transition(self, *args, **kwargs):
        self.joker_projector.score(*args, **kwargs)
        visible_transition_class.project_transition(self, *args, **kwargs)
        tactical_performance.balatro_state.deepcopy(self)
        args[1].copy_for_tactical_projection()
        args[1].copy().detach_tactical_mutable_aliases()
        return SimpleNamespace(expected=1.0, minimum=0.0)

    monkeypatch.setattr(
        visible_transition_class,
        "project_transition",
        visible_transition,
    )
    monkeypatch.setattr(BalatroState, "copy_for_tactical_projection", tactical_copy)
    monkeypatch.setattr(tactical_performance.balatro_state, "deepcopy", state_deepcopy)
    monkeypatch.setattr(
        generated_transition_class,
        "project_transition",
        generated_transition,
    )
    score_outcomes = engine.planner.evaluator.score_outcomes
    hook_held_cards = score_outcomes._held_cards_after_play_selection
    hook_forced_branches = score_outcomes._hook_forced_discard_branches
    hook_remove_cards = score_outcomes._remove_cards
    hook_outcome_aggregation = score_outcomes._append_hook_outcomes
    hook_discard_projection = score_outcomes.discard_joker_projector.project
    discard_projection_helpers = {
        name: getattr(score_outcomes.discard_joker_projector, name)
        for name in (
            "_copy_state_shell",
            "_clone_joker_graph",
            "_active_jokers",
            "_prepare_discard_context",
            "_apply_active_jokers",
            "_finalize_discard_side_effects",
        )
    }

    def non_hook_transition(*args, **kwargs):
        return generated_transition_class.project_transition(
            score_outcomes,
            *args,
            **kwargs,
        )

    score_outcomes._project_non_hook_transition = non_hook_transition

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
    reconstruct = tactical_performance.copy_module._reconstruct
    dict_deepcopy = tactical_performance.copy_module._deepcopy_dispatch[dict]
    list_deepcopy = tactical_performance.copy_module._deepcopy_dispatch[list]
    state_card_validation = (
        tactical_performance.balatro_state._has_exact_scalar_card_state
    )
    state_card_shallow_copy = (
        tactical_performance.balatro_state._copy_exact_scalar_card
    )
    state_detachment = BalatroState.detach_tactical_mutable_aliases
    state_card_detachment = BalatroState._detach_tactical_card_collections
    state_named_detachment = BalatroState._detach_tactical_named_collection
    detached_unique_cards = len(
        {
            id(card)
            for collection in (
                state.deck,
                state.owned_deck or (),
                state.hand,
                state.discard_pile,
            )
            for card in collection
        }
    )
    expected_card_samples = 2 + 2 * detached_unique_cards
    ticks = count()

    report = trace(
        clock=lambda: float(next(ticks)),
    )

    assert requested_streams == [expected_stream]
    assert report.schema == PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA
    assert report.schema == "balatro-red-white-ppo-tactical-candidate-subowner-v18"
    assert report.episode_index == episode_index
    assert report.stream_index == expected_stream
    assert report.game_seed == game_seed
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
    assert helper_costs["_score_outcomes_hook_transition"].calls == 2
    assert helper_costs["_hook_held_cards"].calls == 2
    assert helper_costs["_hook_forced_branches"].calls == 2
    assert helper_costs["_hook_discard_projection"].calls == 2
    assert helper_costs["_hook_remove_cards"].calls == 2
    assert helper_costs["_hook_outcome_aggregation"].calls == 2
    assert report.hook_forced_branch_sets == 2
    assert report.hook_forced_branches == 2
    assert report.hook_discard_projection_calls == 2
    assert report.hook_outcome_aggregation_calls == 2
    assert report.hook_aggregated_outcomes == 2
    for name in (
        "_discard_state_shell_copy",
        "_discard_joker_graph_clone",
        "_discard_active_joker_selection",
        "_discard_context_preparation",
        "_discard_joker_application",
        "_discard_side_effect_finalization",
    ):
        assert helper_costs[name].calls == 2
    assert report.discard_active_joker_selection_calls == 2
    assert report.discard_active_jokers_selected == 2
    assert report.discard_joker_application_calls == 2
    assert report.discard_jokers_applied == 2
    assert helper_costs["_score_outcomes_non_hook_transition"].calls == 2
    assert helper_costs["_generated_consumable_project_transition"].calls == 2
    assert report.generated_consumable_transition_calls == 2
    assert report.generated_consumable_inert_calls == 2
    assert report.generated_consumable_eight_ball_capable_calls == 0
    assert report.generated_consumable_main_generator_capable_calls == 0
    assert report.generated_consumable_sixth_sense_capable_calls == 0
    assert helper_costs["_generated_joker_projector_score"].calls == 2
    assert helper_costs["_visible_card_project_transition"].calls == 2
    assert helper_costs["_state_copy_for_tactical_projection"].calls == 2
    assert helper_costs["_state_projection_deepcopy"].calls == 2
    assert helper_costs["_state_deepcopy_reconstruct"].calls == 2
    assert helper_costs["_state_deepcopy_dict"].calls == 2
    assert helper_costs["_state_deepcopy_list"].calls == 2
    assert helper_costs["_state_detach_tactical_mutable_aliases"].calls == 2
    assert helper_costs["_state_detach_card_collections"].calls == 2
    assert "_state_detach_extended_card_deepcopy" not in helper_costs
    for name in (
        "consumables",
        "shop_jokers",
        "shop_consumables",
        "shop_boosters",
        "shop_vouchers",
        "vouchers",
    ):
        assert helper_costs[f"_state_detach_{name}"].calls == 2
    assert report.reconstruct_type_sample_limit == 100_000
    assert report.reconstruct_type_sampled_calls == 2
    assert [
        (sample.type_name, sample.sampled_calls)
        for sample in report.reconstruct_type_samples
    ] == [("games.balatro.state.BalatroState", 2)]
    assert report.reconstruct_type_samples[0].exclusive_elapsed_seconds >= 0.0
    assert report.state_card_sample_limit == 100_000
    assert report.state_card_validation_sampled_calls == expected_card_samples
    assert report.state_card_validation_elapsed_seconds > 0.0
    assert report.state_card_shallow_copy_sampled_calls == expected_card_samples
    assert report.state_card_shallow_copy_elapsed_seconds > 0.0
    assert helper_costs["_score_outcomes_scorer_score"].calls == 2
    assert helper_costs["_generate_play_actions"].calls == 1
    assert report.evaluation_cache_hits == 1
    assert report.evaluation_cache_misses == 1
    assert generated_transition_class.project_transition is generated_transition
    assert visible_transition_class.project_transition is visible_transition
    assert BalatroState.copy_for_tactical_projection is tactical_copy
    assert BalatroState.detach_tactical_mutable_aliases is state_detachment
    assert BalatroState._detach_tactical_card_collections is state_card_detachment
    assert BalatroState._detach_tactical_named_collection is state_named_detachment
    assert tactical_performance.balatro_state.deepcopy is state_deepcopy
    assert score_outcomes._held_cards_after_play_selection == hook_held_cards
    assert score_outcomes._hook_forced_discard_branches == hook_forced_branches
    assert score_outcomes._remove_cards == hook_remove_cards
    assert score_outcomes._append_hook_outcomes == hook_outcome_aggregation
    assert score_outcomes.discard_joker_projector.project == hook_discard_projection
    for name, original in discard_projection_helpers.items():
        assert getattr(score_outcomes.discard_joker_projector, name) == original
    assert tactical_performance.copy_module._reconstruct is reconstruct
    assert tactical_performance.copy_module._deepcopy_dispatch[dict] is dict_deepcopy
    assert tactical_performance.copy_module._deepcopy_dispatch[list] is list_deepcopy
    assert (
        tactical_performance.balatro_state._has_exact_scalar_card_state
        is state_card_validation
    )
    assert (
        tactical_performance.balatro_state._copy_exact_scalar_card
        is state_card_shallow_copy
    )
    assert helper_costs["_diverse_discard_beam"].exclusive_elapsed_seconds > 0.0
    assert helper_costs["_discard_priority"].exclusive_elapsed_seconds > 0.0
    assert sum(
        cost.exclusive_elapsed_seconds for cost in report.helper_costs
    ) <= report.candidate_generation_elapsed_seconds
    assert json.loads(report.to_json())["target_decision_index"] == 0
    assert json.loads(report.to_json())["reconstruct_type_samples"] == [
        {
            "exclusive_elapsed_seconds": (
                report.reconstruct_type_samples[0].exclusive_elapsed_seconds
            ),
            "sampled_calls": 2,
            "type_name": "games.balatro.state.BalatroState",
        }
    ]


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
    generated_transition = (
        tactical_performance.LiveGeneratedConsumableScoreOutcomeModel.project_transition
    )
    visible_transition = (
        tactical_performance.LiveVisibleCardScoreOutcomeModel.project_transition
    )
    tactical_copy = BalatroState.copy_for_tactical_projection
    state_deepcopy = tactical_performance.balatro_state.deepcopy
    reconstruct = tactical_performance.copy_module._reconstruct
    dict_deepcopy = tactical_performance.copy_module._deepcopy_dispatch[dict]
    list_deepcopy = tactical_performance.copy_module._deepcopy_dispatch[list]
    state_card_validation = (
        tactical_performance.balatro_state._has_exact_scalar_card_state
    )
    state_card_shallow_copy = (
        tactical_performance.balatro_state._copy_exact_scalar_card
    )
    score_outcomes = engine.planner.evaluator.score_outcomes
    hook_helpers = {
        name: getattr(score_outcomes, name)
        for name in (
            "_held_cards_after_play_selection",
            "_hook_forced_discard_branches",
            "_remove_cards",
            "_append_hook_outcomes",
        )
    }
    hook_discard_projection = score_outcomes.discard_joker_projector.project
    discard_projection_helpers = {
        name: getattr(score_outcomes.discard_joker_projector, name)
        for name in (
            "_copy_state_shell",
            "_clone_joker_graph",
            "_active_jokers",
            "_prepare_discard_context",
            "_apply_active_jokers",
            "_finalize_discard_side_effects",
        )
    }
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

    assert (
        tactical_performance.LiveGeneratedConsumableScoreOutcomeModel.project_transition
        is generated_transition
    )
    assert (
        tactical_performance.LiveVisibleCardScoreOutcomeModel.project_transition
        is visible_transition
    )
    assert BalatroState.copy_for_tactical_projection is tactical_copy
    assert tactical_performance.balatro_state.deepcopy is state_deepcopy
    assert tactical_performance.copy_module._reconstruct is reconstruct
    assert tactical_performance.copy_module._deepcopy_dispatch[dict] is dict_deepcopy
    assert tactical_performance.copy_module._deepcopy_dispatch[list] is list_deepcopy
    assert (
        tactical_performance.balatro_state._has_exact_scalar_card_state
        is state_card_validation
    )
    assert (
        tactical_performance.balatro_state._copy_exact_scalar_card
        is state_card_shallow_copy
    )
    for name, original in hook_helpers.items():
        assert getattr(score_outcomes, name) == original
    assert score_outcomes.discard_joker_projector.project == hook_discard_projection
    for name, original in discard_projection_helpers.items():
        assert getattr(score_outcomes.discard_joker_projector, name) == original


@pytest.mark.parametrize(
    ("trace_function", "expected_prefix_name", "target_index"),
    (
        (
            trace_episode_43_decision_11_candidate_subowners,
            "_EPISODE_43_DECISION_11_EXPECTED_PREFIX",
            11,
        ),
        (
            trace_episode_43_decision_12_candidate_subowners,
            "_EPISODE_43_DECISION_12_EXPECTED_PREFIX",
            12,
        ),
    ),
)
def test_env_ppo_episode_43_candidate_subowner_routes_exact_target(
    monkeypatch,
    trace_function,
    expected_prefix_name,
    target_index,
):
    captured = {}
    marker = object()

    def trace(**kwargs):
        captured.update(kwargs)
        return marker

    monkeypatch.setattr(tactical_performance, "_trace_candidate_subowners", trace)
    clock = lambda: 1.0

    assert trace_function(clock=clock) is marker
    assert captured == {
        "episode_index": 43,
        "target_index": target_index,
        "expected_prefix": getattr(tactical_performance, expected_prefix_name),
        "root_seed": "RED-WHITE-PPO-V1",
        "clock": clock,
    }


def test_env_ppo_episode_43_decision_12_prefix_extends_exact_decision_11():
    decision_11 = tactical_performance._EPISODE_43_DECISION_11_EXPECTED_PREFIX
    decision_12 = tactical_performance._EPISODE_43_DECISION_12_EXPECTED_PREFIX

    assert decision_12[:-1] == decision_11
    assert decision_12[-1] == (
        "9231aae5f2605e76643e38b36b74289533e11813c5f0304e0c8cf6f6d11fe23e",
        "DISCARD_CARDS",
        (1,),
        ((2, 252, 2000, False), (3, 2000, 2000, True)),
    )


@pytest.mark.parametrize("episode_index", [-1, True, 1.0, None])
def test_env_ppo_initial_policy_episode_trace_rejects_invalid_index(
    episode_index,
):
    with pytest.raises(PPOContractError, match="nonnegative episode index"):
        trace_initial_policy_ppo_episode_tactical_costs(episode_index=episode_index)


def test_env_ppo_tactical_episode_report_is_atomically_canonical(
    monkeypatch,
    tmp_path,
    capsys,
):
    report = tactical_performance.PPOTacticalEpisodeCostReport(
        schema=PPO_TACTICAL_EPISODE_COST_SCHEMA,
        root_seed="RED-WHITE-PPO-V1",
        episode_index=43,
        stream_index=3,
        game_seed="EE424B52",
        environment_transitions=7,
        total_elapsed_seconds=12.5,
        tactical_elapsed_seconds=11.0,
        decisions=(),
    )
    output = tmp_path / "episode-43.json"
    digest = write_ppo_tactical_episode_report(output, report)

    content = output.read_bytes()
    assert content == report.to_json().encode("utf-8")
    assert digest == sha256(content).hexdigest()
    assert not (tmp_path / ".episode-43.json.tmp").exists()

    monkeypatch.setattr(
        tactical_performance,
        "trace_initial_policy_ppo_episode_tactical_costs",
        lambda **kwargs: report,
    )
    assert tactical_performance.main(
        [
            "--root-seed",
            "RED-WHITE-PPO-V1",
            "--episode-index",
            "43",
            "--output-path",
            str(output),
        ]
    ) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "schema": PPO_TACTICAL_EPISODE_COST_SCHEMA,
        "output_path": str(output),
        "report_sha256": digest,
        "episode_index": 43,
        "decision_count": 0,
        "total_elapsed_seconds": 12.5,
    }


def test_env_ppo_tactical_episode_report_rejects_invalid_publication(tmp_path):
    with pytest.raises(TypeError, match="PPOTacticalEpisodeCostReport"):
        write_ppo_tactical_episode_report(tmp_path / "report.json", object())
    report = tactical_performance.PPOTacticalEpisodeCostReport(
        schema=PPO_TACTICAL_EPISODE_COST_SCHEMA,
        root_seed="RED-WHITE-PPO-V1",
        episode_index=43,
        stream_index=3,
        game_seed="EE424B52",
        environment_transitions=0,
        total_elapsed_seconds=0.0,
        tactical_elapsed_seconds=0.0,
        decisions=(),
    )
    with pytest.raises(PPOContractError, match="directory does not exist"):
        write_ppo_tactical_episode_report(tmp_path / "missing" / "report.json", report)


def test_env_ppo_tactical_cli_rejects_output_without_episode_index(tmp_path):
    with pytest.raises(SystemExit):
        tactical_performance.main(["--output-path", str(tmp_path / "report.json")])


@pytest.mark.parametrize(
    ("trace_name", "flag", "target_index", "selected_index"),
    (
        (
            "trace_episode_43_decision_11_candidate_subowners",
            "--episode-43-decision-11-candidate-subowners",
            11,
            5,
        ),
        (
            "trace_episode_43_decision_12_candidate_subowners",
            "--episode-43-decision-12-candidate-subowners",
            12,
            1,
        ),
    ),
)
def test_env_ppo_candidate_subowner_report_is_atomically_canonical(
    monkeypatch,
    tmp_path,
    capsys,
    trace_name,
    flag,
    target_index,
    selected_index,
):
    report = tactical_performance.PPOTacticalCandidateSubownerReport(
        schema=PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA,
        root_seed="RED-WHITE-PPO-V1",
        episode_index=43,
        stream_index=3,
        game_seed="EE424B52",
        verified_prefix_decisions=target_index + 1,
        target_decision_index=target_index,
        public_input_sha256="a" * 64,
        action="DISCARD_CARDS",
        selected_hand_indices=(selected_index,),
        search_attempts=((2, 252, 2000, False), (3, 2000, 2000, True)),
        evaluation_cache_hits=0,
        evaluation_cache_misses=0,
        generated_consumable_transition_calls=0,
        generated_consumable_inert_calls=0,
        generated_consumable_eight_ball_capable_calls=0,
        generated_consumable_main_generator_capable_calls=0,
        generated_consumable_sixth_sense_capable_calls=0,
        hook_forced_branch_sets=0,
        hook_forced_branches=0,
        hook_discard_projection_calls=0,
        hook_outcome_aggregation_calls=0,
        hook_aggregated_outcomes=0,
        discard_active_joker_selection_calls=0,
        discard_active_jokers_selected=0,
        discard_joker_application_calls=0,
        discard_jokers_applied=0,
        total_elapsed_seconds=12.5,
        candidate_generation_elapsed_seconds=11.0,
        helper_costs=(),
        reconstruct_type_sample_limit=100_000,
        reconstruct_type_sampled_calls=0,
        reconstruct_type_samples=(),
        state_card_sample_limit=100_000,
        state_card_validation_sampled_calls=0,
        state_card_validation_elapsed_seconds=0.0,
        state_card_shallow_copy_sampled_calls=0,
        state_card_shallow_copy_elapsed_seconds=0.0,
        residual_candidate_elapsed_seconds=11.0,
    )
    output = tmp_path / f"episode-43-decision-{target_index}.json"
    digest = write_ppo_tactical_candidate_subowner_report(output, report)
    content = output.read_bytes()
    assert content == report.to_json().encode("utf-8")
    assert digest == sha256(content).hexdigest()

    monkeypatch.setattr(
        tactical_performance,
        trace_name,
        lambda **kwargs: report,
    )
    assert tactical_performance.main(
        [
            flag,
            "--output-path",
            str(output),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema": PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA,
        "output_path": str(output),
        "report_sha256": digest,
        "episode_index": 43,
        "target_decision_index": target_index,
        "total_elapsed_seconds": 12.5,
    }


def test_env_ppo_candidate_subowner_report_rejects_wrong_type(tmp_path):
    with pytest.raises(TypeError, match="PPOTacticalCandidateSubownerReport"):
        write_ppo_tactical_candidate_subowner_report(
            tmp_path / "report.json",
            object(),
        )
