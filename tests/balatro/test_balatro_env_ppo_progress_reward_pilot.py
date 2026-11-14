from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_VERSION,
    ActionMask,
    action_index,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_VERSION,
    EncodedPublicObservation,
)
from games.balatro.env.ppo_campaign import CHECKPOINT_NAME, PROGRESS_NAME
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_ROLLOUT_EPISODE_SCHEMA,
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutBoundary,
    PPORolloutDecision,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_progress_reward_pilot import (
    PILOT_REPORT_NAME,
    PPO_PROGRESS_REWARD_PILOT_SCHEMA,
    run_progress_reward_pilot,
)
from games.balatro.env.seeded_evaluation import EVALUATION_MODE
from games.balatro.env.state import RunStatus, TurnOwner


def _episode(run):
    action = EnvAction.from_alias("SELECT_BLIND")
    selected = action_index(action)
    mask_values = [False] * PPO_PROGRESS_TRAINING_CONTRACT.action_size
    mask_values[selected] = True
    mask = ActionMask(PUBLIC_ACTION_VERSION, tuple(mask_values))
    probabilities = tuple(
        1.0 if index == selected else 0.0
        for index in range(PPO_PROGRESS_TRAINING_CONTRACT.action_size)
    )
    observation = EncodedPublicObservation(
        PUBLIC_OBSERVATION_VERSION,
        (0.0,) * PPO_PROGRESS_TRAINING_CONTRACT.observation_size,
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
            0,
            decision_index,
            observation,
            mask,
            probabilities,
            0.0,
            selected,
            action,
        )
        for decision_index in range(2)
    )
    return PPORolloutEpisode(
        PPO_PROGRESS_ROLLOUT_EPISODE_SCHEMA,
        run,
        0,
        run.game_seed(0),
        (start, start, final),
        decisions,
        (0.04125, -1.0416666666666667),
    )


def test_progress_reward_pilot_writes_exact_one_batch_signal_report(tmp_path):
    calls = []

    def campaign_runner(root_seed, directory, **kwargs):
        calls.append((root_seed, directory, kwargs))
        run = PPOTrainingRun.from_seed(
            root_seed, contract=PPO_PROGRESS_TRAINING_CONTRACT
        )
        session = SimpleNamespace(
            learner=SimpleNamespace(
                model=SimpleNamespace(parameter_sha256="f" * 64)
            )
        )
        kwargs["episode_commit_observer"](session, _episode(run))
        checkpoint = b"checkpoint"
        progress_bytes = b"progress"
        (directory / CHECKPOINT_NAME).write_bytes(checkpoint)
        (directory / PROGRESS_NAME).write_bytes(progress_bytes)
        return {
            "training_run_sha256": run.sha256,
            "checkpoint_sha256": sha256(checkpoint).hexdigest(),
            "completed_batch_count": 1,
            "optimizer_consumed_transitions": 2048,
            "collected_environment_transitions": 2049,
        }

    clock_values = iter((10.0, 15.5))
    report = run_progress_reward_pilot(
        "PILOT",
        tmp_path,
        maximum_episodes=512,
        maximum_workers=8,
        clock=lambda: next(clock_values),
        campaign_runner=campaign_runner,
    )

    assert report.schema == PPO_PROGRESS_REWARD_PILOT_SCHEMA
    assert report.completed_batch_count == 1
    assert report.optimizer_consumed_transitions == 2048
    assert report.collected_environment_transitions == 2049
    assert report.committed_episode_count == 1
    assert report.reward_statistics["count"] == 2
    assert report.reward_statistics["variance"] > 0.0
    assert report.advantage_statistics["variance"] > 0.0
    assert report.episode_depth_statistics == {
        "count": 1,
        "minimum": 2.0,
        "maximum": 2.0,
        "mean": 2.0,
        "variance": 0.0,
    }
    assert report.elapsed_seconds == 5.5
    assert set(report.fail_closed_counts.values()) == {0}
    assert report.initial_policy_parameter_sha256 != report.final_policy_parameter_sha256
    assert calls[0][2]["maximum_batches"] == 1
    assert calls[0][2]["training_contract"] == PPO_PROGRESS_TRAINING_CONTRACT
    report_path = tmp_path / PILOT_REPORT_NAME
    assert json.loads(report_path.read_text(encoding="utf-8")) == json.loads(
        report.to_json()
    )


def test_progress_reward_pilot_refuses_nonempty_artifact_directory(tmp_path):
    (tmp_path / "existing.txt").write_text("belongs to another run", encoding="utf-8")

    with pytest.raises(PPOContractError, match="fresh empty"):
        run_progress_reward_pilot(
            "PILOT",
            tmp_path,
            maximum_episodes=512,
            maximum_workers=8,
            campaign_runner=lambda *args, **kwargs: pytest.fail("must not run"),
        )
