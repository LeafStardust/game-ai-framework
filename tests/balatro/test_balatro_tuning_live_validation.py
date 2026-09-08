import pytest

from games.balatro.tuning.live_validation import (
    LivePromotionGate,
    compare_live_batches,
    wilson_interval,
)
from games.balatro.tuning.metrics import BatchMetrics, EpisodeMetrics


def _batch(
    *,
    count=20,
    wins=4,
    ante=5,
    runtime=2.0,
    illegal=0,
    prefix="build",
):
    episodes = []
    for index in range(count):
        episodes.append(
            EpisodeMetrics(
                seed=None,
                won=index < wins,
                ante_reached=ante,
                boss_clear_rate=0.5,
                survival_margin=0.5,
                scaling_score=2.0,
                power_engine_utilization=0.5,
                illegal_action_count=illegal,
                d1_mean_seconds=runtime,
                build_signature=f"{prefix}-{index % 4}",
            )
        )
    return BatchMetrics.from_episodes(episodes)


def test_wilson_interval_is_bounded_and_validates_inputs():
    low, high = wilson_interval(5, 20)
    assert 0.0 <= low <= 0.25 <= high <= 1.0
    with pytest.raises(ValueError, match="at least one"):
        wilson_interval(0, 0)
    with pytest.raises(ValueError, match="successes"):
        wilson_interval(21, 20)


def test_live_gate_rejects_tiny_evidence_even_when_candidate_looks_better():
    comparison = compare_live_batches(
        _batch(count=5, wins=0, ante=4),
        _batch(count=5, wins=2, ante=6),
    )
    assert not comparison.passes
    assert any("baseline evidence too small" in reason for reason in comparison.reasons)
    assert any("candidate evidence too small" in reason for reason in comparison.reasons)


def test_live_gate_accepts_material_nonpathological_improvement():
    baseline = _batch(count=20, wins=2, ante=4, runtime=2.0, prefix="base")
    candidate = _batch(count=20, wins=5, ante=5, runtime=2.1, prefix="cand")
    comparison = compare_live_batches(baseline, candidate)
    assert comparison.passes
    assert comparison.objective_delta > 0.0
    assert comparison.win_rate_delta > 0.0


def test_live_gate_rejects_illegal_action_even_with_better_results():
    baseline = _batch(count=20, wins=1, ante=4)
    candidate = _batch(count=20, wins=10, ante=7, illegal=1)
    comparison = compare_live_batches(baseline, candidate)
    assert not comparison.passes
    assert "candidate produced illegal actions" in comparison.reasons


def test_live_gate_rejects_material_runtime_regression():
    baseline = _batch(count=20, wins=2, ante=4, runtime=1.0)
    candidate = _batch(count=20, wins=5, ante=5, runtime=3.0)
    comparison = compare_live_batches(baseline, candidate)
    assert not comparison.passes
    assert any("runtime regression" in reason for reason in comparison.reasons)


def test_live_gate_rejects_point_win_rate_regression_beyond_margin():
    baseline = _batch(count=40, wins=20, ante=5)
    candidate = _batch(count=40, wins=10, ante=7)
    comparison = compare_live_batches(
        baseline,
        candidate,
        gate=LivePromotionGate(minimum_objective_delta=0.0),
    )
    assert not comparison.passes
    assert any("non-inferiority margin" in reason for reason in comparison.reasons)


def test_gate_configuration_rejects_negative_thresholds():
    with pytest.raises(ValueError, match="minimum_episodes_per_arm"):
        LivePromotionGate(minimum_episodes_per_arm=0)
    with pytest.raises(ValueError, match="cannot be negative"):
        LivePromotionGate(maximum_runtime_regression_seconds=-1.0)
