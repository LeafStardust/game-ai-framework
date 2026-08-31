from __future__ import annotations

"""Compatibility installer for legacy Joker-generation snapshot emission.

State ownership and translation are native. Until the canonical observer calls the
read-only live-state reader directly, this compatibility layer patches only snapshot
emission. It must not mutate ``BalatroState`` or the translator.
"""

from games.balatro.live.joker_generation_pool_state import observe_joker_generation_state
from games.balatro.live.runtime import live_memory_observer


def install_joker_generation_pool_live_state_policy() -> None:
    if getattr(live_memory_observer, "_joker_generation_pool_snapshot_installed", False):
        return

    original_snapshot_payload = live_memory_observer.snapshot_payload_from_live_memory

    def snapshot_payload_from_live_memory(decoder, root):
        payload, phase, state_complete = original_snapshot_payload(decoder, root)
        payload.update(observe_joker_generation_state(decoder, root, payload, phase))
        return payload, phase, state_complete

    live_memory_observer.snapshot_payload_from_live_memory = snapshot_payload_from_live_memory
    live_memory_observer._joker_generation_pool_snapshot_installed = True
