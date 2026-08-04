from framework.core.environment import GameEnvironment
from framework.core.state import GameState
from framework.core.action import Action

from games.adapter import GameAdapter
from games.dummy.environment import DummyEnvironment


class DummyAdapter(GameAdapter):
    """
    Adapter for the dummy test environment.
    """

    def create_environment(self) -> GameEnvironment:
        return DummyEnvironment()


    def get_state(
        self,
        environment: GameEnvironment
    ) -> GameState:
        return environment.get_state()


    def get_actions(
        self,
        environment: GameEnvironment
    ) -> list[Action]:
        return environment.get_actions()