from framework.core.experience import Experience


class GameRunner:
    """
    Handles the execution loop between an agent and an environment.
    """

    def __init__(self, environment, agent):
        self.environment = environment
        self.agent = agent
        self.history = []


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

            next_state = self.environment.get_state()
            reward = self.environment.get_reward()

            experience = Experience(
                state,
                action,
                reward,
                next_state
            )

            self.history.append(experience)

        return self.environment.get_reward()

    def get_history(self):
        return self.history