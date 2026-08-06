from framework.agent.agent import Agent
from framework.agent.decision import DecisionEngine
from framework.core.action import Action
from framework.core.state import GameState


class BalatroDecisionEngine(DecisionEngine):
    """
    Basic heuristic decision system for Balatro.
    """


    def choose_action(
        self,
        state: GameState,
        actions: list[Action]
    ) -> Action:

        # Prefer playing hands over discarding
        for action in actions:

            if action.name == "PLAY_HAND":
                return action


        # Otherwise choose first available action
        return actions[0]


class BalatroAgent(Agent):
    """
    First Balatro AI agent.
    """

    def __init__(self):

        super().__init__(
            BalatroDecisionEngine()
        )