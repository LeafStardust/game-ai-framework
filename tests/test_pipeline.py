from framework.decision.pipeline import DecisionPipeline
from framework.decision.evaluator import Evaluator
from framework.decision.policy import Policy


class DummyEvaluator(Evaluator):

    def evaluate(
        self,
        state,
        action
    ):
        return 1.0


class DummyPolicy(Policy):

    def select_action(
        self,
        actions,
        scores
    ):
        return actions[0]


def test_pipeline_returns_action():

    pipeline = DecisionPipeline(
        DummyEvaluator(),
        DummyPolicy()
    )

    actions = [
        "ACTION_1",
        "ACTION_2"
    ]

    result = pipeline.choose_action(
        None,
        actions
    )

    assert result == "ACTION_1"