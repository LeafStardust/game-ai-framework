from framework.decision.policies.greedy import GreedyPolicy


def test_greedy_policy_selects_highest_score():

    policy = GreedyPolicy()

    actions = [
        "A",
        "B",
        "C"
    ]

    scores = [
        1.0,
        5.0,
        3.0
    ]

    result = policy.select_action(
        actions,
        scores
    )

    assert result == "B"