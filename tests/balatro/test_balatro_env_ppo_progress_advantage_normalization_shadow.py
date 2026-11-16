from copy import deepcopy
from dataclasses import replace
import json

import numpy as np
import pytest

from games.balatro.env.evaluation_diagnostics import TerminalEpisodeMetrics
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_model import PPOBatch, PPOLoss
import games.balatro.env.ppo_progress_advantage_normalization_shadow as shadow_module
from games.balatro.env.ppo_progress_advantage_normalization_shadow import (
    PPOProgressNormalizedUpdate,
    PPOProgressNormalizationEpisode,
    _ReconstructedBatchOne,
    _combine_evaluations,
    frozen_normalization_acceptance,
    normalize_ppo_batch_advantages,
    run_progress_advantage_normalization_shadow,
    run_normalized_advantage_shadow_update,
)
from games.balatro.env.ppo_progress_reward_evaluation import (
    PPOProgressPairedEpisode,
    PPOProgressPolicyOutcome,
)
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES


def _batch(learner, *, constant=False):
    size = PPO_PROGRESS_TRAINING_CONTRACT.rollout_batch_size
    observations = np.zeros(
        (size, PPO_PROGRESS_TRAINING_CONTRACT.observation_size), dtype=np.float64
    )
    observations[:, 0] = np.linspace(-1.0, 1.0, size)
    masks = np.zeros(
        (size, PPO_PROGRESS_TRAINING_CONTRACT.action_size), dtype=np.bool_
    )
    masks[:, (0, 4)] = True
    actions = np.resize(np.asarray([0, 4], dtype=np.int64), size)
    probabilities, values, _ = learner.model.evaluate_batch(observations, masks)
    advantages = (
        np.ones(size, dtype=np.float64)
        if constant
        else np.linspace(-3.0, 1.0, size, dtype=np.float64)
    )
    return PPOBatch(
        observations,
        masks,
        actions,
        np.repeat(np.arange(8, dtype=np.int64), size // 8),
        np.tile(np.arange(size // 8, dtype=np.int64), 8),
        np.log(probabilities[np.arange(size), actions]),
        values,
        advantages,
        values + advantages,
    )


def _outcome(ante, progress, minimum_cash, terminal_cash):
    requirement = 300.0
    score = requirement * progress
    return PPOProgressPolicyOutcome(
        "LOSS",
        3,
        TerminalEpisodeMetrics(
            frame_count=4,
            ante_reached=ante,
            ante_8_cleared=False,
            terminal_blind_score=score,
            terminal_blind_requirement=requirement,
            terminal_chip_margin=score - requirement,
            terminal_requirement_progress=progress,
            starting_money=4,
            minimum_money=minimum_cash,
            peak_money=max(4, terminal_cash),
            terminal_money=terminal_cash,
        ),
    )


def _normalization_episodes(normalized=None):
    initial = _outcome(1, 0.5, 1, 4)
    published = _outcome(2, 0.6, 2, 5)
    candidate = normalized or _outcome(3, 0.7, 3, 6)
    return tuple(
        PPOProgressNormalizationEpisode(
            spec.episode_index,
            spec.game_seed,
            initial,
            published,
            candidate,
        )
        for spec in FIXED_SEEDED_EPISODES
    )


def test_normalized_shadow_changes_only_advantages_and_centers_exact_batch():
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-BATCH", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    learner = PPOLearner(run)
    source = _batch(learner)

    normalized, statistics = normalize_ppo_batch_advantages(source)

    assert statistics["source_mean"] == pytest.approx(-1.0)
    assert statistics["normalized_mean"] == pytest.approx(0.0, abs=1e-15)
    assert statistics["normalized_variance"] == pytest.approx(1.0)
    for name in (
        "observations",
        "action_masks",
        "action_indices",
        "episode_indices",
        "decision_indices",
        "old_log_probabilities",
        "old_values",
        "returns",
    ):
        assert np.array_equal(getattr(normalized, name), getattr(source, name))
    assert not np.array_equal(normalized.advantages, source.advantages)


def test_normalized_shadow_reproduces_source_and_keeps_initial_immutable():
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-UPDATE", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial = PPOLearner(run)
    batch = _batch(initial)
    source = PPOLearner.restore(run, initial.serialize())
    source.optimizer.update(batch)
    initial_payload = initial.serialize()

    result = run_normalized_advantage_shadow_update(
        initial,
        batch,
        expected_unnormalized_policy_sha256=source.model.parameter_sha256,
    )

    assert initial.serialize() == initial_payload
    assert result.unnormalized_policy_parameter_sha256 == source.model.parameter_sha256
    assert result.normalized_policy_parameter_sha256 != result.unnormalized_policy_parameter_sha256
    assert result.normalized_advantage_mean == pytest.approx(0.0, abs=1e-15)
    assert result.normalized_advantage_variance == pytest.approx(1.0)


def test_normalized_shadow_rejects_zero_variance_and_source_drift():
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-REJECT", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    learner = PPOLearner(run)
    with pytest.raises(PPOContractError, match="variance is invalid"):
        normalize_ppo_batch_advantages(_batch(learner, constant=True))

    with pytest.raises(PPOContractError, match="source policy reproduction drifted"):
        run_normalized_advantage_shadow_update(
            learner,
            _batch(learner),
            expected_unnormalized_policy_sha256="f" * 64,
        )


def test_normalized_shadow_acceptance_is_frozen_against_both_sources():
    accepted = frozen_normalization_acceptance(_normalization_episodes())

    assert accepted["accepted"] is True
    assert accepted["decision"] == "accept"
    assert all(accepted["gates"].values())
    assert accepted["normalized_shadow"]["mean_minimum_money"] == 3.0

    regressed = frozen_normalization_acceptance(
        _normalization_episodes(_outcome(3, 0.7, 1, 6))
    )
    assert regressed["accepted"] is False
    assert regressed["decision"] == "reject"
    assert regressed["gates"]["minimum_cash_nonregression"] is False

    tied = frozen_normalization_acceptance(
        _normalization_episodes(_outcome(2, 0.6, 2, 5))
    )
    assert tied["accepted"] is False
    assert tied["gates"]["strict_competence_improvement"] is False


def test_normalized_shadow_combines_only_identical_initial_corpus_results():
    initial = _outcome(1, 0.5, 1, 4)
    published = _outcome(2, 0.6, 2, 5)
    normalized = _outcome(3, 0.7, 3, 6)
    source = tuple(
        PPOProgressPairedEpisode(
            spec.episode_index, spec.game_seed, initial, published
        )
        for spec in FIXED_SEEDED_EPISODES
    )
    shadow = tuple(
        PPOProgressPairedEpisode(
            spec.episode_index, spec.game_seed, initial, normalized
        )
        for spec in FIXED_SEEDED_EPISODES
    )

    assert _combine_evaluations(source, shadow) == _normalization_episodes()
    drifted = (replace(shadow[0], initial=published), *shadow[1:])
    with pytest.raises(PPOContractError, match="initial evaluation drifted"):
        _combine_evaluations(source, drifted)


def test_normalized_shadow_rejects_output_overwrite_before_replay():
    with pytest.raises(PPOContractError, match="output already exists"):
        run_progress_advantage_normalization_shadow(
            "missing-study",
            __file__,
            maximum_workers=1,
        )


def test_normalized_shadow_runner_writes_complete_frozen_report(monkeypatch):
    run = PPOTrainingRun.from_seed(
        "NORMALIZED-SHADOW-REPORT", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )
    initial = PPOLearner(run)
    published = deepcopy(initial.model)
    published.parameters["policy_b"][0] += 0.1
    normalized = deepcopy(initial.model)
    normalized.parameters["policy_b"][0] += 0.2
    batch = _batch(initial)
    source = _ReconstructedBatchOne(
        run.sha256,
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64,
        12,
        initial,
        published,
        batch,
    )
    losses = (PPOLoss(0.0, 0.0, 0.0, 0.0),) * 80
    update = PPOProgressNormalizedUpdate(
        -1.0,
        4.0,
        2.0,
        0.0,
        1.0,
        initial.model.parameter_sha256,
        published.parameter_sha256,
        normalized.parameter_sha256,
        losses,
        losses,
        normalized,
    )
    initial_outcome = _outcome(1, 0.5, 1, 4)
    published_outcome = _outcome(2, 0.6, 2, 5)
    normalized_outcome = _outcome(3, 0.7, 3, 6)
    written = []

    def evaluate(_initial, candidate, **_kwargs):
        outcome = (
            published_outcome
            if candidate.parameter_sha256 == published.parameter_sha256
            else normalized_outcome
        )
        return tuple(
            PPOProgressPairedEpisode(
                spec.episode_index, spec.game_seed, initial_outcome, outcome
            )
            for spec in FIXED_SEEDED_EPISODES
        )

    monkeypatch.setattr(shadow_module, "_reconstruct_batch_one", lambda *_a, **_k: source)
    monkeypatch.setattr(
        shadow_module, "run_normalized_advantage_shadow_update", lambda *_a, **_k: update
    )
    monkeypatch.setattr(shadow_module, "evaluate_progress_policy_corpus_pair", evaluate)
    monkeypatch.setattr(
        shadow_module, "_atomic_write", lambda path, content: written.append((path, content))
    )

    report = run_progress_advantage_normalization_shadow(
        ".",
        "normalized-shadow-test-output.json",
        maximum_workers=1,
    )

    assert report["summary"]["accepted"] is True
    assert report["source"]["batch_transition_count"] == 2048
    assert len(report["normalization"]["normalized_losses"]) == 80
    assert len(report["episodes"]) == 64
    assert len(written) == 1
    assert json.loads(written[0][1]) == report
