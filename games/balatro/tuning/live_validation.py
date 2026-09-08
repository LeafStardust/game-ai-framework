from __future__ import annotations

"""Conservative validation for unseeded authoritative live tuning evidence.

Real Balatro trials are not seed-matched, so this module intentionally does not
pretend that one candidate batch and one baseline batch form a deterministic A/B
test. Promotion requires repeated evidence and remains a review gate, never an
automatic production write-back.
"""

from dataclasses import dataclass
from math import sqrt

from games.balatro.tuning.metrics import BatchMetrics


def wilson_interval(successes: int, trials: int, *, z: float = 1.96) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("Wilson interval requires at least one trial")
    if successes < 0 or successes > trials:
        raise ValueError("successes must be within [0, trials]")
    n = float(trials)
    p = float(successes) / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denominator
    margin = z * sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n))) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


@dataclass(frozen=True)
class LivePromotionGate:
    minimum_episodes_per_arm: int = 20
    minimum_objective_delta: float = 0.25
    maximum_average_ante_regression: float = 0.10
    maximum_runtime_regression_seconds: float = 1.0
    maximum_diversity_regression: float = 0.15
    maximum_win_rate_noninferiority_margin: float = 0.05

    def __post_init__(self) -> None:
        if self.minimum_episodes_per_arm <= 0:
            raise ValueError("minimum_episodes_per_arm must be positive")
        for name in (
            "minimum_objective_delta",
            "maximum_average_ante_regression",
            "maximum_runtime_regression_seconds",
            "maximum_diversity_regression",
            "maximum_win_rate_noninferiority_margin",
        ):
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True)
class LivePromotionComparison:
    baseline: BatchMetrics
    candidate: BatchMetrics
    objective_delta: float
    win_rate_delta: float
    average_ante_delta: float
    runtime_regression: float
    diversity_delta: float
    baseline_win_interval: tuple[float, float]
    candidate_win_interval: tuple[float, float]
    reasons: tuple[str, ...]

    @property
    def passes(self) -> bool:
        return not self.reasons


def compare_live_batches(
    baseline: BatchMetrics,
    candidate: BatchMetrics,
    *,
    gate: LivePromotionGate | None = None,
) -> LivePromotionComparison:
    gate = gate or LivePromotionGate()
    baseline_wins = sum(1 for episode in baseline.episodes if episode.won)
    candidate_wins = sum(1 for episode in candidate.episodes if episode.won)
    baseline_interval = wilson_interval(baseline_wins, baseline.count)
    candidate_interval = wilson_interval(candidate_wins, candidate.count)

    objective_delta = candidate.scalar_objective() - baseline.scalar_objective()
    win_rate_delta = candidate.win_rate - baseline.win_rate
    ante_delta = candidate.average_ante - baseline.average_ante
    runtime_regression = candidate.mean("d1_mean_seconds") - baseline.mean("d1_mean_seconds")
    diversity_delta = candidate.build_diversity - baseline.build_diversity

    reasons: list[str] = []
    if baseline.count < gate.minimum_episodes_per_arm:
        reasons.append(
            f"baseline evidence too small: {baseline.count} < {gate.minimum_episodes_per_arm} episodes"
        )
    if candidate.count < gate.minimum_episodes_per_arm:
        reasons.append(
            f"candidate evidence too small: {candidate.count} < {gate.minimum_episodes_per_arm} episodes"
        )
    if objective_delta < gate.minimum_objective_delta:
        reasons.append(
            f"objective improvement {objective_delta:.3f} < required {gate.minimum_objective_delta:.3f}"
        )
    if ante_delta < -gate.maximum_average_ante_regression:
        reasons.append(
            f"average Ante regression {ante_delta:.3f} exceeds allowed {-gate.maximum_average_ante_regression:.3f}"
        )
    if runtime_regression > gate.maximum_runtime_regression_seconds:
        reasons.append(
            f"D1 mean runtime regression {runtime_regression:.3f}s exceeds allowed {gate.maximum_runtime_regression_seconds:.3f}s"
        )
    if diversity_delta < -gate.maximum_diversity_regression:
        reasons.append(
            f"build diversity regression {diversity_delta:.3f} exceeds allowed {-gate.maximum_diversity_regression:.3f}"
        )
    if candidate.mean("illegal_action_count") > 0.0:
        reasons.append("candidate produced illegal actions")

    # For unseeded evidence, use both point non-inferiority and interval sanity.
    # The candidate's upper confidence bound falling below the baseline's lower
    # bound is strong evidence of a real win-rate regression and blocks promotion.
    if win_rate_delta < -gate.maximum_win_rate_noninferiority_margin:
        reasons.append(
            f"win-rate delta {win_rate_delta:.3f} is worse than non-inferiority margin "
            f"{-gate.maximum_win_rate_noninferiority_margin:.3f}"
        )
    if candidate_interval[1] + 1e-12 < baseline_interval[0]:
        reasons.append(
            "candidate win-rate confidence interval lies entirely below baseline"
        )

    return LivePromotionComparison(
        baseline=baseline,
        candidate=candidate,
        objective_delta=objective_delta,
        win_rate_delta=win_rate_delta,
        average_ante_delta=ante_delta,
        runtime_regression=runtime_regression,
        diversity_delta=diversity_delta,
        baseline_win_interval=baseline_interval,
        candidate_win_interval=candidate_interval,
        reasons=tuple(reasons),
    )
