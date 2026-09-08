from __future__ import annotations

"""Temporary compatibility for lightweight snapshots lacking runtime mechanics.

Runtime components should expose ``mechanics`` directly. This shim exists only for
legacy string/test snapshots and should be removed at the Bond cleanup gate once
all public snapshots carry canonical descriptors.
"""

from typing import Any

from games.balatro.mechanics import component_has_mechanic


NO_FACE_PLAY_SCALING = "no_face_play_scaling"
HELD_LOWEST_RANK_PAYOFF = "held_lowest_rank_payoff"
HELD_BLACK_STATE_XMULT = "held_black_state_xmult"


def _normalize_name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


_SNAPSHOT_MECHANICS: dict[str, frozenset[str]] = {
    "ridethebus": frozenset({NO_FACE_PLAY_SCALING}),
    "ridethebusjoker": frozenset({NO_FACE_PLAY_SCALING}),
    "raisedfist": frozenset({HELD_LOWEST_RANK_PAYOFF}),
    "raisedfistjoker": frozenset({HELD_LOWEST_RANK_PAYOFF}),
    "blackboard": frozenset({HELD_BLACK_STATE_XMULT}),
    "blackboardjoker": frozenset({HELD_BLACK_STATE_XMULT}),
}


def component_has_public_mechanic(component: Any, mechanic: str) -> bool:
    """Query native canonical mechanics, then migration-only snapshot aliases."""
    if component_has_mechanic(component, mechanic):
        return True
    return mechanic in _SNAPSHOT_MECHANICS.get(_normalize_name(component), frozenset())
