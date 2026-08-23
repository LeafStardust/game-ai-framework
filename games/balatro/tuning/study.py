from __future__ import annotations

"""Persistent offline Optuna studies for Balatro Bond calibration.

This module is intentionally outside the production import path.  The caller owns
actual episode execution through ``BatchEvaluator``; the study runner owns bounded
parameter suggestion, immutable snapshots, provenance, and metric recording.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from games.balatro.bonds.calibration import (
    DEFAULT_BOND_CALIBRATION,
    SCHEMA_VERSION,
    BondCalibration,
)
from games.balatro.tuning.metrics import BatchMetrics


OBJECTIVE_VERSION = 1
PHASE_A_SCHEMA = "composition-v1"


class BatchEvaluator(Protocol):
    def __call__(
        self,
        calibration: BondCalibration,
        seeds: Sequence[int],
    ) -> BatchMetrics: ...


@dataclass(frozen=True)
class StudyConfig:
    name: str
    storage_path: Path
    seeds: tuple[int, ...]
    repository_sha: str
    deck: str = "RED"
    stake: str = "WHITE"
    sampler_seed: int = 20260823

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("study name must not be empty")
        if not self.seeds:
            raise ValueError("study must define at least one evaluation seed")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("study seeds must be unique")
        if not self.repository_sha.strip():
            raise ValueError("repository SHA is required for reproducibility")

    @property
    def storage_url(self) -> str:
        path = self.storage_path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"


def _optuna():
    try:
        import optuna
    except ImportError as exc:  # pragma: no cover - exercised only without tuning extra
        raise RuntimeError(
            "Optuna is an optional offline dependency. Install with "
            "`python -m pip install -r requirements-tuning.txt`."
        ) from exc
    return optuna


def suggest_phase_a(trial) -> BondCalibration:
    """Small first search space: composer balance only, no Bond semantics."""
    r1 = trial.suggest_float("pivot_resistance_r1", 0.25, 0.90)
    r2 = r1 + trial.suggest_float("pivot_resistance_r2_delta", 0.25, 1.10)
    r3 = r2 + trial.suggest_float("pivot_resistance_r3_delta", 0.75, 2.25)
    r4 = r3 + trial.suggest_float("pivot_resistance_r4_delta", 1.00, 3.00)
    r5 = r4 + trial.suggest_float("pivot_resistance_r5_delta", 1.25, 4.00)
    return DEFAULT_BOND_CALIBRATION.with_overrides(
        realization_priority_weight=trial.suggest_float(
            "realization_priority_weight", 0.45, 1.20
        ),
        synergy_bonus=trial.suggest_float("synergy_bonus", 0.75, 2.50),
        conflict_penalty=trial.suggest_float("conflict_penalty", 1.00, 4.00),
        pivot_resistance_r1=r1,
        pivot_resistance_r2=r2,
        pivot_resistance_r3=r3,
        pivot_resistance_r4=r4,
        pivot_resistance_r5=r5,
    )


def _study_attrs(config: StudyConfig) -> dict[str, object]:
    return {
        "parameter_schema": PHASE_A_SCHEMA,
        "calibration_schema_version": SCHEMA_VERSION,
        "objective_version": OBJECTIVE_VERSION,
        "repository_sha": config.repository_sha,
        "deck": config.deck,
        "stake": config.stake,
        "seeds": list(config.seeds),
    }


def _validate_or_initialize_attrs(study, config: StudyConfig) -> None:
    expected = _study_attrs(config)
    existing = dict(study.user_attrs)
    for key, value in expected.items():
        if key in existing and existing[key] != value:
            raise ValueError(
                f"study {config.name!r} is incompatible: {key}="
                f"{existing[key]!r}, expected {value!r}"
            )
    for key, value in expected.items():
        study.set_user_attr(key, value)


def create_phase_a_study(config: StudyConfig):
    optuna = _optuna()
    sampler = optuna.samplers.TPESampler(seed=config.sampler_seed, multivariate=True)
    study = optuna.create_study(
        study_name=config.name,
        storage=config.storage_url,
        direction="maximize",
        sampler=sampler,
        load_if_exists=True,
    )
    _validate_or_initialize_attrs(study, config)
    return study


def make_phase_a_objective(config: StudyConfig, evaluator: BatchEvaluator):
    def objective(trial) -> float:
        calibration = suggest_phase_a(trial)
        batch = evaluator(calibration, config.seeds)
        if not isinstance(batch, BatchMetrics):
            raise TypeError("BatchEvaluator must return BatchMetrics")
        metrics = batch.to_dict()
        trial.set_user_attr("calibration", calibration.to_dict())
        trial.set_user_attr("repository_sha", config.repository_sha)
        trial.set_user_attr("seeds", list(config.seeds))
        for key, value in metrics.items():
            trial.set_user_attr(f"metric.{key}", value)
        return float(metrics["objective"])

    return objective


def enqueue_production_baseline(study) -> None:
    """Queue the current production point once for apples-to-apples comparison."""
    if study.user_attrs.get("production_baseline_enqueued"):
        return
    baseline = DEFAULT_BOND_CALIBRATION
    study.enqueue_trial(
        {
            "pivot_resistance_r1": baseline.pivot_resistance_r1,
            "pivot_resistance_r2_delta": baseline.pivot_resistance_r2 - baseline.pivot_resistance_r1,
            "pivot_resistance_r3_delta": baseline.pivot_resistance_r3 - baseline.pivot_resistance_r2,
            "pivot_resistance_r4_delta": baseline.pivot_resistance_r4 - baseline.pivot_resistance_r3,
            "pivot_resistance_r5_delta": baseline.pivot_resistance_r5 - baseline.pivot_resistance_r4,
            "realization_priority_weight": baseline.realization_priority_weight,
            "synergy_bonus": baseline.synergy_bonus,
            "conflict_penalty": baseline.conflict_penalty,
        }
    )
    study.set_user_attr("production_baseline_enqueued", True)


def run_phase_a(
    config: StudyConfig,
    evaluator: BatchEvaluator,
    *,
    trials: int,
    timeout_seconds: float | None = None,
):
    if trials <= 0:
        raise ValueError("trials must be positive")
    study = create_phase_a_study(config)
    enqueue_production_baseline(study)
    study.optimize(
        make_phase_a_objective(config, evaluator),
        n_trials=trials,
        timeout=timeout_seconds,
        gc_after_trial=True,
        catch=(RuntimeError,),
    )
    return study
