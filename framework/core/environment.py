from abc import ABC, abstractmethod

from framework.core.action import Action
from framework.core.state import GameState


class GameEnvironment(ABC):
    """
    Interface between the AI agent and a game.
    """

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def get_state(self) -> GameState:
        pass

    @abstractmethod
    def get_actions(self) -> list[Action]:
        pass

    @abstractmethod
    def execute_action(self, action: Action) -> None:
        pass

    @abstractmethod
    def is_terminal(self) -> bool:
        pass

    @abstractmethod
    def get_reward(self) -> float:
        pass