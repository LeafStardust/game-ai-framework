from dataclasses import dataclass

from framework.agent.agent import Agent
from framework.decision.pipeline import DecisionPipeline
from framework.decision.policies.greedy import GreedyPolicy

from games.balatro.evaluator import BalatroEvaluator
from games.balatro.search import BalatroSearchStrategy


@dataclass(frozen=True)
class BalatroDeckAgentProfile:
    deck_name: str
    stake_name: str = "WHITE"
    search_simulations: int = 8


class BalatroDeckAgent(Agent):

    def __init__(
        self,
        profile: BalatroDeckAgentProfile
    ):
        self.profile = profile
        evaluator = BalatroEvaluator()

        super().__init__(
            DecisionPipeline(
                evaluator,
                GreedyPolicy(),
                BalatroSearchStrategy(
                    evaluator,
                    None,
                    simulations=profile.search_simulations
                )
            )
        )
