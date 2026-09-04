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
    """Base class for mechanically modeled Balatro Jokers.

    Balatro's ``Card.debuff`` disables a Joker's ability regardless of which
    trigger family would otherwise evaluate it.  Keep that rule at the common
    Joker boundary so Crimson Heart cannot require dozens of per-Joker special
    cases.  Metadata/edition scoring is handled by the scorer and must likewise
    check this public ``debuffed`` state before applying an effect.
    """

    debuffed = False

    def __getattribute__(self, name):
        if name == "apply":
            data = object.__getattribute__(self, "__dict__")
            if bool(data.get("debuffed", False)):
                return object.__getattribute__(self, "_apply_while_debuffed")
        return super().__getattribute__(name)

    def _apply_while_debuffed(self, context: JokerContext) -> JokerContext:
        """A debuffed Joker is present/owned but contributes no ability effect."""
        return context

    @abstractmethod
    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:
        pass
