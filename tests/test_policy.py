from framework.decision.policy import Policy


def test_policy_requires_implementation():

    policy = Policy()

    try:
        policy.select_action(
            [],
            []
        )
        assert False
    except NotImplementedError:
        assert True