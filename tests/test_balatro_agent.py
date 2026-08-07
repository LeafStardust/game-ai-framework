from agents.balatro_agent import BalatroAgent
from games.balatro.environment import BalatroEnvironment
from games.balatro.card import BalatroCard


def test_balatro_agent_prefers_PLAY_CARDS():

    environment = BalatroEnvironment()

    state = environment.get_state()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts")
    ]

    agent = BalatroAgent()

    action = agent.act(
        state,
        environment.get_actions()
    )

    assert action.name == "PLAY_CARDS"