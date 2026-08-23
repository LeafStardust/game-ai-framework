from __future__ import annotations

"""Persistent offline Optuna studies for Balatro Bond calibration.

Seeded/offline simulation and authoritative unseeded live Balatro are intentionally
separate study modes.  Neither mode is imported by the production agent.
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
LIVE_PHASE_A_SCHEMA = "composition-live-unseeded-v1"


class BatchEvaluator(Protocol):
    def __call__(self, calibration: BondCalibration, seeds: Sequence[int]) -> BatchMetrics: ...


class LiveEvaluation(Protocol):
    metrics: BatchMetrics
    session_id: str
    run_ids: tuple[str, ...]
    won: bool
    stop_reason: str


class LiveBatchEvaluator(Protocol):
    def evaluate(self, calibration: BondCalibration) -> LiveEvaluation: ...


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
        _validate_common(self.name, self.repository_sha)
        if not self.seeds:
            raise ValueError("study must define at least one evaluation seed")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("study seeds must be unique")

    @property
    def storage_url(self) -> str:
        return _storage_url(self.storage_path)


@dataclass(frozen=True)
class LiveStudyConfig:
    """Persistent study identity for authoritative unseeded real-game trials."""

    name: str
    storage_path: Path
    repository_sha: str
    attempts_per_trial: int = 5
    deck: str = "RED"
    stake: str = "WHITE"
    sampler_seed: int = 20260823

    def __post_init__(self) -> None:
        _validate_common(self.name, self.repository_sha)
        if int(self.attempts_per_trial) <= 0:
            raise ValueError("attempts_per_trial must be positive")

    @property
    def storage_url(self) -> str:
        return _storage_url(self.storage_path)


def _validate_common(name: str, repository_sha: str) -> None:
    if not str(name).strip():
        raise ValueError("study name must not be empty")
    if not str(repository_sha).strip():
        raise ValueError("repository SHA is required for reproducibility")


def _storage_url(path: Path) -> str:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved.as_posix()}"


def _optuna():
    try:
        import optuna
    except ImportError as exc:  # pragma: no cover
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
        realization_priority_weight=trial.suggest_float("realization_priority_weight", 0.45, 1.20),
        synergy_bonus=trial.suggest_float("synergy_bonus", 0.75, 2.50),
        conflict_penalty=trial.suggest_float("conflict_penalty", 1.00, 4.00),
        pivot_resistance_r1=r1,
        pivot_resistance_r2=r2,
        pivot_resistance_r3=r3,
        pivot_resistance_r4=r4,
        pivot_resistance_r5=r5,
    )


def _seeded_attrs(config: StudyConfig) -> dict[str, object]:
    return {
        "mode": "seeded",
        "parameter_schema": PHASE_A_SCHEMA,
        "calibration_schema_version": SCHEMA_VERSION,
        "objective_version": OBJECTIVE_VERSION,
        "repository_sha": config.repository_sha,
        "deck": config.deck,
        "stake": config.stake,
        "seeds": list(config.seeds),
    }


def _live_attrs(config: LiveStudyConfig) -> dict[str, object]:
    return {
        "mode": "authoritative-live-unseeded",
        "parameter_schema": LIVE_PHASE_A_SCHEMA,
        "calibration_schema_version": SCHEMA_VERSION,
        "objective_version": OBJECTIVE_VERSION,
        "repository_sha": config.repository_sha,
        "deck": config.deck,
        "stake": config.stake,
        "attempts_per_trial": int(config.attempts_per_trial),
    }


def _validate_or_initialize_attrs(study, expected: dict[str, object], name: str) -> None:
    existing = dict(study.user_attrs)
    for key, value in expected.items():
        if key in existing and existing[key] != value:
            raise ValueError(
                f"study {name!r} is incompatible: {key}={existing[key]!r}, expected {value!r}"
            )
    for key, value in expected.items():
        study.set_user_attr(key, value)


def _create_study(*, name: str, storage_url: str, sampler_seed: int, attrs: dict[str, object]):
    optuna = _optuna()
    sampler = optuna.samplers.TPESampler(seed=int(sampler_seed), multivariate=True)
    study = optuna.create_study(
        study_name=name,
        storage=storage_url,
        direction="maximize",
        sampler=sampler,
        load_if_exists=True,
    )
    _validate_or_initialize_attrs(study, attrs, name)
    return study


def create_phase_a_study(config: StudyConfig):
    return _create_study(
        name=config.name,
        storage_url=config.storage_url,
        sampler_seed=config.sampler_seed,
        attrs=_seeded_attrs(config),
    )


def create_live_phase_a_study(config: LiveStudyConfig):
    return _create_study(
        name=config.name,
        storage_url=config.storage_url,
        sampler_seed=config.sampler_seed,
        attrs=_live_attrs(config),
    )


def _is_production_baseline(calibration: BondCalibration) -> bool:
    return calibration == DEFAULT_BOND_CALIBRATION


def _record_metrics(trial, calibration: BondCalibration, metrics: BatchMetrics) -> float:
    values = metrics.to_dict()
    trial.set_user_attr("calibration", calibration.to_dict())
    trial.set_user_attr("production_baseline", _is_production_baseline(calibration))
    for key, value in values.items():
        trial.set_user_attr(f"metric.{key}", value)
    return float(values["objective"])


def make_phase_a_objective(config: StudyConfig, evaluator: BatchEvaluator):
    def objective(trial) -> float:
        calibration = suggest_phase_a(trial)
        batch = evaluator(calibration, config.seeds)
        if not isinstance(batch, BatchMetrics):
            raise TypeError("BatchEvaluator must return BatchMetrics")
        trial.set_user_attr("repository_sha", config.repository_sha)
        trial.set_user_attr("seeds", list(config.seeds))
        return _record_metrics(trial, calibration, batch)
    return objective


def make_live_phase_a_objective(config: LiveStudyConfig, evaluator: LiveBatchEvaluator):
    def objective(trial) -> float:
        calibration = suggest_phase_a(trial)
        result = evaluator.evaluate(calibration)
        if not isinstance(result.metrics, BatchMetrics):
            raise TypeError("LiveBatchEvaluator result must contain BatchMetrics")
        if not result.run_ids:
            raise RuntimeError("live tuning trial produced no run provenance")
        trial.set_user_attr("repository_sha", config.repository_sha)
        trial.set_user_attr("session_id", str(result.session_id))
        trial.set_user_attr("run_ids", list(result.run_ids))
        trial.set_user_attr("won", bool(result.won))
        trial.set_user_attr("stop_reason", str(result.stop_reason))
        trial.set_user_attr("unseeded", True)
        return _record_metrics(trial, calibration, result.metrics)
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


def run_phase_a(config: StudyConfig, evaluator: BatchEvaluator, *, trials: int, timeout_seconds: float | None = None):
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


def run_live_phase_a(
    config: LiveStudyConfig,
    evaluator: LiveBatchEvaluator,
    *,
    trials: int,
    timeout_seconds: float | None = None,
):
    """Run authoritative unseeded trials; every trial preserves exact run IDs."""
    if trials <= 0:
        raise ValueError("trials must be positive")
    study = create_live_phase_a_study(config)
    enqueue_production_baseline(study)
    study.optimize(
        make_live_phase_a_objective(config, evaluator),
        n_trials=trials,
        timeout=timeout_seconds,
        gc_after_trial=True,
        catch=(RuntimeError,),
    )
    return study
