from abc import ABC, abstractmethod

from framework.core.action import Action
from framework.core.state import GameState


class DecisionEngine(ABC):
    """
    Defines how an agent selects an action.
    """

    @abstractmethod
    def choose_action(
        self,
        state: GameState,
        actions: list[Action]
    ) -> Action:
        pass