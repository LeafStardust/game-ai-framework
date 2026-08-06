from framework.agent.decision import DecisionEngine
from framework.core.action import Action
from framework.core.state import GameState

from framework.decision.evaluator import Evaluator
from framework.decision.policy import Policy


class DecisionPipeline(DecisionEngine):
    """
    Connects action evaluation and action selection.
    """

    def __init__(
        self,
        evaluator: Evaluator,
        policy: Policy
    ):
        self.evaluator = evaluator
        self.policy = policy


    def choose_action(
        self,
        state: GameState,
        actions: list[Action]
    ) -> Action:

        scores = []

        for action in actions:
            score = self.evaluator.evaluate(
                state,
                action
            )

            scores.append(score)


        return self.policy.select_action(
            actions,
            scores
        )