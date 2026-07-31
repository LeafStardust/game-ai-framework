from agents.random_agent import RandomAgent
from games.dummy.environment import DummyEnvironment


def main():

    environment = DummyEnvironment()
    agent = RandomAgent()

    while not environment.is_terminal():

        state = environment.get_state()
        actions = environment.get_actions()

        action = agent.act(
            state,
            actions
        )

        print(
            f"State: {state.value}, Action: {action.name}"
        )

        environment.execute_action(action)

    print(
        f"Final state: {environment.get_state().value}"
    )

    print(
        f"Reward: {environment.get_reward()}"
    )


if __name__ == "__main__":
    main()