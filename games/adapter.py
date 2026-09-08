from framework.core.environment import GameEnvironment
from framework.core.state import GameState
from framework.core.action import Action


class GameAdapter:
    """
    Base interface for connecting games to the framework.
    """

    def create_environment(self) -> GameEnvironment:
        raise NotImplementedError


    def get_state(
        self,
        environment: GameEnvironment
    ) -> GameState:
        raise NotImplementedError


    def get_actions(
        self,
        environment: GameEnvironment
    ) -> list[Action]:
        raise NotImplementedError