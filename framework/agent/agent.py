from framework.agent.decision import DecisionEngine
from framework.core.action import Action
from framework.core.state import GameState


class Agent:
    """
    Base AI agent.

    An agent observes a state,
    evaluates available actions,
    and selects an action.
    """

    def __init__(
        self,
        decision_engine: DecisionEngine
    ):
        self.decision_engine: DecisionEngine = decision_engine


    def act(
        self,
        state: GameState,
        actions: list[Action]
    ) -> Action:

        return self.decision_engine.choose_action(
            state,
            actions
        )