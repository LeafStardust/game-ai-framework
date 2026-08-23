from __future__ import annotations

"""Retention guard for already-realized canonical Bond power engines.

D2 may discover that a candidate creates several fresh low-rank Bonds.  That must
not by itself justify selling the run's already ACTIVE/MATURE power engine.  This
layer compares the current and projected canonical power engines after ordinary D2
and pivot-authority scoring have admitted a replacement.
"""

from dataclasses import replace

from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_REALIZATION_VALUE = {
    "DORMANT": 0.0,
    "PARTIAL": 0.5,
    "ACTIVE": 1.0,
    "MATURE": 1.5,
}


def _strength(payload: dict | None) -> float:
    if not payload:
        return 0.0
    return float(payload.get("rank_value", 0) or 0) + _REALIZATION_VALUE.get(
        str(payload.get("realization", "DORMANT")).upper(), 0.0
    )


def _relevant_map(diagnostics: dict) -> dict[str, dict]:
    return {
        str(item.get("bond_id")): item
        for item in diagnostics.get("relevant_bonds", ())
        if item.get("bond_id")
    }


def _projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def install_bond_power_engine_retention_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_bond_power_engine_retention_installed", False):
        return

    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if getattr(decision, "action", None) != REPLACE or getattr(decision, "selected", None) is None:
            return decision

        try:
            index = int(decision.selected.replace_index)
        except (AttributeError, TypeError, ValueError):
            return decision

        current = bond_strategy_diagnostics(state)
        current_engine = current.get("power_engine")
        current_payload = _relevant_map(current).get(str(current_engine)) if current_engine else None
        if not current_payload or str(current_payload.get("realization", "")).upper() not in {"ACTIVE", "MATURE"}:
            return decision

        projected_jokers = _projected_jokers(state, candidate, index)
        if projected_jokers is None:
            return decision
        projected_state = projected_state_with_jokers(state, projected_jokers)
        projected = bond_strategy_diagnostics(projected_state)
        projected_engine = projected.get("power_engine")
        if projected_engine == current_engine:
            return decision

        projected_payload = _relevant_map(projected).get(str(projected_engine)) if projected_engine else None
        current_strength = _strength(current_payload)
        projected_strength = _strength(projected_payload)

        # A realized engine is sticky, not immortal. A replacement may pivot away
        # only when the newly projected power engine is materially stronger by the
        # same rank/realization scale used by canonical diagnostics.
        required = current_strength + 0.75
        if projected_strength + 1e-12 >= required:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    f"canonical power-engine pivot allowed: {current_engine} strength={current_strength:.2f} -> {projected_engine} strength={projected_strength:.2f}",
                    f"required projected strength={required:.2f}",
                ),
            )

        return replace(
            decision,
            action=HOLD,
            selected=None,
            rationale=(
                *decision.rationale,
                f"canonical power-engine retention veto: {current_engine} is {current_payload.get('rank')}/{current_payload.get('realization')}",
                f"current power strength={current_strength:.2f}; projected {projected_engine or 'NONE'} strength={projected_strength:.2f}; required={required:.2f}",
                "fresh partial Bonds do not justify dismantling an already realized power engine",
            ),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._bond_power_engine_retention_installed = True
