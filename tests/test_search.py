from framework.decision.search import SearchStrategy

from games.balatro.environment import BalatroEnvironment
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.actions import BalatroAction, PLAY_CARDS


def test_search_evaluates_future_states():

    environment = BalatroEnvironment()

    search = SearchStrategy(
        BalatroEvaluator(),
        environment
    )

    actions = [
        BalatroAction(
            PLAY_CARDS
        )
    ]

    scores = search.evaluate_actions(
        environment.get_state(),
        actions
    )

    assert len(scores) == 1


def test_search_supports_multiple_simulations():

    environment = BalatroEnvironment()

    search = SearchStrategy(
        BalatroEvaluator(),
        environment,
        simulations=3
    )

    scores = search.evaluate_actions(
        environment.get_state(),
        [
            BalatroAction(
                PLAY_CARDS
            )
        ]
    )

    assert len(scores) == 1