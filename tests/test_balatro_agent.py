from agents.balatro_agent import BalatroAgent
from games.balatro.environment import BalatroEnvironment


def test_balatro_agent_prefers_PLAY_CARDS():

    environment = BalatroEnvironment()

    agent = BalatroAgent()

    action = agent.act(
        environment.get_state(),
        environment.get_actions()
    )

    assert action.name == "PLAY_CARDS"