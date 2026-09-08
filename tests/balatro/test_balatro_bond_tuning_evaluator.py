import pytest

from games.balatro.bonds.calibration import DEFAULT_BOND_CALIBRATION, current_bond_calibration
from games.balatro.tuning.evaluator import LocalBatchEvaluator
from games.balatro.tuning.metrics import EpisodeMetrics
from games.balatro.tuning.validation import compare_on_holdout


def test_local_batch_evaluator_applies_one_calibration_to_every_seed():
    seen = []
    tuned = DEFAULT_BOND_CALIBRATION.with_overrides(synergy_bonus=2.0)

    def execute(seed):
        seen.append((seed, current_bond_calibration()))
        return EpisodeMetrics(seed=seed, won=seed == 2, ante_reached=seed + 4,
                              build_signature=f"build-{seed}")

    batch = LocalBatchEvaluator(execute)(tuned, (1, 2, 3))
    assert [seed for seed, _ in seen] == [1, 2, 3]
    assert all(calibration is tuned for _, calibration in seen)
    assert batch.count == 3
    assert current_bond_calibration() is DEFAULT_BOND_CALIBRATION


def test_local_batch_evaluator_rejects_seed_provenance_mismatch():
    evaluator = LocalBatchEvaluator(
        lambda seed: EpisodeMetrics(seed=999, won=False, ante_reached=1)
    )
    with pytest.raises(ValueError, match="seed provenance mismatch"):
        evaluator(DEFAULT_BOND_CALIBRATION, (1,))


def test_holdout_comparison_requires_candidate_to_beat_baseline_without_regressions():
    def evaluator(calibration, seeds):
        tuned = calibration.synergy_bonus > DEFAULT_BOND_CALIBRATION.synergy_bonus
        from games.balatro.tuning.metrics import BatchMetrics
        return BatchMetrics.from_episodes(
            EpisodeMetrics(
                seed=seed,
                won=tuned,
                ante_reached=8 if tuned else 6,
                boss_clear_rate=1.0 if tuned else 0.5,
                power_engine_utilization=1.0 if tuned else 0.5,
                d1_mean_seconds=2.0,
                build_signature=f"build-{seed}",
            )
            for seed in seeds
        )

    candidate = DEFAULT_BOND_CALIBRATION.with_overrides(synergy_bonus=2.0)
    comparison = compare_on_holdout(evaluator, candidate, (11, 12, 13))
    assert comparison.objective_delta > 0.0
    assert comparison.win_rate_delta > 0.0
    assert comparison.passes_basic_gate
