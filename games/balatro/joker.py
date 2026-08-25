from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from framework.core.state import GameState

from games.balatro.card import BalatroCard
from games.balatro.events import BalatroEvent
from games.balatro.hand import PokerHand

if TYPE_CHECKING:
    from games.balatro.scoring import HandScore


@dataclass
class JokerContext:

    state: GameState
    score: HandScore | None = None
    poker_hand: PokerHand | None = None

    cards: list[BalatroCard] = field(default_factory=list)
    held_cards: list[BalatroCard] = field(default_factory=list)

    trigger: str = ""
    event: BalatroEvent | None = None
    data: dict = field(default_factory=dict)


class Joker(ABC):
    """Base class for mechanically modeled Balatro Jokers."""

    @abstractmethod
    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:
        pass
