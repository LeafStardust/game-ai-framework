from framework.core.action import Action
from framework.core.state import GameState
from framework.core.environment import GameEnvironment

from framework.decision.evaluator import Evaluator


class SearchStrategy:
    """
    Performs lookahead search before action selection.
    """

    def __init__(
        self,
        evaluator: Evaluator,
        environment: GameEnvironment
    ):
        self.evaluator = evaluator
        self.environment = environment


    def evaluate_actions(
        self,
        state: GameState,
        actions: list[Action]
    ) -> list[float]:

        scores = []

        for action in actions:

            next_state = self.environment.simulate_action(
                action
            )

            score = self.evaluator.evaluate(
                next_state,
                action
            )

            scores.append(score)

        return scores