from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True)
class EpisodeMetrics:
    seed: int | None
    won: bool
    ante_reached: int
    blind_clear_margin: float = 0.0
    boss_clear_rate: float = 0.0
    scaling_score: float = 0.0
    survival_margin: float = 0.0
    power_engine_utilization: float = 0.0
    unused_active_engine_count: int = 0
    destructive_pivot_count: int = 0
    motif_mature_count: int = 0
    cash_reserve_failure_count: int = 0
    illegal_action_count: int = 0
    d1_mean_seconds: float = 0.0
    d1_max_seconds: float = 0.0
    build_signature: str = ""


@dataclass(frozen=True)
class BatchMetrics:
    episodes: tuple[EpisodeMetrics, ...]

    @classmethod
    def from_episodes(cls, episodes: Iterable[EpisodeMetrics]) -> "BatchMetrics":
        values = tuple(episodes)
        if not values:
            raise ValueError("tuning batch must contain at least one completed episode")
        return cls(values)

    @property
    def count(self) -> int:
        return len(self.episodes)

    @property
    def win_rate(self) -> float:
        return sum(1 for episode in self.episodes if episode.won) / self.count

    @property
    def average_ante(self) -> float:
        return sum(episode.ante_reached for episode in self.episodes) / self.count

    @property
    def median_ante(self) -> float:
        return float(median(episode.ante_reached for episode in self.episodes))

    @property
    def build_diversity(self) -> float:
        signatures = {episode.build_signature for episode in self.episodes if episode.build_signature}
        return len(signatures) / self.count

    def mean(self, field: str) -> float:
        return sum(float(getattr(episode, field)) for episode in self.episodes) / self.count

    def scalar_objective(self) -> float:
        """Conservative v1 objective for low-dimensional calibration studies.

        Win rate dominates.  Ante progress supplies dense signal, while obvious
        architecture/runtime pathologies are penalized enough that the optimizer
        cannot cheaply improve by stalling, destructive pivoting, or ignoring a
        functioning engine.
        """
        competence = (
            100.0 * self.win_rate
            + 4.0 * self.average_ante
            + 1.5 * self.mean("boss_clear_rate")
            + 1.0 * self.mean("survival_margin")
            + 0.5 * self.mean("scaling_score")
            + 2.0 * self.mean("power_engine_utilization")
            + 2.0 * self.build_diversity
        )
        pathology = (
            8.0 * self.mean("illegal_action_count")
            + 3.0 * self.mean("destructive_pivot_count")
            + 2.0 * self.mean("unused_active_engine_count")
            + 1.5 * self.mean("cash_reserve_failure_count")
            + 0.25 * max(0.0, self.mean("d1_mean_seconds") - 8.0)
            + 0.10 * max(0.0, self.mean("d1_max_seconds") - 20.0)
        )
        return competence - pathology

    def to_dict(self) -> dict[str, float | int]:
        return {
            "episodes": self.count,
            "win_rate": self.win_rate,
            "average_ante": self.average_ante,
            "median_ante": self.median_ante,
            "blind_clear_margin": self.mean("blind_clear_margin"),
            "boss_clear_rate": self.mean("boss_clear_rate"),
            "scaling_score": self.mean("scaling_score"),
            "survival_margin": self.mean("survival_margin"),
            "power_engine_utilization": self.mean("power_engine_utilization"),
            "unused_active_engine_count": self.mean("unused_active_engine_count"),
            "destructive_pivot_count": self.mean("destructive_pivot_count"),
            "motif_mature_count": self.mean("motif_mature_count"),
            "cash_reserve_failure_count": self.mean("cash_reserve_failure_count"),
            "illegal_action_count": self.mean("illegal_action_count"),
            "d1_mean_seconds": self.mean("d1_mean_seconds"),
            "d1_max_seconds": self.mean("d1_max_seconds"),
            "build_diversity": self.build_diversity,
            "objective": self.scalar_objective(),
        }
