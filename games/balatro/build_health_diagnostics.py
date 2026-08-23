from __future__ import annotations

from games.balatro.build_component_roles import BuildComponentRoleClassifier
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator


_HEALTH = RuntimeBuildHealthEvaluator()
_ROLES = BuildComponentRoleClassifier()


def build_health_diagnostics_payload(state) -> dict:
    """Return JSON-safe, read-only Build Health diagnostics for one checkpoint."""
    health = _HEALTH.evaluate(state)
    roles = _ROLES.classify(state)
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
                "bond_id": component.bond_id,
                "bond_rank": (
                    component.bond_rank.name
                    if component.bond_rank is not None
                    else None
                ),
                "realized_engine_id": component.realized_engine_id,
                "rationale": [str(value) for value in component.rationale],
            }
            for component in roles
        ],
    }
