from abc import ABC, abstractmethod

from framework.core.action import Action
from framework.core.state import GameState


class Evaluator(ABC):
    """
    Defines how states or actions are evaluated.
    """

    @abstractmethod
    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:
        pass