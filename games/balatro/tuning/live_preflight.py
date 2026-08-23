from __future__ import annotations

"""Fail-closed preflight for authoritative live Bond tuning.

This module is offline-only. It validates that a live trial starts from the exact
public boundary the tuner expects before Optuna is allowed to spend a real run.
"""

from dataclasses import dataclass
from typing import Callable

from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.runtime.live_memory_achievement_guard import achievement_gate_state
from games.balatro.live.runtime.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
)


@dataclass(frozen=True)
class LiveTuningPreflight:
    phase: str
    state_complete: bool
    deck: str
    stake: str
    ante: int
    bridge_version: str
    bridge_revision: str
    achievement_gate: str


ObserverFactory = Callable[[], object]
BridgeFactory = Callable[[], object]


def _identity(payload: dict, key: str, fallback: str) -> str:
    return str(payload.get(key, payload.get(fallback, "")) or "").upper()


def validate_live_tuning_preflight(
    *,
    expected_deck: str,
    expected_stake: str,
    observer_factory: ObserverFactory = SupervisorLiveMemoryBalatroObserver,
    bridge_factory: BridgeFactory = FirstPartyBalatroBridge,
) -> LiveTuningPreflight:
    """Validate a fresh authoritative run boundary without mutating gameplay."""

    expected_deck = str(expected_deck).upper().strip()
    expected_stake = str(expected_stake).upper().strip()
    if not expected_deck or not expected_stake:
        raise ValueError("expected deck/stake identity is required")

    with observer_factory() as observer:
        snapshot = observer.observe()

    phase = str(snapshot.phase)
    if phase != "BLIND_SELECT":
        raise RuntimeError(
            "live tuning must start from fresh BLIND_SELECT; "
            f"observed {phase}"
        )
    if not bool(snapshot.state_complete):
        raise RuntimeError("live tuning start checkpoint is not settled")

    payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
    deck = _identity(payload, "deck", "deck_name")
    stake = _identity(payload, "stake", "stake_name")
    ante = int(payload.get("ante_num", payload.get("ante", 0)) or 0)
    if deck != expected_deck or stake != expected_stake:
        raise RuntimeError(
            "live tuning deck/stake mismatch: "
            f"observed {deck or 'UNKNOWN'}/{stake or 'UNKNOWN'}, "
            f"expected {expected_deck}/{expected_stake}"
        )
    # A reset boundary for an independent trial must be the opening Ante 1 blind
    # selection. Starting later would contaminate a candidate with prior policy.
    if ante != 1:
        raise RuntimeError(
            f"live tuning requires fresh Ante 1 boundary; observed Ante {ante}"
        )

    bridge = bridge_factory()
    status = bridge.status()
    bridge_version = str(status.get("bridge", ""))
    if bridge_version != "1":
        raise RuntimeError(
            "live tuning requires compatible first-party bridge protocol 1; "
            f"observed {bridge_version or 'MISSING'}"
        )
    gate, disabled = achievement_gate_state(status.get("achievement_gate"))
    if disabled is True:
        raise RuntimeError("Balatro achievement-disable gate is active")
    if disabled is None:
        raise RuntimeError(
            f"Balatro achievement-disable gate is unavailable/unexpected: {gate}"
        )

    return LiveTuningPreflight(
        phase=phase,
        state_complete=True,
        deck=deck,
        stake=stake,
        ante=ante,
        bridge_version=bridge_version,
        bridge_revision=str(status.get("bridge_revision", "unknown")),
        achievement_gate=gate,
    )
