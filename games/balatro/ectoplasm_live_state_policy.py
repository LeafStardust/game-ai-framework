from __future__ import annotations

"""Compatibility shim for native Ectoplasm live-state observation.

The canonical live-memory observer now exposes ``G.GAME.ecto_minus`` directly and
``DefaultBalatroStateTranslator`` hydrates the existing
``BalatroState.ectoplasm_hand_size_penalty`` field. Production startup no longer
needs a late observer/translator mutation.
"""


def install_ectoplasm_live_state_policy() -> None:
    """Retained for compatibility; native live-state ownership requires no install."""
    return
