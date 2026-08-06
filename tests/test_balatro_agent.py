from agents.balatro_agent import BalatroAgent

from framework.decision.evaluator import Evaluator
from framework.decision.policy import Policy

from games.balatro.environment import BalatroEnvironment


class DummyEvaluator(Evaluator):

    def evaluate(
        self,
        state,
        action
    ):
        if action.name == "PLAY_HAND":
            return 10.0

        return 0.0


class DummyPolicy(Policy):

    def select_action(
        self,
        actions,
        scores
    ):

        highest_index = scores.index(
            max(scores)
        )

        return actions[highest_index]


def test_balatro_agent_prefers_play_hand():

    environment = BalatroEnvironment()

    agent = BalatroAgent(
        DummyEvaluator(),
        DummyPolicy()
    )

    action = agent.act(
        environment.get_state(),
        environment.get_actions()
    )

    assert action.name == "PLAY_HAND"