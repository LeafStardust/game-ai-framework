from framework.agent.decision import DecisionEngine
from framework.core.action import Action
from framework.core.state import GameState

from framework.decision.evaluator import Evaluator
from framework.decision.policy import Policy
from framework.decision.search import SearchStrategy


class DecisionPipeline(DecisionEngine):
    """
    Connects action evaluation and action selection.
    """

    def __init__(
        self,
        evaluator: Evaluator,
        policy: Policy,
        search: SearchStrategy | None = None
    ):
        self.evaluator = evaluator
        self.policy = policy
        self.search = search


    def choose_action(
        self,
        state: GameState,
        actions: list[Action]
    ) -> Action:

        if self.search:

            scores = self.search.evaluate_actions(
                state,
                actions
            )

        else:

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