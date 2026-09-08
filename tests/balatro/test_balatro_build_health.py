import pytest

from games.balatro.build_health import (
    BuildHealthEvaluator,
    BuildHealthInputs,
    EngineState,
    RealizedEngineStrength,
)


def test_build_health_reports_critical_survival_even_when_other_dimensions_are_strong():
    health = BuildHealthEvaluator().evaluate(
        BuildHealthInputs(
            survival_probability=0.10,
            immediate_score_ratio=0.95,
            scaling_ratio=0.90,
            coherence_ratio=0.90,
            runway_ratio=0.90,
        )
    )

    assert health.critical is True
    assert health.survival == pytest.approx(10.0)
    assert any("critical survival deficit" in warning for warning in health.warnings)


def test_build_health_detects_midgame_scaling_deficit_separately_from_immediate_strength():
    health = BuildHealthEvaluator().evaluate(
        BuildHealthInputs(
            survival_probability=0.85,
            immediate_score_ratio=0.80,
            scaling_ratio=0.25,
            coherence_ratio=0.70,
            runway_ratio=0.55,
        )
    )

    assert health.critical is False
    assert health.scaling_deficit is True
    assert health.immediate == pytest.approx(80.0)
    assert health.scaling == pytest.approx(25.0)
    assert any("scaling deficit" in warning for warning in health.warnings)


def test_build_health_does_not_call_low_current_output_a_scaling_deficit():
    health = BuildHealthEvaluator().evaluate(
        BuildHealthInputs(
            survival_probability=0.55,
            immediate_score_ratio=0.40,
            scaling_ratio=0.20,
            coherence_ratio=0.50,
            runway_ratio=0.50,
        )
    )

    assert health.scaling_deficit is False


def test_owned_inactive_engine_is_visible_without_fabricating_strategy_power():
    hologram = RealizedEngineStrength(
        engine_id="hologram",
        state=EngineState.OWNED_INACTIVE,
        current_strength=0.0,
        growth_rate=0.0,
        runway_need=0.7,
        rationale=("Hologram remains at x1.0",),
    )

    health = BuildHealthEvaluator().evaluate(
        BuildHealthInputs(
            survival_probability=0.80,
            immediate_score_ratio=0.75,
            scaling_ratio=0.30,
            coherence_ratio=0.65,
            runway_ratio=0.35,
            engines=(hologram,),
        )
    )

    assert health.engines == (hologram,)
    assert hologram.active is False
    assert any("hologram" in warning and "inactive" in warning for warning in health.warnings)


def test_mature_engine_is_active_and_does_not_emit_inactive_warning():
    bull_bootstraps = RealizedEngineStrength(
        engine_id="bull_bootstraps",
        state=EngineState.MATURE,
        current_strength=0.9,
        growth_rate=0.6,
        runway_need=0.0,
    )

    health = BuildHealthEvaluator().evaluate(
        BuildHealthInputs(
            survival_probability=0.95,
            immediate_score_ratio=0.95,
            scaling_ratio=0.90,
            coherence_ratio=0.90,
            runway_ratio=0.95,
            engines=(bull_bootstraps,),
        )
    )

    assert bull_bootstraps.active is True
    assert not any("bull_bootstraps" in warning for warning in health.warnings)
    assert health.total > 90.0


def test_build_health_clamps_inputs_instead_of_allowing_unbounded_scores():
    health = BuildHealthEvaluator().evaluate(
        BuildHealthInputs(
            survival_probability=2.0,
            immediate_score_ratio=1.5,
            scaling_ratio=-1.0,
            coherence_ratio=0.5,
            runway_ratio=0.5,
        )
    )

    assert health.survival == pytest.approx(100.0)
    assert health.immediate == pytest.approx(100.0)
    assert health.scaling == pytest.approx(0.0)
    assert 0.0 <= health.total <= 100.0
