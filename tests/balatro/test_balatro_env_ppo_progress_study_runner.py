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
from games.balatro.env.ppo_campaign import make_ppo_progress_training_environment
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_ROLLOUT_EPISODE_SCHEMA,
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPORolloutBoundary,
    PPORolloutDecision,
    PPORolloutEpisode,
    PPOTrainingRun,
)
from games.balatro.env.ppo_progress_study import (
    STUDY_JOURNAL_NAME,
    STUDY_MILESTONE_BATCHES,
    PPOProgressStudyEpisodeRecord,
    load_progress_study_journal,
    load_progress_study_milestone,
)
from games.balatro.env.ppo_progress_study_runner import (
    PPO_PROGRESS_STUDY_ROOT_SEED,
    PPO_PROGRESS_STUDY_RUNTIME_SCHEMA,
    STUDY_IDENTITY_NAME,
    STUDY_RUNTIME_NAME,
    PPOProgressStudyRuntime,
    PPOProgressStudyRuntimeCall,
    _build_report,
    _load_live_session,
    _load_runtime,
    initialize_progress_study,
    run_progress_study,
)
from games.balatro.env.ppo_training_session import PPOTrainingSession
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
            index,
            observation,
            mask,
            probabilities,
            0.0,
            selected,
            action,
        )
        for index in range(2)
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


def test_progress_study_initialization_is_fresh_exact_and_resumable(tmp_path):
    run, identity = initialize_progress_study(tmp_path)
    resumed_run, resumed_identity = initialize_progress_study(tmp_path)
    milestone = load_progress_study_milestone(tmp_path, run, 0)

    assert run == resumed_run
    assert identity == resumed_identity
    assert identity.root_seed == PPO_PROGRESS_STUDY_ROOT_SEED
    assert identity.batch_limit == 8
    assert milestone.milestone.completed_batch_count == 0
    assert milestone.journal.records == ()

    (tmp_path / STUDY_IDENTITY_NAME).write_bytes(b"{}")
    with pytest.raises(PPOContractError, match="identity is malformed"):
        initialize_progress_study(tmp_path)


def test_progress_study_initialization_rejects_unowned_directory(tmp_path):
    (tmp_path / "foreign.txt").write_text("not this study", encoding="utf-8")
    with pytest.raises(PPOContractError, match="fresh empty"):
        initialize_progress_study(tmp_path)


def test_progress_study_runtime_is_canonical_and_tracks_resume_gaps(tmp_path):
    run = PPOTrainingRun.from_seed(
        PPO_PROGRESS_STUDY_ROOT_SEED, contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    runtime = PPOProgressStudyRuntime(PPO_PROGRESS_STUDY_RUNTIME_SCHEMA, run.sha256)
    runtime = runtime.append(PPOProgressStudyRuntimeCall(0, 1, 0, 10, 4.5))
    runtime = runtime.append(PPOProgressStudyRuntimeCall(1, 2, 12, 20, 5.5))
    path = tmp_path / STUDY_RUNTIME_NAME
    path.write_text(runtime.to_json(), encoding="utf-8")

    restored = _load_runtime(path, run)

    assert restored == runtime
    assert restored.elapsed_through_batch(1) == 4.5
    assert restored.elapsed_through_batch(2) == 10.0
    resumed = PPOProgressStudyRuntime(PPO_PROGRESS_STUDY_RUNTIME_SCHEMA, run.sha256)
    resumed = resumed.append(PPOProgressStudyRuntimeCall(1, 2, 12, 20, 5.5))
    assert resumed.elapsed_through_batch(1) == 0.0
    assert resumed.elapsed_through_batch(2) == 5.5
    resumed = resumed.append(PPOProgressStudyRuntimeCall(3, 4, 25, 30, 2.0))
    assert resumed.elapsed_through_batch(3) == 5.5
    assert resumed.elapsed_through_batch(4) == 7.5
    with pytest.raises(PPOContractError, match="order drifted"):
        runtime.append(PPOProgressStudyRuntimeCall(0, 1, 20, 21, 1.0))


def test_progress_study_interrupted_observer_journal_is_trimmed_on_resume(tmp_path):
    def fake_evaluation(directory, run, batch_count, **kwargs):
        path = directory / "milestones" / "batch-000" / "evaluation.json"
        path.write_bytes(b"{}")
        return SimpleNamespace()

    def interrupted_campaign(root_seed, directory, **kwargs):
        assert root_seed == PPO_PROGRESS_STUDY_ROOT_SEED
        assert kwargs["maximum_batches"] == 1
        assert kwargs["training_contract"] == PPO_PROGRESS_TRAINING_CONTRACT
        assert kwargs["progress_study_batch_limit"] == 8
        run = PPOTrainingRun.from_seed(
            root_seed, contract=PPO_PROGRESS_TRAINING_CONTRACT
        )
        session = PPOTrainingSession(run, make_ppo_progress_training_environment)
        episode = _episode(run)
        session.learner.add_episode(episode)
        kwargs["episode_commit_observer"](session, episode)
        raise RuntimeError("simulated checkpoint interruption")

    with pytest.raises(RuntimeError, match="checkpoint interruption"):
        run_progress_study(
            tmp_path,
            maximum_episodes_per_call=1,
            maximum_workers=1,
            campaign_runner=interrupted_campaign,
            evaluation_runner=fake_evaluation,
        )

    run = PPOTrainingRun.from_seed(
        PPO_PROGRESS_STUDY_ROOT_SEED, contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    ahead = load_progress_study_journal(tmp_path / STUDY_JOURNAL_NAME, run)
    assert len(ahead.records) == 1

    session, reconciled = _load_live_session(tmp_path, run)

    assert session.learner.completed_batch_count == 0
    assert reconciled.records == ()
    assert load_progress_study_journal(tmp_path / STUDY_JOURNAL_NAME, run) == reconciled


def test_progress_study_runner_rejects_invalid_episode_bound_before_writes(tmp_path):
    with pytest.raises(PPOContractError, match="maximum episodes"):
        run_progress_study(
            tmp_path,
            maximum_episodes_per_call=0,
            maximum_workers=1,
        )
    assert not tmp_path.exists() or not any(tmp_path.iterdir())

    with pytest.raises(PPOContractError, match="workers"):
        run_progress_study(
            tmp_path,
            maximum_episodes_per_call=1,
            maximum_workers=9,
        )
    assert not tmp_path.exists() or not any(tmp_path.iterdir())


def test_progress_study_final_report_contains_each_exact_checkpoint(
    tmp_path, monkeypatch
):
    run, identity = initialize_progress_study(tmp_path)
    runtime = PPOProgressStudyRuntime(PPO_PROGRESS_STUDY_RUNTIME_SCHEMA, run.sha256)
    for batch in range(1, 9):
        runtime = runtime.append(
            PPOProgressStudyRuntimeCall(batch - 1, batch, batch - 1, batch, 1.0)
        )
    milestones = {}
    evaluations = {}
    for batch in STUDY_MILESTONE_BATCHES:
        directory = tmp_path / "milestones" / f"batch-{batch:03d}"
        directory.mkdir(parents=True, exist_ok=True)
        manifest = directory / "milestone.json"
        if not manifest.exists():
            manifest.write_bytes(f"manifest-{batch}".encode())
        (directory / "evaluation.json").write_bytes(f"evaluation-{batch}".encode())
        records = tuple(
            PPOProgressStudyEpisodeRecord(
                training_run_sha256=run.sha256,
                episode_index=index,
                game_seed=run.game_seed(index),
                status="LOSS",
                action_count=1,
                completed_batch_count_after_commit=min(index + 1, batch),
                collected_transition_count_after_commit=index + 1,
                policy_parameter_sha256_after_commit="a" * 64,
                rewards=(-1.0,),
                advantages=(-0.5,),
            )
            for index in range(batch)
        )
        milestones[batch] = SimpleNamespace(
            milestone=SimpleNamespace(
                as_dict=lambda batch=batch: {"completed_batch_count": batch}
            ),
            journal=SimpleNamespace(records=records),
        )
        evaluations[batch] = SimpleNamespace(
            as_dict=lambda batch=batch: {
                "summary": {"candidate": {"batch": batch}}
            }
        )
    monkeypatch.setattr(
        "games.balatro.env.ppo_progress_study_runner.load_progress_study_milestone",
        lambda directory, training_run, batch: milestones[batch],
    )
    monkeypatch.setattr(
        "games.balatro.env.ppo_progress_study_runner.load_progress_study_evaluation",
        lambda directory, training_run, batch: evaluations[batch],
    )

    report = _build_report(tmp_path, run, identity, runtime)

    assert report["complete"] is True
    assert [item["completed_batch_count"] for item in report["checkpoints"]] == [
        0,
        1,
        2,
        4,
        8,
    ]
    assert report["checkpoints"][-1]["reward_statistics"]["count"] == 8
    assert report["checkpoints"][-1]["advantage_statistics"]["mean"] == -0.5
    assert report["checkpoints"][-1]["measured_training_seconds"] == 8.0
    assert set(report["checkpoints"][-1]["fail_closed_counts"].values()) == {0}
    assert report["unmeasured_interrupted_episode_count"] == 0
