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
    PPO_PROGRESS_STUDY_JOURNAL_SCHEMA,
    PPOProgressStudyEpisodeRecord,
    PPOProgressStudyJournal,
    load_progress_study_journal,
    write_progress_study_journal,
)
from games.balatro.env.seeded_evaluation import EVALUATION_MODE
from games.balatro.env.state import RunStatus, TurnOwner


def _run():
    return PPOTrainingRun.from_seed(
        "PROGRESS-STUDY-JOURNAL", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )


def _record(run, index, *, actions=2, batches=0, prior_transitions=0):
    return PPOProgressStudyEpisodeRecord(
        training_run_sha256=run.sha256,
        episode_index=index,
        game_seed=run.game_seed(index),
        status="LOSS",
        action_count=actions,
        completed_batch_count_after_commit=batches,
        collected_transition_count_after_commit=prior_transitions + actions,
        policy_parameter_sha256_after_commit="a" * 64,
        rewards=(0.1,) * (actions - 1) + (-1.0,),
        advantages=(-0.5,) * actions,
    )


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


def test_progress_study_journal_records_exact_reward_and_advantage_signal():
    run = _run()
    episode = _episode(run)
    session = SimpleNamespace(
        training_run=run,
        learner=SimpleNamespace(
            completed_batch_count=0,
            total_consumed_environment_transitions=2,
            model=SimpleNamespace(parameter_sha256="b" * 64),
        ),
    )

    record = PPOProgressStudyEpisodeRecord.from_episode(session, episode)

    assert record.episode_index == 0
    assert record.rewards == episode.rewards
    assert record.advantages == pytest.approx((-0.9384375, -1.0416666666666667))
    assert record.collected_transition_count_after_commit == 2


def test_progress_study_journal_round_trips_canonical_bytes(tmp_path):
    run = _run()
    journal = PPOProgressStudyJournal.fresh(run).append(_record(run, 0))
    path = tmp_path / "journal.json"

    write_progress_study_journal(path, journal)
    restored = load_progress_study_journal(path, run)

    assert restored == journal
    assert path.read_bytes() == journal.to_json().encode("utf-8")
    assert restored.schema == PPO_PROGRESS_STUDY_JOURNAL_SCHEMA


def test_progress_study_journal_trims_only_one_checkpoint_ahead_record():
    run = _run()
    first = _record(run, 0)
    second = _record(run, 1, prior_transitions=2)
    journal = PPOProgressStudyJournal.fresh(run).append(first).append(second)

    reconciled = journal.reconciled((8, 1, 2, 3, 4, 5, 6, 7))

    assert reconciled.records == (first,)
    with pytest.raises(PPOContractError, match="too far ahead"):
        journal.reconciled(tuple(range(8)))


def test_progress_study_journal_fails_closed_when_checkpoint_is_ahead():
    run = _run()
    journal = PPOProgressStudyJournal.fresh(run).append(_record(run, 0))

    with pytest.raises(PPOContractError, match="behind checkpoint"):
        journal.reconciled((8, 9, 2, 3, 4, 5, 6, 7))


def test_progress_study_journal_rejects_order_counter_and_provenance_drift(tmp_path):
    run = _run()
    with pytest.raises(PPOContractError, match="order drifted"):
        PPOProgressStudyJournal(
            PPO_PROGRESS_STUDY_JOURNAL_SCHEMA,
            run.sha256,
            (_record(run, 1),),
        )
    with pytest.raises(PPOContractError, match="counters drifted"):
        PPOProgressStudyJournal.fresh(run).append(
            _record(run, 0, prior_transitions=1)
        )

    path = tmp_path / "journal.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(PPOContractError, match="provenance drifted"):
        load_progress_study_journal(path, run)
