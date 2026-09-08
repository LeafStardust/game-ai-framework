from framework.decision.policy import Policy
from framework.decision.policies.greedy import GreedyPolicy
from framework.decision.policies.softmax import SoftmaxPolicy
from framework.config.config import FrameworkConfig


class PolicyFactory:
    """
    Creates policy instances from configuration.
    """

    @staticmethod
    def create(
        config: FrameworkConfig
    ) -> Policy:

        if config.policy == "greedy":
            return GreedyPolicy()

        elif config.policy == "softmax":
            return SoftmaxPolicy(
                temperature=config.temperature
            )

        raise ValueError(
            f"Unknown policy: {config.policy}"
        )