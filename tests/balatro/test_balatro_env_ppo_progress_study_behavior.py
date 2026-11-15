import json

import pytest

from games.balatro.env.evaluation_diagnostics import TerminalEpisodeMetrics
from games.balatro.env.ppo_campaign import make_ppo_training_environment
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_progress_study import STUDY_MILESTONE_BATCHES
from games.balatro.env.ppo_progress_study_behavior import (
    ACTION_SCHEMA_SHA256,
    PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA,
    PPOProgressBehaviorDecision,
    PPOProgressBehaviorEpisode,
    PPOProgressBehaviorMilestoneLink,
    PPOProgressBehaviorReport,
    _first_divergence,
    _trace_policy,
    run_progress_study_behavior_attribution,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.action_encoding import PUBLIC_ACTION_VERSION


def _metrics():
    return TerminalEpisodeMetrics(
        frame_count=2,
        ante_reached=1,
        ante_8_cleared=False,
        terminal_blind_score=150.0,
        terminal_blind_requirement=300.0,
        terminal_chip_margin=-150.0,
        terminal_requirement_progress=0.5,
        starting_money=4,
        minimum_money=4,
        peak_money=4,
        terminal_money=4,
    )


def _deltas():
    return {
        "action_count": 0,
        "ante_8_clear": 0,
        "ante_reached": 0,
        "terminal_money": 0,
        "terminal_requirement_progress": 0.0,
    }


def _episode(batch, spec, *, selected=0, observation="a" * 64):
    return PPOProgressBehaviorEpisode(
        batch,
        spec.episode_index,
        spec.game_seed,
        "LOSS",
        _metrics(),
        (
            PPOProgressBehaviorDecision(
                0,
                observation,
                (0, 1),
                selected,
                0.75,
                0.5,
                -0.25,
            ),
        ),
        _deltas(),
    )


def _report():
    links = tuple(
        PPOProgressBehaviorMilestoneLink(
            batch,
            f"{batch + 1:064x}",
            f"{batch + 2:064x}",
            f"{batch + 3:064x}",
        )
        for batch in STUDY_MILESTONE_BATCHES
    )
    episodes = tuple(
        _episode(
            batch,
            spec,
            selected=1 if batch == 8 and spec.episode_index < 3 else 0,
        )
        for batch in STUDY_MILESTONE_BATCHES
        for spec in FIXED_SEEDED_EPISODES
    )
    return PPOProgressBehaviorReport(
        PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA,
        "f" * 64,
        FIXED_SEEDED_CORPUS_SHA256,
        PUBLIC_ACTION_VERSION,
        ACTION_SCHEMA_SHA256,
        links,
        episodes,
    )


def test_progress_behavior_report_publishes_frequencies_and_first_divergences():
    report = _report()
    payload = json.loads(report.to_json())

    assert len(payload["episodes"]) == 5 * 64
    assert payload["checkpoint_summaries"][0]["decision_count"] == 64
    assert payload["checkpoint_summaries"][0]["action_slots"][0]["count"] == 64
    comparison = payload["comparisons_to_batch_0"][-1]
    assert comparison["completed_batch_count"] == 8
    assert comparison["episodes_with_greedy_divergence"] == 3
    assert comparison["first_divergence_action_transitions"] == {"0->1": 3}
    assert comparison["episodes"][0]["first_greedy_divergence"][
        "decision_index"
    ] == 0


def test_progress_behavior_first_divergence_requires_shared_public_state():
    spec = FIXED_SEEDED_EPISODES[0]
    initial = _episode(0, spec, selected=0, observation="a" * 64)
    candidate = _episode(8, spec, selected=1, observation="b" * 64)

    with pytest.raises(PPOContractError, match="divergence state drifted"):
        _first_divergence(initial, candidate)


def test_progress_behavior_traces_the_frozen_sparse_greedy_path():
    run = PPOTrainingRun.from_seed(
        "PROGRESS-BEHAVIOR-TRACE", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    model = PPOActorCritic(run)
    spec = FIXED_SEEDED_EPISODES[0]

    episode = _trace_policy(
        model,
        spec,
        0,
        _deltas(),
        make_ppo_training_environment(0),
    )

    assert episode.status == "LOSS"
    assert len(episode.decisions) == episode.metrics.frame_count - 1
    assert all(
        decision.selected_action_index in decision.legal_action_indices
        for decision in episode.decisions
    )
    assert all(decision.selected_probability > 0.0 for decision in episode.decisions)


def test_progress_behavior_runner_rejects_overwrite_before_loading_artifacts(tmp_path):
    output = tmp_path / "behavior.json"
    output.write_text("belongs to prior evidence", encoding="utf-8")

    with pytest.raises(PPOContractError, match="already exists"):
        run_progress_study_behavior_attribution(
            tmp_path / "missing-study",
            output,
            maximum_workers=1,
        )
