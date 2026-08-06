from games.balatro.evaluator import BalatroEvaluator
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import BalatroAction


def test_balatro_evaluator_scores_play_hand_higher():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    play_score = evaluator.evaluate(
        environment.get_state(),
        BalatroAction("PLAY_HAND")
    )

    discard_score = evaluator.evaluate(
        environment.get_state(),
        BalatroAction("DISCARD_HAND")
    )

    assert play_score > discard_score