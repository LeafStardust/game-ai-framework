import random

from framework.agent.decision import DecisionEngine
from framework.agent.agent import Agent


class RandomDecisionEngine(DecisionEngine):
    """
    Selects an action randomly.
    """

    def choose_action(self, state, actions):
        return random.choice(actions)


class RandomAgent(Agent):
    """
    Agent that chooses random actions.
    """

    def __init__(self):
        super().__init__(
            RandomDecisionEngine()
        )