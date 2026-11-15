from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.evaluation_diagnostics import TerminalEpisodeMetrics
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_model import PPOActorCritic
from games.balatro.env.ppo_progress_reward_evaluation import (
    PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
    PPO_PROGRESS_REWARD_EVALUATION_SCHEMA,
    PPOProgressPairedEpisode,
    PPOProgressPairedEvaluationReport,
    PPOProgressPolicyOutcome,
    _LoadedPilotPolicies,
    _canonical_bytes,
    _load_pilot_policies,
    evaluate_policy_pair,
    evaluate_progress_policy_corpus_pair,
    run_progress_reward_evaluation,
)
from games.balatro.env.ppo_progress_reward_pilot import PILOT_REPORT_NAME
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


def _metrics(*, ante=1, progress=0.5, money=4):
    requirement = 300.0
    score = requirement * progress
    return TerminalEpisodeMetrics(
        frame_count=2,
        ante_reached=ante,
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


def _paired(spec, *, improved=True):
    return PPOProgressPairedEpisode(
        spec.episode_index,
        spec.game_seed,
        PPOProgressPolicyOutcome("LOSS", 3, _metrics()),
        PPOProgressPolicyOutcome(
            "LOSS",
            4 if improved else 3,
            _metrics(
                ante=2 if improved else 1,
                progress=0.75 if improved else 0.5,
                money=5 if improved else 4,
            ),
        ),
    )


def _report(episodes=None):
    return PPOProgressPairedEvaluationReport(
        PPO_PROGRESS_REWARD_EVALUATION_SCHEMA,
        FIXED_SEEDED_CORPUS_SHA256,
        PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
        "0" * 64,
        "1" * 64,
        "2" * 64,
        "3" * 64,
        "4" * 64,
        "5" * 64,
        tuple(_paired(spec) for spec in FIXED_SEEDED_EPISODES)
        if episodes is None
        else episodes,
    )


def test_progress_reward_evaluation_report_is_complete_paired_and_canonical():
    report = _report()
    payload = json.loads(report.to_json())

    assert len(report.episodes) == 64
    assert payload["summary"]["initial"]["ante_8_clears"] == 0
    assert payload["summary"]["one_batch"]["mean_ante_reached"] == 2.0
    assert payload["summary"]["deltas"]["mean_ante_reached"] == 1.0
    assert payload["episodes"][0]["deltas"] == {
        "action_count": 1,
        "ante_8_clear": 0,
        "ante_reached": 1,
        "terminal_money": 1,
        "terminal_requirement_progress": 0.25,
    }
    assert report.to_json().encode("utf-8") == _canonical_bytes(report.as_dict())


def test_progress_reward_evaluation_report_rejects_missing_or_reordered_episodes():
    report = _report()
    for episodes in (report.episodes[:-1], tuple(reversed(report.episodes))):
        with pytest.raises(PPOContractError, match="incomplete or out of order"):
            replace(report, episodes=episodes)


def test_progress_reward_evaluation_uses_identical_greedy_policy_path():
    run = PPOTrainingRun.from_seed(
        "PAIR-EVAL", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    model = PPOActorCritic(run)

    result = evaluate_policy_pair(
        FIXED_SEEDED_EPISODES[0],
        model,
        model,
        environment_factory=lambda stream: BalatroHeadlessEnvironment(
            PPOHeadlessBackend(_OneCardTacticalPolicy())
        ),
    )

    assert result.initial == result.one_batch
    assert result.initial.status == "LOSS"
    assert result.initial.action_count >= 1


def test_progress_reward_corpus_pair_requires_linked_models_and_complete_order():
    first_run = PPOTrainingRun.from_seed(
        "CORPUS-FIRST", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    second_run = PPOTrainingRun.from_seed(
        "CORPUS-SECOND", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    with pytest.raises(PPOContractError, match="policy provenance drifted"):
        evaluate_progress_policy_corpus_pair(
            PPOActorCritic(first_run),
            PPOActorCritic(second_run),
            maximum_workers=1,
            pair_executor=lambda *args: pytest.fail("must not evaluate"),
        )

    model = PPOActorCritic(first_run)
    with pytest.raises(PPOContractError, match="incomplete or out of order"):
        evaluate_progress_policy_corpus_pair(
            model,
            model,
            maximum_workers=1,
            pair_executor=lambda spec, *_: _paired(
                FIXED_SEEDED_EPISODES[(spec.episode_index + 1) % 64]
            ),
        )


def test_progress_reward_evaluation_loader_verifies_exact_artifact_links(
    tmp_path, monkeypatch
):
    run = PPOTrainingRun.from_seed(
        "LOAD-EVAL", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial = PPOActorCritic(run)
    trained = PPOActorCritic(run)
    trained.parameters["policy_b"][0] += 0.25
    checkpoint = {"training_run": run.as_dict()}
    checkpoint_raw = _canonical_bytes(checkpoint)
    checkpoint_sha256 = sha256(checkpoint_raw).hexdigest()
    progress = {
        "checkpoint_sha256": checkpoint_sha256,
        "training_run_sha256": run.sha256,
    }
    progress_raw = _canonical_bytes(progress)
    pilot_report = {
        "checkpoint_sha256": checkpoint_sha256,
        "progress_sha256": sha256(progress_raw).hexdigest(),
        "training_run_sha256": run.sha256,
        "completed_batch_count": 1,
        "optimizer_consumed_transitions": 2048,
        "initial_policy_parameter_sha256": initial.parameter_sha256,
        "final_policy_parameter_sha256": trained.parameter_sha256,
    }
    (tmp_path / "checkpoint.json").write_bytes(checkpoint_raw)
    (tmp_path / "progress.json").write_bytes(progress_raw)
    (tmp_path / PILOT_REPORT_NAME).write_bytes(_canonical_bytes(pilot_report))
    monkeypatch.setattr(
        "games.balatro.env.ppo_progress_reward_evaluation._restore_session",
        lambda *args: SimpleNamespace(
            learner=SimpleNamespace(completed_batch_count=1, model=trained)
        ),
    )

    loaded = _load_pilot_policies(tmp_path)

    assert loaded.training_run == run
    assert loaded.initial_model.parameter_sha256 == initial.parameter_sha256
    assert loaded.one_batch_model.parameter_sha256 == trained.parameter_sha256
    assert loaded.checkpoint_sha256 == checkpoint_sha256

    (tmp_path / "progress.json").write_bytes(b"{}")
    with pytest.raises(PPOContractError, match="linkage drifted"):
        _load_pilot_policies(tmp_path)


def test_progress_reward_evaluation_runner_writes_one_fresh_report(
    tmp_path, monkeypatch
):
    run = PPOTrainingRun.from_seed(
        "RUN-EVAL", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial = PPOActorCritic(run)
    trained = PPOActorCritic(run)
    trained.parameters["policy_b"][0] += 0.5
    policies = _LoadedPilotPolicies(
        run,
        initial,
        trained,
        "1" * 64,
        "2" * 64,
        "3" * 64,
    )
    monkeypatch.setattr(
        "games.balatro.env.ppo_progress_reward_evaluation._load_pilot_policies",
        lambda directory: policies,
    )
    output = tmp_path / "paired.json"
    progress = []

    report = run_progress_reward_evaluation(
        tmp_path / "pilot",
        output,
        maximum_workers=8,
        pair_executor=lambda spec, first, second: _paired(spec),
        progress_callback=lambda completed, total: progress.append(
            (completed, total)
        ),
    )

    assert output.read_bytes() == report.to_json().encode("utf-8")
    assert progress == [(index, 64) for index in range(1, 65)]
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]["deltas"][
        "mean_terminal_requirement_progress"
    ] == 0.25
    with pytest.raises(PPOContractError, match="already exists"):
        run_progress_reward_evaluation(
            tmp_path / "pilot",
            output,
            maximum_workers=8,
            pair_executor=lambda spec, first, second: _paired(spec),
        )
