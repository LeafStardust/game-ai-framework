"""Frozen one-batch advantage-normalization shadow for progress-reward PPO."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import math
import multiprocessing
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

import numpy as np

from games.balatro.env.ppo_campaign import (
    _atomic_write,
    _canonical_bytes,
    _checkpoint_payload,
    _collect_production_wave,
)
from games.balatro.env.ppo_contract import PPOContractError
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_model import PPOActorCritic, PPOBatch, PPOLoss
from games.balatro.env.ppo_progress_reward_evaluation import (
    PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
    PPOProgressPairedEpisode,
    PPOProgressPolicyOutcome,
    evaluate_progress_policy_corpus_pair,
)
from games.balatro.env.ppo_progress_study import (
    STUDY_JOURNAL_NAME,
    STUDY_MILESTONE_DIRECTORY,
    STUDY_MILESTONE_MANIFEST_NAME,
    PPOProgressStudyEpisodeRecord,
    load_progress_study_milestone,
)
from games.balatro.env.ppo_progress_study_runner import initialize_progress_study
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)


PPO_PROGRESS_ADVANTAGE_NORMALIZATION_SHADOW_SCHEMA = (
    "balatro-red-white-progress-advantage-normalization-shadow-v1"
)
PPO_PROGRESS_ADVANTAGE_NORMALIZATION_SHADOW_REPORT_NAME = (
    "advantage_normalization_shadow.json"
)


@dataclass(frozen=True)
class PPOProgressNormalizedUpdate:
    source_advantage_mean: float
    source_advantage_variance: float
    source_advantage_standard_deviation: float
    normalized_advantage_mean: float
    normalized_advantage_variance: float
    initial_policy_parameter_sha256: str
    unnormalized_policy_parameter_sha256: str
    normalized_policy_parameter_sha256: str
    unnormalized_losses: tuple[PPOLoss, ...]
    normalized_losses: tuple[PPOLoss, ...]
    normalized_model: PPOActorCritic

    def __post_init__(self) -> None:
        numbers = (
            self.source_advantage_mean,
            self.source_advantage_variance,
            self.source_advantage_standard_deviation,
            self.normalized_advantage_mean,
            self.normalized_advantage_variance,
        )
        if any(not math.isfinite(value) for value in numbers):
            raise PPOContractError("normalized shadow statistics are nonfinite")
        if (
            self.source_advantage_variance <= 0.0
            or self.source_advantage_standard_deviation <= 0.0
            or abs(self.normalized_advantage_mean) > 1e-12
            or not math.isclose(
                self.normalized_advantage_variance,
                1.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise PPOContractError("normalized shadow statistics drifted")
        for digest in (
            self.initial_policy_parameter_sha256,
            self.unnormalized_policy_parameter_sha256,
            self.normalized_policy_parameter_sha256,
        ):
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise PPOContractError("normalized shadow policy digest is invalid")
        if (
            len(self.unnormalized_losses) != 80
            or len(self.normalized_losses) != 80
            or not isinstance(self.normalized_model, PPOActorCritic)
        ):
            raise PPOContractError("normalized shadow optimizer evidence is incomplete")


@dataclass(frozen=True)
class PPOProgressNormalizationEpisode:
    episode_index: int
    game_seed: str
    initial: PPOProgressPolicyOutcome
    published_unnormalized: PPOProgressPolicyOutcome
    normalized_shadow: PPOProgressPolicyOutcome

    def __post_init__(self) -> None:
        if (
            isinstance(self.episode_index, bool)
            or not isinstance(self.episode_index, int)
            or not 0 <= self.episode_index < len(FIXED_SEEDED_EPISODES)
            or FIXED_SEEDED_EPISODES[self.episode_index].game_seed != self.game_seed
        ):
            raise PPOContractError("normalized shadow episode provenance drifted")
        if any(
            not isinstance(outcome, PPOProgressPolicyOutcome)
            for outcome in (
                self.initial,
                self.published_unnormalized,
                self.normalized_shadow,
            )
        ):
            raise PPOContractError("normalized shadow episode outcome is invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_index": self.episode_index,
            "game_seed": self.game_seed,
            "initial": self.initial.as_dict(),
            "published_unnormalized": self.published_unnormalized.as_dict(),
            "normalized_shadow": self.normalized_shadow.as_dict(),
        }


@dataclass(frozen=True)
class _ReconstructedBatchOne:
    training_run_sha256: str
    initial_milestone_sha256: str
    published_milestone_sha256: str
    published_checkpoint_sha256: str
    published_journal_sha256: str
    replayed_episode_count: int
    initial_learner: PPOLearner
    published_model: PPOActorCritic
    batch: PPOBatch

    def __post_init__(self) -> None:
        for digest in (
            self.training_run_sha256,
            self.initial_milestone_sha256,
            self.published_milestone_sha256,
            self.published_checkpoint_sha256,
            self.published_journal_sha256,
        ):
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise PPOContractError("normalized shadow source digest is invalid")
        if self.replayed_episode_count < 1 or not isinstance(self.batch, PPOBatch):
            raise PPOContractError("normalized shadow source replay is incomplete")


def _summarize_outcomes(
    episodes: tuple[PPOProgressNormalizationEpisode, ...], attribute: str
) -> dict[str, float | int]:
    outcomes = tuple(getattr(episode, attribute) for episode in episodes)
    if len(outcomes) != len(FIXED_SEEDED_EPISODES):
        raise PPOContractError("normalized shadow evaluation corpus is incomplete")
    return {
        "episode_count": len(outcomes),
        "ante_8_clears": sum(
            outcome.metrics.ante_8_cleared for outcome in outcomes
        ),
        "mean_ante_reached": fmean(
            outcome.metrics.ante_reached for outcome in outcomes
        ),
        "mean_terminal_requirement_progress": fmean(
            outcome.metrics.terminal_requirement_progress for outcome in outcomes
        ),
        "mean_minimum_money": fmean(
            outcome.metrics.minimum_money for outcome in outcomes
        ),
        "mean_terminal_money": fmean(
            outcome.metrics.terminal_money for outcome in outcomes
        ),
        "mean_action_count": fmean(outcome.action_count for outcome in outcomes),
    }


def frozen_normalization_acceptance(
    episodes: tuple[PPOProgressNormalizationEpisode, ...],
) -> dict[str, Any]:
    """Apply the predeclared no-regression and strict-improvement gates."""

    expected = tuple(
        (spec.episode_index, spec.game_seed) for spec in FIXED_SEEDED_EPISODES
    )
    if tuple((episode.episode_index, episode.game_seed) for episode in episodes) != expected:
        raise PPOContractError(
            "normalized shadow evaluation episodes are incomplete or out of order"
        )
    summaries = {
        name: _summarize_outcomes(episodes, name)
        for name in ("initial", "published_unnormalized", "normalized_shadow")
    }
    candidate = summaries["normalized_shadow"]
    sources = (summaries["initial"], summaries["published_unnormalized"])
    gates = {
        "clears_nonregression": candidate["ante_8_clears"]
        >= max(source["ante_8_clears"] for source in sources),
        "mean_ante_nonregression": candidate["mean_ante_reached"]
        >= max(source["mean_ante_reached"] for source in sources),
        "terminal_requirement_progress_nonregression": candidate[
            "mean_terminal_requirement_progress"
        ]
        >= max(source["mean_terminal_requirement_progress"] for source in sources),
        "minimum_cash_nonregression": candidate["mean_minimum_money"]
        >= max(source["mean_minimum_money"] for source in sources),
        "terminal_cash_nonregression": candidate["mean_terminal_money"]
        >= max(source["mean_terminal_money"] for source in sources),
    }
    strict = any(
        candidate[key] > max(source[key] for source in sources)
        for key in (
            "ante_8_clears",
            "mean_ante_reached",
            "mean_terminal_requirement_progress",
        )
    )
    accepted = all(gates.values()) and strict
    return {
        "initial": summaries["initial"],
        "published_unnormalized": summaries["published_unnormalized"],
        "normalized_shadow": summaries["normalized_shadow"],
        "gates": {**gates, "strict_competence_improvement": strict},
        "accepted": accepted,
        "decision": "accept" if accepted else "reject",
    }


def normalize_ppo_batch_advantages(
    batch: PPOBatch,
) -> tuple[PPOBatch, dict[str, float]]:
    """Return one detached batch with only advantages centered and scaled."""

    if not isinstance(batch, PPOBatch):
        raise TypeError("normalized shadow requires PPOBatch")
    source = batch.validated(expected_size=2048)
    advantages = np.asarray(source.advantages, dtype=np.float64)
    mean = float(np.mean(advantages))
    variance = float(np.mean((advantages - mean) ** 2))
    deviation = math.sqrt(variance)
    if not math.isfinite(deviation) or deviation <= 0.0:
        raise PPOContractError("normalized shadow advantage variance is invalid")
    normalized = (advantages - mean) / deviation
    shadow = replace(source, advantages=normalized).validated(expected_size=2048)
    return shadow, {
        "source_mean": mean,
        "source_variance": variance,
        "source_standard_deviation": deviation,
        "normalized_mean": float(np.mean(normalized)),
        "normalized_variance": float(np.mean(normalized * normalized)),
    }


def run_normalized_advantage_shadow_update(
    initial_learner: PPOLearner,
    batch: PPOBatch,
    *,
    expected_unnormalized_policy_sha256: str,
) -> PPOProgressNormalizedUpdate:
    """Apply exact source and normalized updates to independent learner clones."""

    if not isinstance(initial_learner, PPOLearner):
        raise TypeError("normalized shadow requires PPOLearner")
    initial_payload = initial_learner.serialize()
    initial_digest = initial_learner.model.parameter_sha256
    normalized_batch, statistics = normalize_ppo_batch_advantages(batch)
    source_batch = batch.validated(expected_size=2048)

    unnormalized = PPOLearner.restore(initial_learner.training_run, initial_payload)
    normalized = PPOLearner.restore(initial_learner.training_run, initial_payload)
    unnormalized_losses = unnormalized.optimizer.update(source_batch)
    normalized_losses = normalized.optimizer.update(normalized_batch)
    if initial_learner.serialize() != initial_payload:
        raise PPOContractError("normalized shadow mutated its initial learner")
    if unnormalized.model.parameter_sha256 != expected_unnormalized_policy_sha256:
        raise PPOContractError("normalized shadow source policy reproduction drifted")
    return PPOProgressNormalizedUpdate(
        statistics["source_mean"],
        statistics["source_variance"],
        statistics["source_standard_deviation"],
        statistics["normalized_mean"],
        statistics["normalized_variance"],
        initial_digest,
        unnormalized.model.parameter_sha256,
        normalized.model.parameter_sha256,
        unnormalized_losses,
        normalized_losses,
        normalized.model,
    )


def _manifest_path(directory: Path, batch_count: int) -> Path:
    return (
        directory
        / STUDY_MILESTONE_DIRECTORY
        / f"batch-{batch_count:03d}"
        / STUDY_MILESTONE_MANIFEST_NAME
    )


def _batch_sha256(batch: PPOBatch) -> str:
    digest = sha256()
    for name in (
        "observations",
        "action_masks",
        "action_indices",
        "episode_indices",
        "decision_indices",
        "old_log_probabilities",
        "old_values",
        "advantages",
        "returns",
    ):
        values = np.ascontiguousarray(getattr(batch, name))
        digest.update(name.encode("ascii"))
        digest.update(values.dtype.str.encode("ascii"))
        digest.update(json.dumps(values.shape, separators=(",", ":")).encode("ascii"))
        digest.update(values.tobytes())
    return digest.hexdigest()


def _reconstruct_batch_one(
    artifact_directory: str | Path,
    *,
    maximum_workers: int,
    wave_collector: Callable | None = None,
) -> _ReconstructedBatchOne:
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("normalized shadow workers must be from 1 through 8")
    if wave_collector is not None and not callable(wave_collector):
        raise TypeError("wave_collector must be callable")
    directory = Path(artifact_directory)
    training_run, _ = initialize_progress_study(directory)
    initial = load_progress_study_milestone(directory, training_run, 0)
    published = load_progress_study_milestone(directory, training_run, 1)
    source_records = published.journal.records
    if not source_records:
        raise PPOContractError("normalized shadow batch-1 journal is empty")
    initial_payload = initial.session.learner.serialize()
    initial_learner = PPOLearner.restore(training_run, initial_payload)
    session = initial.session
    captured: list[PPOBatch] = []
    cursor = 0

    def observe_batch(batch: PPOBatch) -> None:
        if captured:
            raise PPOContractError("normalized shadow captured multiple batches")
        captured.append(deepcopy(batch).validated(expected_size=2048))

    def observe_episode(current_session, episode) -> None:
        nonlocal cursor
        if cursor >= len(source_records):
            raise PPOContractError("normalized shadow replay exceeded batch-1 journal")
        actual = PPOProgressStudyEpisodeRecord.from_episode(current_session, episode)
        if actual != source_records[cursor]:
            raise PPOContractError("normalized shadow replayed episode drifted")
        cursor += 1

    def replay(collector: Callable) -> None:
        advance = session.advance_parallel(
            maximum_episodes=len(source_records),
            maximum_batches=1,
            wave_collector=collector,
            on_episode_committed=observe_episode,
            on_batch_ready=observe_batch,
        )
        if (
            advance.batches_completed != 1
            or advance.completed_batch_count != 1
            or cursor != len(source_records)
            or len(captured) != 1
            or session.learner.model.parameter_sha256
            != published.milestone.policy_parameter_sha256
        ):
            raise PPOContractError("normalized shadow batch-1 reproduction drifted")
        checkpoint_digest = sha256(
            _canonical_bytes(_checkpoint_payload(training_run, session))
        ).hexdigest()
        if checkpoint_digest != published.milestone.checkpoint_sha256:
            raise PPOContractError("normalized shadow checkpoint reproduction drifted")

    if wave_collector is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers, mp_context=context
        ) as executor:
            replay(
                lambda requests, run, model: _collect_production_wave(
                    executor, requests, run, model
                )
            )
    else:
        replay(wave_collector)

    initial_manifest = _manifest_path(directory, 0).read_bytes()
    published_manifest = _manifest_path(directory, 1).read_bytes()
    published_journal = (
        _manifest_path(directory, 1).with_name(STUDY_JOURNAL_NAME).read_bytes()
    )
    return _ReconstructedBatchOne(
        training_run.sha256,
        sha256(initial_manifest).hexdigest(),
        sha256(published_manifest).hexdigest(),
        published.milestone.checkpoint_sha256,
        sha256(published_journal).hexdigest(),
        cursor,
        initial_learner,
        deepcopy(published.session.learner.model),
        captured[0],
    )


def _combine_evaluations(
    published: tuple[PPOProgressPairedEpisode, ...],
    normalized: tuple[PPOProgressPairedEpisode, ...],
) -> tuple[PPOProgressNormalizationEpisode, ...]:
    if len(published) != len(normalized):
        raise PPOContractError("normalized shadow paired evaluations drifted")
    combined = []
    for source, shadow in zip(published, normalized, strict=True):
        if (
            source.episode_index != shadow.episode_index
            or source.game_seed != shadow.game_seed
            or source.initial != shadow.initial
        ):
            raise PPOContractError("normalized shadow initial evaluation drifted")
        combined.append(
            PPOProgressNormalizationEpisode(
                source.episode_index,
                source.game_seed,
                source.initial,
                source.one_batch,
                shadow.one_batch,
            )
        )
    episodes = tuple(combined)
    frozen_normalization_acceptance(episodes)
    return episodes


def _loss_dict(loss: PPOLoss) -> dict[str, float | None]:
    return {
        "total": loss.total,
        "policy": loss.policy,
        "value": loss.value,
        "entropy": loss.entropy,
        "unclipped_gradient_norm": loss.unclipped_gradient_norm,
        "applied_gradient_norm": loss.applied_gradient_norm,
    }


def run_progress_advantage_normalization_shadow(
    artifact_directory: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    wave_collector: Callable | None = None,
    pair_executor=None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Reconstruct batch 1, normalize one clone, and freeze its corpus result."""

    destination = Path(output_path)
    if destination.exists():
        raise PPOContractError("normalized shadow output already exists")
    if not destination.parent.is_dir():
        raise PPOContractError("normalized shadow output directory is missing")
    if pair_executor is not None and not callable(pair_executor):
        raise TypeError("pair_executor must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable")
    source = _reconstruct_batch_one(
        artifact_directory,
        maximum_workers=maximum_workers,
        wave_collector=wave_collector,
    )
    update = run_normalized_advantage_shadow_update(
        source.initial_learner,
        source.batch,
        expected_unnormalized_policy_sha256=(
            source.published_model.parameter_sha256
        ),
    )
    if update.initial_policy_parameter_sha256 != (
        source.initial_learner.model.parameter_sha256
    ):
        raise PPOContractError("normalized shadow initial policy linkage drifted")

    def progress(stage: str):
        if progress_callback is None:
            return None
        return lambda completed, total: progress_callback(stage, completed, total)

    published_pairs = evaluate_progress_policy_corpus_pair(
        source.initial_learner.model,
        source.published_model,
        maximum_workers=maximum_workers,
        pair_executor=pair_executor,
        progress_callback=progress("published_unnormalized"),
    )
    normalized_pairs = evaluate_progress_policy_corpus_pair(
        source.initial_learner.model,
        update.normalized_model,
        maximum_workers=maximum_workers,
        pair_executor=pair_executor,
        progress_callback=progress("normalized_shadow"),
    )
    episodes = _combine_evaluations(published_pairs, normalized_pairs)
    report = {
        "schema": PPO_PROGRESS_ADVANTAGE_NORMALIZATION_SHADOW_SCHEMA,
        "fixed_corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "selection_contract": PPO_PROGRESS_GREEDY_SELECTION_CONTRACT,
        "training_run_sha256": source.training_run_sha256,
        "source": {
            "initial_milestone_sha256": source.initial_milestone_sha256,
            "published_batch_1_milestone_sha256": (
                source.published_milestone_sha256
            ),
            "published_batch_1_checkpoint_sha256": (
                source.published_checkpoint_sha256
            ),
            "published_batch_1_journal_sha256": source.published_journal_sha256,
            "replayed_episode_count": source.replayed_episode_count,
            "batch_transition_count": len(source.batch.action_indices),
            "batch_sha256": _batch_sha256(source.batch),
        },
        "policies": {
            "initial_parameter_sha256": update.initial_policy_parameter_sha256,
            "published_unnormalized_parameter_sha256": (
                update.unnormalized_policy_parameter_sha256
            ),
            "normalized_shadow_parameter_sha256": (
                update.normalized_policy_parameter_sha256
            ),
        },
        "normalization": {
            "source_advantage_mean": update.source_advantage_mean,
            "source_advantage_variance": update.source_advantage_variance,
            "source_advantage_standard_deviation": (
                update.source_advantage_standard_deviation
            ),
            "normalized_advantage_mean": update.normalized_advantage_mean,
            "normalized_advantage_variance": update.normalized_advantage_variance,
            "unnormalized_losses": [
                _loss_dict(loss) for loss in update.unnormalized_losses
            ],
            "normalized_losses": [
                _loss_dict(loss) for loss in update.normalized_losses
            ],
        },
        "summary": frozen_normalization_acceptance(episodes),
        "episodes": [episode.as_dict() for episode in episodes],
    }
    _atomic_write(destination, _canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)

    def progress(stage: str, completed: int, total: int) -> None:
        print(
            _canonical_bytes(
                {"stage": stage, "completed": completed, "total": total}
            ).decode("utf-8"),
            flush=True,
        )

    report = run_progress_advantage_normalization_shadow(
        arguments.artifact_directory,
        arguments.output_path,
        maximum_workers=arguments.maximum_workers,
        progress_callback=progress,
    )
    path = Path(arguments.output_path)
    print(
        _canonical_bytes(
            {
                "schema": report["schema"],
                "output_path": str(path),
                "report_sha256": sha256(path.read_bytes()).hexdigest(),
                "summary": report["summary"],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
