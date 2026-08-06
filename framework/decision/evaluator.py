from framework.core.action import Action
from framework.core.state import GameState


class Evaluator:
    """
    Base interface for evaluating actions.
    """

    def evaluate(
        self,
        state: GameState,
        action: Action
    ) -> float:
        raise NotImplementedError