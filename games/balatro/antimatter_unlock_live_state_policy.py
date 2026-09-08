from __future__ import annotations

"""Expose only Antimatter's public profile unlock state to Balatro policy.

Blank Voucher redemption is meaningful progression only while Antimatter remains
locked.  Balatro already materializes that unlock state on the public ``v_antimatter``
center after loading the active profile.  This adapter exposes only that boolean;
it does not read RNG state, future shops, or unrelated profile/collection data.
"""

from games.balatro.live.runtime import live_memory_observer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def install_antimatter_unlock_live_state_policy() -> None:
    if getattr(DefaultBalatroStateTranslator, "_antimatter_unlock_live_state_installed", False):
        return

    original_snapshot_payload = live_memory_observer.snapshot_payload_from_live_memory
    original_translate = DefaultBalatroStateTranslator.translate
    original_state_init = BalatroState.__init__
    original_state_copy = BalatroState.copy

    def state_init(self):
        original_state_init(self)
        self.antimatter_unlock_observed = False
        self.antimatter_unlocked = False

    def state_copy(self):
        copied = original_state_copy(self)
        copied.antimatter_unlock_observed = bool(
            getattr(self, "antimatter_unlock_observed", False)
        )
        copied.antimatter_unlocked = bool(getattr(self, "antimatter_unlocked", False))
        return copied

    def snapshot_payload_from_live_memory(decoder, root):
        payload, phase, state_complete = original_snapshot_payload(decoder, root)
        centers = live_memory_observer._table_fields(decoder, root.get("P_CENTERS"))
        antimatter = live_memory_observer._table_fields(decoder, centers.get("v_antimatter"))
        observed = bool(antimatter)
        payload["antimatter_unlock_observed"] = observed
        payload["antimatter_unlocked"] = (
            live_memory_observer._boolean(antimatter.get("unlocked"), False)
            if observed
            else False
        )
        return payload, phase, state_complete

    def translate(self, snapshot):
        state = original_translate(self, snapshot)
        payload = snapshot.payload
        state.antimatter_unlock_observed = bool(
            payload.get("antimatter_unlock_observed", False)
        )
        state.antimatter_unlocked = bool(payload.get("antimatter_unlocked", False))
        return state

    BalatroState.__init__ = state_init
    BalatroState.copy = state_copy
    live_memory_observer.snapshot_payload_from_live_memory = snapshot_payload_from_live_memory
    DefaultBalatroStateTranslator.translate = translate
    DefaultBalatroStateTranslator._antimatter_unlock_live_state_installed = True
