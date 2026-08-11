from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from games.balatro.actions import (
    BUY_AND_USE_CONSUMABLE,
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    DISCARD_CARDS,
    END_ROUND,
    END_SHOP,
    PLAY_CARDS,
    REFRESH_SHOP,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_hand_executor import LiveMemoryHandExecutor
from .live_memory_observer import LiveMemoryBalatroObserver
from .live_pack_card_mouse import LivePackCardMouseExecutor
from .live_pack_skip_mouse import LivePackSkipMouseExecutor
from .live_round_eval_mouse import LiveMemoryRoundEvalMouseExecutor
from .live_shop_next_round_mouse import LiveMemoryShopNextRoundMouseExecutor
from .live_shop_purchase_mouse import LiveMemoryShopPurchaseMouseExecutor
from .live_shop_reroll_mouse import LiveMemoryShopRerollMouseExecutor
from .live_shop_special_action_mouse import LiveMemoryShopSpecialActionMouseExecutor
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


class UnsupportedExternalLiveAction(RuntimeError):
    pass


class ExternalLiveActionPostconditionError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveExternalActionResult:
    action: BalatroAction
    before: LiveBalatroSnapshot
    after: LiveBalatroSnapshot
    details: Any = None


def _target_index(target) -> int:
    if isinstance(target, bool):
        raise UnsupportedExternalLiveAction("boolean is not a valid live action target index")
    if isinstance(target, int):
        index = target
    elif isinstance(target, dict):
        if "area_index" not in target:
            raise UnsupportedExternalLiveAction("live action target has no area_index")
        index = int(target["area_index"])
    else:
        value = getattr(target, "area_index", None)
        if value is None:
            raise UnsupportedExternalLiveAction("live action target has no area_index")
        index = int(value)
    if index < 0:
        raise UnsupportedExternalLiveAction("live action target index cannot be negative")
    return index


def _same_live_item(card: dict, *, live_id, label) -> bool:
    if live_id is not None:
        return card.get("live_id") == live_id
    name = card.get("label") or card.get("ability_name") or card.get("center")
    return name == label


def _area_contains(snapshot: LiveBalatroSnapshot, payload_name: str, *, live_id, label) -> bool:
    cards = list((snapshot.payload.get(payload_name) or {}).get("cards") or [])
    return any(_same_live_item(card, live_id=live_id, label=label) for card in cards)


class LiveMemoryActionDispatcher:
    """Route framework ``BalatroAction`` objects to verified external mouse primitives.

    This is deliberately separate from ``DefaultBalatroActionExecutor``, whose job
    is to serialize commands for the injected BalatroBot bridge. This dispatcher
    performs normal desktop mouse input against the read-only process-memory state.
    """

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        *,
        mouse: BalatroMouseController | None = None,
        window_locator: BalatroWindowLocator | None = None,
        timeout: float = 12.0,
        poll_interval: float = 0.05,
        hand_executor=None,
        buy_executor=None,
        buy_and_use_executor=None,
        special_executor=None,
        reroll_executor=None,
        next_round_executor=None,
        cash_out_executor=None,
        pack_card_executor=None,
        pack_skip_executor=None,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.mouse = mouse or BalatroMouseController(armed=True, hover_delay=0.0)
        self.window_locator = window_locator or BalatroWindowLocator()
        self.timeout = max(0.0, float(timeout))
        self.poll_interval = max(0.0, float(poll_interval))
        self._owns_observer = observer is None

        self.hand_executor = hand_executor or LiveMemoryHandExecutor(
            self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        self.buy_executor = buy_executor or LiveMemoryShopPurchaseMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
            action="buy",
        )
        self.buy_and_use_executor = buy_and_use_executor or LiveMemoryShopPurchaseMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
            action="buy_and_use",
        )
        self.special_executor = special_executor or LiveMemoryShopSpecialActionMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        self.reroll_executor = reroll_executor or LiveMemoryShopRerollMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        self.next_round_executor = next_round_executor or LiveMemoryShopNextRoundMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        self.cash_out_executor = cash_out_executor or LiveMemoryRoundEvalMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        self.pack_card_executor = pack_card_executor or LivePackCardMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )
        self.pack_skip_executor = pack_skip_executor or LivePackSkipMouseExecutor(
            observer=self.observer,
            mouse=self.mouse,
            window_locator=self.window_locator,
        )

    def _wait(self, before: LiveBalatroSnapshot, predicate: Callable[[LiveBalatroSnapshot], bool], label: str):
        deadline = time.monotonic() + self.timeout
        last = before
        while True:
            current = self.observer.observe()
            last = current
            if predicate(current):
                return current
            if time.monotonic() >= deadline:
                raise ExternalLiveActionPostconditionError(
                    f"timed out verifying {label}; phase={last.phase}, sequence={last.sequence}"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)

    def _wait_purchase(self, before, item, *, require_shop: bool):
        before_money = before.payload.get("money")
        expected_money = (
            float(before_money) - float(item.cost)
            if isinstance(before_money, (int, float))
            else None
        )

        def complete(after):
            if after.sequence <= before.sequence:
                return False
            if require_shop and after.phase != "SHOP":
                return False
            money = after.payload.get("money")
            if expected_money is not None and (
                not isinstance(money, (int, float)) or float(money) != expected_money
            ):
                return False
            return not _area_contains(
                after,
                "shop_jokers",
                live_id=item.live_id,
                label=item.label,
            )

        return self._wait(before, complete, "shop purchase")

    def _wait_special(self, before, item, payload_name: str, *, require_shop: bool):
        before_money = before.payload.get("money")
        expected_money = (
            float(before_money) - float(item.cost)
            if isinstance(before_money, (int, float))
            else None
        )

        def complete(after):
            if after.sequence <= before.sequence:
                return False
            if require_shop and after.phase != "SHOP":
                return False
            money = after.payload.get("money")
            if expected_money is not None and (
                not isinstance(money, (int, float)) or float(money) != expected_money
            ):
                return False
            return not _area_contains(
                after,
                payload_name,
                live_id=item.live_id,
                label=item.label,
            )

        return self._wait(before, complete, payload_name)

    def dispatch(
        self,
        action: BalatroAction,
        *,
        state=None,
        snapshot: LiveBalatroSnapshot | None = None,
    ) -> LiveExternalActionResult:
        name = action.name
        before = snapshot or self.observer.observe()

        if name in {PLAY_CARDS, DISCARD_CARDS}:
            if state is None:
                raise UnsupportedExternalLiveAction(
                    f"{name} requires the translated BalatroState used to select the cards"
                )
            details = self.hand_executor.dispatch(action, state, before)
            after = self._wait(
                before,
                lambda value: value.sequence > before.sequence,
                name,
            )
            return LiveExternalActionResult(action, before, after, details)

        if name in {BUY_JOKER, BUY_CONSUMABLE}:
            index = _target_index(action.target)
            actual_before, item, verified = self.buy_executor.dispatch(index)
            after = self._wait_purchase(actual_before, item, require_shop=True)
            return LiveExternalActionResult(
                action,
                actual_before,
                after,
                {"item": item, "control": verified},
            )

        if name == BUY_AND_USE_CONSUMABLE:
            index = _target_index(action.target)
            actual_before, item, verified = self.buy_and_use_executor.dispatch(index)
            after = self._wait_purchase(actual_before, item, require_shop=False)
            return LiveExternalActionResult(
                action,
                actual_before,
                after,
                {"item": item, "control": verified},
            )

        if name == BUY_VOUCHER:
            index = _target_index(action.target)
            actual_before, item, target = self.special_executor.dispatch("vouchers", index)
            after = self._wait_special(
                actual_before,
                item,
                "shop_vouchers",
                require_shop=True,
            )
            return LiveExternalActionResult(
                action, actual_before, after, {"item": item, "control": target}
            )

        if name == BUY_BOOSTER:
            index = _target_index(action.target)
            actual_before, item, target = self.special_executor.dispatch("boosters", index)
            after = self._wait_special(
                actual_before,
                item,
                "shop_boosters",
                require_shop=False,
            )
            return LiveExternalActionResult(
                action, actual_before, after, {"item": item, "control": target}
            )

        if name == REFRESH_SHOP:
            actual_before, target = self.reroll_executor.dispatch()
            after = self._wait(
                actual_before,
                lambda value: value.sequence > actual_before.sequence,
                "shop reroll",
            )
            return LiveExternalActionResult(action, actual_before, after, target)

        if name == END_SHOP:
            actual_before, target = self.next_round_executor.dispatch()
            after = self._wait(
                actual_before,
                lambda value: value.phase != "SHOP",
                "next round",
            )
            return LiveExternalActionResult(action, actual_before, after, target)

        if name == END_ROUND:
            actual_before, target = self.cash_out_executor.dispatch()
            after = self._wait(
                actual_before,
                lambda value: value.phase != actual_before.phase,
                "cash out",
            )
            return LiveExternalActionResult(action, actual_before, after, target)

        if name == SELECT_PACK_CARD:
            index = _target_index(action.target)
            details = self.pack_card_executor.dispatch(index)
            after = self.observer.observe()
            return LiveExternalActionResult(action, before, after, details)

        if name == SKIP_BOOSTER:
            _, _, details = self.pack_skip_executor.dispatch()
            after = self.observer.observe()
            return LiveExternalActionResult(action, before, after, details)

        raise UnsupportedExternalLiveAction(
            f"live external dispatcher cannot execute {name!r}"
        )

    def close(self) -> None:
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryActionDispatcher":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
