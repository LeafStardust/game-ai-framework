from __future__ import annotations

from time import monotonic, sleep

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import (
    LiveMemoryObservationError,
    _array_table_values,
    _boolean,
    _integer,
    _table_fields,
)
from .live_memory_supervisor_observer import SupervisorLiveMemoryBalatroObserver


def _semantic_value(value):
    """Freeze public planner state while excluding presentation-only ``ui`` data."""
    if isinstance(value, dict):
        return tuple(
            (str(key), _semantic_value(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) != "ui"
        )
    if isinstance(value, list):
        return tuple(_semantic_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_semantic_value(item) for item in value)
    return value


def semantic_snapshot_key(snapshot) -> tuple:
    """Return the same planner-relevant checkpoint identity used by stale guards."""
    return (
        str(snapshot.phase),
        bool(snapshot.state_complete),
        _semantic_value(snapshot.payload),
    )


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


def public_forced_selection_flags(decoder, root) -> tuple[bool, ...] | None:
    """Return the public Cerulean Bell forced-selection bit for each hand card."""
    hand = _table_fields(decoder, root.get("hand"))
    raw_cards = _array_table_values(decoder, hand.get("cards"))
    if not raw_cards:
        return ()

    flags: list[bool] = []
    try:
        for _, address in raw_cards:
            card = decoder.string_fields(address)
            ability = _table_fields(decoder, card.get("ability"))
            flags.append(_boolean(ability.get("forced_selection"), False))
    except Exception:
        # Missing/unstable memory must not invent a forced card. Leave the base
        # snapshot untouched and let the translator/action layer fail open.
        return None
    return tuple(flags)


class DiscardHistorySupervisorLiveMemoryBalatroObserver(
    SupervisorLiveMemoryBalatroObserver
):
    """Expose public controller fields with semantic supervisor quiescence.

    Besides exact discard usage, Cerulean Bell's currently forced hand card is a
    public controller constraint stored on ``card.ability.forced_selection``.

    The production supervisor's general quiet barrier is semantic rather than
    presentation-geometric. Native readiness remains authoritative, and the base
    observer's dedicated pack-to-SHOP Joker visual-settle gate still handles the
    one transition where card geometry is itself evidence that a native callback
    is still completing. Ordinary card/shop hover and animation geometry must not
    block the planner for the full raw-sequence timeout.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_semantic_quiescent_key: tuple | None = None

    def _wait_for_full_state_quiet(self, snapshot):
        """Require semantic public state to stay quiet; ignore ``ui``-only churn."""
        key = semantic_snapshot_key(snapshot)
        if (
            snapshot.state_complete
            and self._last_semantic_quiescent_key is not None
            and key == self._last_semantic_quiescent_key
        ):
            return snapshot

        deadline = monotonic() + self.full_state_quiet_timeout_seconds
        last = snapshot
        last_key = key
        quiet_since = monotonic() if snapshot.state_complete else None

        while True:
            now = monotonic()
            if (
                quiet_since is not None
                and now - quiet_since >= self.full_state_quiet_seconds
            ):
                self._last_semantic_quiescent_key = last_key
                # Retain the inherited diagnostic/cache field for compatibility.
                # A later UI-only raw sequence may differ, but semantic key reuse
                # above remains authoritative for this production subclass.
                self._last_quiescent_sequence = int(last.sequence)
                return last

            if now >= deadline:
                raise LiveMemoryObservationError(
                    "Balatro semantic public state did not remain quiescent before "
                    "supervisor command readiness; "
                    f"phase={last.phase}, sequence={last.sequence}, "
                    f"complete={bool(last.state_complete)}"
                )

            if self.full_state_quiet_poll_seconds:
                sleep(self.full_state_quiet_poll_seconds)
            current = self._observe_public()
            current_key = semantic_snapshot_key(current)

            if current_key != last_key or not current.state_complete:
                last_key = current_key
                quiet_since = monotonic() if current.state_complete else None
            elif quiet_since is None and current.state_complete:
                quiet_since = monotonic()

            last = current

    def _observe_public(self):
        snapshot = super()._observe_public()
        decoder, _, root = self._root()
        payload = dict(snapshot.payload)
        changed = False

        history = public_discard_history(decoder, root)
        if history is not None:
            total, used = history
            round_payload = dict(payload.get("round") or {})
            round_payload["discards_total"] = total
            round_payload["discards_used"] = used
            payload["round"] = round_payload
            changed = True

        forced_flags = public_forced_selection_flags(decoder, root)
        hand_payload = payload.get("hand")
        if forced_flags is not None and isinstance(hand_payload, dict):
            raw_cards = hand_payload.get("cards")
            if isinstance(raw_cards, list) and len(raw_cards) == len(forced_flags):
                hand_copy = dict(hand_payload)
                cards_copy = []
                for card, forced in zip(raw_cards, forced_flags):
                    if isinstance(card, dict):
                        value = dict(card)
                        value["forced_selection"] = bool(forced)
                        cards_copy.append(value)
                    else:
                        cards_copy.append(card)
                hand_copy["cards"] = cards_copy
                payload["hand"] = hand_copy
                changed = True

        if not changed:
            return snapshot
        return LiveBalatroSnapshot(
            sequence=snapshot.sequence,
            phase=snapshot.phase,
            state_complete=snapshot.state_complete,
            payload=payload,
        )
