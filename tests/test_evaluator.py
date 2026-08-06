from framework.decision.evaluator import Evaluator


def test_evaluator_requires_implementation():

    evaluator = Evaluator()

    try:
        evaluator.evaluate(
            None,
            None
        )
        assert False
    except NotImplementedError:
        assert True