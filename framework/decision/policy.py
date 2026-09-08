from framework.core.action import Action


class Policy:
    """
    Base interface for selecting actions.
    """

    def select_action(
        self,
        actions: list[Action],
        scores: list[float]
    ) -> Action:
        raise NotImplementedError