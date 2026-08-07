from agents.balatro_agent import BalatroAgent
from games.balatro.environment import BalatroEnvironment
from games.balatro.card import BalatroCard


def test_balatro_agent_selects_best_play_cards_subset():

    environment = BalatroEnvironment()

    state = environment.get_state()

    state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts"),
        BalatroCard("2", "Clubs")
    ]

    agent = BalatroAgent()

    action = agent.act(
        state,
        environment.get_actions()
    )

    assert action.name == "PLAY_CARDS"

    assert action.cards == [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts")
    ]