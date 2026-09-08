from framework.core.action import Action
from framework.core.state import GameState
from framework.decision.evaluator import Evaluator
from framework.decision.search import SearchStrategy

from games.balatro.actions import DISCARD_CARDS
from games.balatro.expected_value import BalatroExpectedValueEstimator
from games.balatro.prediction import BalatroFutureStatePredictor


class BalatroSearchStrategy(SearchStrategy):

    def evaluate_actions(
        self,
        state: GameState,
        actions: list[Action]
    ) -> list[float]:

        if self.environment is None:
            raise ValueError("environment is required for Balatro search")

        predictor = BalatroFutureStatePredictor(
            self.environment
        )
        estimator = BalatroExpectedValueEstimator(
            self.evaluator,
            predictor
        )
        scores = []

        for action in actions:

            samples = self.simulations

            if action.name != DISCARD_CARDS:
                samples = 1

            scores.append(
                estimator.estimate(
                    action,
                    samples=samples
                )
            )

        return scores
