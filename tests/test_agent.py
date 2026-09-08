from agents.random_agent import RandomAgent
from games.dummy.environment import DummyEnvironment


def test_agent_selects_valid_action():

    environment = DummyEnvironment()
    agent = RandomAgent()

    state = environment.get_state()
    actions = environment.get_actions()

    action = agent.act(
        state,
        actions
    )

    assert action in actions