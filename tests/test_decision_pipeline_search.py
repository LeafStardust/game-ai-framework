from framework.decision.pipeline import DecisionPipeline
from framework.decision.search import SearchStrategy

from framework.decision.policy import Policy
from framework.decision.evaluator import Evaluator

from games.balatro.environment import BalatroEnvironment
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.actions import BalatroAction, PLAY_CARDS


class FirstActionPolicy(Policy):

    def select_action(
        self,
        actions,
        scores
    ):
        return actions[0]


def test_pipeline_uses_search_when_provided():

    environment = BalatroEnvironment()

    evaluator = BalatroEvaluator()

    pipeline = DecisionPipeline(
        evaluator,
        FirstActionPolicy(),
        SearchStrategy(
            evaluator,
            environment
        )
    )

    action = pipeline.choose_action(
        environment.get_state(),
        [
            BalatroAction(
                PLAY_CARDS
            )
        ]
    )

    assert action.name == PLAY_CARDS