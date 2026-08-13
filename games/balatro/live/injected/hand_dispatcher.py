from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from games.balatro.actions import (
    DISCARD_CARDS,
    PLAY_CARDS,
    USE_CONSUMABLE,
    BalatroAction,
)
from games.balatro.live.protocol import LiveBalatroSnapshot

from .bridge import FirstPartyBalatroBridge


class UnsupportedInjectedHandAction(RuntimeError):
    pass


class InjectedHandActionPostconditionError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveInjectedActionResult:
    action: BalatroAction
    before: LiveBalatroSnapshot
    after: LiveBalatroSnapshot
    details: Any = None


SHOP_SAFE_HELD_CONSUMABLES = frozenset(
    {"The Hermit", "Temperance", "The Wheel of Fortune"}
)


def _round_resource(
    snapshot: LiveBalatroSnapshot,
    key: str,
) -> int | None:
    value = (snapshot.payload.get("round") or {}).get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _hand_action_complete(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
    action_name: str,
) -> bool:
    if after.sequence <= before.sequence:
        return False

    if action_name == PLAY_CARDS:
        # HAND_PLAYED and other scoring/animation phases are transient. A Play
        # checkpoint is authoritative only once Balatro has either returned to
        # SELECTING_HAND for the next decision, entered ROUND_EVAL because the
        # blind ended, or reached the terminal GAME_OVER state because the final
        # available hand failed to clear the blind.
        if after.phase in {"ROUND_EVAL", "GAME_OVER"}:
            return True
        if after.phase != "SELECTING_HAND":
            return False

        before_hands = _round_resource(before, "hands_left")
        after_hands = _round_resource(after, "hands_left")
        return (
            before_hands is not None
            and after_hands == before_hands - 1
        )

    if action_name == DISCARD_CARDS:
        before_discards = _round_resource(before, "discards_left")
        after_discards = _round_resource(after, "discards_left")
        return (
            after.phase == "SELECTING_HAND"
            and before_discards is not None
            and after_discards == before_discards - 1
        )

    return False


def _area_cards(snapshot: LiveBalatroSnapshot, name: str) -> list[dict]:
    area = snapshot.payload.get(name)
    if not isinstance(area, dict):
        return []
    cards = area.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, dict)]


def _consumable_use_complete(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
    *,
    before_count: int,
    consumed_live_id: object | None,
) -> bool:
    if (
        after.sequence <= before.sequence
        or after.phase != before.phase
        or not after.state_complete
    ):
        return False

    after_cards = _area_cards(after, "consumables")
    if consumed_live_id is not None:
        return all(card.get("live_id") != consumed_live_id for card in after_cards)
    return len(after_cards) == before_count - 1


def _action_indices(
    state,
    action: BalatroAction,
) -> tuple[int, ...]:
    selected_object_ids = {id(card) for card in action.cards}
    selected_live_ids = {
        getattr(card, "live_id", None)
        for card in action.cards
        if getattr(card, "live_id", None) is not None
    }
    indices = tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_object_ids
        or (
            getattr(card, "live_id", None) is not None
            and getattr(card, "live_id", None) in selected_live_ids
        )
    )
    if len(indices) != len(action.cards):
        raise UnsupportedInjectedHandAction(
            "hand action cards no longer map one-to-one to the "
            "authoritative live hand"
        )
    return indices


def _consumable_index(state, action: BalatroAction) -> int:
    target = action.target
    if target is None:
        raise UnsupportedInjectedHandAction(
            "USE_CONSUMABLE requires the held consumable as action.target"
        )

    target_live_id = getattr(target, "live_id", None)
    matches = [
        index
        for index, consumable in enumerate(getattr(state, "consumables", ()))
        if consumable is target
        or (
            target_live_id is not None
            and getattr(consumable, "live_id", None) == target_live_id
        )
    ]
    if len(matches) != 1:
        raise UnsupportedInjectedHandAction(
            "USE_CONSUMABLE target no longer maps one-to-one to the "
            "authoritative held consumables"
        )
    return matches[0]


class LiveMemoryInjectedHandDispatcher:
    """Execute hand actions and validated held-consumable uses via the bridge.

    Commands use current zero-based positions and Balatro's own callbacks. The
    process-memory observer remains read-only and independently verifies the
    resulting semantic checkpoint. SHOP use is limited to explicitly validated
    no-hand-target consumables; targeted use remains SELECTING_HAND-only.
    """

    def __init__(
        self,
        observer,
        *,
        bridge: FirstPartyBalatroBridge | None = None,
        timeout: float = 12.0,
        poll_interval: float = 0.05,
    ) -> None:
        self.observer = observer
        self.bridge = bridge or FirstPartyBalatroBridge()
        self.timeout = max(0.0, float(timeout))
        self.poll_interval = max(0.0, float(poll_interval))

    def dispatch(
        self,
        action: BalatroAction,
        *,
        state,
        snapshot: LiveBalatroSnapshot,
    ) -> LiveInjectedActionResult:
        if action.name not in {PLAY_CARDS, DISCARD_CARDS, USE_CONSUMABLE}:
            raise UnsupportedInjectedHandAction(
                "first-party injected hand bridge does not support "
                f"{action.name}"
            )

        if action.name == USE_CONSUMABLE:
            if snapshot.phase not in {"SELECTING_HAND", "SHOP"}:
                raise UnsupportedInjectedHandAction(
                    "consumable use requires SELECTING_HAND or validated SHOP use, "
                    f"observed {snapshot.phase}"
                )
        elif snapshot.phase != "SELECTING_HAND":
            raise UnsupportedInjectedHandAction(
                "hand action requires SELECTING_HAND, "
                f"observed {snapshot.phase}"
            )

        indices = _action_indices(state, action)

        if action.name == USE_CONSUMABLE:
            if snapshot.phase == "SHOP":
                if indices:
                    raise UnsupportedInjectedHandAction(
                        "SHOP held-consumable use cannot include hand targets"
                    )
                name = str(getattr(action.target, "name", ""))
                if name not in SHOP_SAFE_HELD_CONSUMABLES:
                    raise UnsupportedInjectedHandAction(
                        "SHOP held-consumable use is not validated for "
                        f"{name or 'unknown consumable'}"
                    )

            consumable_index = _consumable_index(state, action)
            before_cards = _area_cards(snapshot, "consumables")
            if consumable_index >= len(before_cards):
                raise UnsupportedInjectedHandAction(
                    "held consumable index is out of range for the live snapshot"
                )
            consumed_live_id = before_cards[consumable_index].get("live_id")
            self.bridge.use_consumable(consumable_index, indices)
            after = self._wait_consumable(
                snapshot,
                before_count=len(before_cards),
                consumed_live_id=consumed_live_id,
            )
            return LiveInjectedActionResult(
                action=action,
                before=snapshot,
                after=after,
                details={
                    "consumable_index": consumable_index,
                    "target_indices": indices,
                    "consumed_live_id": consumed_live_id,
                },
            )

        if action.name == PLAY_CARDS:
            self.bridge.play(indices)
        else:
            self.bridge.discard(indices)

        after = self._wait_hand(snapshot, action.name)
        return LiveInjectedActionResult(
            action=action,
            before=snapshot,
            after=after,
            details=indices,
        )

    def _wait_hand(
        self,
        before: LiveBalatroSnapshot,
        action_name: str,
    ) -> LiveBalatroSnapshot:
        deadline = time.monotonic() + self.timeout
        last = before
        while True:
            current = self.observer.observe()
            last = current
            if _hand_action_complete(before, current, action_name):
                return current
            if time.monotonic() >= deadline:
                raise InjectedHandActionPostconditionError(
                    "timed out verifying injected hand action; "
                    f"phase={last.phase}, sequence={last.sequence}"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)

    def _wait_consumable(
        self,
        before: LiveBalatroSnapshot,
        *,
        before_count: int,
        consumed_live_id: object | None,
    ) -> LiveBalatroSnapshot:
        deadline = time.monotonic() + self.timeout
        last = before
        while True:
            current = self.observer.observe()
            last = current
            if _consumable_use_complete(
                before,
                current,
                before_count=before_count,
                consumed_live_id=consumed_live_id,
            ):
                return current
            if time.monotonic() >= deadline:
                raise InjectedHandActionPostconditionError(
                    "timed out verifying injected consumable use; "
                    f"phase={last.phase}, sequence={last.sequence}"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)
