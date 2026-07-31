class GameRunner:
    """
    Handles the execution loop between an agent and an environment.
    """

    def __init__(self, environment, agent):
        self.environment = environment
        self.agent = agent


    def run(self):

        self.environment.reset()

        while not self.environment.is_terminal():

            state = self.environment.get_state()
            actions = self.environment.get_actions()

            action = self.agent.act(
                state,
                actions
            )

            self.environment.execute_action(action)

        return self.environment.get_reward()