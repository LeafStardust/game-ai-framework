from agents.balatro_agent import BalatroAgent
from games.balatro.environment import BalatroEnvironment


def test_balatro_agent_prefers_play_hand():

    environment = BalatroEnvironment()

    state = environment.get_state()
    actions = environment.get_actions()

    agent = BalatroAgent()

    action = agent.act(
        state,
        actions
    )

    assert action.name == "PLAY_HAND"