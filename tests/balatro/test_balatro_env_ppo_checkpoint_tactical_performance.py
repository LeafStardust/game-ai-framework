import json
from hashlib import sha256

import pytest

import games.balatro.env.ppo_checkpoint_tactical_performance as checkpoint_tactical
from games.balatro.env.ppo_campaign import (
    _canonical_bytes,
    _checkpoint_payload,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_checkpoint_tactical_performance import (
    PPO_CHECKPOINT_TACTICAL_EPISODE_SCHEMA,
    trace_checkpoint_ppo_episode_tactical_costs,
    write_checkpoint_tactical_episode_report,
)
from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.env.ppo_tactical_performance import (
    PPOTacticalEpisodeDecisionCost,
)
from games.balatro.env.ppo_training_session import PPOTrainingSession
from tests.balatro.test_balatro_env_ppo_batch import _episode


def _checkpoint(tmp_path, seed="CHECKPOINT-TACTICAL"):
    run = PPOTrainingRun.from_seed(seed)
    session = PPOTrainingSession(run, make_ppo_training_environment)
    path = tmp_path / "checkpoint.json"
    content = _canonical_bytes(_checkpoint_payload(run, session))
    path.write_bytes(content)
    return run, path, content


def _decision_cost(total=1.0):
    return PPOTacticalEpisodeDecisionCost(
        public_input_sha256="a" * 64,
        action="PLAY_CARDS",
        selected_hand_indices=(0,),
        search_attempts=((2, 18, 2000, False),),
        total_elapsed_seconds=total,
        candidate_generation_elapsed_seconds=total * 0.25,
        search_evaluation_elapsed_seconds=total * 0.5,
        policy_arbitration_elapsed_seconds=total * 0.125,
        other_elapsed_seconds=total * 0.125,
    )


def test_checkpoint_tactical_trace_is_exact_read_only_and_provenanced(
    monkeypatch, tmp_path
):
    run, path, checkpoint_bytes = _checkpoint(tmp_path)
    before = path.read_bytes()
    observed = []
    record = _decision_cost(2.0)

    def instrument(engine, clock, records):
        records.append(record)

    def collect(environment, training_run, *, episode_index, policy):
        observed.append((environment, training_run, episode_index, policy))
        return _episode(run, episode_index, length=3)

    monkeypatch.setattr(checkpoint_tactical, "_instrument_episode_engine", instrument)
    ticks = iter((10.0, 15.0))
    report = trace_checkpoint_ppo_episode_tactical_costs(
        "CHECKPOINT-TACTICAL",
        path,
        episode_index=5,
        clock=lambda: next(ticks),
        episode_collector=collect,
    )

    episode = _episode(run, 5, length=3)
    assert report.schema == PPO_CHECKPOINT_TACTICAL_EPISODE_SCHEMA
    assert report.checkpoint_sha256 == sha256(checkpoint_bytes).hexdigest()
    assert report.training_run_sha256 == run.sha256
    assert report.policy_parameter_sha256
    assert report.session_sha256_before == report.session_sha256_after
    assert report.episode_index == 5
    assert report.stream_index == 5
    assert report.game_seed == run.game_seed(5)
    assert report.episode_sha256 == sha256(episode.to_json().encode()).hexdigest()
    assert report.terminal_status == "LOSS"
    assert report.environment_transitions == 3
    assert report.total_elapsed_seconds == 5.0
    assert report.tactical_elapsed_seconds == 2.0
    assert report.committed is False
    assert report.decisions == (record,)
    assert observed[0][1:3] == (run, 5)
    assert callable(observed[0][3])
    assert path.read_bytes() == before


def test_checkpoint_tactical_trace_rejects_nonpending_episode(tmp_path):
    _, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-SELECTION")

    with pytest.raises(PPOContractError, match="not the pending stream index"):
        trace_checkpoint_ppo_episode_tactical_costs(
            "CHECKPOINT-SELECTION",
            path,
            episode_index=13,
            episode_collector=lambda *_args, **_kwargs: None,
        )


def test_checkpoint_tactical_trace_rejects_clock_and_timing_drift(
    monkeypatch, tmp_path
):
    run, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-DRIFT")
    collector = lambda *_args, **_kwargs: _episode(run, 0, length=1)

    monkeypatch.setattr(
        checkpoint_tactical, "_instrument_episode_engine", lambda *_args: None
    )
    with pytest.raises(PPOContractError, match="clock moved backwards"):
        trace_checkpoint_ppo_episode_tactical_costs(
            "CHECKPOINT-DRIFT",
            path,
            episode_index=0,
            clock=iter((2.0, 1.0)).__next__,
            episode_collector=collector,
        )

    def unbalanced(engine, clock, records):
        records.append(
            PPOTacticalEpisodeDecisionCost(
                public_input_sha256="b" * 64,
                action="PLAY_CARDS",
                selected_hand_indices=(),
                search_attempts=(),
                total_elapsed_seconds=2.0,
                candidate_generation_elapsed_seconds=0.0,
                search_evaluation_elapsed_seconds=0.0,
                policy_arbitration_elapsed_seconds=0.0,
                other_elapsed_seconds=1.0,
            )
        )

    monkeypatch.setattr(checkpoint_tactical, "_instrument_episode_engine", unbalanced)
    with pytest.raises(PPOContractError, match="did not balance"):
        trace_checkpoint_ppo_episode_tactical_costs(
            "CHECKPOINT-DRIFT",
            path,
            episode_index=0,
            clock=iter((0.0, 3.0)).__next__,
            episode_collector=collector,
        )


def test_checkpoint_tactical_trace_rejects_policy_mutation(monkeypatch, tmp_path):
    run, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-MUTATION")
    monkeypatch.setattr(
        checkpoint_tactical, "_instrument_episode_engine", lambda *_args: None
    )

    def mutate(environment, training_run, *, episode_index, policy):
        session_model = policy.__self__
        session_model.parameters["policy_b"][0] += 1.0
        return _episode(run, episode_index, length=1)

    with pytest.raises(PPOContractError, match="policy changed"):
        trace_checkpoint_ppo_episode_tactical_costs(
            "CHECKPOINT-MUTATION",
            path,
            episode_index=0,
            clock=iter((0.0, 1.0)).__next__,
            episode_collector=mutate,
        )


def test_checkpoint_tactical_trace_rejects_session_mutation(monkeypatch, tmp_path):
    run, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-SESSION-MUTATION")
    original_restore = checkpoint_tactical._restore_session
    restored = {}

    def capture_restore(training_run, payload, environment_factory):
        session = original_restore(training_run, payload, environment_factory)
        restored["session"] = session
        return session

    monkeypatch.setattr(checkpoint_tactical, "_restore_session", capture_restore)
    monkeypatch.setattr(
        checkpoint_tactical, "_instrument_episode_engine", lambda *_args: None
    )

    def mutate(environment, training_run, *, episode_index, policy):
        restored["session"].learner.optimizer._rng.random()
        return _episode(run, episode_index, length=1)

    with pytest.raises(PPOContractError, match="mutated campaign state"):
        trace_checkpoint_ppo_episode_tactical_costs(
            "CHECKPOINT-SESSION-MUTATION",
            path,
            episode_index=0,
            clock=iter((0.0, 1.0)).__next__,
            episode_collector=mutate,
        )


def test_checkpoint_tactical_report_is_atomically_canonical(monkeypatch, tmp_path, capsys):
    run, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-WRITE")
    monkeypatch.setattr(
        checkpoint_tactical, "_instrument_episode_engine", lambda *_args: None
    )
    report = trace_checkpoint_ppo_episode_tactical_costs(
        "CHECKPOINT-WRITE",
        path,
        episode_index=0,
        clock=iter((0.0, 1.0)).__next__,
        episode_collector=lambda *_args, **_kwargs: _episode(run, 0, length=1),
    )
    output = tmp_path / "episode.json"
    digest = write_checkpoint_tactical_episode_report(output, report)

    assert output.read_bytes() == report.to_json().encode("utf-8")
    assert digest == sha256(output.read_bytes()).hexdigest()
    assert not (tmp_path / ".episode.json.tmp").exists()

    monkeypatch.setattr(
        checkpoint_tactical,
        "trace_checkpoint_ppo_episode_tactical_costs",
        lambda *_args, **_kwargs: report,
    )
    assert checkpoint_tactical.main(
        [
            "--root-seed",
            "CHECKPOINT-WRITE",
            "--checkpoint-path",
            str(path),
            "--episode-index",
            "0",
            "--output-path",
            str(output),
        ]
    ) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["report_sha256"] == digest
    assert summary["episode_index"] == 0
    assert summary["stream_index"] == 0
    assert summary["episode_sha256"] == report.episode_sha256


def test_checkpoint_tactical_trace_rejects_noncanonical_checkpoint(tmp_path):
    _, path, content = _checkpoint(tmp_path, seed="CHECKPOINT-NONCANONICAL")
    path.write_bytes(content + b"\n")

    with pytest.raises(PPOContractError, match="not canonical"):
        trace_checkpoint_ppo_episode_tactical_costs(
            "CHECKPOINT-NONCANONICAL",
            path,
            episode_index=0,
        )
