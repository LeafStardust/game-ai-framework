from __future__ import annotations

"""Compatibility shim for native round-reset resource observation.

The canonical live observer exposes ``G.GAME.round_resets.discards`` and the state
translator hydrates native ``BalatroState`` fields. Production startup no longer
needs to monkeypatch observer, translator, or state copy behavior.
"""


def install_round_resource_live_state_policy() -> None:
    """Retained for compatibility; native live-state ownership requires no install."""
    return
