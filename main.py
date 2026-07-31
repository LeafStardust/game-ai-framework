from agents.random_agent import RandomAgent
from games.dummy.environment import DummyEnvironment
from framework.core.game_runner import GameRunner


def main():

    environment = DummyEnvironment()
    agent = RandomAgent()

    runner = GameRunner(
        environment,
        agent
    )

    reward = runner.run()

    print(f"Reward: {reward}")


if __name__ == "__main__":
    main()