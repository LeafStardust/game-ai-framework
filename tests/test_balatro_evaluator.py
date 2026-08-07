from games.balatro.evaluator import BalatroEvaluator
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import BalatroAction
from games.balatro.card import BalatroCard


def test_balatro_evaluator_scores_PLAY_CARDS_higher():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    state = environment.get_state()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    play_score = evaluator.evaluate(
        state,
        BalatroAction("PLAY_CARDS")
    )

    discard_score = evaluator.evaluate(
        state,
        BalatroAction("DISCARD_CARDS")
    )

    assert play_score > discard_score


def test_balatro_evaluator_rewards_blind_clear():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    state = environment.get_state()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    state.blind_requirement = 10

    score = evaluator.evaluate(
        state,
        BalatroAction("PLAY_CARDS")
    )

    assert score > 100


def test_balatro_evaluator_does_not_reward_failed_blind():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    state = environment.get_state()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    state.blind_requirement = 9999

    score = evaluator.evaluate(
        state,
        BalatroAction("PLAY_CARDS")
    )

    assert score < 1000