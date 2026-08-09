from games.balatro.actions import DISCARD_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.decks import RED_DECK
from games.balatro.environment import BalatroEnvironment
from games.balatro.prediction import BalatroFutureStatePredictor


def test_prediction_does_not_modify_environment():

    environment = BalatroEnvironment(RED_DECK)
    environment.state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("5", "Spades"),
        BalatroCard("6", "Hearts"),
    ]

    action = BalatroAction(
        DISCARD_CARDS,
        cards=environment.state.hand[:2]
    )

    original_hand = environment.state.hand.copy()
    original_discards = environment.state.discards_remaining

    predictor = BalatroFutureStatePredictor(
        environment,
        seed=1
    )
    states = predictor.predict(action, samples=3)

    assert len(states) == 3
    assert environment.state.hand == original_hand
    assert environment.state.discards_remaining == original_discards


def test_prediction_respects_discard_action():

    environment = BalatroEnvironment(RED_DECK)
    environment.state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("5", "Spades"),
        BalatroCard("6", "Hearts"),
    ]

    action = BalatroAction(
        DISCARD_CARDS,
        cards=environment.state.hand[:2]
    )

    states = BalatroFutureStatePredictor(
        environment,
        seed=1
    ).predict(action)

    assert len(states[0].hand) == 5
    assert states[0].discards_remaining == 3
