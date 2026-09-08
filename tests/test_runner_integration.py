from agents.random_agent import RandomAgent
from framework.core.game_runner import GameRunner
from framework.core.game import Game
from games.dummy.adapter import DummyAdapter


def test_game_runner_records_metrics():

    game = Game(
        DummyAdapter()
    )
    agent = RandomAgent()

    runner = GameRunner(
        game,
        agent
    )

    runner.run()

    metrics = runner.get_metrics()

    assert metrics.get("steps") is not None
    assert metrics.get("reward") is not None


def test_game_runner_emits_events():

    game = Game(
        DummyAdapter()
    )
    agent = RandomAgent()

    runner = GameRunner(
        game,
        agent
    )

    received = []

    def on_finished(data):
        received.append(data)

    runner.get_events().subscribe(
        "game_finished",
        on_finished
    )

    runner.run()

    assert len(received) == 1
    assert "steps" in received[0]
    assert "reward" in received[0]