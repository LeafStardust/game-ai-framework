class ExperimentResult:
    """
    Stores results from an experiment run.
    """

    def __init__(
        self,
        rewards: list[float],
        steps: list[int]
    ):
        self.rewards = rewards
        self.steps = steps

    @property
    def episodes(self) -> int:
        return len(self.rewards)

    @property
    def average_reward(self) -> float:
        if not self.rewards:
            return 0.0

        return sum(self.rewards) / len(self.rewards)

    @property
    def max_reward(self) -> float:
        if not self.rewards:
            return 0.0

        return max(self.rewards)

    @property
    def min_reward(self) -> float:
        if not self.rewards:
            return 0.0

        return min(self.rewards)

    @property
    def average_steps(self) -> float:
        if not self.steps:
            return 0.0

        return sum(self.steps) / len(self.steps)