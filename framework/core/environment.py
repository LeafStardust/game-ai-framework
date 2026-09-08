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
    def execute_action(
        self,
        action: Action
    ) -> None:
        pass


    def simulate_action(
        self,
        action: Action
    ) -> GameState:
        """
        Returns the resulting state after applying an action without
        modifying the real environment.

        Games supporting search should override this method.
        """

        raise NotImplementedError(
            "This environment does not support simulation."
        )


    @abstractmethod
    def is_terminal(self) -> bool:
        pass


    @abstractmethod
    def get_reward(self) -> float:
        pass