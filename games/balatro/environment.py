from framework.core.environment import GameEnvironment
from framework.core.action import Action
from framework.core.state import GameState

from games.balatro.state import BalatroState


class BalatroEnvironment(GameEnvironment):
    """
    Environment for a Balatro game instance.
    """

    def __init__(self):
        self.state = BalatroState()


    def reset(self) -> None:
        self.state = BalatroState()


    def get_state(self) -> GameState:
        return self.state


    def get_actions(self) -> list[Action]:
        return []


    def execute_action(
        self,
        action: Action
    ) -> None:
        pass


    def is_terminal(self) -> bool:
        return False


    def get_reward(self) -> float:
        return float(self.state.score)