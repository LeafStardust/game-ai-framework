from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from games.balatro.bonds.calibration import BondCalibration, use_bond_calibration
from games.balatro.tuning.metrics import BatchMetrics, EpisodeMetrics


EpisodeExecutor = Callable[[int], EpisodeMetrics]


@dataclass(frozen=True)
class LocalBatchEvaluator:
    """Run a fixed seed schedule under one immutable Bond calibration snapshot.

    The episode executor owns the actual deterministic Balatro simulation or other
    approved offline environment.  This wrapper guarantees that every episode in
    one trial observes the same calibration and validates seed provenance.
    """

    execute_episode: EpisodeExecutor

    def __call__(
        self,
        calibration: BondCalibration,
        seeds: Sequence[int],
    ) -> BatchMetrics:
        episodes: list[EpisodeMetrics] = []
        with use_bond_calibration(calibration):
            for seed in seeds:
                expected = int(seed)
                episode = self.execute_episode(expected)
                if not isinstance(episode, EpisodeMetrics):
                    raise TypeError("episode executor must return EpisodeMetrics")
                if episode.seed is not None and int(episode.seed) != expected:
                    raise ValueError(
                        f"episode seed provenance mismatch: expected {expected}, "
                        f"got {episode.seed}"
                    )
                if episode.seed is None:
                    episode = EpisodeMetrics(
                        seed=expected,
                        won=episode.won,
                        ante_reached=episode.ante_reached,
                        blind_clear_margin=episode.blind_clear_margin,
                        boss_clear_rate=episode.boss_clear_rate,
                        scaling_score=episode.scaling_score,
                        survival_margin=episode.survival_margin,
                        power_engine_utilization=episode.power_engine_utilization,
                        unused_active_engine_count=episode.unused_active_engine_count,
                        destructive_pivot_count=episode.destructive_pivot_count,
                        motif_mature_count=episode.motif_mature_count,
                        cash_reserve_failure_count=episode.cash_reserve_failure_count,
                        illegal_action_count=episode.illegal_action_count,
                        d1_mean_seconds=episode.d1_mean_seconds,
                        d1_max_seconds=episode.d1_max_seconds,
                        build_signature=episode.build_signature,
                    )
                episodes.append(episode)
        return BatchMetrics.from_episodes(episodes)
