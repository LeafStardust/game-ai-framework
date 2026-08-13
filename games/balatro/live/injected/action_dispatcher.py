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
    SELECT_BLIND,
    SELECT_PACK_CARD,
    SELL_JOKER,
    SKIP_BOOSTER,
    USE_CONSUMABLE,
    BalatroAction,
)
from games.balatro.live.external.live_memory_pack_terms import (
    LivePackSelectionTerms,
    read_live_pack_selection_terms,
)
from games.balatro.live.external.live_memory_shop_terms import (
    LiveShopRerollTerms,
    read_live_shop_reroll_terms,
)
from games.balatro.live.protocol import LiveBalatroSnapshot

from .bridge import FirstPartyBalatroBridge
from .hand_dispatcher import (
    LiveInjectedActionResult,
    LiveMemoryInjectedHandDispatcher,
    _action_indices,
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
    before_terms: LiveShopRerollTerms,
    after_terms: LiveShopRerollTerms,
) -> bool:
    if (
        after.sequence <= before.sequence
        or after.phase != "SHOP"
        or not after.state_complete
        or _shop_signature(after) == _shop_signature(before)
    ):
        return False

    before_money = _money(before)
    after_money = _money(after)
    if before_money is None or after_money is None:
        return False

    if before_terms.free_rerolls > 0:
        return (
            after_money == before_money
            and after_terms.free_rerolls == before_terms.free_rerolls - 1
        )

    return after_money == before_money - before_terms.cost


def _is_pack_phase(phase: str) -> bool:
    return str(phase).endswith("_PACK")


def _pack_selection_complete(
    before: LiveBalatroSnapshot,
    after: LiveBalatroSnapshot,
    before_terms: LivePackSelectionTerms,
    after_terms: LivePackSelectionTerms | None,
    *,
    selected_address: int,
) -> bool:
    if after.sequence <= before.sequence or not after.state_complete:
        return False

    if before_terms.choices_remaining <= 1:
        return after.phase == "SHOP"

    if after.phase == "SHOP":
        return True
    if not _is_pack_phase(after.phase) or after_terms is None:
        return False

    return (
        after_terms.choices_remaining == before_terms.choices_remaining - 1
        and selected_address not in after_terms.choice_addresses
    )


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
        reroll_terms_reader: Callable[[], LiveShopRerollTerms] | None = None,
        pack_terms_reader: Callable[[], LivePackSelectionTerms] | None = None,
    ) -> None:
        self.observer = observer
        self.bridge = bridge or FirstPartyBalatroBridge()
        self.timeout = max(0.0, float(timeout))
        self.poll_interval = max(0.0, float(poll_interval))
        self.reroll_terms_reader = reroll_terms_reader or (
            lambda: read_live_shop_reroll_terms(self.observer)
        )
        self.pack_terms_reader = pack_terms_reader or (
            lambda: read_live_pack_selection_terms(self.observer)
        )

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

        if name in {PLAY_CARDS, DISCARD_CARDS, USE_CONSUMABLE}:
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

        if name == SELECT_BLIND:
            if before.phase != "BLIND_SELECT":
                raise UnsupportedInjectedAction(
                    f"SELECT_BLIND requires BLIND_SELECT, observed {before.phase}"
                )
            self.bridge.select_blind()
            after = self._wait(
                before,
                lambda value: (
                    value.sequence > before.sequence
                    and value.phase == "SELECTING_HAND"
                    and value.state_complete
                ),
                "blind selection",
            )
            return LiveInjectedActionResult(action, before, after)

        if name == REFRESH_SHOP:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"REFRESH_SHOP requires SHOP, observed {before.phase}"
                )
            before_terms = self.reroll_terms_reader()
            self.bridge.reroll_shop()

            def reroll_settled(value: LiveBalatroSnapshot) -> bool:
                after_terms = self.reroll_terms_reader()
                return _reroll_complete(
                    before,
                    value,
                    before_terms,
                    after_terms,
                )

            after = self._wait(
                before,
                reroll_settled,
                "shop reroll",
            )
            return LiveInjectedActionResult(
                action,
                before,
                after,
                {
                    "reroll_cost": before_terms.cost,
                    "free_rerolls": before_terms.free_rerolls,
                },
            )

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

        if name == SELL_JOKER:
            if before.phase != "SHOP":
                raise UnsupportedInjectedAction(
                    f"SELL_JOKER requires SHOP, observed {before.phase}"
                )
            index = _target_index(action.target)
            item = _area_item(before, "jokers", index)
            before_count = len(_area_cards(before, "jokers"))
            target_live_id = item.get("live_id")
            self.bridge.sell_joker(index)

            def sale_settled(value: LiveBalatroSnapshot) -> bool:
                after_jokers = _area_cards(value, "jokers")
                if (
                    value.sequence <= before.sequence
                    or value.phase != "SHOP"
                    or not value.state_complete
                    or len(after_jokers) != before_count - 1
                ):
                    return False
                if target_live_id is None:
                    return True
                return all(
                    not isinstance(joker, dict)
                    or joker.get("live_id") != target_live_id
                    for joker in after_jokers
                )

            after = self._wait(
                before,
                sale_settled,
                "joker sale",
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
            before_terms = self.pack_terms_reader()
            if index >= len(before_terms.choice_addresses):
                raise UnsupportedInjectedAction(
                    f"pack choice index {index} is out of range for "
                    f"{len(before_terms.choice_addresses)} visible choices"
                )
            if before_terms.choices_remaining <= 0:
                raise UnsupportedInjectedAction(
                    "Balatro reports no remaining booster-pack choices"
                )
            target_indices: tuple[int, ...] = ()
            if action.cards:
                if state is None:
                    raise UnsupportedInjectedAction(
                        "targeted SELECT_PACK_CARD requires the translated state "
                        "used to choose hand targets"
                    )
                try:
                    target_indices = _action_indices(state, action)
                except RuntimeError as error:
                    raise UnsupportedInjectedAction(str(error)) from error
            selected_address = before_terms.choice_addresses[index]
            if target_indices:
                self.bridge.select_pack_card(index, target_indices)
            else:
                self.bridge.select_pack_card(index)

            def pack_selection_settled(value: LiveBalatroSnapshot) -> bool:
                after_terms = None
                if (
                    before_terms.choices_remaining > 1
                    and value.phase != "SHOP"
                    and _is_pack_phase(value.phase)
                    and value.state_complete
                ):
                    after_terms = self.pack_terms_reader()
                return _pack_selection_complete(
                    before,
                    value,
                    before_terms,
                    after_terms,
                    selected_address=selected_address,
                )

            after = self._wait(
                before,
                pack_selection_settled,
                "pack selection",
            )
            return LiveInjectedActionResult(
                action,
                before,
                after,
                {
                    "area_index": index,
                    "target_indices": target_indices,
                    "choices_remaining_before": before_terms.choices_remaining,
                    "selected_address": selected_address,
                },
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
