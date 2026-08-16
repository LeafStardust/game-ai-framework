from __future__ import annotations

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import _integer, _table_fields
from .live_memory_supervisor_observer import SupervisorLiveMemoryBalatroObserver


def public_discard_history(decoder, root) -> tuple[int, int] | None:
    """Return ``(total, used)`` from Balatro's public current-round counters."""
    game = _table_fields(decoder, root.get("GAME"))
    current_round = _table_fields(decoder, game.get("current_round"))
    round_resets = _table_fields(decoder, game.get("round_resets"))
    reset_discards = round_resets.get("discards")
    if reset_discards is None:
        return None

    left = max(0, _integer(current_round.get("discards_left"), 0))
    total = max(0, _integer(reset_discards, left))
    return total, max(0, total - left)


class DiscardHistorySupervisorLiveMemoryBalatroObserver(
    SupervisorLiveMemoryBalatroObserver
):
    """Add exact public current-round discard usage to supervisor snapshots.

    Balatro keeps the round reset allowance in ``G.GAME.round_resets.discards``
    and the current allowance in ``G.GAME.current_round.discards_left``. Their
    difference is enough to identify the first discard without exposing hidden
    RNG state or relying on controller-local action history.
    """

    def _observe_public(self):
        snapshot = super()._observe_public()
        decoder, _, root = self._root()
        history = public_discard_history(decoder, root)
        if history is None:
            return snapshot
        total, used = history

        payload = dict(snapshot.payload)
        round_payload = dict(payload.get("round") or {})
        round_payload["discards_total"] = total
        round_payload["discards_used"] = used
        payload["round"] = round_payload
        return LiveBalatroSnapshot(
            sequence=snapshot.sequence,
            phase=snapshot.phase,
            state_complete=snapshot.state_complete,
            payload=payload,
        )
