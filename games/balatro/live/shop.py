from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
)
from games.balatro.actions import BalatroAction
from games.balatro.state import BalatroState


@dataclass
class LiveShopItem:
    """Observable purchasable item without a dedicated gameplay implementation."""

    kind: str
    label: str
    price: int
    live_id: int | str | None = None
    area_index: int | None = None
    center: str | None = None
    edition: str | None = None
    discovered: bool | None = None


class LiveShopItemFactory:

    def create(self, data: dict, *, kind: str | None = None) -> LiveShopItem | None:
        label = data.get("label") or data.get("ability_name")
        if not label:
            return None

        item_kind = kind or data.get("ability_set") or data.get("set") or "ITEM"
        area_index = data.get("area_index")
        discovered = data.get("discovered")

        return LiveShopItem(
            kind=str(item_kind).upper(),
            label=str(label),
            price=self._price(data.get("cost", data.get("price", 0))),
            live_id=data.get("live_id", data.get("id")),
            area_index=(int(area_index) if area_index is not None else None),
            center=data.get("center") or data.get("key"),
            edition=data.get("edition"),
            discovered=discovered if isinstance(discovered, bool) else None,
        )

    @staticmethod
    def _price(value) -> int:
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


class BalatroShopActionGenerator:
    """Generate legal purchase/leave actions from translated observable shop state."""

    BUFFERABLE_ACTIONS = {
        BUY_JOKER,
        BUY_CONSUMABLE,
        BUY_VOUCHER,
        END_SHOP,
    }

    def generate_actions(self, state: BalatroState) -> list[BalatroAction]:
        if state.phase != "SHOP":
            return []

        actions: list[BalatroAction] = []

        if len(state.jokers) < state.joker_slots:
            actions.extend(
                BalatroAction(BUY_JOKER, target=joker)
                for joker in state.shop_jokers
                if state.money >= self._price(joker)
            )

        if len(state.consumables) < state.consumable_slots:
            actions.extend(
                BalatroAction(BUY_CONSUMABLE, target=consumable)
                for consumable in state.shop_consumables
                if state.money >= self._price(consumable)
            )

        actions.extend(
            BalatroAction(BUY_VOUCHER, target=voucher)
            for voucher in state.shop_vouchers
            if state.money >= self._price(voucher)
        )

        actions.extend(
            BalatroAction(BUY_BOOSTER, target=booster)
            for booster in state.shop_boosters
            if state.money >= self._price(booster)
        )

        actions.append(BalatroAction(END_SHOP))
        return actions

    def generate_bufferable_actions(
        self,
        state: BalatroState,
    ) -> list[BalatroAction]:
        """Return shop actions that the current save-checkpoint path can confirm safely."""
        return [
            action
            for action in self.generate_actions(state)
            if action.name in self.BUFFERABLE_ACTIONS
        ]

    @staticmethod
    def _price(item) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
