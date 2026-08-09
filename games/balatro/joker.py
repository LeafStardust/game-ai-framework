from abc import ABC, abstractmethod

from framework.core.state import GameState

from games.balatro.scoring import HandScore


class Joker(ABC):
    """
    Base interface for Balatro Jokers.
    """

    @abstractmethod
    def apply(
        self,
        state: GameState,
        score: HandScore
    ) -> HandScore:
        pass