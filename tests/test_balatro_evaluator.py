from games.balatro.evaluator import BalatroEvaluator
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import BalatroAction


def test_balatro_evaluator_scores_PLAY_CARDS_higher():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    play_score = evaluator.evaluate(
        environment.get_state(),
        BalatroAction("PLAY_CARDS")
    )

    discard_score = evaluator.evaluate(
        environment.get_state(),
        BalatroAction("DISCARD_CARDS")
    )

    assert play_score > discard_score