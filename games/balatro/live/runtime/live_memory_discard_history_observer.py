from __future__ import annotations

from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import (
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
    """Return planner-relevant public checkpoint identity without UI geometry."""
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
    """Expose public controller fields without a duplicate blocking quiet gate.

    Besides exact discard usage, Cerulean Bell's currently forced hand card is a
    public controller constraint stored on ``card.ability.forced_selection``.

    Native readiness remains authoritative in the base supervisor observer. The
    dedicated pack-to-SHOP Joker visual-settle barrier also remains authoritative
    for the one transition where card geometry is evidence that an asynchronous
    callback is still completing.

    General semantic checkpoint settling belongs to
    ``LiveMemoryInjectedAutonomousLoop._wait_for_stable_checkpoint``. That layer
    already prefers two semantically equal snapshots, has a bounded two-second
    soft window for legitimate animation/state churn, and is followed by the
    runner's mandatory stale-state guard before execution. A second blocking quiet
    loop inside each ``observe()`` call prevents that outer bounded policy from
    ever taking effect and can make an actionable SHOP appear hung before D14 is
    even entered. The production observer therefore returns immediately from the
    inherited general quiet hook once native readiness/post-pack settlement has
    completed.
    """

    def _wait_for_full_state_quiet(self, snapshot):
        """Delegate semantic stability to the bounded autonomous-loop authority."""
        return snapshot

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
