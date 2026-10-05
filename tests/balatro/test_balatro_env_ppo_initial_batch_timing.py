from hashlib import sha256

import pytest

from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.env.ppo_initial_batch_timing import (
    PPO_INITIAL_BATCH_TIMING_SCHEMA,
    TimedPPOCollectedEpisode,
    _collect_timed_production_episode,
    measure_initial_batch_timing,
    write_initial_batch_timing_report,
)
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_training_session import PPOCollectedEpisode
from tests.balatro.test_balatro_env_ppo_batch import _episode


def test_env_ppo_timed_worker_uses_injected_clock_without_changing_episode():
    run = PPOTrainingRun.from_seed("TIMED-WORKER")
    model = PPOActorCritic(run)
    environment = object()
    from games.balatro.env.ppo_training_session import PPOEpisodeRequest

    exact_request = PPOEpisodeRequest(0, 0)
    samples = iter((10.0, 12.5))
    expected = _episode(run, 0, length=1)

    result = _collect_timed_production_episode(
        exact_request,
        run,
        model,
        clock=lambda: next(samples),
        environment_factory=lambda stream: environment,
        episode_collector=lambda current_environment, training_run, **kwargs: expected,
    )

    assert result.elapsed_seconds == 2.5
    assert result.collected.request == exact_request
    assert result.collected.episode is expected
    assert result.collected.policy_parameter_sha256 == model.parameter_sha256


def test_env_ppo_initial_batch_timing_preserves_order_hashes_and_injected_time():
    run = PPOTrainingRun.from_seed("TIMING")
    model = PPOActorCritic(run)
    episodes = tuple(_episode(run, index, length=257) for index in range(8))

    def collect_wave(requests, training_run, current_model):
        assert training_run == run
        assert current_model.parameter_sha256 == model.parameter_sha256
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(
                    request,
                    current_model.parameter_sha256,
                    episodes[request.episode_index],
                ),
                request.episode_index + 0.25,
            )
            for request in requests
        )

    samples = iter((100.0, 101.0, 104.0, 105.0))
    report = measure_initial_batch_timing(
        "TIMING",
        maximum_episodes=8,
        maximum_workers=8,
        clock=lambda: next(samples),
        episode_wave_collector=collect_wave,
    )

    assert report.schema == PPO_INITIAL_BATCH_TIMING_SCHEMA
    assert report.elapsed_seconds == 5.0
    assert report.committed_episode_count == 8
    assert report.collected_episode_count == 8
    assert report.collected_environment_transitions == 2056
    assert report.queued_transition_counts == (257,) * 8
    assert report.carryover_counts == (1,) * 8
    assert report.next_episode_indices == tuple(range(8, 16))
    assert len(report.waves) == 1
    wave = report.waves[0]
    assert wave.elapsed_seconds == 3.0
    assert wave.requested_episode_indices == tuple(range(8))
    assert wave.committed_episode_indices == tuple(range(8))
    assert [item.elapsed_seconds for item in wave.episodes] == [
        index + 0.25 for index in range(8)
    ]
    assert [item.episode_sha256 for item in wave.episodes] == [
        sha256(episode.to_json().encode("utf-8")).hexdigest()
        for episode in episodes
    ]
    assert report.to_json() == report.to_json()

def test_env_ppo_initial_batch_timing_report_is_atomically_canonical(tmp_path):
    run = PPOTrainingRun.from_seed("WRITE")

    def collect_wave(requests, training_run, model):
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(
                    request,
                    model.parameter_sha256,
                    _episode(run, request.episode_index, length=257),
                ),
                1.0,
            )
            for request in requests
        )

    samples = iter((0.0, 0.0, 1.0, 1.0))
    report = measure_initial_batch_timing(
        "WRITE",
        maximum_episodes=8,
        maximum_workers=8,
        clock=lambda: next(samples),
        episode_wave_collector=collect_wave,
    )
    output = tmp_path / "timing.json"
    digest = write_initial_batch_timing_report(output, report)

    content = output.read_bytes()
    assert content == report.to_json().encode("utf-8")
    assert digest == sha256(content).hexdigest()
    assert not (tmp_path / ".timing.json.tmp").exists()


def test_env_ppo_initial_batch_timing_fails_closed_on_bounds_and_clock_drift():
    with pytest.raises(PPOContractError, match="maximum episodes"):
        measure_initial_batch_timing("BOUND", maximum_episodes=0, maximum_workers=1)
    with pytest.raises(PPOContractError, match="maximum workers"):
        measure_initial_batch_timing("BOUND", maximum_episodes=1, maximum_workers=9)

    run = PPOTrainingRun.from_seed("CLOCK")
    episode = _episode(run, 0, length=1)

    def collector(requests, training_run, model):
        return (
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(requests[0], model.parameter_sha256, episode),
                1.0,
            ),
        )

    samples = iter((5.0, 4.0, 3.0))
    with pytest.raises(PPOContractError, match="clock moved backwards"):
        measure_initial_batch_timing(
            "CLOCK",
            maximum_episodes=1,
            maximum_workers=1,
            clock=lambda: next(samples),
            episode_wave_collector=collector,
        )
