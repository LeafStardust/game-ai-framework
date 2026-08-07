from framework.experiment.comparator import Comparator
from framework.core.action import Action
from framework.core.game import Game


class DummyAction(Action):

    @property
    def name(self):
        return "DUMMY"


class DummyEnvironment:

    def reset(self):
        pass

    def is_terminal(self):
        return True

    def get_state(self):
        return None

    def get_actions(self):
        return [
            DummyAction()
        ]

    def execute_action(self, action):
        pass

    def get_reward(self):
        return 1.0


class DummyGame(Game):

    def __init__(self):
        self.environment = DummyEnvironment()


class DummyAgent:

    def act(self, state, actions):
        return actions[0]


def test_comparator_runs_multiple_agents():

    game = DummyGame()

    agent_a = DummyAgent()
    agent_b = DummyAgent()

    comparator = Comparator(
        game
    )

    results = comparator.compare(
        [
            agent_a,
            agent_b
        ],
        episodes=5
    )

    assert len(results) == 2
    assert results[0].episodes == 5
    assert results[1].episodes == 5