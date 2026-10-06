from hashlib import sha256

import pytest

from games.balatro.env.ppo_campaign import (
    _canonical_bytes,
    _checkpoint_payload,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_campaign_wave_timing import (
    PPO_CAMPAIGN_WAVE_TIMING_SCHEMA,
    measure_checkpoint_wave_timing,
    write_campaign_wave_timing_report,
)
from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.env.ppo_initial_batch_timing import TimedPPOCollectedEpisode
from games.balatro.env.ppo_training_session import (
    PPOCollectedEpisode,
    PPOTrainingSession,
)
from tests.balatro.test_balatro_env_ppo_batch import _episode


def _checkpoint(tmp_path, seed="WAVE-TIMING"):
    run = PPOTrainingRun.from_seed(seed)
    session = PPOTrainingSession(run, make_ppo_training_environment)
    path = tmp_path / "checkpoint.json"
    content = _canonical_bytes(_checkpoint_payload(run, session))
    path.write_bytes(content)
    return run, path, content


def test_env_ppo_checkpoint_wave_timing_is_exact_read_only_and_provenanced(tmp_path):
    run, path, checkpoint_bytes = _checkpoint(tmp_path)
    before = path.read_bytes()
    observed = []
    episodes = tuple(_episode(run, index, length=1) for index in range(8))

    def collect_wave(requests, training_run, model):
        observed.extend(requests)
        assert training_run == run
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(request, model.parameter_sha256, episodes[index]),
                index + 0.5,
            )
            for index, request in enumerate(requests)
        )

    samples = iter((10.0, 14.0))
    report = measure_checkpoint_wave_timing(
        "WAVE-TIMING",
        path,
        maximum_workers=8,
        clock=lambda: next(samples),
        episode_wave_collector=collect_wave,
    )

    assert report.schema == PPO_CAMPAIGN_WAVE_TIMING_SCHEMA
    assert report.checkpoint_sha256 == sha256(checkpoint_bytes).hexdigest()
    assert report.training_run_sha256 == run.sha256
    assert report.elapsed_seconds == 4.0
    assert report.requested_episode_indices == tuple(range(8))
    assert report.requested_stream_indices == tuple(range(8))
    assert [(item.stream_index, item.episode_index) for item in report.episodes] == [
        (index, index) for index in range(8)
    ]
    assert [item.elapsed_seconds for item in report.episodes] == [
        index + 0.5 for index in range(8)
    ]
    assert [item.episode_sha256 for item in report.episodes] == [
        sha256(episode.to_json().encode("utf-8")).hexdigest()
        for episode in episodes
    ]
    assert all(item.committed is False for item in report.episodes)
    assert [(request.stream_index, request.episode_index) for request in observed] == [
        (index, index) for index in range(8)
    ]
    assert path.read_bytes() == before


def test_env_ppo_checkpoint_wave_timing_report_is_atomically_canonical(tmp_path):
    run, checkpoint, _ = _checkpoint(tmp_path, seed="WAVE-WRITE")

    def collect_wave(requests, training_run, model):
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(
                    request,
                    model.parameter_sha256,
                    _episode(run, request.episode_index, length=1),
                ),
                1.0,
            )
            for request in requests
        )

    samples = iter((0.0, 1.0))
    report = measure_checkpoint_wave_timing(
        "WAVE-WRITE",
        checkpoint,
        maximum_workers=8,
        clock=lambda: next(samples),
        episode_wave_collector=collect_wave,
    )
    output = tmp_path / "wave.json"
    digest = write_campaign_wave_timing_report(output, report)

    assert output.read_bytes() == report.to_json().encode("utf-8")
    assert digest == sha256(output.read_bytes()).hexdigest()
    assert not (tmp_path / ".wave.json.tmp").exists()


def test_env_ppo_checkpoint_wave_timing_fails_closed_on_partial_results(tmp_path):
    run, checkpoint, _ = _checkpoint(tmp_path, seed="WAVE-PARTIAL")

    def partial(requests, training_run, model):
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(
                    request,
                    model.parameter_sha256,
                    _episode(run, request.episode_index, length=1),
                ),
                1.0,
            )
            for request in requests[:-1]
        )

    with pytest.raises(PPOContractError, match="partial wave"):
        measure_checkpoint_wave_timing(
            "WAVE-PARTIAL",
            checkpoint,
            maximum_workers=8,
            clock=iter((0.0, 1.0)).__next__,
            episode_wave_collector=partial,
        )


def test_env_ppo_checkpoint_wave_timing_fails_closed_on_clock_and_policy_drift(
    tmp_path,
):
    run, checkpoint, _ = _checkpoint(tmp_path, seed="WAVE-DRIFT")

    def valid(requests, training_run, model):
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(
                    request,
                    model.parameter_sha256,
                    _episode(run, request.episode_index, length=1),
                ),
                1.0,
            )
            for request in requests
        )

    with pytest.raises(PPOContractError, match="clock moved backwards"):
        measure_checkpoint_wave_timing(
            "WAVE-DRIFT",
            checkpoint,
            maximum_workers=8,
            clock=iter((2.0, 1.0)).__next__,
            episode_wave_collector=valid,
        )

    def mutate_policy(requests, training_run, model):
        policy_sha256 = model.parameter_sha256
        model.parameters["policy_b"][0] += 1.0
        return tuple(
            TimedPPOCollectedEpisode(
                PPOCollectedEpisode(
                    request,
                    policy_sha256,
                    _episode(run, request.episode_index, length=1),
                ),
                1.0,
            )
            for request in requests
        )

    with pytest.raises(PPOContractError, match="policy changed"):
        measure_checkpoint_wave_timing(
            "WAVE-DRIFT",
            checkpoint,
            maximum_workers=8,
            clock=iter((0.0, 1.0)).__next__,
            episode_wave_collector=mutate_policy,
        )


def test_env_ppo_checkpoint_wave_timing_rejects_noncanonical_checkpoint(tmp_path):
    _, checkpoint, content = _checkpoint(tmp_path, seed="WAVE-NONCANONICAL")
    checkpoint.write_bytes(content + b"\n")

    with pytest.raises(PPOContractError, match="not canonical"):
        measure_checkpoint_wave_timing(
            "WAVE-NONCANONICAL",
            checkpoint,
            maximum_workers=8,
            episode_wave_collector=lambda *_: (),
        )
