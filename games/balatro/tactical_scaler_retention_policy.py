from __future__ import annotations

"""D2 retention for invested non-Bond persistent scalers.

Tactical/support classification means "no Bond quota", not "disposable". A Joker
with already-realized persistent scaling must not be replaced merely because a fresh
candidate creates a new low-rank Bond label. This guard covers the finite tactical
scalers whose accumulated public state is already modeled by Build Health.
"""

from dataclasses import replace

from games.balatro.build_health import EngineState
from games.balatro.build_health_runtime import RealizedEngineAnalyzer, RuntimeBuildHealthEvaluator, projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_PROTECTED_TACTICAL_ENGINES = frozenset({
    "campfire",
    "flash_card",
    "obelisk",
    "red_card",
    "hiker_card_growth",
})
_STATE_VALUE = {
    EngineState.NOT_OWNED: 0,
    EngineState.OWNED_INACTIVE: 0,
    EngineState.ACTIVATED_WEAK: 1,
    EngineState.ACTIVATED_HEALTHY: 2,
    EngineState.MATURE: 3,
}
_MATERIAL_SCALING_GAIN = 7.5
_ANALYZER = RealizedEngineAnalyzer()
_HEALTH = RuntimeBuildHealthEvaluator()


def _engine_map(state):
    return {
        engine.engine_id: engine
        for engine in _ANALYZER.analyze(state)
        if engine.engine_id in _PROTECTED_TACTICAL_ENGINES
    }


def _invested(engine) -> bool:
    return _STATE_VALUE.get(engine.state, 0) >= _STATE_VALUE[EngineState.ACTIVATED_HEALTHY]


def install_tactical_scaler_retention_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_tactical_scaler_retention_installed", False):
        return
    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if getattr(decision, "action", None) != REPLACE or getattr(decision, "selected", None) is None:
            return decision
        try:
            index = int(decision.selected.replace_index)
            jokers = list(getattr(state, "jokers", ()) or ())
            if index < 0 or index >= len(jokers):
                return decision
        except (AttributeError, TypeError, ValueError):
            return decision

        current_engines = _engine_map(state)
        invested = {engine_id: engine for engine_id, engine in current_engines.items() if _invested(engine)}
        if not invested:
            return decision

        jokers[index] = candidate
        projected_state = projected_state_with_jokers(state, tuple(jokers))
        projected_engines = _engine_map(projected_state)
        damaged = []
        for engine_id, before in invested.items():
            after = projected_engines.get(engine_id)
            if after is None or _STATE_VALUE.get(after.state, 0) < _STATE_VALUE.get(before.state, 0):
                damaged.append((engine_id, before, after))
        if not damaged:
            return decision

        current_health = _HEALTH.evaluate(state)
        projected_health = _HEALTH.evaluate(projected_state)
        scaling_gain = float(projected_health.scaling) - float(current_health.scaling)
        if scaling_gain >= _MATERIAL_SCALING_GAIN:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    f"invested tactical-scaler pivot allowed: projected scaling improves {scaling_gain:+.1f}",
                ),
            )

        damaged_text = ", ".join(
            f"{engine_id}:{before.state.value}->{getattr(getattr(after, 'state', None), 'value', 'lost')}"
            for engine_id, before, after in damaged
        )
        return replace(
            decision,
            action=HOLD,
            selected=None,
            rationale=(
                *decision.rationale,
                f"invested tactical-scaler retention veto: replacement damages {damaged_text}",
                f"numeric scaling delta={scaling_gain:+.1f}; requires >= +{_MATERIAL_SCALING_GAIN:.1f} to justify dismantling realized scaling",
                "tactical/support classification does not make accumulated persistent power disposable",
            ),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._tactical_scaler_retention_installed = True
