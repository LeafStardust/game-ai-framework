from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.build_health import BuildHealthState
from games.balatro.live.bond_health import LiveBondHealthSnapshot, evaluate_live_build_health


class StrategyHealthMode(StrEnum):
    SURVIVE = "SURVIVE"
    REPAIR = "REPAIR"
    HOLD = "HOLD"
    REINFORCE = "REINFORCE"
    EXPLOIT = "EXPLOIT"


@dataclass(frozen=True)
class LiveStrategyHealth:
    mode: StrategyHealthMode
    snapshot: LiveBondHealthSnapshot
    developments: tuple
    composition: object
    strategy_authority: float
    rationale: tuple[str, ...]


def evaluate_live_strategy_health(state: Any, *, selected_plan: Any) -> LiveStrategyHealth:
    """Evaluate strategy authority from the exact plan D1 selected.

    This function is intentionally downstream of D1 plan selection. It cannot
    replace a safer action with a strategically attractive losing action. Its
    output is for strategy reinforcement, shop/pivot pressure, prescriptions and
    telemetry after survival evidence has been established.
    """
    developments, composition = evaluate_bond_composition(state)
    snapshot = evaluate_live_build_health(
        state,
        developments=developments,
        composition=composition,
        blind_plan=selected_plan,
    )

    health_state = snapshot.health.state
    if health_state == BuildHealthState.COLLAPSING:
        mode = StrategyHealthMode.SURVIVE
        authority = 0.0
        rationale = (
            "projected build ceiling/survival is inadequate",
            "suppress strategic greed and preserve immediate survival authority",
        )
    elif health_state == BuildHealthState.FRAGILE:
        mode = StrategyHealthMode.REPAIR
        authority = 0.20
        rationale = (
            "build can survive only with weak margin or reliability",
            "prefer immediate repair over expensive motif chasing or pivots",
        )
    elif health_state == BuildHealthState.STABLE:
        mode = StrategyHealthMode.HOLD
        authority = 0.50
        rationale = (
            "current build is adequate but not comfortably ahead",
            "maintain coherent Bonds while preserving scoring/economy runway",
        )
    elif health_state == BuildHealthState.STRONG:
        mode = StrategyHealthMode.REINFORCE
        authority = 0.75
        rationale = (
            "current build clears with healthy margin",
            "allow stronger Bond/motif reinforcement beneath survival constraints",
        )
    else:
        mode = StrategyHealthMode.EXPLOIT
        authority = 1.0
        rationale = (
            "current build has dominant projected health",
            "exploit mature composition and pursue efficient capstone reinforcement",
        )

    return LiveStrategyHealth(
        mode=mode,
        snapshot=snapshot,
        developments=developments,
        composition=composition,
        strategy_authority=authority,
        rationale=rationale,
    )
