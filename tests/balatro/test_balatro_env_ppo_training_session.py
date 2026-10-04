from types import SimpleNamespace

import pytest

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_VERSION,
    ActionMask,
    action_index,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_VERSION,
    EncodedPublicObservation,
)
from games.balatro.env.ppo_contract import (
    PPO_ROLLOUT_EPISODE_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutBoundary,
    PPORolloutDecision,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_training_session import (
    PPO_TRAINING_SESSION_VERSION,
    PPOCollectedEpisode,
    PPOEpisodeRequest,
    PPOTrainingSession,
)
from games.balatro.env.seeded_evaluation import EVALUATION_MODE
from games.balatro.env.state import RunStatus, TurnOwner


class _InertBackend:
    def __init__(self, stream_index):
        self.stream_index = stream_index

    def reset(self, seed):
        raise AssertionError("the injected bounded collector must own collection")

    def step(self, action):
        raise AssertionError("the injected bounded collector must own collection")

    def legal_actions(self):
        return ()

    def serialize(self):
        return {}

    def restore(self, payload):
        raise AssertionError("the injected bounded collector must own collection")


def _factory(streams=None):
    def create(stream_index):
        if streams is not None:
            streams.append(stream_index)
        return BalatroHeadlessEnvironment(_InertBackend(stream_index))

    return create


def _episode(run, episode_index, *, length=1):
    action = EnvAction.from_alias("SELECT_BLIND")
    selected = action_index(action)
    mask_values = [False] * PPO_TRAINING_CONTRACT.action_size
    mask_values[selected] = True
    mask = ActionMask(PUBLIC_ACTION_VERSION, tuple(mask_values))
    probabilities = tuple(
        1.0 if index == selected else 0.0
        for index in range(PPO_TRAINING_CONTRACT.action_size)
    )
    observation = EncodedPublicObservation(
        PUBLIC_OBSERVATION_VERSION,
        (0.0,) * PPO_TRAINING_CONTRACT.observation_size,
    )
    start = PPORolloutBoundary(
        observation,
        "RED",
        "WHITE",
        EVALUATION_MODE,
        "BLIND_SELECT",
        RunStatus.RUNNING,
        TurnOwner.AGENT,
        1,
        4,
        0.0,
        300.0,
    )
    final = PPORolloutBoundary(
        None,
        "RED",
        "WHITE",
        EVALUATION_MODE,
        "GAME_OVER",
        RunStatus.LOSS,
        TurnOwner.TERMINAL,
        1,
        4,
        0.0,
        300.0,
    )
    decisions = tuple(
        PPORolloutDecision(
            run.sha256,
            episode_index,
            decision_index,
            observation,
            mask,
            probabilities,
            0.0,
            selected,
            action,
        )
        for decision_index in range(length)
    )
    return PPORolloutEpisode(
        PPO_ROLLOUT_EPISODE_SCHEMA,
        run,
        episode_index,
        run.game_seed(episode_index),
        (start,) * length + (final,),
        decisions,
        (0.0,) * (length - 1) + (-1.0,),
    )


class _FakeAssembler:
    def __init__(self, start=0):
        count = PPO_TRAINING_CONTRACT.parallel_environments
        self.indices = [start + stream for stream in range(count)]
        self.queued = [0] * count

    @property
    def next_episode_indices(self):
        return tuple(self.indices)

    @property
    def ready(self):
        required = PPO_TRAINING_CONTRACT.rollout_steps_per_environment
        return all(count >= required for count in self.queued)


class _FakeLearner:
    def __init__(self, run, *, completed=0, next_episode_index=0):
        self.training_run = run
        self.assembler = _FakeAssembler(next_episode_index)
        self.model = SimpleNamespace(
            infer=lambda observation, mask: None,
            parameter_sha256="0" * 64,
        )
        self.completed_batch_count = completed
        self.total_consumed_environment_transitions = (
            completed * PPO_TRAINING_CONTRACT.rollout_batch_size
        )
        self.updates = 0

    def add_episode(self, episode):
        stream = episode.episode_index % PPO_TRAINING_CONTRACT.parallel_environments
        assert episode.episode_index == self.assembler.indices[stream]
        self.assembler.indices[stream] += PPO_TRAINING_CONTRACT.parallel_environments
        self.assembler.queued[stream] += episode.action_count
        self.total_consumed_environment_transitions += episode.action_count

    def update_ready_batch(self):
        required = PPO_TRAINING_CONTRACT.rollout_steps_per_environment
        assert self.assembler.ready
        self.assembler.queued = [count - required for count in self.assembler.queued]
        self.completed_batch_count += 1
        self.updates += 1
        self.model.parameter_sha256 = f"{self.updates:064x}"
        return ()

    def serialize(self):
        return {"fake": True}


def test_env_ppo_training_session_stops_at_exact_frozen_schedule():
    run = PPOTrainingRun.from_seed("SESSION-STOP")
    target = (
        PPO_TRAINING_CONTRACT.total_environment_steps
        // PPO_TRAINING_CONTRACT.rollout_batch_size
    )
    learner = _FakeLearner(run, completed=target - 1)
    collected = []

    def collector(environment, training_run, *, episode_index, policy):
        collected.append((environment._backend.stream_index, episode_index))
        return _episode(training_run, episode_index, length=256)

    session = PPOTrainingSession(
        run,
        _factory(),
        learner=learner,
        episode_collector=collector,
    )
    result = session.advance(maximum_episodes=100)

    assert PPO_TRAINING_SESSION_VERSION == "balatro-red-white-ppo-training-session-v1"
    assert collected == [(index, index) for index in range(8)]
    assert result.episodes_collected == 8
    assert result.batches_completed == 1
    assert result.completed_batch_count == 1024
    assert result.optimizer_consumed_transitions == 2_097_152
    assert result.collected_environment_transitions == 2_097_152
    assert result.complete is True
    assert learner.updates == 1
    assert session.advance(maximum_episodes=1).episodes_collected == 0


def test_env_ppo_training_session_checkpoint_resume_does_not_recollect_episode():
    run = PPOTrainingRun.from_seed("SESSION-RESUME")
    first_indices = []

    def first_collector(environment, training_run, *, episode_index, policy):
        first_indices.append(episode_index)
        return _episode(training_run, episode_index)

    session = PPOTrainingSession(run, _factory(), episode_collector=first_collector)
    first = session.advance(maximum_episodes=3)
    checkpoint = session.serialize()
    resumed_indices = []

    def resumed_collector(environment, training_run, *, episode_index, policy):
        resumed_indices.append(episode_index)
        return _episode(training_run, episode_index)

    restored = PPOTrainingSession.restore(
        run,
        _factory(),
        checkpoint,
        episode_collector=resumed_collector,
    )
    second = restored.advance(maximum_episodes=2)

    assert first_indices == [0, 1, 2]
    assert first.last_episode_index == 2
    assert resumed_indices == [3, 4]
    assert second.last_episode_index == 4
    assert restored.learner.assembler.next_episode_indices == (
        8,
        9,
        10,
        11,
        12,
        5,
        6,
        7,
    )


def test_env_ppo_training_session_uses_exact_stream_order_and_bound():
    run = PPOTrainingRun.from_seed("SESSION-ORDER")
    learner = _FakeLearner(run, next_episode_index=16)
    streams = []
    indices = []

    def collector(environment, training_run, *, episode_index, policy):
        indices.append(episode_index)
        assert environment._backend.stream_index == episode_index % 8
        return _episode(training_run, episode_index)

    session = PPOTrainingSession(
        run,
        _factory(streams),
        learner=learner,
        episode_collector=collector,
    )
    result = session.advance(maximum_episodes=10)

    assert streams == list(range(8))
    assert indices == list(range(16, 26))
    assert result.episodes_collected == 10
    assert result.batches_completed == 0
    assert result.last_episode_index == 25


def test_env_ppo_training_session_parallel_wave_commits_exact_global_order():
    run = PPOTrainingRun.from_seed("SESSION-PARALLEL-ORDER")
    learner = _FakeLearner(run)
    waves = []
    committed = []

    def collect_wave(requests, training_run, model):
        waves.append(requests)
        return tuple(
            PPOCollectedEpisode(
                request,
                model.parameter_sha256,
                _episode(training_run, request.episode_index),
            )
            for request in requests
        )

    session = PPOTrainingSession(run, _factory(), learner=learner)
    result = session.advance_parallel(
        maximum_episodes=8,
        maximum_batches=1,
        wave_collector=collect_wave,
        on_episode_committed=lambda _session, episode: committed.append(
            episode.episode_index
        ),
    )

    assert waves == [tuple(PPOEpisodeRequest(index, index) for index in range(8))]
    assert committed == list(range(8))
    assert result.episodes_collected == 8
    assert result.batches_completed == 0
    assert result.last_episode_index == 7
    assert learner.assembler.next_episode_indices == tuple(range(8, 16))


def test_env_ppo_training_session_parallel_wave_recollects_suffix_after_update():
    run = PPOTrainingRun.from_seed("SESSION-PARALLEL-BOUNDARY")
    learner = _FakeLearner(run)
    learner.assembler.queued = [255, 255, 256, 256, 256, 256, 256, 256]
    learner.total_consumed_environment_transitions = sum(learner.assembler.queued)
    waves = []
    committed = []

    def collect_wave(requests, training_run, model):
        waves.append((requests, model.parameter_sha256))
        return tuple(
            PPOCollectedEpisode(
                request,
                model.parameter_sha256,
                _episode(training_run, request.episode_index),
            )
            for request in requests
        )

    session = PPOTrainingSession(run, _factory(), learner=learner)
    result = session.advance_parallel(
        maximum_episodes=4,
        maximum_batches=2,
        wave_collector=collect_wave,
        on_episode_committed=lambda _session, episode: committed.append(
            episode.episode_index
        ),
    )

    assert waves == [
        (tuple(PPOEpisodeRequest(index, index) for index in range(4)), "0" * 64),
        (tuple(PPOEpisodeRequest(index, index) for index in (2, 3)), f"{1:064x}"),
    ]
    assert committed == [0, 1, 2, 3]
    assert result.episodes_collected == 4
    assert result.batches_completed == 1
    assert learner.updates == 1
    assert learner.assembler.next_episode_indices == (8, 9, 10, 11, 4, 5, 6, 7)


def test_env_ppo_training_session_parallel_wave_rejects_drift_before_commit():
    run = PPOTrainingRun.from_seed("SESSION-PARALLEL-REJECT")
    learner = _FakeLearner(run)
    session = PPOTrainingSession(run, _factory(), learner=learner)

    def misordered(requests, training_run, model):
        results = [
            PPOCollectedEpisode(
                request,
                model.parameter_sha256,
                _episode(training_run, request.episode_index),
            )
            for request in requests
        ]
        results[0], results[1] = results[1], results[0]
        return tuple(results)

    with pytest.raises(PPOContractError, match="order drifted"):
        session.advance_parallel(
            maximum_episodes=2, maximum_batches=1, wave_collector=misordered
        )

    assert learner.total_consumed_environment_transitions == 0
    assert learner.assembler.next_episode_indices == tuple(range(8))


@pytest.mark.parametrize(
    ("collector_kind", "message"),
    (
        ("partial", "partial wave"),
        ("policy", "policy version drifted"),
        ("worker", "worker failed"),
    ),
)
def test_env_ppo_training_session_parallel_wave_fails_atomically(
    collector_kind, message
):
    run = PPOTrainingRun.from_seed(f"SESSION-PARALLEL-{collector_kind}")
    learner = _FakeLearner(run)
    session = PPOTrainingSession(run, _factory(), learner=learner)

    def collect_wave(requests, training_run, model):
        if collector_kind == "worker":
            raise RuntimeError("worker failed")
        results = tuple(
            PPOCollectedEpisode(
                request,
                ("f" * 64 if collector_kind == "policy" else model.parameter_sha256),
                _episode(training_run, request.episode_index),
            )
            for request in requests
        )
        return results[:1] if collector_kind == "partial" else results

    with pytest.raises((PPOContractError, RuntimeError), match=message):
        session.advance_parallel(
            maximum_episodes=2, maximum_batches=1, wave_collector=collect_wave
        )

    assert learner.total_consumed_environment_transitions == 0
    assert learner.assembler.next_episode_indices == tuple(range(8))


def test_env_ppo_training_session_parallel_stops_at_exact_new_batch_bound():
    run = PPOTrainingRun.from_seed("SESSION-PARALLEL-BATCH-STOP")
    learner = _FakeLearner(run)
    learner.assembler.queued = [255, 255, 256, 256, 256, 256, 256, 256]
    learner.total_consumed_environment_transitions = sum(learner.assembler.queued)
    waves = []
    committed = []

    def collect_wave(requests, training_run, model):
        waves.append(requests)
        return tuple(
            PPOCollectedEpisode(
                request,
                model.parameter_sha256,
                _episode(training_run, request.episode_index),
            )
            for request in requests
        )

    session = PPOTrainingSession(run, _factory(), learner=learner)
    result = session.advance_parallel(
        maximum_episodes=4,
        maximum_batches=1,
        wave_collector=collect_wave,
        on_episode_committed=lambda _session, episode: committed.append(
            episode.episode_index
        ),
    )

    assert waves == [tuple(PPOEpisodeRequest(index, index) for index in range(4))]
    assert committed == [0, 1]
    assert result.episodes_collected == 2
    assert result.batches_completed == 1
    assert learner.assembler.next_episode_indices == (8, 9, 2, 3, 4, 5, 6, 7)


@pytest.mark.parametrize("maximum_batches", (0, True, 1025))
def test_env_ppo_training_session_parallel_rejects_invalid_batch_bound(
    maximum_batches,
):
    run = PPOTrainingRun.from_seed("SESSION-PARALLEL-BATCH-BOUND")
    session = PPOTrainingSession(run, _factory(), learner=_FakeLearner(run))

    with pytest.raises(PPOContractError, match="maximum batches"):
        session.advance_parallel(
            maximum_episodes=1,
            maximum_batches=maximum_batches,
            wave_collector=lambda *_args: (),
        )


def test_env_ppo_training_session_rejects_incomplete_or_drifted_collection():
    run = PPOTrainingRun.from_seed("SESSION-REJECT")
    learner = _FakeLearner(run)
    session = PPOTrainingSession(
        run,
        _factory(),
        learner=learner,
        episode_collector=lambda *args, **kwargs: object(),
    )
    with pytest.raises(PPOContractError, match="incomplete episode"):
        session.advance(maximum_episodes=1)
    with pytest.raises(PPOContractError, match="positive exact integer"):
        session.advance(maximum_episodes=0)

    drifted = PPOTrainingSession(
        run,
        _factory(),
        learner=_FakeLearner(run),
        episode_collector=lambda environment, training_run, **kwargs: _episode(
            training_run, 1
        ),
    )
    with pytest.raises(PPOContractError, match="episode index drifted"):
        drifted.advance(maximum_episodes=1)

    bad_counter = _FakeLearner(run)
    bad_counter.total_consumed_environment_transitions = -1
    with pytest.raises(PPOContractError, match="transition count is invalid"):
        PPOTrainingSession(run, _factory(), learner=bad_counter)


def test_env_ppo_training_session_restore_rejects_schema_and_run_drift():
    run = PPOTrainingRun.from_seed("SESSION-SCHEMA")
    checkpoint = PPOTrainingSession(run, _factory()).serialize()

    missing = dict(checkpoint)
    del missing["learner"]
    with pytest.raises(PPOContractError, match="fields are incomplete"):
        PPOTrainingSession.restore(run, _factory(), missing)

    wrong_version = dict(checkpoint)
    wrong_version["version"] = "old"
    with pytest.raises(PPOContractError, match="version mismatch"):
        PPOTrainingSession.restore(run, _factory(), wrong_version)

    with pytest.raises(PPOContractError, match="run provenance"):
        PPOTrainingSession.restore(
            PPOTrainingRun.from_seed("OTHER"), _factory(), checkpoint
        )
