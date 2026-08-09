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
