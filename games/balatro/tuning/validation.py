from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from games.balatro.bonds.calibration import DEFAULT_BOND_CALIBRATION, BondCalibration
from games.balatro.tuning.metrics import BatchMetrics
from games.balatro.tuning.study import BatchEvaluator


@dataclass(frozen=True)
class PromotionComparison:
    baseline: BatchMetrics
    candidate: BatchMetrics
    objective_delta: float
    win_rate_delta: float
    average_ante_delta: float
    runtime_regression: float
    diversity_delta: float

    @property
    def passes_basic_gate(self) -> bool:
        return (
            self.objective_delta > 0.0
            and self.win_rate_delta >= 0.0
            and self.average_ante_delta >= -0.10
            and self.runtime_regression <= 1.0
            and self.diversity_delta >= -0.15
            and self.candidate.mean("illegal_action_count") == 0.0
        )


def compare_on_holdout(
    evaluator: BatchEvaluator,
    candidate: BondCalibration,
    seeds: Sequence[int],
) -> PromotionComparison:
    if not seeds:
        raise ValueError("holdout seeds must not be empty")
    baseline = evaluator(DEFAULT_BOND_CALIBRATION, seeds)
    tuned = evaluator(candidate, seeds)
    return PromotionComparison(
        baseline=baseline,
        candidate=tuned,
        objective_delta=tuned.scalar_objective() - baseline.scalar_objective(),
        win_rate_delta=tuned.win_rate - baseline.win_rate,
        average_ante_delta=tuned.average_ante - baseline.average_ante,
        runtime_regression=tuned.mean("d1_mean_seconds") - baseline.mean("d1_mean_seconds"),
        diversity_delta=tuned.build_diversity - baseline.build_diversity,
    )
