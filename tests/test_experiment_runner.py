from framework.experiment.runner import ExperimentRunner
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


def test_experiment_runs_multiple_episodes():

    game = DummyGame()
    agent = DummyAgent()

    experiment = ExperimentRunner(
        game,
        agent
    )

    result = experiment.run(
        episodes=5
    )

    assert result.episodes == 5