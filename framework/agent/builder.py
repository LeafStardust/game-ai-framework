from framework.agent.agent import Agent

from framework.config.config import FrameworkConfig

from framework.core.random import set_seed

from framework.decision.evaluator import Evaluator
from framework.decision.factory import PolicyFactory
from framework.decision.pipeline import DecisionPipeline


class AgentBuilder:
    """
    Builds configured AI agents.
    """

    @staticmethod
    def create(
        config: FrameworkConfig,
        evaluator: Evaluator
    ) -> Agent:

        set_seed(
            config.seed
        )

        policy = PolicyFactory.create(
            config
        )

        decision_engine = DecisionPipeline(
            evaluator,
            policy
        )

        return Agent(
            decision_engine
        )