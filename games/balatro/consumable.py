from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from games.balatro.card import BalatroCard

if TYPE_CHECKING:
    from games.balatro.state import BalatroState


@dataclass
class ConsumableContext:

    state: BalatroState
    cards: list[BalatroCard] = field(default_factory=list)
    target: object | None = None
    data: dict = field(default_factory=dict)


class Consumable(ABC):

    name: str = ""
    category: str = ""
    price: int = 3

    @abstractmethod
    def can_use(
        self,
        context: ConsumableContext
    ) -> bool:
        pass

    @abstractmethod
    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:
        pass

    def get_target_cards(
        self,
        state: BalatroState
    ) -> list[list[BalatroCard]]:

        return [[]]


class PlanetCard(Consumable):

    category = "PLANET"

    def __init__(
        self,
        name: str,
        hand_type: str,
        chips: int,
        mult: int
    ):
        self.name = name
        self.hand_type = hand_type
        self.chips = chips
        self.mult = mult

    def can_use(
        self,
        context: ConsumableContext
    ) -> bool:

        return self.hand_type in context.state.hand_levels

    def use(
        self,
        context: ConsumableContext
    ) -> ConsumableContext:

        context.state.hand_levels[self.hand_type] += 1

        context.data["chips"] = self.chips
        context.data["mult"] = self.mult

        return context