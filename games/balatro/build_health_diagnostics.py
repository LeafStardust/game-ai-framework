from __future__ import annotations

from copy import deepcopy

from games.balatro.build_component_roles import BuildComponentRoleClassifier
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator


_HEALTH = RuntimeBuildHealthEvaluator()
_ROLES = BuildComponentRoleClassifier()


def _diagnostic_tracker(strategy_tracker):
    if strategy_tracker is None:
        return None
    try:
        return deepcopy(strategy_tracker)
    except (TypeError, ValueError):
        # Telemetry is never allowed to mutate the production run-scoped tracker.
        # If a tracker cannot be cloned, omit strategy-dependent diagnostic detail.
        return None


def build_health_diagnostics_payload(state, *, strategy_tracker=None) -> dict:
    """Return JSON-safe, read-only Build Health diagnostics for one checkpoint."""
    health_tracker = _diagnostic_tracker(strategy_tracker)
    role_tracker = _diagnostic_tracker(strategy_tracker)
    health = _HEALTH.evaluate(state, strategy_tracker=health_tracker)
    roles = _ROLES.classify(state, strategy_tracker=role_tracker)
    return {
        "total": float(health.total),
        "survival": float(health.survival),
        "immediate": float(health.immediate),
        "scaling": float(health.scaling),
        "coherence": float(health.coherence),
        "runway": float(health.runway),
        "critical": bool(health.critical),
        "scaling_deficit": bool(health.scaling_deficit),
        "warnings": [str(value) for value in health.warnings],
        "engines": [
            {
                "engine_id": engine.engine_id,
                "state": engine.state.value,
                "current_strength": float(engine.current_strength),
                "growth_rate": float(engine.growth_rate),
                "runway_need": float(engine.runway_need),
                "rationale": [str(value) for value in engine.rationale],
            }
            for engine in health.engines
        ],
        "components": [
            {
                "index": int(component.index),
                "name": component.name,
                "role": component.role.value,
                "strategy_id": component.strategy_id,
                "tier": component.tier,
                "realized_engine_id": component.realized_engine_id,
                "rationale": [str(value) for value in component.rationale],
            }
            for component in roles
        ],
    }
