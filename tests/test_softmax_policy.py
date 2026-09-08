import pytest

from framework.decision.policies.softmax import SoftmaxPolicy
from framework.core.action import Action


class DummyAction(Action):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


def test_softmax_returns_valid_action():

    policy = SoftmaxPolicy()

    actions = [
        DummyAction("A"),
        DummyAction("B")
    ]

    scores = [
        10.0,
        5.0
    ]

    selected = policy.select_action(
        actions,
        scores
    )

    assert selected in actions


def test_softmax_rejects_empty_actions():

    policy = SoftmaxPolicy()

    with pytest.raises(ValueError):
        policy.select_action(
            [],
            []
        )


def test_softmax_rejects_mismatched_lengths():

    policy = SoftmaxPolicy()

    actions = [
        DummyAction("A")
    ]

    scores = [
        10.0,
        5.0
    ]

    with pytest.raises(ValueError):
        policy.select_action(
            actions,
            scores
        )


def test_softmax_prefers_higher_scores():

    policy = SoftmaxPolicy(
        temperature=0.1
    )

    actions = [
        DummyAction("HIGH"),
        DummyAction("LOW")
    ]

    scores = [
        10.0,
        1.0
    ]

    results = []

    for _ in range(100):
        results.append(
            policy.select_action(
                actions,
                scores
            ).name
        )

    assert results.count("HIGH") > results.count("LOW")