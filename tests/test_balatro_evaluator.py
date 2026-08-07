from games.balatro.evaluator import BalatroEvaluator
from games.balatro.environment import BalatroEnvironment
from games.balatro.actions import BalatroAction
from games.balatro.card import BalatroCard


def test_balatro_evaluator_scores_PLAY_CARDS_higher():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    state = environment.get_state()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    state.hand = cards

    play_score = evaluator.evaluate(
        state,
        BalatroAction(
            "PLAY_CARDS",
            cards=cards
        )
    )

    discard_score = evaluator.evaluate(
        state,
        BalatroAction(
            "DISCARD_CARDS",
            cards=cards
        )
    )

    assert play_score > discard_score


def test_balatro_evaluator_rewards_blind_clear():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    state = environment.get_state()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    state.hand = cards
    state.blind_requirement = 10

    score = evaluator.evaluate(
        state,
        BalatroAction(
            "PLAY_CARDS",
            cards=cards
        )
    )

    assert score > 100


def test_balatro_evaluator_does_not_reward_failed_blind():

    evaluator = BalatroEvaluator()

    environment = BalatroEnvironment()

    state = environment.get_state()

    cards = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    state.hand = cards
    state.blind_requirement = 9999

    score = evaluator.evaluate(
        state,
        BalatroAction(
            "PLAY_CARDS",
            cards=cards
        )
    )

    assert score < 1000