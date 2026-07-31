from framework.core.environment import GameEnvironment
from framework.core.action import Action
from framework.core.state import GameState

from games.dummy.state import DummyState
from games.dummy.actions import INCREASE, DECREASE


class DummyEnvironment(GameEnvironment):
    """
    Simple environment for testing the framework loop.
    """

    def __init__(self):
        self.state: DummyState = DummyState()


    def reset(self) -> None:
        self.state = DummyState()


    def get_state(self) -> GameState:
        return self.state


    def get_actions(self) -> list[Action]:
        return [
            INCREASE,
            DECREASE
        ]


    def execute_action(
        self,
        action: Action
    ) -> None:

        if action.name == "INCREASE":
            self.state.value += 1

        elif action.name == "DECREASE":
            self.state.value -= 1


    def is_terminal(self) -> bool:
        return self.state.value >= 5


    def get_reward(self) -> float:
        if self.state.value >= 5:
            return 1.0

        return 0.0