from __future__ import annotations

"""Expose public per-round reset resources needed by prospective shop scoring.

Balatro keeps the authoritative starting discard allowance in
``G.GAME.round_resets.discards``. In SHOP, ``current_round.discards_left`` is the
leftover amount from the blind that just ended and is therefore the wrong context
for prospective Banner scoring. The reset allowance is ordinary visible run state
(deck/voucher/Joker modifiers can change it); it contains no hidden RNG.

Keep the adapter narrow and preserve the observed value through ``BalatroState``
copy projections.
"""

from games.balatro.live.runtime import live_memory_observer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def install_round_resource_live_state_policy() -> None:
    if getattr(DefaultBalatroStateTranslator, "_round_resource_live_state_installed", False):
        return

    original_snapshot_payload = live_memory_observer.snapshot_payload_from_live_memory
    original_translate = DefaultBalatroStateTranslator.translate
    original_state_init = BalatroState.__init__
    original_state_copy = BalatroState.copy

    def state_init(self):
        original_state_init(self)
        self.round_reset_discards_observed = False
        self.round_reset_discards = 0

    def state_copy(self):
        copied = original_state_copy(self)
        copied.round_reset_discards_observed = bool(
            getattr(self, "round_reset_discards_observed", False)
        )
        copied.round_reset_discards = max(
            0,
            int(getattr(self, "round_reset_discards", 0) or 0),
        )
        return copied

    def snapshot_payload_from_live_memory(decoder, root):
        payload, phase, state_complete = original_snapshot_payload(decoder, root)
        game = live_memory_observer._table_fields(decoder, root.get("GAME"))
        round_resets = live_memory_observer._table_fields(decoder, game.get("round_resets"))
        raw_discards = live_memory_observer._number(round_resets.get("discards"))
        payload["round_reset_discards_observed"] = raw_discards is not None
        if raw_discards is not None:
            payload["round_reset_discards"] = max(0, int(raw_discards))
        return payload, phase, state_complete

    def translate(self, snapshot):
        state = original_translate(self, snapshot)
        payload = snapshot.payload
        state.round_reset_discards_observed = bool(
            payload.get("round_reset_discards_observed", False)
        )
        try:
            value = int(payload.get("round_reset_discards", 0) or 0)
        except (TypeError, ValueError):
            value = 0
        state.round_reset_discards = max(0, value)
        return state

    BalatroState.__init__ = state_init
    BalatroState.copy = state_copy
    live_memory_observer.snapshot_payload_from_live_memory = snapshot_payload_from_live_memory
    DefaultBalatroStateTranslator.translate = translate
    DefaultBalatroStateTranslator._round_resource_live_state_installed = True
