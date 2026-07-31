from framework.core.environment import GameEnvironment

from games.dummy.state import DummyState
from games.dummy.actions import INCREASE, DECREASE


class DummyEnvironment(GameEnvironment):
    """
    Simple environment for testing the framework loop.
    """

    def __init__(self):
        self.state = DummyState()


    def reset(self):
        self.state = DummyState()


    def get_state(self):
        return self.state


    def get_actions(self):
        return [
            INCREASE,
            DECREASE
        ]


    def execute_action(self, action):

        if action.name == "INCREASE":
            self.state.value += 1

        elif action.name == "DECREASE":
            self.state.value -= 1


    def is_terminal(self):
        return self.state.value >= 5


    def get_reward(self):
        if self.state.value >= 5:
            return 1

        return 0