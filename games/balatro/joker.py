from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from framework.core.state import GameState

from games.balatro.card import BalatroCard

if TYPE_CHECKING:
    from games.balatro.hand import PokerHand
    from games.balatro.scoring import HandScore


@dataclass
class JokerContext:

    state: GameState
    score: HandScore | None = None
    poker_hand: PokerHand | None = None

    cards: list[BalatroCard] = field(default_factory=list)
    held_cards: list[BalatroCard] = field(default_factory=list)

    trigger: str = ""
    data: dict = field(default_factory=dict)


class Joker(ABC):

    @abstractmethod
    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:
        pass