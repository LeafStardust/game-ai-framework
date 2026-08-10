from framework.core.action import Action
from framework.decision.evaluator import Evaluator

from games.balatro.prediction import BalatroFutureStatePredictor


class BalatroExpectedValueEstimator:

    def __init__(
        self,
        evaluator: Evaluator,
        predictor: BalatroFutureStatePredictor
    ):
        self.evaluator = evaluator
        self.predictor = predictor

    def estimate(
        self,
        action: Action,
        samples: int = 8
    ) -> float:

        states = self.predictor.predict(
            action,
            samples=samples
        )

        if not states:
            return 0.0

        return sum(
            self.evaluator.evaluate(
                state,
                action
            )
            for state in states
        ) / len(states)
