from dataclasses import replace
import json

import pytest

from games.balatro.env.evaluation_diagnostics import TerminalEpisodeMetrics
from games.balatro.env.ppo_campaign import make_ppo_progress_training_environment
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_progress_reward_evaluation import (
    PPOProgressPairedEpisode,
    PPOProgressPolicyOutcome,
)
from games.balatro.env.ppo_progress_study import (
    PPOProgressStudyJournal,
    publish_progress_study_milestone,
)
from games.balatro.env.ppo_progress_study_evaluation import (
    PPO_PROGRESS_STUDY_EVALUATION_SCHEMA,
    PPOProgressStudyEvaluationReport,
    load_progress_study_evaluation,
    run_progress_study_evaluation,
)
from games.balatro.env.ppo_training_session import PPOTrainingSession
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)


def _metrics(progress: float, money: int) -> TerminalEpisodeMetrics:
    requirement = 300.0
    score = requirement * progress
    return TerminalEpisodeMetrics(
        frame_count=3,
        ante_reached=1,
        ante_8_cleared=False,
        terminal_blind_score=score,
        terminal_blind_requirement=requirement,
        terminal_chip_margin=score - requirement,
        terminal_requirement_progress=progress,
        starting_money=4,
        minimum_money=min(4, money),
        peak_money=max(4, money),
        terminal_money=money,
    )


def _pair(spec) -> PPOProgressPairedEpisode:
    return PPOProgressPairedEpisode(
        spec.episode_index,
        spec.game_seed,
        PPOProgressPolicyOutcome("LOSS", 2, _metrics(0.5, 4)),
        PPOProgressPolicyOutcome("LOSS", 3, _metrics(0.75, 5)),
    )


def _prepare_batch_zero(directory):
    run = PPOTrainingRun.from_seed(
        "PROGRESS-STUDY-EVALUATION", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    session = PPOTrainingSession(run, make_ppo_progress_training_environment)
    publish_progress_study_milestone(
        directory, session, PPOProgressStudyJournal.fresh(run), 0
    )
    return run


def test_progress_study_evaluation_is_complete_canonical_and_linked(tmp_path):
    run = _prepare_batch_zero(tmp_path)
    progress = []

    report = run_progress_study_evaluation(
        tmp_path,
        run,
        0,
        maximum_workers=1,
        pair_executor=lambda spec, *_: _pair(spec),
        progress_callback=lambda completed, total: progress.append(
            (completed, total)
        ),
    )
    restored = load_progress_study_evaluation(tmp_path, run, 0)
    payload = json.loads(report.to_json())

    assert report.schema == PPO_PROGRESS_STUDY_EVALUATION_SCHEMA
    assert report.fixed_corpus_sha256 == FIXED_SEEDED_CORPUS_SHA256
    assert restored == report
    assert progress == [(index, 64) for index in range(1, 65)]
    assert payload["summary"]["candidate"]["mean_terminal_money"] == 5.0
    assert payload["summary"]["deltas"]["mean_action_count"] == 1.0
    assert payload["episodes"][0]["batch_0"]["action_count"] == 2
    assert payload["episodes"][0]["candidate"]["action_count"] == 3

    with pytest.raises(PPOContractError, match="already exists"):
        run_progress_study_evaluation(
            tmp_path,
            run,
            0,
            maximum_workers=1,
            pair_executor=lambda spec, *_: _pair(spec),
        )


def test_progress_study_evaluation_rejects_missing_order_and_tampering(tmp_path):
    run = _prepare_batch_zero(tmp_path)
    report = run_progress_study_evaluation(
        tmp_path,
        run,
        0,
        maximum_workers=1,
        pair_executor=lambda spec, *_: _pair(spec),
    )
    with pytest.raises(PPOContractError, match="incomplete or out of order"):
        replace(report, episodes=tuple(reversed(report.episodes)))

    path = tmp_path / "milestones" / "batch-000" / "evaluation.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["summary"]["candidate"]["mean_terminal_money"] = 999.0
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(PPOContractError, match="linkage drifted"):
        load_progress_study_evaluation(tmp_path, run, 0)
