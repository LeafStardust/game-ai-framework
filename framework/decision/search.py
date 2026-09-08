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
        environment: GameEnvironment,
        simulations: int = 1
    ):
        self.evaluator = evaluator
        self.environment = environment
        self.simulations = simulations


    def evaluate_actions(
        self,
        state: GameState,
        actions: list[Action]
    ) -> list[float]:

        scores = []

        for action in actions:

            total_score = 0.0

            for _ in range(self.simulations):

                next_state = self.environment.simulate_action(
                    action
                )

                score = self.evaluator.evaluate(
                    next_state,
                    action
                )

                total_score += score


            average_score = (
                total_score / self.simulations
            )

            scores.append(
                average_score
            )

        return scores