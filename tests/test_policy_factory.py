from framework.config.config import FrameworkConfig
from framework.decision.factory import PolicyFactory
from framework.decision.policies.greedy import GreedyPolicy
from framework.decision.policies.softmax import SoftmaxPolicy


def test_factory_creates_greedy():

    config = FrameworkConfig(
        policy="greedy"
    )

    policy = PolicyFactory.create(config)

    assert isinstance(
        policy,
        GreedyPolicy
    )


def test_factory_creates_softmax():

    config = FrameworkConfig(
        policy="softmax",
        temperature=0.5
    )

    policy = PolicyFactory.create(config)

    assert isinstance(
        policy,
        SoftmaxPolicy
    )