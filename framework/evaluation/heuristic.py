from abc import ABC, abstractmethod

from framework.core.action import Action
from framework.core.state import GameState


class Heuristic(ABC):
    """
    Base interface for individual evaluation components.
    """

    @abstractmethod
    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:
        pass