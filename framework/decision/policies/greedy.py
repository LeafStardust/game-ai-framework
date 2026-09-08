from framework.decision.policy import Policy
from framework.core.action import Action


class GreedyPolicy(Policy):
    """
    Selects the action with the highest score.
    """

    def select_action(
        self,
        actions: list[Action],
        scores: list[float]
    ) -> Action:

        highest_index = scores.index(
            max(scores)
        )

        return actions[highest_index]