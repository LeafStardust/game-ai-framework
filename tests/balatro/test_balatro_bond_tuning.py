from pathlib import Path

import pytest

from games.balatro.bonds.calibration import DEFAULT_BOND_CALIBRATION
from games.balatro.tuning.metrics import BatchMetrics, EpisodeMetrics
from games.balatro.tuning.study import StudyConfig, suggest_phase_a


class _Trial:
    def __init__(self):
        self.calls = []

    def suggest_float(self, name, low, high):
        self.calls.append((name, low, high))
        defaults = {
            "pivot_resistance_r1": 0.5,
            "pivot_resistance_r2_delta": 0.5,
            "pivot_resistance_r3_delta": 1.5,
            "pivot_resistance_r4_delta": 2.0,
            "pivot_resistance_r5_delta": 2.5,
            "realization_priority_weight": 0.75,
            "synergy_bonus": 1.5,
            "conflict_penalty": 2.0,
        }
        return defaults[name]


def test_phase_a_search_space_can_reproduce_production_baseline():
    calibration = suggest_phase_a(_Trial())
    assert calibration == DEFAULT_BOND_CALIBRATION


def test_phase_a_search_space_preserves_monotonic_pivot_geometry():
    calibration = suggest_phase_a(_Trial())
    values = calibration.pivot_resistance_values()
    assert all(left <= right for left, right in zip(values, values[1:]))


def test_batch_metrics_reward_competence_and_penalize_pathologies():
    healthy = BatchMetrics.from_episodes([
        EpisodeMetrics(seed=1, won=True, ante_reached=8, boss_clear_rate=1.0,
                       survival_margin=1.0, scaling_score=1.0,
                       power_engine_utilization=1.0, build_signature="burnt"),
        EpisodeMetrics(seed=2, won=False, ante_reached=7, boss_clear_rate=0.8,
                       survival_margin=0.8, scaling_score=0.9,
                       power_engine_utilization=0.9, build_signature="held"),
    ])
    pathological = BatchMetrics.from_episodes([
        EpisodeMetrics(seed=1, won=False, ante_reached=5, illegal_action_count=1,
                       destructive_pivot_count=2, unused_active_engine_count=2,
                       cash_reserve_failure_count=1, d1_mean_seconds=20.0,
                       d1_max_seconds=60.0, build_signature="same"),
        EpisodeMetrics(seed=2, won=False, ante_reached=5, illegal_action_count=1,
                       destructive_pivot_count=2, unused_active_engine_count=2,
                       cash_reserve_failure_count=1, d1_mean_seconds=20.0,
                       d1_max_seconds=60.0, build_signature="same"),
    ])
    assert healthy.scalar_objective() > pathological.scalar_objective()
    assert healthy.build_diversity == pytest.approx(1.0)
    assert pathological.build_diversity == pytest.approx(0.5)


def test_empty_tuning_batch_is_invalid():
    with pytest.raises(ValueError, match="at least one"):
        BatchMetrics.from_episodes([])


def test_study_config_requires_unique_seeds_and_repository_sha(tmp_path: Path):
    with pytest.raises(ValueError, match="unique"):
        StudyConfig("x", tmp_path / "x.db", (1, 1), "abc")
    with pytest.raises(ValueError, match="repository SHA"):
        StudyConfig("x", tmp_path / "x.db", (1,), "")
