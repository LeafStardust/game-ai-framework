from __future__ import annotations

import time
from typing import Callable

from games.balatro.actions import (
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

from .bridge import FirstPartyBalatroBridge
from .hand_dispatcher import (
    LiveInjectedActionResult,
    LiveMemoryInjectedHandDispatcher,
)


class UnsupportedInjectedAction(RuntimeError):
    pass


class InjectedActionPostconditionError(RuntimeError):
    pass


def _target_index(target) -> int:
    if isinstance(target, bool):
        raise UnsupportedInjectedAction(
            "boolean is not a valid live action target index"
        )
    if isinstance(target, int):
        index = target
    elif isinstance(target, dict):
        if "area_index" not in target:
            raise UnsupportedInjectedAction(
                "live action target has no area_index"
            )
        index = int(target["area_index"])
    else:
        value = getattr(target, "area_index", None)
        if value is None:
            raise UnsupportedInjectedAction(
                "live action target has no area_index"
            )
        index = int(value)
    if index < 0:
        raise UnsupportedInjectedAction(
            "live action target index cannot be negative"
        )
    return index


def _area(snapshot: LiveBalatroSnapshot, name: str) -> dict:
    value = snapshot.payload.get(name)
    return value if isinstance(value, dict) else {}


def _area_cards(snapshot: LiveBalatroSnapshot, name: str) -> list[dict]:
    cards = _area(snapshot, name).get("cards")
    return list(cards) if isinstance(cards, list) else []


def _area_item(
    snapshot: LiveBalatroSnapshot,
    name: str,
    index: int,
) -> dict:
    cards = _area_cards(snapshot, name)
    if index >= len(cards):
        raise UnsupportedInjectedAction(
            f"{name} index {index} is out of range for {len(cards)} items"
        )
    value = cards[index]
    if not isinstance(value, dict):
        raise UnsupportedInjectedAction(
            f"{name} index {index} is not a public item record"
        )
    return value


def _money(snapshot: LiveBalatroSnapshot) -> float | None:
    value = snapshot.payload.get("money")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _cost(item: dict) -> float | None:
    value = item.get("cost")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _purchase_money_matches(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
    item: dict,
) -> bool:
    before_money = _money(before)
    after_money = _money(after)
    cost = _cost(item)
    if before_money is None or after_money is None or cost is None:
        return True
    return after_money == before_money - cost


def _shop_signature(snapshot: LiveBalatroSnapshot) -> tuple[tuple, ...]:
    result: list[tuple] = []
    for area_name in ("shop_jokers", "shop_boosters", "shop_vouchers"):
        for index, item in enumerate(_area_cards(snapshot, area_name)):
            result.append(
                (
                    area_name,
                    index,
                    item.get("live_id"),
                    item.get("center"),
                    item.get("label"),
                    item.get("cost"),
                )
            )
    return tuple(result)


def _reroll_complete(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
) -> bool:
    if (
        after.sequence <= before.sequence
        or after.phase != "SHOP"
        or not after.state_complete
    ):
        return False

    before_money = _money(before)
    after_money = _money(after)
    money_decreased = (
        before_money is not None
        and after_money is not None
        and after_money < before_money
    )
    inventory_changed = _shop_signature(after) != _shop_signature(before)
    return money_decreased or inventory_changed


def _is_pack_phase(phase: str) -> bool:
    return str(phase).endswith("_PACK")


class LiveMemoryInjectedActionDispatcher:
    """Execute supported Balatro actions through the first-party Lua bridge.

    The bridge invokes Balatro's ordinary in-process callbacks. This dispatcher
    never writes gameplay memory; the read-only live-memory observer supplies
    independent semantic postconditions after every command.
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

    def _wait(
        self,
        before: LiveBalatroSnapshot,
        predicate: Callable[[LiveBalatroSnapshot], bool],
        label: str,
    ) -> LiveBalatroSnapshot:
        deadline = time.monotonic() + self.timeout
        last = before
        while True:
            current = self.observer.observe()
            last = current
            if predicate(current):
                return current
            if time.monotonic() >= deadline:
                raise InjectedActionPostconditionError(
                    f"timed out verifying injected {label}; "
                    f"phase={last.phase}, sequence={last.sequence}"
                )
            if self.poll_interval:
                time.sleep(self.poll_interval)

    def dispatch(
        self,
        action: BalatroAction,
        *,
        state=None,
        snapshot: LiveBalatroSnapshot | None = None,
    ) -> LiveInjectedActionResult:
        before = snapshot or self.observer.observe()
        name = action.name

        if name in {PLAY_CARDS, DISCARD_CARDS}:
            if state is None:
                raise UnsupportedInjectedAction(
                    f"{name} requires the translated state used to select cards"
                )
            return LiveMemoryInjectedHandDispatcher(
                self.observer,
                bridge=self.bridge,
                timeout=self.timeout,
                poll_interval=self.poll_interval,
            ).dispatch(action, state=state, snapshot=before)

        if name == END_ROUND:
            if before.phase != "ROUND_EVAL":
                raise UnsupportedInjectedAction(
                    f"END_ROUND requires ROUND_EVAL, observed {before.phase}"
                )
            self.bridge.cash_out()
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.phase == "SHOP"
                    and value.state_complete
                ),
                "cash out",
            )
            return LiveInjectedActionResult(action, before, after)

        if name == END_SHOP:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"END_SHOP requires SHOP, observed {before.phase}"
                )
            self.bridge.next_round()
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.phase == "BLIND_SELECT"
                    and value.state_complete
                ),
                "next round",
            )
            return LiveInjectedActionResult(action, before, after)

        if name == REFRESH_SHOP:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"REFRESH_SHOP requires SHOP, observed {before.phase}"
                )
            self.bridge.reroll_shop()
            after = self._wait(
                before,
                lambda value: _reroll_complete(before, value),
                "shop reroll",
            )
            return LiveInjectedActionResult(action, before, after)

        if name in {BUY_JOKER, BUY_CONSUMABLE}:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"{name} requires SHOP, observed {before.phase}"
                )
            index = _target_index(action.target)
            item = _area_item(before, "shop_jokers", index)
            before_count = len(_area_cards(before, "shop_jokers"))
            self.bridge.buy_shop_card(index)
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.phase == "SHOP"
                    and value.state_complete
                    and len(_area_cards(value, "shop_jokers"))
                    == before_count - 1
                    and _purchase_money_matches(before, value, item)
                ),
                "shop card purchase",
            )
            return LiveInjectedActionResult(
                action,
                before,
                after,
                {"area_index": index, "item": item},
            )

        if name == BUY_VOUCHER:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"BUY_VOUCHER requires SHOP, observed {before.phase}"
                )
            index = _target_index(action.target)
            item = _area_item(before, "shop_vouchers", index)
            before_count = len(_area_cards(before, "shop_vouchers"))
            self.bridge.buy_voucher(index)
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.phase == "SHOP"
                    and value.state_complete
                    and len(_area_cards(value, "shop_vouchers"))
                    == before_count - 1
                    and _purchase_money_matches(before, value, item)
                ),
                "voucher purchase",
            )
            return LiveInjectedActionResult(
                action,
                before,
                after,
                {"area_index": index, "item": item},
            )

        if name == BUY_BOOSTER:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"BUY_BOOSTER requires SHOP, observed {before.phase}"
                )
            index = _target_index(action.target)
            item = _area_item(before, "shop_boosters", index)
            self.bridge.buy_booster(index)
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and _is_pack_phase(value.phase)
                    and value.state_complete
                    and _purchase_money_matches(before, value, item)
                ),
                "booster purchase",
            )
            return LiveInjectedActionResult(
                action,
                before,
                after,
                {"area_index": index, "item": item},
            )

        if name == SELECT_PACK_CARD:
            if not _is_pack_phase(before.phase):
                raise UnsupportedInjectedAction(
                    f"SELECT_PACK_CARD requires a *_PACK phase, observed {before.phase}"
                )
            index = _target_index(action.target)
            self.bridge.select_pack_card(index)
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.state_complete
                    and (_is_pack_phase(value.phase) or value.phase == "SHOP")
                ),
                "pack selection",
            )
            return LiveInjectedActionResult(
                action,
                before,
                after,
                {"area_index": index},
            )

        if name == SKIP_BOOSTER:
            if not _is_pack_phase(before.phase):
                raise UnsupportedInjectedAction(
                    f"SKIP_BOOSTER requires a *_PACK phase, observed {before.phase}"
                )
            self.bridge.skip_booster()
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.phase == "SHOP"
                    and value.state_complete
                ),
                "pack skip",
            )
            return LiveInjectedActionResult(action, before, after)

        raise UnsupportedInjectedAction(
            f"first-party injected dispatcher cannot execute {name!r}"
        )
