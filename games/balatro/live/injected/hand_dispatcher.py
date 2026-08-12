from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from games.balatro.actions import (
    DISCARD_CARDS,
    PLAY_CARDS,
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
        # SELECTING_HAND for the next decision or entered ROUND_EVAL because the
        # blind ended. This prevents the dispatcher from returning before score,
        # draw, Joker, and blind-resolution events have completed.
        if after.phase == "ROUND_EVAL":
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
            "D1 action cards no longer map one-to-one to the "
            "authoritative live hand"
        )
    return indices


class LiveMemoryInjectedHandDispatcher:
    """Execute Play/Discard through the repo-owned in-process Lua bridge.

    The command selects cards by current zero-based hand positions and invokes
    Balatro's own action callbacks. The process-memory observer remains read-only
    and independently verifies the resulting semantic checkpoint.
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
        if action.name not in {PLAY_CARDS, DISCARD_CARDS}:
            raise UnsupportedInjectedHandAction(
                "first-party injected hand bridge does not support "
                f"{action.name}"
            )
        if snapshot.phase != "SELECTING_HAND":
            raise UnsupportedInjectedHandAction(
                "hand action requires SELECTING_HAND, "
                f"observed {snapshot.phase}"
            )

        indices = _action_indices(state, action)
        if action.name == PLAY_CARDS:
            self.bridge.play(indices)
        else:
            self.bridge.discard(indices)

        after = self._wait(snapshot, action.name)
        return LiveInjectedActionResult(
            action=action,
            before=snapshot,
            after=after,
            details=indices,
        )

    def _wait(
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
