from __future__ import annotations

"""Expose Ectoplasm's deterministic escalating hand-size cost.

Balatro stores the next Ectoplasm hand-size reduction in ``G.GAME.ecto_minus``.
The value defaults to 1 before the first use and increments after every use. This
is ordinary public run history: a player can know how many Ectoplasms were used,
and the field contains no RNG or future outcome information.

Keep the correction narrow. The observer exposes only this counter and the state
translator copies it into ``BalatroState.ectoplasm_hand_size_penalty``. Valuation
remains a separate policy concern.
"""

from games.balatro.live.runtime import live_memory_observer
from games.balatro.live.translator import DefaultBalatroStateTranslator


def install_ectoplasm_live_state_policy() -> None:
    if getattr(DefaultBalatroStateTranslator, "_ectoplasm_live_state_installed", False):
        return

    original_snapshot_payload = live_memory_observer.snapshot_payload_from_live_memory
    original_translate = DefaultBalatroStateTranslator.translate

    def snapshot_payload_from_live_memory(decoder, root):
        payload, phase, state_complete = original_snapshot_payload(decoder, root)
        game = live_memory_observer._table_fields(decoder, root.get("GAME"))
        penalty = live_memory_observer._integer(game.get("ecto_minus"), 1)
        payload["ectoplasm_hand_size_penalty"] = max(1, int(penalty))
        return payload, phase, state_complete

    def translate(self, snapshot):
        state = original_translate(self, snapshot)
        raw_penalty = snapshot.payload.get("ectoplasm_hand_size_penalty", 1)
        try:
            penalty = int(raw_penalty)
        except (TypeError, ValueError):
            penalty = 1
        state.ectoplasm_hand_size_penalty = max(1, penalty)
        return state

    live_memory_observer.snapshot_payload_from_live_memory = snapshot_payload_from_live_memory
    DefaultBalatroStateTranslator.translate = translate
    DefaultBalatroStateTranslator._ectoplasm_live_state_installed = True
