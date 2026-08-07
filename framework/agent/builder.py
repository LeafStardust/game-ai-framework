from framework.agent.agent import Agent
from framework.agent.decision import DecisionEngine

from framework.config.config import FrameworkConfig

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

        policy = PolicyFactory.create(
            config
        )

        decision_engine: DecisionEngine = DecisionPipeline(
            evaluator,
            policy
        )

        return Agent(
            decision_engine
        )