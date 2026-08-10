from __future__ import annotations

from dataclasses import dataclass, field

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
)
from games.balatro.actions import BalatroAction
from games.balatro.state import BalatroState


class UnsupportedBufferedShopAction(RuntimeError):
    pass


@dataclass
class BufferedShopTransaction:
    """Tracks deterministic shop mutations that Balatro may not persist immediately."""

    baseline_money: int
    expected_money: int
    purchases: list[BalatroAction] = field(default_factory=list)

    @classmethod
    def begin(cls, state: BalatroState) -> "BufferedShopTransaction":
        if state.phase != "SHOP":
            raise ValueError("buffered shop transactions require SHOP phase")
        return cls(
            baseline_money=state.money,
            expected_money=state.money,
        )

    def validate(self, state: BalatroState, action: BalatroAction) -> None:
        """Reject an unsafe or impossible buffered purchase without mutating state."""
        source, destination, capacity = self._purchase_context(state, action)
        self._validate_buy(
            state,
            action,
            source=source,
            destination=destination,
            capacity=capacity,
        )

    def apply(self, state: BalatroState, action: BalatroAction) -> None:
        if state.phase != "SHOP":
            raise ValueError("buffered shop mutations require SHOP phase")

        source, destination, capacity = self._purchase_context(state, action)
        self._validate_buy(
            state,
            action,
            source=source,
            destination=destination,
            capacity=capacity,
        )

        target = action.target
        price = self._price(target)
        state.money -= price
        source.remove(target)
        destination.append(target)

        self.purchases.append(action)
        self.expected_money = state.money

    def reconciles(self, persisted: BalatroState) -> bool:
        """Return whether a later persisted checkpoint acknowledges the buffered spend."""
        return persisted.money == self.expected_money

    def assert_reconciled(self, persisted: BalatroState) -> None:
        if not self.reconciles(persisted):
            raise RuntimeError(
                "persisted Balatro state did not reconcile buffered shop purchases: "
                f"expected money={self.expected_money}, observed money={persisted.money}"
            )

    def _purchase_context(
        self,
        state: BalatroState,
        action: BalatroAction,
    ) -> tuple[list, list, int | None]:
        if state.phase != "SHOP":
            raise ValueError("buffered shop mutations require SHOP phase")

        if action.name == BUY_JOKER:
            return state.shop_jokers, state.jokers, state.joker_slots
        if action.name == BUY_CONSUMABLE:
            return (
                state.shop_consumables,
                state.consumables,
                state.consumable_slots,
            )
        if action.name == BUY_VOUCHER:
            return state.shop_vouchers, state.vouchers, None

        raise UnsupportedBufferedShopAction(
            f"shop action {action.name!r} cannot be projected safely"
        )

    def _validate_buy(
        self,
        state: BalatroState,
        action: BalatroAction,
        *,
        source: list,
        destination: list,
        capacity: int | None,
    ) -> None:
        target = action.target
        if target not in source:
            raise ValueError("shop purchase target is not present in the current shop")
        if capacity is not None and len(destination) >= capacity:
            raise ValueError("shop purchase destination has no free slot")

        price = self._price(target)
        if state.money < price:
            raise ValueError("insufficient money for shop purchase")

    @staticmethod
    def _price(item) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
