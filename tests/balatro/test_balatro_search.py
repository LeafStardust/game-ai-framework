from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.search import BalatroSearchStrategy


def test_balatro_search_evaluates_discard_with_multiple_future_states():

    environment = BalatroEnvironment()
    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Clubs"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("7", "Spades"),
        BalatroCard("2", "Hearts"),
    ]

    search = BalatroSearchStrategy(
        BalatroEvaluator(),
        environment,
        simulations=4
    )

    action = BalatroAction(
        DISCARD_CARDS,
        cards=environment.state.hand[-2:]
    )

    scores = search.evaluate_actions(
        environment.state,
        [action]
    )

    assert len(scores) == 1
    assert isinstance(scores[0], float)
