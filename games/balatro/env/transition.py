"""First exact R1 headless transition slice.

This module owns environment-private run state that is required for deterministic
simulation but is not part of the canonical public observation.  The initial
transition engine deliberately covers only deterministic shop operations whose
outcomes do not require R2 RNG.  Booster opening and all stochastic transitions
remain unavailable until their exact RNG/state ownership exists.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from games.balatro.card import BalatroCard
from games.balatro.env.actions import EnvAction
from games.balatro.state import BalatroState


class HeadlessTransitionError(ValueError):
    """Raised when a requested headless transition is not exact/legal."""


@dataclass
class HeadlessRunState:
    """Exact environment-owned state around the canonical public observation.

    ``public`` remains the single source of truth for information visible to the
    policy.  The other fields are simulator-owned state needed to make future
    transitions deterministic and replayable without leaking hidden information
    into observations.
    """

    public: BalatroState
    seed: str | int
    rng_state: Any = None
    draw_pile: list[BalatroCard] = field(default_factory=list)
    discard_pile: list[BalatroCard] = field(default_factory=list)
    played_pile: list[BalatroCard] = field(default_factory=list)
    reroll_cost: int = 5
    skips: int = 0
    tags: list[str] = field(default_factory=list)
    pack_choices: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if str(self.public.deck_name).upper() != "RED":
            raise HeadlessTransitionError("R1 headless state currently supports Red Deck only")
        if str(self.public.stake_name).upper() != "WHITE":
            raise HeadlessTransitionError("R1 headless state currently supports White Stake only")
        if self.reroll_cost < 0 or self.skips < 0:
            raise HeadlessTransitionError("environment counters cannot be negative")

    def copy(self) -> "HeadlessRunState":
        """Return an isolated transition snapshot.

        A deep copy is intentional here: public ``BalatroState.copy`` is shallow
        for several contained gameplay objects, while a simulator transition must
        never mutate the pre-transition state through shared Joker/shop/card
        objects.
        """

        return deepcopy(self)


class ShopTransitionEngine:
    """Exact deterministic transitions for the currently modeled shop subset."""

    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        state = run.public
        if state.phase != "SHOP" or not state.shop_active:
            return ()

        actions: list[EnvAction] = []
        if len(state.jokers) < state.joker_slots:
            actions.extend(
                EnvAction.from_alias("BUY_JOKER", {"slot": slot})
                for slot, item in enumerate(state.shop_jokers)
                if state.money >= self._price(item)
            )
        if len(state.consumables) < state.consumable_slots:
            actions.extend(
                EnvAction.from_alias("BUY_CONSUMABLE", {"slot": slot})
                for slot, item in enumerate(state.shop_consumables)
                if state.money >= self._price(item)
            )
        actions.extend(
            EnvAction.from_alias("BUY_VOUCHER", {"slot": slot})
            for slot, item in enumerate(state.shop_vouchers)
            if state.money >= self._price(item)
        )

        # BUY_BOOSTER / OPEN_PACK is intentionally not exposed here: purchase is
        # deterministic, but entering a generated pack is not exact until R2 owns
        # pack RNG and R1 owns the resulting pack state.
        actions.append(EnvAction.from_alias("END_SHOP"))
        return tuple(actions)

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal shop transition: {action.alias}")

        next_run = run.copy()
        state = next_run.public
        params = action.payload()

        if action.alias == "END_SHOP":
            state.shop_active = False
            state.phase = "BLIND_SELECT"
            state.shop_jokers.clear()
            state.shop_consumables.clear()
            state.shop_boosters.clear()
            state.shop_vouchers.clear()
            return next_run

        slot = self._slot(params)
        if action.alias == "BUY_JOKER":
            self._buy(state, state.shop_jokers, state.jokers, slot)
            return next_run
        if action.alias == "BUY_CONSUMABLE":
            self._buy(state, state.shop_consumables, state.consumables, slot)
            return next_run
        if action.alias == "BUY_VOUCHER":
            self._buy(state, state.shop_vouchers, state.vouchers, slot)
            return next_run

        raise HeadlessTransitionError(f"unimplemented shop transition: {action.alias}")

    @classmethod
    def _buy(cls, state: BalatroState, source: list, destination: list, slot: int) -> None:
        if slot < 0 or slot >= len(source):
            raise HeadlessTransitionError(f"shop slot out of range: {slot}")
        item = source[slot]
        price = cls._price(item)
        if price < 0 or state.money < price:
            raise HeadlessTransitionError("shop item is not affordable")
        state.money -= price
        destination.append(source.pop(slot))

    @staticmethod
    def _slot(params: dict[str, Any]) -> int:
        value = params.get("slot")
        if isinstance(value, bool):
            raise HeadlessTransitionError("shop slot must be an integer")
        try:
            slot = int(value)
        except (TypeError, ValueError) as exc:
            raise HeadlessTransitionError("shop action requires integer slot") from exc
        if slot != value and not isinstance(value, int):
            raise HeadlessTransitionError("shop slot must be an integer")
        return slot

    @staticmethod
    def _price(item: Any) -> int:
        value = getattr(item, "price", getattr(item, "cost", 0))
        if isinstance(value, dict):
            value = value.get("buy", 0)
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise HeadlessTransitionError("shop item has invalid price") from exc
