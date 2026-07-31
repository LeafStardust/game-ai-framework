import random

from framework.agent.agent import Agent
from framework.agent.decision import DecisionEngine
from framework.core.action import Action
from framework.core.state import GameState


class RandomDecisionEngine(DecisionEngine):
    """
    Selects an action randomly.
    """

    def choose_action(
        self,
        state: GameState,
        actions: list[Action]
    ) -> Action:

        return random.choice(actions)


class RandomAgent(Agent):
    """
    Agent that chooses random actions.
    """

    def __init__(self):
        super().__init__(
            RandomDecisionEngine()
        )