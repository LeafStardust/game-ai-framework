from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.expected_value import BalatroExpectedValueEstimator
from games.balatro.prediction import BalatroFutureStatePredictor


def test_expected_value_estimator_returns_average_score():

    environment = BalatroEnvironment()
    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("4", "Spades"),
        BalatroCard("2", "Hearts"),
    ]

    action = BalatroAction(
        DISCARD_CARDS,
        cards=environment.state.hand[-2:]
    )

    estimator = BalatroExpectedValueEstimator(
        BalatroEvaluator(),
        BalatroFutureStatePredictor(
            environment,
            seed=1
        )
    )

    value = estimator.estimate(
        action,
        samples=4
    )

    assert isinstance(value, float)
